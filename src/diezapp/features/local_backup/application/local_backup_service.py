from typing import Protocol


class BackupAdapter(Protocol):
    def export_calculations(self, path: str, calculations: list) -> None: ...

    def export_notes(self, path: str, notes: list) -> None: ...

    def read_calculations(self, path: str) -> list: ...

    def read_notes(self, path: str) -> list: ...


class LocalBackupService:
    def __init__(self, adapter: BackupAdapter):
        self.adapter = adapter

    def export_calculations(self, path: str, calculations: list) -> None:
        self.adapter.export_calculations(path, calculations)

    def export_notes(self, path: str, notes: list) -> None:
        self.adapter.export_notes(path, notes)

    def read_calculations(self, path: str) -> list:
        return self.adapter.read_calculations(path)

    def read_notes(self, path: str) -> list:
        return self.adapter.read_notes(path)
