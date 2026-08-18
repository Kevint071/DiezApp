import json
import uuid

from diezapp.features.google_drive.domain.models import BackupHistoryEntry
from utils.db import get_connection


class SqliteBackupHistoryRepository:
    def save(
        self,
        started_at: str,
        finished_at: str,
        status: str,
        details: list[dict],
    ) -> None:
        conn = get_connection()
        conn.execute(
            "INSERT INTO backup_history (id, started_at, finished_at, status, details) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                uuid.uuid4().hex,
                started_at,
                finished_at,
                status,
                json.dumps(details),
            ),
        )
        conn.commit()

    def list(self, limit: int = 20) -> list[BackupHistoryEntry]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, started_at, finished_at, status, details "
            "FROM backup_history ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        history = []
        for row in rows:
            try:
                details = json.loads(row[4])
            except json.JSONDecodeError, TypeError:
                details = []
            history.append(
                {
                    "id": row[0],
                    "started_at": row[1],
                    "finished_at": row[2],
                    "status": row[3],
                    "details": details,
                }
            )
        return history
