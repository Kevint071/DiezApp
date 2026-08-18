from datetime import datetime

from diezapp.infrastructure.database.connection import get_setting, set_setting

INTERVAL_SETTING = "backup_interval_seconds"
LAST_BACKUP_SETTING = "last_backup_success_at"


class SqliteBackupScheduleRepository:
    def get_interval_seconds(self) -> int | None:
        raw = get_setting(INTERVAL_SETTING)
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def set_interval_seconds(self, seconds: int) -> None:
        set_setting(INTERVAL_SETTING, str(seconds))

    def get_last_backup_at(self) -> datetime | None:
        raw = get_setting(LAST_BACKUP_SETTING)
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    def set_last_backup_at(self, timestamp: datetime) -> None:
        set_setting(LAST_BACKUP_SETTING, timestamp.isoformat())
