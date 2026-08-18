from collections.abc import Callable
from datetime import UTC, datetime


class BackupScheduler:
    def __init__(
        self,
        get_interval_seconds: Callable[[], int | None],
        get_last_backup_at: Callable[[], datetime | None],
    ):
        self._get_interval_seconds = get_interval_seconds
        self._get_last_backup_at = get_last_backup_at

    def seconds_until_due(self, now: datetime | None = None) -> float | None:
        """Return remaining seconds, or None when scheduling is disabled."""
        interval = self._get_interval_seconds()
        if interval is None:
            return None
        current_time = now or datetime.now(UTC)
        last_backup_at = self._get_last_backup_at()
        if last_backup_at is None:
            return 0.0
        elapsed = (current_time - last_backup_at).total_seconds()
        return interval - elapsed

    def is_due(self, now: datetime | None = None) -> bool:
        remaining = self.seconds_until_due(now)
        return remaining is not None and remaining <= 0
