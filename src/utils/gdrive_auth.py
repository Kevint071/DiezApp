"""Google OAuth2 login for linking up to 2 Drive accounts, proxied through the
diezmapp-api Next.js backend (see ../../../diezmapp-api/src/app/api/auth).

Google no longer accepts a custom-scheme `redirect_uri` (e.g.
`oauth2redirect://...`) for the Authorization Code flow — the authorization
server rejects it outright with `Error 400: invalid_request`. Only a real
`https://` redirect_uri is accepted now (see README-setup-android-oauth.md
for the history of what was tried before this).

This module therefore never talks to Google directly. Instead:
1. `start_link_flow` opens the system browser at the backend's
   `/api/auth/login`, passing an `app_state` nonce it generated.
2. The backend runs the full Authorization Code + PKCE exchange against
   Google using its own `https://` redirect_uri and a confidential "Web
   application" OAuth client (client_secret lives only on the server).
3. The backend redirects back into this app via a custom-scheme deep link
   (Android/iOS allow this because it's *our own server* redirecting, not
   Google), landing on the "/callback" route (see main.py) with the tokens
   and the original `app_state` as query params.
4. Refreshing an expired access_token also requires client_secret, so
   `ensure_fresh_access_token` posts to the backend's `/api/auth/refresh`
   instead of calling Google directly.
"""

import uuid
from datetime import UTC, datetime, timedelta

import flet as ft
import httpx

from utils.db import get_connection

# Base URL of the deployed diezmapp-api backend. Not a secret: it only ever
# forwards data the user's own browser already has (see design.md).
BACKEND_BASE_URL = "https://diezapp-api.vercel.app"
LOGIN_ENDPOINT = f"{BACKEND_BASE_URL}/api/auth/login"
REFRESH_ENDPOINT = f"{BACKEND_BASE_URL}/api/auth/refresh"

# Must match the backend's APP_SHARED_SECRET env var (defense in depth for
# /api/auth/refresh; leave empty if the backend doesn't set one either).
BACKEND_SHARED_SECRET = ""

MAX_ACCOUNTS = 2


def is_configured(page: ft.Page) -> bool:
    """Whether the backend proxy URL is configured."""
    return bool(BACKEND_BASE_URL)


async def start_link_flow(page: ft.Page) -> bool:
    """Open the backend's login endpoint to start linking a new account.

    Returns False (without opening anything) if the 2-account limit is
    already reached or the backend proxy isn't configured.
    """
    if not is_configured(page):
        return False
    if not can_add_account():
        return False

    app_state = uuid.uuid4().hex
    page.session.store.set("gdrive_oauth_pending", {"state": app_state})

    url = f"{LOGIN_ENDPOINT}?app_state={app_state}"
    await ft.UrlLauncher().launch_url(url)
    return True


async def complete_link_flow(page: ft.Page, query_params: dict) -> dict:
    """Handle the deep-link redirect back from the backend proxy (called
    from the "/callback" route).

    Returns a dict: {"ok": bool, "message": str}.
    """
    pending = page.session.store.get("gdrive_oauth_pending")
    page.session.store.remove("gdrive_oauth_pending")

    returned_state = query_params.get("app_state")
    if not pending or returned_state != pending.get("state"):
        return {"ok": False, "message": "No se pudo completar la vinculación"}

    if query_params.get("error"):
        return {"ok": False, "message": "Vinculación cancelada"}

    access_token = query_params.get("access_token")
    email = query_params.get("email")
    if not access_token or not email:
        return {"ok": False, "message": "No se pudo completar la vinculación"}

    try:
        expires_in = int(query_params.get("expires_in", 3600))
    except ValueError:
        expires_in = 3600

    try:
        add_account(
            email=email,
            access_token=access_token,
            refresh_token=query_params.get("refresh_token", ""),
            expires_in=expires_in,
        )
    except ValueError as e:
        return {"ok": False, "message": str(e)}

    return {"ok": True, "message": f"Cuenta {email} vinculada"}


async def ensure_fresh_access_token(page: ft.Page, account: dict) -> str | None:
    """Return a valid access token for `account`, refreshing it via the
    backend proxy if expired (refreshing requires client_secret, which only
    the backend holds)."""
    expiry = account.get("token_expiry_at")
    if expiry:
        try:
            expires_at = datetime.fromisoformat(expiry)
        except ValueError:
            expires_at = None
        if expires_at and datetime.now(UTC) < expires_at:
            return account["access_token"]

    refresh_token = account.get("refresh_token")
    if not refresh_token:
        return account.get("access_token")

    headers = {"X-App-Secret": BACKEND_SHARED_SECRET} if BACKEND_SHARED_SECRET else {}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                REFRESH_ENDPOINT,
                json={"refresh_token": refresh_token},
                headers=headers,
            )
            resp.raise_for_status()
            tokens = resp.json()
    except httpx.HTTPError:
        return None

    new_access_token = tokens["access_token"]
    new_expiry = datetime.now(UTC) + timedelta(seconds=tokens.get("expires_in", 3600))
    _update_account_token(account["id"], new_access_token, new_expiry.isoformat())
    return new_access_token


# ── Data-access layer (gdrive_accounts) ──────────────────────────────


def list_accounts() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, google_account_email, display_label, folder_id, folder_name, "
        "access_token, refresh_token, token_expiry_at, created_at "
        "FROM gdrive_accounts ORDER BY created_at"
    ).fetchall()
    cols = [
        "id",
        "google_account_email",
        "display_label",
        "folder_id",
        "folder_name",
        "access_token",
        "refresh_token",
        "token_expiry_at",
        "created_at",
    ]
    return [dict(zip(cols, row, strict=True)) for row in rows]


def count_accounts() -> int:
    conn = get_connection()
    return conn.execute("SELECT COUNT(*) FROM gdrive_accounts").fetchone()[0]


def can_add_account() -> bool:
    return count_accounts() < MAX_ACCOUNTS


def add_account(
    email: str, access_token: str, refresh_token: str, expires_in: int
) -> str:
    if not can_add_account():
        raise ValueError(f"Ya hay {MAX_ACCOUNTS} cuentas vinculadas")

    account_id = uuid.uuid4().hex
    now = datetime.now(UTC)
    expiry = now + timedelta(seconds=expires_in)
    conn = get_connection()
    conn.execute(
        "INSERT INTO gdrive_accounts "
        "(id, google_account_email, display_label, folder_id, folder_name, "
        "access_token, refresh_token, token_expiry_at, created_at) "
        "VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?)",
        (
            account_id,
            email,
            email,
            access_token,
            refresh_token,
            expiry.isoformat(),
            now.isoformat(),
        ),
    )
    conn.commit()
    return account_id


def remove_account(account_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM gdrive_accounts WHERE id = ?", (account_id,))
    conn.commit()


def set_account_folder(account_id: str, folder_id: str, folder_name: str):
    conn = get_connection()
    conn.execute(
        "UPDATE gdrive_accounts SET folder_id = ?, folder_name = ? WHERE id = ?",
        (folder_id, folder_name, account_id),
    )
    conn.commit()


def _update_account_token(account_id: str, access_token: str, expiry_iso: str):
    conn = get_connection()
    conn.execute(
        "UPDATE gdrive_accounts SET access_token = ?, token_expiry_at = ? WHERE id = ?",
        (access_token, expiry_iso, account_id),
    )
    conn.commit()


