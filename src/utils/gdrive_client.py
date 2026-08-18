"""Compatibility facade for the migrated Google Drive client."""

from diezapp.infrastructure.google.drive_client import (
    DRIVE_FILES_ENDPOINT,
    DRIVE_SSL_CONTEXT,
    DRIVE_UPLOAD_ENDPOINT,
    FOLDER_MIME_TYPE,
    DriveApiError,
    create_backup_folder,
    create_folder,
    delete_folder,
    list_folders,
    upload_backup_file,
)

__all__ = [
    "DRIVE_FILES_ENDPOINT",
    "DRIVE_SSL_CONTEXT",
    "DRIVE_UPLOAD_ENDPOINT",
    "FOLDER_MIME_TYPE",
    "DriveApiError",
    "create_backup_folder",
    "create_folder",
    "delete_folder",
    "list_folders",
    "upload_backup_file",
]
