import asyncio

from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderError,
)
from diezapp.features.google_drive.application.validate_drive_account import (
    ValidateDriveAccount,
)


class FolderClientFake:
    def __init__(self, email="account@example.com", folder=None, error=None):
        self.email = email
        self.folder = folder
        self.error = error
        self.get_calls = []

    async def check_access(self, access_token):
        del access_token
        return self.email

    async def get(self, access_token, folder_id):
        del access_token
        self.get_calls.append(folder_id)
        if self.error:
            raise self.error
        return self.folder


def test_validate_account_accepts_existing_folder():
    client = FolderClientFake(
        folder={
            "id": "folder-1",
            "name": "Backups",
            "mimeType": "application/vnd.google-apps.folder",
            "trashed": False,
        }
    )

    result = asyncio.run(
        ValidateDriveAccount(client).execute("token", "ACCOUNT@example.com", "folder-1")
    )

    assert result == {"status": "valid", "folder_name": "Backups"}
    assert client.get_calls == ["folder-1"]


def test_validate_account_clears_missing_folder():
    client = FolderClientFake(
        error=DriveFolderError("Not found", status_code=404, reason="notFound")
    )

    result = asyncio.run(
        ValidateDriveAccount(client).execute("token", "account@example.com", "folder-1")
    )

    assert result == {"status": "no_folder", "folder_name": None}


def test_validate_account_keeps_folder_on_temporary_drive_error():
    client = FolderClientFake(
        error=DriveFolderError("Forbidden", status_code=403, reason="forbidden")
    )

    result = asyncio.run(
        ValidateDriveAccount(client).execute("token", "account@example.com", "folder-1")
    )

    assert result == {"status": "folder_unavailable", "folder_name": None}


def test_validate_account_checks_identity_before_folder():
    client = FolderClientFake(email="other@example.com")

    result = asyncio.run(
        ValidateDriveAccount(client).execute("token", "account@example.com", "folder-1")
    )

    assert result == {"status": "unauthenticated", "folder_name": None}
    assert client.get_calls == []


def test_validate_account_reports_temporary_access_error():
    client = FolderClientFake(
        error=DriveFolderError("Server error", status_code=500, reason="backendError")
    )

    class AccessErrorClient(FolderClientFake):
        async def check_access(self, access_token):
            del access_token
            raise self.error

    client = AccessErrorClient(error=client.error)

    result = asyncio.run(
        ValidateDriveAccount(client).execute("token", "account@example.com", "folder-1")
    )

    assert result == {"status": "access_unavailable", "folder_name": None}


def test_validate_account_without_folder_only_checks_identity():
    client = FolderClientFake()

    result = asyncio.run(
        ValidateDriveAccount(client).execute("token", "account@example.com", None)
    )

    assert result == {"status": "no_folder", "folder_name": None}
    assert client.get_calls == []
