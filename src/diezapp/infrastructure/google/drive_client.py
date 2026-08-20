"""Minimal Google Drive API v3 client for backup folders and uploads."""

import asyncio
import json
import ssl

import httpx
import truststore

DRIVE_FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME_TYPE = "application/vnd.google-apps.folder"
DRIVE_SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


class DriveApiError(Exception):
    """A safe, user-facing summary of a Google Drive API failure."""

    def __init__(self, status_code: int, reason: str, message: str):
        self.status_code = status_code
        self.reason = reason
        self.message = message
        super().__init__(f"{status_code} {reason}: {message}")


def _raise_for_drive_error(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    reason = "http_error"
    message = resp.text[:240]
    try:
        error = resp.json().get("error", {})
        details = error.get("errors", [{}])[0]
        reason = details.get("reason") or error.get("status") or reason
        message = error.get("message") or message
    except ValueError, AttributeError, IndexError, TypeError:
        pass
    raise DriveApiError(resp.status_code, reason, message)


async def create_backup_folder(access_token: str, folder_name: str) -> str:
    """Create a new Drive folder in the My Drive root."""
    return await create_folder(access_token, folder_name, "root")


async def get_authenticated_email(access_token: str) -> str:
    """Return the Google account email associated with an access token."""
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        resp = await client.get(
            "https://www.googleapis.com/drive/v3/about",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "user(emailAddress)"},
        )
        _raise_for_drive_error(resp)
        return resp.json()["user"]["emailAddress"]


async def create_folder(access_token: str, folder_name: str, parent_id: str) -> str:
    """Create a new Drive folder below ``parent_id`` and return its file ID."""
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        resp = await client.post(
            DRIVE_FILES_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": folder_name,
                "mimeType": FOLDER_MIME_TYPE,
                "parents": [parent_id],
            },
        )
        _raise_for_drive_error(resp)
        return resp.json()["id"]


async def delete_folder(access_token: str, folder_id: str) -> None:
    """Delete a folder selected by the user from Google Drive."""
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        resp = await client.delete(
            f"{DRIVE_FILES_ENDPOINT}/{folder_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        _raise_for_drive_error(resp)


async def get_folder(access_token: str, folder_id: str) -> dict[str, str]:
    """Return metadata for a Drive folder selected by the user."""
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        resp = await client.get(
            f"{DRIVE_FILES_ENDPOINT}/{folder_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"fields": "id,name,mimeType,trashed"},
        )
        _raise_for_drive_error(resp)
        return resp.json()


async def list_folders(
    access_token: str, parent_id: str = "root"
) -> list[dict[str, str]]:
    """List folders directly below ``parent_id`` visible to the app."""
    folders = []
    page_token = None
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        while True:
            params = {
                "q": (
                    f"'{parent_id}' in parents and "
                    f"mimeType = '{FOLDER_MIME_TYPE}' and trashed = false"
                ),
                "fields": "nextPageToken,files(id,name)",
                "orderBy": "name",
                "pageSize": "100",
            }
            if page_token:
                params["pageToken"] = page_token
            resp = await client.get(
                DRIVE_FILES_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            _raise_for_drive_error(resp)
            data = resp.json()
            folders.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return folders


async def list_backup_files(access_token: str, parent_id: str) -> list[dict[str, str]]:
    """List SQLite backups directly inside a Drive folder."""
    files = []
    page_token = None
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        while True:
            params = {
                "q": (
                    f"'{parent_id}' in parents and trashed = false and "
                    "mimeType != 'application/vnd.google-apps.folder'"
                ),
                "fields": "nextPageToken,files(id,name,size,modifiedTime,mimeType)",
                "orderBy": "modifiedTime desc",
                "pageSize": "100",
            }
            if page_token:
                params["pageToken"] = page_token
            resp = await client.get(
                DRIVE_FILES_ENDPOINT,
                headers={"Authorization": f"Bearer {access_token}"},
                params=params,
            )
            _raise_for_drive_error(resp)
            data = resp.json()
            files.extend(data.get("files", []))
            page_token = data.get("nextPageToken")
            if not page_token:
                return files


async def delete_file(access_token: str, file_id: str) -> None:
    """Move a Drive backup to trash."""
    async with httpx.AsyncClient(timeout=20, verify=DRIVE_SSL_CONTEXT) as client:
        resp = await client.delete(
            f"{DRIVE_FILES_ENDPOINT}/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        _raise_for_drive_error(resp)


async def download_file(access_token: str, file_id: str, destination: str) -> None:
    """Download a Drive file to a local path."""
    async with (
        httpx.AsyncClient(timeout=60, verify=DRIVE_SSL_CONTEXT) as client,
        client.stream(
            "GET",
            f"{DRIVE_FILES_ENDPOINT}/{file_id}",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"alt": "media"},
        ) as resp,
    ):
        _raise_for_drive_error(resp)
        content = await resp.aread()
    await asyncio.to_thread(_write_file_bytes, destination, content)


async def upload_backup_file(
    access_token: str, folder_id: str, file_path: str, file_name: str
) -> str:
    """Upload ``file_path`` into ``folder_id`` and return the new file ID."""
    metadata = {"name": file_name, "parents": [folder_id]}
    file_bytes = await asyncio.to_thread(_read_file_bytes, file_path)

    boundary = "diezapp_backup_boundary"
    body = (
        (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + file_bytes
        + f"\r\n--{boundary}--".encode()
    )

    async with httpx.AsyncClient(timeout=60, verify=DRIVE_SSL_CONTEXT) as client:
        resp = await client.post(
            f"{DRIVE_UPLOAD_ENDPOINT}?uploadType=multipart",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            content=body,
        )
        _raise_for_drive_error(resp)
        return resp.json()["id"]


def _read_file_bytes(file_path: str) -> bytes:
    with open(file_path, "rb") as file:
        return file.read()


def _write_file_bytes(file_path: str, content: bytes) -> None:
    with open(file_path, "wb") as file:
        file.write(content)
