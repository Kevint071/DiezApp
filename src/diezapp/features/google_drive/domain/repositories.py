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
