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
from diezapp.features.google_drive.application.link_account import LinkAccountService
from diezapp.features.google_drive.application.start_link import build_login_url
from diezapp.infrastructure.google.oauth_client import BackendOAuthClient
from diezapp.infrastructure.persistence.sqlite_drive_account_repository import (
    SqliteDriveAccountRepository,
)
from diezapp.infrastructure.persistence.sqlite_drive_token_repository import (
    SqliteDriveTokenRepository,
)

# Base URL of the deployed diezmapp-api backend. Not a secret: it only ever
# forwards data the user's own browser already has (see design.md).
BACKEND_BASE_URL = "https://diezapp-api.vercel.app"
LOGIN_ENDPOINT = f"{BACKEND_BASE_URL}/api/auth/login"

MAX_ACCOUNTS = 2
_account_repository = SqliteDriveAccountRepository()
_token_repository = SqliteDriveTokenRepository()
_oauth_client = BackendOAuthClient()
_link_account_service = LinkAccountService(_account_repository, MAX_ACCOUNTS)


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
    if page.session.store.get("gdrive_callback_done"):
        page.session.store.remove("gdrive_callback_done")

    url = build_login_url(LOGIN_ENDPOINT, app_state, page.url)
    await ft.UrlLauncher().launch_url(url)
    return True


async def complete_link_flow(
    page: ft.Page,
    query_params: dict,
    link_account_service: LinkAccountService | None = None,
) -> dict:
    """Handle the deep-link redirect back from the backend proxy (called
    from the "/callback" route).

    Returns a dict: {"ok": bool, "message": str}.
    """
    pending = page.session.store.get("gdrive_oauth_pending")
    pending_state = pending.get("state") if pending else None
    is_web_runtime = page.web or (page.url or "").startswith(("ws://", "wss://"))
    service = link_account_service or _link_account_service
    result = service.complete_link(
        query_params,
        pending_state,
        is_web_runtime,
        callback_done=page.session.store.get("gdrive_callback_done", False),
    )
    if not result["ok"]:
        if pending and result["message"] in (
            "No se pudo completar la vinculación",
            "Vinculación cancelada",
        ):
            page.session.store.remove("gdrive_oauth_pending")
        return result

    if pending:
        page.session.store.remove("gdrive_oauth_pending")
    page.session.store.set("gdrive_callback_done", True)
    return result


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

    tokens = await _oauth_client.refresh_access_token(refresh_token)
    if tokens is None:
        return None

    new_access_token = tokens["access_token"]
    new_expiry = datetime.now(UTC) + timedelta(seconds=tokens.get("expires_in", 3600))
    _token_repository.update(account["id"], new_access_token, new_expiry.isoformat())
    return new_access_token


def list_accounts() -> list[dict]:
    return _account_repository.list()


def count_accounts() -> int:
    return _account_repository.count()


def can_add_account() -> bool:
    return _link_account_service.can_add_account()


def add_account(
    email: str, access_token: str, refresh_token: str, expires_in: int
) -> str:
    return _link_account_service.add_account(
        email=email,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


def remove_account(account_id: str):
    _account_repository.remove(account_id)


def set_account_folder(account_id: str, folder_id: str, folder_name: str):
    _account_repository.set_folder(account_id, folder_id, folder_name)
