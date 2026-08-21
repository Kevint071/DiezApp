import ssl

import httpx
import truststore

from diezapp.features.google_drive.domain.models import DriveTokens

BACKEND_BASE_URL = "https://diezapp-api.vercel.app"
REFRESH_ENDPOINT = f"{BACKEND_BASE_URL}/api/auth/refresh"

# Must match the backend's APP_SHARED_SECRET when that defense is enabled.
BACKEND_SHARED_SECRET = ""

# Windows' certifi-bundled CA store is often missing the local issuer chain,
# so use the OS trust store instead (same fix as drive_client.py).
OAUTH_SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


class BackendOAuthClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None):
        self._transport = transport

    async def refresh_access_token(self, refresh_token: str) -> DriveTokens | None:
        headers = (
            {"X-App-Secret": BACKEND_SHARED_SECRET} if BACKEND_SHARED_SECRET else {}
        )
        try:
            async with httpx.AsyncClient(
                timeout=20, transport=self._transport, verify=OAUTH_SSL_CONTEXT
            ) as client:
                response = await client.post(
                    REFRESH_ENDPOINT,
                    json={"refresh_token": refresh_token},
                    headers=headers,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            return None
