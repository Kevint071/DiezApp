import uuid
from datetime import UTC, datetime

from utils.db import get_connection

_COLUMNS = ["id", "title", "content", "created_at", "updated_at"]


def load_notes() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, content, created_at, updated_at FROM notes "
        "ORDER BY sort_index ASC"
    ).fetchall()
    return [dict(zip(_COLUMNS, row)) for row in rows]


def save_notes(notes: list):
    conn = get_connection()
    conn.execute("DELETE FROM notes")
    for i, note in enumerate(notes):
        conn.execute(
            "INSERT INTO notes (id, title, content, created_at, updated_at, sort_index) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                note.get("id"),
                note.get("title", ""),
                note.get("content"),
                note.get("created_at"),
                note.get("updated_at"),
                i,
            ),
        )
    conn.commit()


def add_note(content: str, title: str = "") -> dict:
    note = {
        "id": str(uuid.uuid4()),
        "title": title,
        "content": content,
        "created_at": datetime.now(UTC).astimezone().isoformat(),
        "updated_at": None,
    }
    notes = load_notes()
    notes.insert(0, note)
    save_notes(notes)
    return note


def update_note(
    note_id: str, new_content: str, new_title: str | None = None
) -> dict | None:
    notes = load_notes()
    for note in notes:
        if note["id"] == note_id:
            note["content"] = new_content
            if new_title is not None:
                note["title"] = new_title
            note["updated_at"] = datetime.now(UTC).astimezone().isoformat()
            save_notes(notes)
            return note
    return None


def delete_note(note_id: str) -> bool:
    notes = load_notes()
    original_len = len(notes)
    notes = [n for n in notes if n["id"] != note_id]
    if len(notes) < original_len:
        save_notes(notes)
        return True
    return False
