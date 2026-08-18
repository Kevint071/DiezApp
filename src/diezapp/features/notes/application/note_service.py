import uuid
from datetime import UTC, datetime

from diezapp.features.notes.domain.models import Note
from diezapp.features.notes.domain.repositories import NoteRepository


class NoteService:
    def __init__(self, repository: NoteRepository):
        self.repository = repository

    def list(self) -> list[Note]:
        return self.repository.list()

    @staticmethod
    def sort_for_display(notes: list[Note]) -> list[Note]:
        return sorted(
            notes,
            key=lambda note: note.get("updated_at") or note.get("created_at") or "",
            reverse=True,
        )

    def replace_all(self, notes: list[Note]) -> None:
        self.repository.replace_all(notes)

    def add(self, content: str, title: str = "") -> Note:
        note: Note = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "created_at": datetime.now(UTC).astimezone().isoformat(),
            "updated_at": None,
        }
        notes = self.repository.list()
        notes.insert(0, note)
        self.repository.replace_all(notes)
        return note

    def update(
        self, note_id: str, content: str, title: str | None = None
    ) -> Note | None:
        notes = self.repository.list()
        for note in notes:
            if note["id"] != note_id:
                continue
            note["content"] = content
            if title is not None:
                note["title"] = title
            note["updated_at"] = datetime.now(UTC).astimezone().isoformat()
            self.repository.replace_all(notes)
            return note
        return None

    def delete(self, note_id: str) -> bool:
        notes = self.repository.list()
        remaining = [note for note in notes if note["id"] != note_id]
        if len(remaining) == len(notes):
            return False
        self.repository.replace_all(remaining)
        return True
