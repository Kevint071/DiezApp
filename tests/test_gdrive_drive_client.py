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


def test_list_backup_files_returns_file_metadata(monkeypatch):
    def handler(request):
        assert request.url.params["q"] == (
            "'folder-1' in parents and trashed = false and "
            "mimeType != 'application/vnd.google-apps.folder'"
        )
        return httpx.Response(
            200,
            json={
                "files": [
                    {
                        "id": "file-1",
                        "name": "backup.db",
                        "size": "1234",
                        "modifiedTime": "2026-08-18T12:00:00Z",
                    }
                ]
            },
        )

    _use_transport(monkeypatch, httpx.MockTransport(handler))

    files = asyncio.run(drive_client.list_backup_files("access-token", "folder-1"))

    assert files[0]["id"] == "file-1"
    assert files[0]["name"] == "backup.db"


def test_delete_file_uses_file_endpoint(monkeypatch):
    def handler(request):
        assert request.method == "DELETE"
        assert str(request.url).endswith("/files/file-1")
        return httpx.Response(204)

    _use_transport(monkeypatch, httpx.MockTransport(handler))

    asyncio.run(drive_client.delete_file("access-token", "file-1"))


def test_download_file_writes_drive_response(monkeypatch, tmp_path):
    def handler(request):
        assert request.url.params["alt"] == "media"
        return httpx.Response(200, content=b"sqlite-backup")

    _use_transport(monkeypatch, httpx.MockTransport(handler))
    destination = tmp_path / "backup.db"

    asyncio.run(drive_client.download_file("access-token", "file-1", str(destination)))

    assert destination.read_bytes() == b"sqlite-backup"
