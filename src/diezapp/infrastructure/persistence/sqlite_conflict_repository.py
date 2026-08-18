import json

from diezapp.features.conflicts.domain.models import ConflictSet
from diezapp.infrastructure.database.connection import get_connection


class SqliteConflictRepository:
    def load(self, kind: str = "calculations") -> ConflictSet:
        conn = get_connection()
        row = conn.execute(
            "SELECT payload FROM pending_conflicts WHERE kind = ?", (kind,)
        ).fetchone()
        if row is None:
            return {"conflicts": [], "pending_add": []}
        try:
            data = json.loads(row[0])
        except json.JSONDecodeError, TypeError:
            return {"conflicts": [], "pending_add": []}
        return {
            "conflicts": data.get("conflicts", []),
            "pending_add": data.get("pending_add", []),
        }

    def save(
        self,
        conflicts: list[dict],
        pending_add: list[dict],
        kind: str = "calculations",
    ) -> None:
        conn = get_connection()
        payload = json.dumps(
            {"conflicts": conflicts, "pending_add": pending_add},
            ensure_ascii=False,
        )
        conn.execute(
            "INSERT INTO pending_conflicts (kind, payload) VALUES (?, ?) "
            "ON CONFLICT(kind) DO UPDATE SET payload = excluded.payload",
            (kind, payload),
        )
        conn.commit()

    def clear(self, kind: str = "calculations") -> None:
        conn = get_connection()
        conn.execute("DELETE FROM pending_conflicts WHERE kind = ?", (kind,))
        conn.commit()
