import httpx

from diezapp.features.google_drive.domain.models import DriveTokens

BACKEND_BASE_URL = "https://diezapp-api.vercel.app"
REFRESH_ENDPOINT = f"{BACKEND_BASE_URL}/api/auth/refresh"

# Must match the backend's APP_SHARED_SECRET when that defense is enabled.
BACKEND_SHARED_SECRET = ""


class BackendOAuthClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def refresh_access_token(self, refresh_token: str) -> DriveTokens | None:
        headers = (
            {"X-App-Secret": BACKEND_SHARED_SECRET} if BACKEND_SHARED_SECRET else {}
        )
        try:
            async with httpx.AsyncClient(
                timeout=20, transport=self._transport
            ) as client:
                response = await client.post(
                    REFRESH_ENDPOINT,
                    json={"refresh_token": refresh_token},
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as error:
            print(f"[DEBUG-AUTH] refresh_access_token failed: {error!r}")  # noqa: T201
            return None
