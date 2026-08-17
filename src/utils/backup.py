"""Compatibility facade for local SQLite backup operations."""

from diezapp.features.local_backup.application.local_backup_service import (
    LocalBackupService,
)
from diezapp.infrastructure.files.sqlite_backup_adapter import SqliteBackupAdapter

_service = LocalBackupService(SqliteBackupAdapter())


def export_calculations(path: str, calculations: list):
    _service.export_calculations(path, calculations)


def export_notes(path: str, notes: list):
    _service.export_notes(path, notes)


def read_calculations(path: str) -> list:
    return _service.read_calculations(path)


def read_notes(path: str) -> list:
    return _service.read_notes(path)
