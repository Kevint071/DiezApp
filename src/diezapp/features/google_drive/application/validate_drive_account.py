from typing import Literal, TypedDict

from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderError,
    DriveFolderService,
)

DRIVE_FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"


class DriveAccountValidation(TypedDict):
    status: Literal[
        "valid",
        "no_folder",
        "unauthenticated",
        "access_unavailable",
        "folder_unavailable",
    ]
    folder_name: str | None


class ValidateDriveAccount:
    def __init__(self, folder_service: DriveFolderService):
        self._folder_service = folder_service

    async def execute(
        self,
        access_token: str,
        expected_email: str,
        folder_id: str | None,
    ) -> DriveAccountValidation:
        try:
            authenticated_email = await self._folder_service.check_access(access_token)
        except DriveFolderError as error:
            if error.status_code not in (401, 403):
                return {"status": "access_unavailable", "folder_name": None}
            return {"status": "unauthenticated", "folder_name": None}
        if authenticated_email.casefold() != expected_email.casefold():
            return {"status": "unauthenticated", "folder_name": None}
        if not folder_id:
            return {"status": "no_folder", "folder_name": None}
        try:
            folder = await self._folder_service.get(access_token, folder_id)
        except DriveFolderError as error:
            if error.status_code == 404:
                return {"status": "no_folder", "folder_name": None}
            return {"status": "folder_unavailable", "folder_name": None}
        if (
            folder.get("trashed")
            or folder.get("mimeType") != DRIVE_FOLDER_MIME_TYPE
            or not folder.get("name")
        ):
            return {"status": "no_folder", "folder_name": None}
        return {"status": "valid", "folder_name": folder.get("name")}
