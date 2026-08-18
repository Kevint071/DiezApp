import asyncio

import httpx

from diezapp.infrastructure.google.oauth_client import BackendOAuthClient


def test_refresh_access_token_uses_backend_response():
    def handler(request):
        assert request.url.path == "/api/auth/refresh"
        assert request.headers["content-type"] == "application/json"
        assert request.content == b'{"refresh_token":"refresh-token"}'
        return httpx.Response(
            200,
            json={"access_token": "access-token", "expires_in": 1800},
        )

    async def scenario():
        client = BackendOAuthClient(httpx.MockTransport(handler))
        return await client.refresh_access_token("refresh-token")

    result = asyncio.run(scenario())
    assert result == {"access_token": "access-token", "expires_in": 1800}
