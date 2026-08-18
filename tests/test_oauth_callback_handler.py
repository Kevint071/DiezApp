import asyncio
from types import SimpleNamespace

from diezapp.navigation.oauth_callback_handler import OAuthCallbackHandler


class FakeStore:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)


class FakePage:
    def __init__(self):
        self.route = "/callback"
        self.url = ""
        self.web = True
        self.query = SimpleNamespace(to_dict={})
        self.session = SimpleNamespace(store=FakeStore())
        self.pushed_routes = []

    async def push_route(self, route):
        self.pushed_routes.append(route)

    def run_task(self, handler):
        return asyncio.create_task(handler())


class FakeOAuthFlow:
    def __init__(self):
        self.arguments = None

    def complete(self, store, query_params, is_web_runtime):
        self.arguments = (store, query_params, is_web_runtime)
        return {"ok": True, "message": "Cuenta user@example.com vinculada"}


def test_callback_completes_from_event_route_before_navigating():
    async def run_callback():
        page = FakePage()
        oauth_flow = FakeOAuthFlow()
        messages = []
        handler = OAuthCallbackHandler(page, oauth_flow, messages.append)

        handler.handle(
            SimpleNamespace(
                route="/callback?access_token=token&email=user%40example.com"
            )
        )
        await asyncio.sleep(0)

        task = page.session.store.get("gdrive_callback_route")
        assert task is None
        assert oauth_flow.arguments[1] == {
            "access_token": "token",
            "email": "user@example.com",
        }
        assert messages == ["Cuenta user@example.com vinculada"]
        assert page.pushed_routes == ["/google-drive"]

    asyncio.run(run_callback())
