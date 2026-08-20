from datetime import datetime
from typing import Protocol

from diezapp.features.google_drive.domain.models import BackupHistoryEntry, DriveAccount


class DriveAccountRepository(Protocol):
    def list(self) -> list[DriveAccount]: ...

    def count(self) -> int: ...

    def add(
        self,
        email: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> str: ...

    def update_tokens(
        self,
        account_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> None: ...

    def remove(self, account_id: str) -> None: ...

    def set_folder(
        self, account_id: str, folder_id: str | None, folder_name: str | None
    ) -> None: ...


class DriveTokenRepository(Protocol):
    def update(self, account_id: str, access_token: str, expiry_iso: str) -> None: ...


class BackupHistoryRepository(Protocol):
    def save(
        self,
        started_at: str,
        finished_at: str,
        status: str,
        details: list[dict],
    ) -> None: ...

    def list(self, limit: int = 20) -> list[BackupHistoryEntry]: ...


class BackupScheduleRepository(Protocol):
    def get_interval_seconds(self) -> int | None: ...

    def set_interval_seconds(self, seconds: int) -> None: ...

    def get_last_backup_at(self) -> datetime | None: ...

    def set_last_backup_at(self, timestamp: datetime) -> None: ...
