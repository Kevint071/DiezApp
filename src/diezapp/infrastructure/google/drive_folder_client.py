import httpx

from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderError,
)
from diezapp.infrastructure.google.drive_client import (
    DriveApiError,
    create_folder,
    delete_folder,
    get_authenticated_email,
    get_folder,
    list_folders,
)


class DriveFolderClient:
    async def check_access(self, access_token: str) -> str:
        try:
            return await get_authenticated_email(access_token)
        except DriveApiError as error:
            raise DriveFolderError(
                error.message, error.status_code, error.reason
            ) from error
        except httpx.HTTPError as error:
            raise DriveFolderError("No se pudo conectar con Google Drive") from error

    async def list(self, access_token: str, parent_id: str) -> list[dict[str, str]]:
        try:
            return await list_folders(access_token, parent_id)
        except DriveApiError as error:
            raise DriveFolderError(
                error.message, error.status_code, error.reason
            ) from error
        except httpx.HTTPError as error:
            raise DriveFolderError("No se pudo conectar con Google Drive") from error

    async def get(self, access_token: str, folder_id: str) -> dict[str, str]:
        try:
            return await get_folder(access_token, folder_id)
        except DriveApiError as error:
            raise DriveFolderError(
                error.message, error.status_code, error.reason
            ) from error
        except httpx.HTTPError as error:
            raise DriveFolderError("No se pudo conectar con Google Drive") from error

    async def create(self, access_token: str, folder_name: str, parent_id: str) -> str:
        try:
            return await create_folder(access_token, folder_name, parent_id)
        except DriveApiError as error:
            raise DriveFolderError(
                error.message, error.status_code, error.reason
            ) from error
        except httpx.HTTPError as error:
            raise DriveFolderError("No se pudo conectar con Google Drive") from error

    async def delete(self, access_token: str, folder_id: str) -> None:
        try:
            await delete_folder(access_token, folder_id)
        except DriveApiError as error:
            raise DriveFolderError(
                error.message, error.status_code, error.reason
            ) from error
        except httpx.HTTPError as error:
            raise DriveFolderError("No se pudo conectar con Google Drive") from error
