"""Backup engine: snapshot `app.db` and upload it to every linked Google account.

Single entry point `run_backup_now()` is used by the manual "Respaldar
ahora" button and both scheduler triggers (in-app timer + startup catch-up),
per design.md Decision 4 (one code path for "a backup happens").
"""

import asyncio
from datetime import UTC, datetime

from diezapp.features.google_drive.application.run_backup import (
    GoogleDriveBackupService,
)
from diezapp.infrastructure.files.sqlite_snapshot_adapter import SqliteSnapshotAdapter
from diezapp.infrastructure.persistence.sqlite_backup_history_repository import (
    SqliteBackupHistoryRepository,
)

from utils.db import get_setting, set_setting
from utils.gdrive_auth import ensure_fresh_access_token, list_accounts
from utils.gdrive_client import upload_backup_file

RETRY_DELAYS_SECONDS = [5, 30, 120]
LAST_BACKUP_SETTING = "last_backup_success_at"
INTERVAL_SETTING = "backup_interval_seconds"
_history_repository = SqliteBackupHistoryRepository()
_snapshot_adapter = SqliteSnapshotAdapter()


def _snapshot_db() -> str:
    return _snapshot_adapter.create_snapshot()


async def run_backup_now(page, account_ids: set[str] | None = None) -> dict:
    """Compatibility facade for the Google Drive backup use case."""
    return await _backup_service.run(
        lambda account: ensure_fresh_access_token(page, account), account_ids
    )


def _write_history(
    started_at: datetime, finished_at: datetime, status: str, results: list[dict]
):
    _history_repository.save(
        started_at.isoformat(), finished_at.isoformat(), status, results
    )


_backup_service = GoogleDriveBackupService(
    list_accounts=lambda: list_accounts(),
    snapshot_db=lambda: _snapshot_db(),
    upload_file=lambda access_token, folder_id, file_path, file_name: (
        upload_backup_file(access_token, folder_id, file_path, file_name)
    ),
    write_history=lambda started_at, finished_at, status, results: _write_history(
        started_at, finished_at, status, results
    ),
    save_success_at=lambda timestamp: set_setting(
        LAST_BACKUP_SETTING, timestamp.isoformat()
    ),
    sleep=lambda seconds: asyncio.sleep(seconds),
)


def list_history(limit: int = 20) -> list[dict]:
    return _history_repository.list(limit)


# ── Scheduling helpers (interval stored as seconds in `settings`) ────


def get_interval_seconds() -> int | None:
    raw = get_setting(INTERVAL_SETTING)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def set_interval_seconds(seconds: int):
    set_setting(INTERVAL_SETTING, str(seconds))


def get_last_backup_at() -> datetime | None:
    raw = get_setting(LAST_BACKUP_SETTING)
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def seconds_until_due(now: datetime | None = None) -> float | None:
    """Seconds remaining until the next backup is due.

    Returns None if no interval is configured. A value <= 0 means a backup
    is due right now. `now` is injectable for tests.
    """
    interval = get_interval_seconds()
    if interval is None:
        return None
    now = now or datetime.now(UTC)
    last = get_last_backup_at()
    if last is None:
        return 0.0
    elapsed = (now - last).total_seconds()
    return interval - elapsed


def is_due(now: datetime | None = None) -> bool:
    remaining = seconds_until_due(now)
    return remaining is not None and remaining <= 0
