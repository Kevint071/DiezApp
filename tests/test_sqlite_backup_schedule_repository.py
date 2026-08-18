from datetime import UTC, datetime

from diezapp.infrastructure.persistence.sqlite_backup_schedule_repository import (
    INTERVAL_SETTING,
    LAST_BACKUP_SETTING,
    SqliteBackupScheduleRepository,
)
from utils.db import set_setting


def test_sqlite_backup_schedule_repository_round_trips_settings():
    repository = SqliteBackupScheduleRepository()
    timestamp = datetime(2026, 8, 17, 12, tzinfo=UTC)

    repository.set_interval_seconds(3600)
    repository.set_last_backup_at(timestamp)

    assert repository.get_interval_seconds() == 3600
    assert repository.get_last_backup_at() == timestamp


def test_sqlite_backup_schedule_repository_handles_missing_and_invalid_values():
    repository = SqliteBackupScheduleRepository()

    assert repository.get_interval_seconds() is None
    assert repository.get_last_backup_at() is None

    set_setting(INTERVAL_SETTING, "not-a-number")
    set_setting(LAST_BACKUP_SETTING, "not-a-date")

    assert repository.get_interval_seconds() is None
    assert repository.get_last_backup_at() is None
