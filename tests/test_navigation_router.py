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

    def update(self):
        self.updated = True

    async def push_route(self, route):
        self.pushed_routes.append(route)


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
