from diezapp.features.notes.application.note_service import NoteService


class InMemoryNoteRepository:
    def __init__(self):
        self.notes = []

    def list(self):
        return list(self.notes)

    def replace_all(self, notes):
        self.notes = list(notes)

    def save(self, note):
        self.notes = [dict(note) if n["id"] == note["id"] else n for n in self.notes]


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


def test_note_service_update_keeps_format_unless_given():
    repository = InMemoryNoteRepository()
    service = NoteService(repository)
    note = service.add("Hola", fmt='[{"k":"h1"}]')

    service.update(note["id"], "Hola!")
    assert repository.list()[0]["format"] == '[{"k":"h1"}]'

    service.update(note["id"], "Hola!", fmt=None)
    assert repository.list()[0]["format"] is None


def test_note_service_update_only_rewrites_that_note():
    repository = InMemoryNoteRepository()
    service = NoteService(repository)
    first = service.add("Uno")
    second = service.add("Dos")

    service.update(first["id"], "Uno editado", "T")

    stored = {n["id"]: n for n in repository.list()}
    assert stored[first["id"]]["content"] == "Uno editado"
    assert stored[second["id"]]["content"] == "Dos"
    assert [n["id"] for n in repository.list()] == [second["id"], first["id"]]
