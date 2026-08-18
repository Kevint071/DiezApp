from typing import Literal, NotRequired, TypedDict

BackupStatus = Literal["success", "partial", "failed", "skipped"]


class BackupResult(TypedDict):
    email: str
    ok: bool
    error: NotRequired[str]


class BackupSummary(TypedDict):
    status: BackupStatus
    results: list[BackupResult]
    message: NotRequired[str]
