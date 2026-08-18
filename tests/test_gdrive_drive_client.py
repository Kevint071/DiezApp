import asyncio

import httpx
import pytest

from diezapp.infrastructure.google import drive_client


def _use_transport(monkeypatch, transport):
    original_client = httpx.AsyncClient

    def build_client(*args, **kwargs):
        return original_client(*args, transport=transport, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", build_client)


def test_list_folders_uses_drive_transport(monkeypatch):
    def handler(request):
        assert request.headers["Authorization"] == "Bearer access-token"
        assert request.url.params["pageSize"] == "100"
        return httpx.Response(
            200,
            json={"files": [{"id": "folder-1", "name": "Backups"}]},
        )

    _use_transport(monkeypatch, httpx.MockTransport(handler))

    folders = asyncio.run(drive_client.list_folders("access-token"))

    assert folders == [{"id": "folder-1", "name": "Backups"}]


def test_drive_api_error_preserves_google_error_details(monkeypatch):
    def handler(request):
        return httpx.Response(
            403,
            json={
                "error": {
                    "status": "PERMISSION_DENIED",
                    "message": "Insufficient permissions",
                    "errors": [{"reason": "forbidden"}],
                }
            },
        )

    _use_transport(monkeypatch, httpx.MockTransport(handler))

    with pytest.raises(drive_client.DriveApiError) as error:
        asyncio.run(drive_client.create_folder("access-token", "Backups", "root"))

    assert error.value.status_code == 403
    assert error.value.reason == "forbidden"
    assert error.value.message == "Insufficient permissions"
