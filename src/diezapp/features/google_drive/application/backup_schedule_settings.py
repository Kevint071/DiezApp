from datetime import datetime

from diezapp.features.google_drive.domain.repositories import BackupScheduleRepository


class BackupScheduleSettings:
    def __init__(
        self,
        repository: BackupScheduleRepository,
    ):
        self.repository = repository

    def get_interval_seconds(self) -> int | None:
        return self.repository.get_interval_seconds()

    def set_interval_seconds(self, seconds: int) -> None:
        self.repository.set_interval_seconds(seconds)

    def get_last_backup_at(self) -> datetime | None:
        return self.repository.get_last_backup_at()
