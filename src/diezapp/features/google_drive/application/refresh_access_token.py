from datetime import UTC, datetime, timedelta

from diezapp.features.google_drive.domain.models import DriveAccount
from diezapp.features.google_drive.domain.repositories import DriveTokenRepository


class RefreshAccessToken:
    def __init__(self, oauth_client, token_repository: DriveTokenRepository):
        self._oauth_client = oauth_client
        self._token_repository = token_repository

    async def execute(self, account: DriveAccount) -> str | None:
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

        tokens = await self._oauth_client.refresh_access_token(refresh_token)
        if tokens is None:
            return None

        access_token = tokens["access_token"]
        expires_at = datetime.now(UTC) + timedelta(
            seconds=tokens.get("expires_in", 3600)
        )
        self._token_repository.update(
            account["id"], access_token, expires_at.isoformat()
        )
        return access_token
