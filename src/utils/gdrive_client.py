"""Minimal Google Drive API v3 client (folder creation + file upload).

Only what's needed for the `drive.file` scope: creating a backup
destination folder (v1 folder-selection UX — see design.md's Drive Picker
open question, deferred; "create a new folder" is the v1 flow) and
uploading a backup file to it via multipart upload.
"""

import asyncio
import json

import httpx

DRIVE_FILES_ENDPOINT = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_ENDPOINT = "https://www.googleapis.com/upload/drive/v3/files"


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
    except (ValueError, AttributeError, IndexError, TypeError):
        pass
    raise DriveApiError(resp.status_code, reason, message)


async def create_backup_folder(access_token: str, folder_name: str) -> str:
    """Create a new Drive folder (in "My Drive" root) and return its file ID."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            DRIVE_FILES_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "name": folder_name,
                "mimeType": "application/vnd.google-apps.folder",
            },
        )
        _raise_for_drive_error(resp)
        return resp.json()["id"]


async def upload_backup_file(
    access_token: str, folder_id: str, file_path: str, file_name: str
) -> str:
    """Upload `file_path` into `folder_id` via multipart upload. Returns the new file ID."""
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

    async with httpx.AsyncClient(timeout=60) as client:
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
    with open(file_path, "rb") as f:
        return f.read()
