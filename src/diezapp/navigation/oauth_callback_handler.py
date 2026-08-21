from collections.abc import Callable
from urllib.parse import parse_qsl, urlparse

import flet as ft

from diezapp.features.google_drive.application.oauth_flow import GoogleDriveOAuthFlow
from diezapp.navigation import routes


class OAuthCallbackHandler:
    def __init__(
        self,
        page: ft.Page,
        oauth_flow: GoogleDriveOAuthFlow,
        on_completed: Callable[[str], None],
    ):
        self.page = page
        self.oauth_flow = oauth_flow
        self.on_completed = on_completed
        self.processing = False

    def handle(self, event: ft.RouteChangeEvent | None = None) -> None:
        callback_route = getattr(event, "route", None) if event is not None else None
        if not callback_route and "?" in self.page.route:
            callback_route = self.page.route
        if callback_route:
            self.page.session.store.set("gdrive_callback_route", callback_route)
        if not self.processing:
            self.page.run_task(self.complete)

    async def complete(self) -> None:
        if self.processing:
            return
        self.processing = True
        callback_route = self.page.session.store.get("gdrive_callback_route")
        if callback_route:
            self.page.session.store.remove("gdrive_callback_route")
        try:
            query_params = dict(self.page.query.to_dict)
            if callback_route:
                query_params = dict(parse_qsl(urlparse(callback_route).query))
            result = self.oauth_flow.complete(
                self.page.session.store,
                query_params,
                self.page.web or (self.page.url or "").startswith(("ws://", "wss://")),
            )
            self.on_completed(result["message"])
            await self.page.push_route(routes.GOOGLE_DRIVE)
        finally:
            self.processing = False
