from collections.abc import Callable
from datetime import datetime


class BackupScheduleSettings:
    def __init__(
        self,
        get_interval_seconds: Callable[[], int | None],
        set_interval_seconds: Callable[[int], None],
        get_last_backup_at: Callable[[], datetime | None],
    ):
        self._get_interval_seconds = get_interval_seconds
        self._set_interval_seconds = set_interval_seconds
        self._get_last_backup_at = get_last_backup_at

    def get_interval_seconds(self) -> int | None:
        return self._get_interval_seconds()

    def set_interval_seconds(self, seconds: int) -> None:
        self._set_interval_seconds(seconds)

    def get_last_backup_at(self) -> datetime | None:
        return self._get_last_backup_at()
