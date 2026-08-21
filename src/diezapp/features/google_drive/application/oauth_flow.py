import uuid
from typing import Protocol

from diezapp.features.google_drive.application.link_account import LinkAccountService
from diezapp.features.google_drive.application.start_link import build_login_url
from diezapp.features.google_drive.application.url_opener import UrlOpener

BACKEND_BASE_URL = "https://diezapp-api.vercel.app"
LOGIN_ENDPOINT = f"{BACKEND_BASE_URL}/api/auth/login"


class SessionStore(Protocol):
    def get(self, key: str): ...

    def set(self, key: str, value) -> None: ...

    def remove(self, key: str) -> None: ...


def _account_id_from_state(state: str | None) -> str | None:
    """Recover the account_id embedded in app_state.

    Re-auth opens the Google consent screen in a new browser tab, which in
    web runtime gets its own page session, so `gdrive_oauth_pending` set
    before the redirect is not visible when the callback lands. Embedding
    the account_id in app_state lets it survive that round trip regardless
    of session continuity.
    """
    if not state or "." not in state:
        return None
    return state.split(".", 1)[1] or None


class GoogleDriveOAuthFlow:
    def __init__(
        self,
        link_account_service: LinkAccountService,
        url_opener: UrlOpener,
        login_endpoint: str = LOGIN_ENDPOINT,
    ):
        self._link_account_service = link_account_service
        self._url_opener = url_opener
        self._login_endpoint = login_endpoint

    def is_configured(self) -> bool:
        return bool(self._login_endpoint)

    async def start(
        self,
        store: SessionStore,
        page_url: str | None = None,
        account_id: str | None = None,
    ) -> bool:
        if not self.is_configured() or (
            not account_id and not self._link_account_service.can_add_account()
        ):
            return False

        app_state = uuid.uuid4().hex
        if account_id:
            app_state = f"{app_state}.{account_id}"
        store.set(
            "gdrive_oauth_pending", {"state": app_state, "account_id": account_id}
        )
        if store.get("gdrive_callback_done"):
            store.remove("gdrive_callback_done")

        url = build_login_url(self._login_endpoint, app_state, page_url, account_id)
        await self._url_opener.open_url(url)
        return True

    def complete(
        self,
        store: SessionStore,
        query_params: dict,
        is_web_runtime: bool,
    ) -> dict:
        pending = store.get("gdrive_oauth_pending")
        pending_state = pending.get("state") if pending else None
        account_id = _account_id_from_state(query_params.get("app_state")) or (
            pending.get("account_id") if pending else None
        )
        result = self._link_account_service.complete_link(
            query_params,
            pending_state,
            is_web_runtime,
            callback_done=bool(store.get("gdrive_callback_done")),
            account_id=account_id,
        )
        if not result["ok"]:
            if pending and result["message"] in (
                "No se pudo completar la vinculación",
                "Vinculación cancelada",
            ):
                store.remove("gdrive_oauth_pending")
            return result

        if pending:
            store.remove("gdrive_oauth_pending")
        store.set("gdrive_callback_done", True)
        return result
