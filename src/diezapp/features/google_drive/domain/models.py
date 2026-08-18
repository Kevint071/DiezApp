from typing import TypedDict


class DriveAccount(TypedDict):
    id: str
    google_account_email: str
    display_label: str
    folder_id: str | None
    folder_name: str | None
    access_token: str
    refresh_token: str
    token_expiry_at: str
    created_at: str


class BackupHistoryEntry(TypedDict):
    id: str
    started_at: str
    finished_at: str
    status: str
    details: list[dict]
