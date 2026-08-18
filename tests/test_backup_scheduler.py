from datetime import UTC, datetime, timedelta

from diezapp.features.google_drive.application.backup_scheduler import BackupScheduler


def test_scheduler_is_disabled_without_interval():
    scheduler = BackupScheduler(lambda: None, lambda: None)

    assert scheduler.seconds_until_due() is None
    assert scheduler.is_due() is False


def test_scheduler_is_due_when_never_backed_up():
    scheduler = BackupScheduler(lambda: 3600, lambda: None)

    assert scheduler.seconds_until_due() == 0.0
    assert scheduler.is_due() is True


def test_scheduler_waits_until_interval_elapses():
    last_backup = datetime(2026, 8, 17, 12, tzinfo=UTC)
    scheduler = BackupScheduler(lambda: 3600, lambda: last_backup)

    now = last_backup + timedelta(minutes=30)

    assert scheduler.seconds_until_due(now) == 1800
    assert scheduler.is_due(now) is False


def test_scheduler_is_due_after_interval_elapses():
    last_backup = datetime(2026, 8, 17, 12, tzinfo=UTC)
    scheduler = BackupScheduler(lambda: 3600, lambda: last_backup)

    assert scheduler.is_due(last_backup + timedelta(hours=1)) is True
