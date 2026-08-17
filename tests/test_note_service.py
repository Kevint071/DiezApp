from diezapp.features.notes.application.note_service import NoteService


class InMemoryNoteRepository:
    def __init__(self):
        self.notes = []

    def list(self):
        return list(self.notes)

    def replace_all(self, notes):
        self.notes = list(notes)


def test_note_service_adds_note():
    repository = InMemoryNoteRepository()
    note = NoteService(repository).add("Contenido", "Título")

    assert note["title"] == "Título"
    assert note["content"] == "Contenido"
    assert note["updated_at"] is None
    assert repository.list() == [note]


def test_note_service_updates_and_deletes_note():
    repository = InMemoryNoteRepository()
    service = NoteService(repository)
    note = service.add("Antes")

    updated = service.update(note["id"], "Después", "Editada")

    assert updated["content"] == "Después"
    assert updated["title"] == "Editada"
    assert updated["updated_at"] is not None
    assert service.delete(note["id"]) is True
    assert repository.list() == []
    assert service.delete(note["id"]) is False
