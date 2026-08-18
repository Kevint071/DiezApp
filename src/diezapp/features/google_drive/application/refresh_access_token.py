from datetime import timedelta

from diezapp.features.google_drive.domain.models import DriveAccount
from diezapp.features.google_drive.domain.repositories import DriveTokenRepository
from diezapp.shared.datetime_utils import local_now, parse_datetime, to_local_iso


class RefreshAccessToken:
    def __init__(self, oauth_client, token_repository: DriveTokenRepository):
        self._oauth_client = oauth_client
        self._token_repository = token_repository

    async def execute(self, account: DriveAccount) -> str | None:
        expiry = account.get("token_expiry_at")
        if expiry:
            try:
                expires_at = parse_datetime(expiry)
            except ValueError:
                expires_at = None
            if expires_at and local_now() < expires_at:
                return account["access_token"]

        refresh_token = account.get("refresh_token")
        if not refresh_token:
            return account.get("access_token")

        tokens = await self._oauth_client.refresh_access_token(refresh_token)
        if tokens is None:
            return None

        access_token = tokens["access_token"]
        expires_at = local_now() + timedelta(seconds=tokens.get("expires_in", 3600))
        self._token_repository.update(
            account["id"], access_token, to_local_iso(expires_at)
        )
        return access_token
