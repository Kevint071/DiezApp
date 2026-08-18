import uuid
from datetime import UTC, datetime, timedelta

from diezapp.features.google_drive.domain.models import DriveAccount
from utils.db import get_connection


class SqliteDriveAccountRepository:
    def list(self) -> list[DriveAccount]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, google_account_email, display_label, folder_id, folder_name, "
            "access_token, refresh_token, token_expiry_at, created_at "
            "FROM gdrive_accounts ORDER BY created_at"
        ).fetchall()
        columns = [
            "id",
            "google_account_email",
            "display_label",
            "folder_id",
            "folder_name",
            "access_token",
            "refresh_token",
            "token_expiry_at",
            "created_at",
        ]
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def count(self) -> int:
        conn = get_connection()
        return conn.execute("SELECT COUNT(*) FROM gdrive_accounts").fetchone()[0]

    def add(
        self,
        email: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> str:
        account_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        expiry = now + timedelta(seconds=expires_in)
        conn = get_connection()
        conn.execute(
            "INSERT INTO gdrive_accounts "
            "(id, google_account_email, display_label, folder_id, folder_name, "
            "access_token, refresh_token, token_expiry_at, created_at) "
            "VALUES (?, ?, ?, NULL, NULL, ?, ?, ?, ?)",
            (
                account_id,
                email,
                email,
                access_token,
                refresh_token,
                expiry.isoformat(),
                now.isoformat(),
            ),
        )
        conn.commit()
        return account_id

    def remove(self, account_id: str) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM gdrive_accounts WHERE id = ?", (account_id,))
        conn.commit()

    def set_folder(
        self, account_id: str, folder_id: str | None, folder_name: str | None
    ) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE gdrive_accounts SET folder_id = ?, folder_name = ? WHERE id = ?",
            (folder_id, folder_name, account_id),
        )
        conn.commit()
