from collections.abc import Callable, Sequence

import flet as ft

from diezapp.navigation import routes
from diezapp.navigation.navigation_state import NavigationState

RootBuilder = Callable[[str], tuple[int, ft.View]]
NestedBuilder = Callable[[str], list[ft.View]]
CallbackHandler = Callable[[ft.ControlEvent | None], None]
NavigationGuard = Callable[[Callable[[], None], Callable[[], None]], None]


class AppRouter:
    """Own the Flet route stack while delegating view construction."""

    def __init__(
        self,
        page: ft.Page,
        navigation_bar: ft.NavigationBar,
        build_root: RootBuilder,
        build_nested: NestedBuilder,
        on_callback: CallbackHandler,
        navigation_state: NavigationState | None = None,
        navigation_guard: NavigationGuard | None = None,
    ):
        self.page = page
        self.navigation_bar = navigation_bar
        self.build_root = build_root
        self.build_nested = build_nested
        self.on_callback = on_callback
        self.navigation_state = navigation_state or NavigationState()
        self.navigation_guard = navigation_guard

    def handle_navigation_change(
        self, event: ft.ControlEvent, root_routes: Sequence[str]
    ) -> None:
        index = event.control.selected_index
        previous_index = self.navigation_state.selected_index

        def navigate() -> None:
            self.navigation_state.select(index)
            self.page.navigate(root_routes[index])

        def cancel() -> None:
            self.navigation_bar.selected_index = previous_index
            self.page.update()

        if self.navigation_guard:
            self.navigation_guard(navigate, cancel)
        else:
            navigate()

    def handle_route_change(self, event: ft.RouteChangeEvent | None = None):
        route = self.page.route
        if route.startswith(routes.CALLBACK_PREFIX):
            self.on_callback(event)
            return

        root_index, root_view = self.build_root(route)
        self.navigation_bar.selected_index = root_index
        self.navigation_state.select(root_index)
        self.page.views = [root_view, *self.build_nested(route)]
        self.page.update()

    async def handle_view_pop(self, event: ft.ViewPopEvent):
        if event.view is not None and event.view in self.page.views:
            self.page.views.remove(event.view)
        if self.page.views:
            await self.page.push_route(self.page.views[-1].route)
