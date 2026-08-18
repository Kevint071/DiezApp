from utils.db import get_connection


class SqliteDriveTokenRepository:
    def update(self, account_id: str, access_token: str, expiry_iso: str) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE gdrive_accounts SET access_token = ?, token_expiry_at = ? WHERE id = ?",
            (access_token, expiry_iso, account_id),
        )
        conn.commit()
