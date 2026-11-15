import uuid

from diezapp.features.notes.domain.models import Note
from diezapp.features.notes.domain.repositories import NoteRepository
from diezapp.shared.datetime_utils import local_now, to_local_iso

# Lets `update` tell "leave the formatting alone" apart from "clear it" (None).
_KEEP = object()


class NoteService:
    def __init__(self, repository: NoteRepository):
        self.repository = repository

    def list(self) -> list[Note]:
        """In the order the user arranged them; new notes go first."""
        return self.repository.list()

    def replace_all(self, notes: list[Note]) -> None:
        self.repository.replace_all(notes)

    def add(self, content: str, title: str = "", fmt: str | None = None) -> Note:
        note: Note = {
            "id": str(uuid.uuid4()),
            "title": title,
            "content": content,
            "created_at": to_local_iso(local_now()),
            "updated_at": None,
            "format": fmt,
            "color": None,
        }
        notes = self.repository.list()
        notes.insert(0, note)
        self.repository.replace_all(notes)
        return note

    def update(
        self,
        note_id: str,
        content: str,
        title: str | None = None,
        fmt: str | None | object = _KEEP,
    ) -> Note | None:
        for note in self.repository.list():
            if note["id"] != note_id:
                continue
            note["content"] = content
            if title is not None:
                note["title"] = title
            if fmt is not _KEEP:
                note["format"] = fmt
            note["updated_at"] = to_local_iso(local_now())
            self.repository.save(note)
            return note
        return None

    def delete(self, note_id: str) -> bool:
        return self.delete_many([note_id]) > 0

    def delete_many(self, note_ids) -> int:
        doomed = set(note_ids)
        notes = self.repository.list()
        remaining = [note for note in notes if note["id"] not in doomed]
        removed = len(notes) - len(remaining)
        if removed:
            self.repository.replace_all(remaining)
        return removed

    def set_color(self, note_ids, color: str | None) -> None:
        """Paint the cards; not an edit, so ``updated_at`` stays as it was."""
        targets = set(note_ids)
        notes = self.repository.list()
        for note in notes:
            if note["id"] in targets:
                note["color"] = color
        self.repository.replace_all(notes)

    def move(self, note_id: str, new_index: int) -> None:
        """Put a note at ``new_index`` of the list, shifting the rest."""
        notes = self.repository.list()
        index = next((i for i, n in enumerate(notes) if n["id"] == note_id), None)
        if index is None:
            return
        note = notes.pop(index)
        notes.insert(max(0, min(new_index, len(notes))), note)
        self.repository.replace_all(notes)
