"""Google OAuth2 (Authorization Code + PKCE) for linking up to 2 Drive accounts.

Flet's built-in `page.login()`/`GoogleOAuthProvider` assumes a reachable HTTP
redirect target and a mandatory `client_secret` — not a fit for a serverless
packaged mobile app (see design.md, Decision 1). This module instead talks
directly to Google's OAuth endpoints using the Authorization Code + PKCE flow
with a custom-scheme redirect, relying on Flet's built-in
`[tool.flet.<platform>.deep_linking]` mechanism (configured in
``pyproject.toml``) to route the incoming redirect back into the app as a
normal ``page.route`` change (see main.py's handling of the "/callback" route).

Client IDs are read from environment variables rather than hardcoded, since
they are only known once the user creates OAuth Client IDs of type "Android"
and "iOS" in Google Cloud Console (see tasks.md 1.1 — this step must be done
manually; it cannot be automated here). The matching custom-scheme
``deep_linking`` entries must be filled in ``pyproject.toml`` with the exact
same client IDs before building for a device.
"""

import base64
import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import flet as ft
import httpx

from utils.db import get_connection

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPE = "https://www.googleapis.com/auth/drive.file openid email"

# Redirect host/path must match the `host`/path used in the
# `[tool.flet.android.deep_linking]` / `[tool.flet.ios.deep_linking]` entries
# in pyproject.toml. The scheme itself is per-platform (each OAuth client
# type gets its own reversed-domain scheme), so the redirect_uri is built
# per-platform below.
REDIRECT_HOST = "oauth2redirect"
REDIRECT_PATH = "/callback"

MAX_ACCOUNTS = 2
ANDROID_CLIENT_ID = (
    "105025843954-9p82u5mujmfakqmt4t52bt8pb9ntak4o.apps.googleusercontent.com"
)

_CLIENT_IDS = {
    ft.PagePlatform.ANDROID: ANDROID_CLIENT_ID,
    ft.PagePlatform.IOS: "",
}


def _client_id_for(page: ft.Page) -> str | None:
    platform = page.platform
    if isinstance(platform, str):
        platform = next(
            (item for item in ft.PagePlatform if item.value == platform.lower()),
            platform,
        )
    client_id = _CLIENT_IDS.get(platform)
    if client_id:
        return client_id
    # Plain `flet run` uses the desktop platform. Reuse the public Android
    # client ID for local UI testing; the native redirect still requires an
    # Android build (`flet run --android` or `flet build apk`).
    if platform != ft.PagePlatform.IOS:
        return _CLIENT_IDS.get(ft.PagePlatform.ANDROID) or None
    return None


def _scheme_for_client_id(client_id: str) -> str:
    # Google's convention for "Android"/"iOS" (installed app) OAuth client
    # types: the reversed-domain form of the client ID, e.g.
    # "123-abc.apps.googleusercontent.com" -> "com.googleusercontent.apps.123-abc".
    prefix = client_id.split(".apps.googleusercontent.com")[0]
    return f"com.googleusercontent.apps.{prefix}"


def is_configured(page: ft.Page) -> bool:
    """Whether an OAuth Client ID is configured for the current platform."""
    return _client_id_for(page) is not None


def redirect_uri_for(page: ft.Page) -> str:
    client_id = _client_id_for(page)
    scheme = _scheme_for_client_id(client_id)
    return f"{scheme}://{REDIRECT_HOST}{REDIRECT_PATH}"


def _generate_pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


async def start_link_flow(page: ft.Page) -> bool:
    """Open the Google consent screen for linking a new account.

    Returns False (without opening anything) if the 2-account limit is
    already reached or no OAuth Client ID is configured for this platform.
    """
    if not is_configured(page):
        return False
    if not can_add_account():
        return False

    client_id = _client_id_for(page)
    verifier, challenge = _generate_pkce_pair()
    state = uuid.uuid4().hex
    page.session.store.set(
        "gdrive_oauth_pending", {"verifier": verifier, "state": state}
    )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri_for(page),
        "response_type": "code",
        "scope": SCOPE,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state,
        "prompt": "select_account consent",
        "access_type": "offline",
    }
    url = f"{AUTH_ENDPOINT}?{urlencode(params)}"
    await ft.UrlLauncher().launch_url(url)
    return True


async def complete_link_flow(page: ft.Page, query_params: dict) -> dict:
    """Handle the redirect back from Google (called from the "/callback" route).

    Returns a dict: {"ok": bool, "message": str}.
    """
    pending = page.session.store.get("gdrive_oauth_pending")
    page.session.store.remove("gdrive_oauth_pending")

    error = query_params.get("error")
    if error:
        return {"ok": False, "message": "Vinculación cancelada"}

    code = query_params.get("code")
    returned_state = query_params.get("state")
    if not pending or not code or returned_state != pending.get("state"):
        return {"ok": False, "message": "No se pudo completar la vinculación"}

    client_id = _client_id_for(page)
    if not client_id:
        return {"ok": False, "message": "OAuth de Google no configurado"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_resp = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "client_id": client_id,
                    "code": code,
                    "code_verifier": pending["verifier"],
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri_for(page),
                },
            )
            token_resp.raise_for_status()
            tokens = token_resp.json()

            userinfo_resp = await client.get(
                USERINFO_ENDPOINT,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )
            userinfo_resp.raise_for_status()
            email = userinfo_resp.json().get("email", "")
    except httpx.HTTPError:
        return {"ok": False, "message": "Error de red al vincular la cuenta"}

    try:
        add_account(
            email=email,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", ""),
            expires_in=tokens.get("expires_in", 3600),
        )
    except ValueError as e:
        return {"ok": False, "message": str(e)}

    return {"ok": True, "message": f"Cuenta {email} vinculada"}


async def ensure_fresh_access_token(page: ft.Page, account: dict) -> str | None:
    """Return a valid access token for `account`, refreshing it if expired.

    Refresh tokens are issued per Client ID, and the account was linked while
    running on `page.platform`'s client — so refreshing must reuse the same
    platform's client_id, not any other configured one.
    """
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

    client_id = _client_id_for(page)
    if not client_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                TOKEN_ENDPOINT,
                data={
                    "client_id": client_id,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
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
