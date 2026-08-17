from typing import Protocol

from diezapp.features.notes.domain.models import Note


class NoteRepository(Protocol):
    def list(self) -> list[Note]: ...

    def replace_all(self, notes: list[Note]) -> None: ...
