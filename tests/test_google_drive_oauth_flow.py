import asyncio

from diezapp.features.google_drive.application.link_account import LinkAccountService
from diezapp.features.google_drive.application.oauth_flow import GoogleDriveOAuthFlow


class FakeStore:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)


class FakeRepository:
    def __init__(self, count=0):
        self.count_value = count
        self.accounts = []

    def count(self):
        return self.count_value

    def list(self):
        return self.accounts

    def add(self, email, access_token, refresh_token, expires_in):
        self.accounts.append({"id": "new", "google_account_email": email})
        return "new"

    def update_tokens(self, account_id, access_token, refresh_token, expires_in):
        self.updated = (account_id, access_token, refresh_token, expires_in)


class FakeUrlOpener:
    def __init__(self):
        self.urls = []

    async def open_url(self, url):
        self.urls.append(url)


def _flow(repository=None):
    repository = repository or FakeRepository()
    opener = FakeUrlOpener()
    return (
        GoogleDriveOAuthFlow(
            LinkAccountService(repository), opener, "https://api.test/login"
        ),
        opener,
        repository,
    )


def test_oauth_flow_start_stores_state_and_opens_login_url():
    flow, opener, _ = _flow()
    store = FakeStore()

    assert asyncio.run(flow.start(store, "wss://app.test/settings"))

    assert store.get("gdrive_oauth_pending")["state"]
    assert "app_state=" in opener.urls[0]
    assert "web_return_url=https%3A%2F%2Fapp.test%2Fcallback" in opener.urls[0]


def test_oauth_flow_start_rejects_account_limit():
    flow, opener, _ = _flow(FakeRepository(count=2))

    assert not asyncio.run(flow.start(FakeStore()))
    assert opener.urls == []


def test_oauth_flow_start_allows_reauthentication_at_account_limit():
    flow, opener, _ = _flow(FakeRepository(count=2))

    assert asyncio.run(flow.start(FakeStore(), account_id="account-1"))
    assert "account_id=account-1" in opener.urls[0]


def test_oauth_flow_complete_updates_existing_account_tokens():
    repository = FakeRepository(count=2)
    flow, _, repository = _flow(repository)
    store = FakeStore()
    store.set("gdrive_oauth_pending", {"state": "state-1", "account_id": "account-1"})

    result = flow.complete(
        store,
        {
            "app_state": "state-1",
            "access_token": "new-token",
            "refresh_token": "new-refresh-token",
            "email": "user@example.com",
            "expires_in": "7200",
        },
        False,
    )

    assert result["ok"]
    assert repository.updated == (
        "account-1",
        "new-token",
        "new-refresh-token",
        7200,
    )


def test_oauth_flow_complete_consumes_pending_state():
    flow, _, repository = _flow()
    store = FakeStore()
    store.set("gdrive_oauth_pending", {"state": "state-1"})

    result = flow.complete(
        store,
        {
            "app_state": "state-1",
            "access_token": "token",
            "email": "user@example.com",
        },
        False,
    )

    assert result["ok"]
    assert store.get("gdrive_oauth_pending") is None
    assert store.get("gdrive_callback_done") is True
    assert repository.accounts[0]["google_account_email"] == "user@example.com"


def test_oauth_flow_complete_rejects_repeated_callback():
    flow, _, _ = _flow()
    store = FakeStore()
    store.set("gdrive_callback_done", True)

    result = flow.complete(store, {}, False)

    assert result == {"ok": False, "message": "La vinculación ya fue procesada"}
