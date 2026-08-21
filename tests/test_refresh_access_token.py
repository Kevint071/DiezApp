import asyncio
from datetime import UTC, datetime, timedelta

from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)


class FakeOAuthClient:
    def __init__(self, tokens=None):
        self.tokens = tokens
        self.refresh_tokens = []

    async def refresh_access_token(self, refresh_token):
        self.refresh_tokens.append(refresh_token)
        return self.tokens


class FakeAccountRepository:
    def __init__(self):
        self.updates = []

    def update_tokens(self, account_id, access_token, refresh_token, expires_in):
        self.updates.append((account_id, access_token, refresh_token, expires_in))


def _account(expiry, refresh_token="refresh"):
    return {
        "id": "account-1",
        "google_account_email": "user@example.com",
        "display_label": "user@example.com",
        "folder_id": "folder-1",
        "folder_name": "Backups",
        "access_token": "current",
        "refresh_token": refresh_token,
        "token_expiry_at": expiry,
        "created_at": datetime.now(UTC).isoformat(),
    }


def test_refresh_access_token_returns_current_token_when_still_valid():
    oauth_client = FakeOAuthClient()
    token_repository = FakeAccountRepository()
    service = RefreshAccessToken(oauth_client, token_repository)

    result = asyncio.run(
        service.execute(
            _account((datetime.now(UTC) + timedelta(minutes=5)).isoformat())
        )
    )

    assert result == "current"
    assert oauth_client.refresh_tokens == []
    assert token_repository.updates == []


def test_refresh_access_token_persists_a_new_token():
    oauth_client = FakeOAuthClient({"access_token": "new", "expires_in": 3600})
    token_repository = FakeAccountRepository()
    service = RefreshAccessToken(oauth_client, token_repository)

    result = asyncio.run(service.execute(_account("2020-01-01T00:00:00+00:00")))

    assert result == "new"
    assert oauth_client.refresh_tokens == ["refresh"]
    assert token_repository.updates[0] == ("account-1", "new", "refresh", 3600)


def test_refresh_access_token_returns_none_when_refresh_fails():
    oauth_client = FakeOAuthClient(None)
    token_repository = FakeAccountRepository()
    service = RefreshAccessToken(oauth_client, token_repository)

    result = asyncio.run(service.execute(_account("invalid-date")))

    assert result is None
    assert token_repository.updates == []
