from diezapp.features.google_drive.domain.models import DriveAccount
from diezapp.features.google_drive.domain.repositories import DriveAccountRepository
from diezapp.shared.datetime_utils import local_now, parse_datetime


class RefreshAccessToken:
    def __init__(self, oauth_client, account_repository: DriveAccountRepository):
        self._oauth_client = oauth_client
        self._account_repository = account_repository

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
        self._account_repository.update_tokens(
            account["id"], access_token, refresh_token, tokens.get("expires_in", 3600)
        )
        return access_token
