from typing import ClassVar

from diezapp.features.notes.domain.models import Note
from diezapp.infrastructure.database.connection import get_connection


class SqliteNoteRepository:
    _columns: ClassVar[list[str]] = [
        "id",
        "title",
        "content",
        "created_at",
        "updated_at",
        "format",
    ]

    def list(self) -> list[Note]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, title, content, created_at, updated_at, format FROM notes "
            "ORDER BY sort_index ASC"
        ).fetchall()
        return [dict(zip(self._columns, row, strict=True)) for row in rows]

    def replace_all(self, notes: list[Note]) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM notes")
        for index, note in enumerate(notes):
            conn.execute(
                "INSERT INTO notes (id, title, content, created_at, updated_at, "
                "format, sort_index) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    note["id"],
                    note["title"],
                    note["content"],
                    note["created_at"],
                    note["updated_at"],
                    note.get("format"),
                    index,
                ),
            )
        conn.commit()

    def save(self, note: Note) -> None:
        conn = get_connection()
        conn.execute(
            "UPDATE notes SET title = ?, content = ?, updated_at = ?, format = ? "
            "WHERE id = ?",
            (
                note["title"],
                note["content"],
                note["updated_at"],
                note.get("format"),
                note["id"],
            ),
        )
        conn.commit()
