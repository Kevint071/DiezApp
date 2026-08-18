import asyncio
from types import SimpleNamespace

from diezapp.navigation.navigation_state import NavigationState
from diezapp.navigation.router import AppRouter


class FakePage:
    def __init__(self, route):
        self.route = route
        self.views = []
        self.updated = False
        self.pushed_routes = []
        self.navigated_routes = []

    def update(self):
        self.updated = True

    async def push_route(self, route):
        self.pushed_routes.append(route)

    def navigate(self, route):
        self.navigated_routes.append(route)


class FakeNavigationBar:
    selected_index = 0


def create_router(page, root_builder, nested_builder, state=None):
    return AppRouter(
        page,
        FakeNavigationBar(),
        root_builder,
        nested_builder,
        lambda _event: None,
        state,
    )


def test_route_change_builds_root_and_nested_views():
    page = FakePage("/detail")
    root = SimpleNamespace(route="/")
    nested = SimpleNamespace(route="/detail")
    state = NavigationState()
    router = create_router(
        page,
        lambda route: (1, root),
        lambda route: [nested],
        state,
    )

    router.handle_route_change()

    assert page.views == [root, nested]
    assert router.navigation_bar.selected_index == 1
    assert state.selected_index == 1
    assert page.updated is True


def test_view_pop_pushes_previous_route():
    page = FakePage("/detail")
    root = SimpleNamespace(route="/")
    detail = SimpleNamespace(route="/detail")
    router = create_router(page, lambda route: (0, root), lambda route: [])
    page.views = [root, detail]

    asyncio.run(router.handle_view_pop(SimpleNamespace(view=detail)))

    assert page.views == [root]
    assert page.pushed_routes == ["/"]


def test_nested_route_preserves_root_view_and_builds_nested_stack():
    page = FakePage("/monthly/breakdown")
    root = SimpleNamespace(route="/monthly")
    monthly = SimpleNamespace(route="/monthly")
    breakdown = SimpleNamespace(route="/monthly/breakdown")
    router = create_router(
        page,
        lambda route: (0, root),
        lambda route: [monthly, breakdown],
    )

    router.handle_route_change()

    assert page.views == [root, monthly, breakdown]
    assert page.views[0].route == "/monthly"


def test_navigation_change_updates_state_and_route():
    page = FakePage("/")
    state = NavigationState()
    router = create_router(page, lambda route: (0, None), lambda route: [], state)
    event = SimpleNamespace(control=SimpleNamespace(selected_index=2))

    router.handle_navigation_change(event, ("/", "/saved", "/pdf-export"))

    assert state.selected_index == 2
    assert page.navigated_routes == ["/pdf-export"]


def test_navigation_change_cancel_restores_previous_selection():
    page = FakePage("/")
    navigation_bar = FakeNavigationBar()
    state = NavigationState(selected_index=1)
    router = AppRouter(
        page,
        navigation_bar,
        lambda route: (0, None),
        lambda route: [],
        lambda _event: None,
        state,
        lambda _proceed, cancel: cancel(),
    )
    event = SimpleNamespace(control=SimpleNamespace(selected_index=3))

    router.handle_navigation_change(event, ("/", "/saved", "/pdf-export", "/notes"))

    assert state.selected_index == 1
    assert navigation_bar.selected_index == 1
    assert page.navigated_routes == []
    assert page.updated is True
