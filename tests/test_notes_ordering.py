import pytest

from diezapp.features.notes.application.note_service import NoteService
from diezapp.infrastructure.persistence.sqlite_note_repository import (
    SqliteNoteRepository,
)


@pytest.fixture
def notes_service():
    return NoteService(SqliteNoteRepository())


def _ids(service):
    return [n["id"] for n in service.list()]


def test_new_notes_go_first(notes_service):
    first = notes_service.add("contenido 1", "Nota 1")
    second = notes_service.add("contenido 2", "Nota 2")

    assert _ids(notes_service) == [second["id"], first["id"]]


def test_editing_a_note_keeps_its_place(notes_service):
    # The user orders the list by hand, so an edit must not reshuffle it.
    first = notes_service.add("contenido 1", "Nota 1")
    second = notes_service.add("contenido 2", "Nota 2")

    updated = notes_service.update(first["id"], "contenido 1 editado", "Nota 1")

    assert updated["updated_at"] is not None
    assert _ids(notes_service) == [second["id"], first["id"]]


def test_moving_and_painting_survive_a_reload(notes_service):
    first = notes_service.add("contenido 1", "Nota 1")
    second = notes_service.add("contenido 2", "Nota 2")
    third = notes_service.add("contenido 3", "Nota 3")

    notes_service.move(third["id"], 2)
    notes_service.set_color([first["id"]], "green")

    reloaded = NoteService(SqliteNoteRepository())
    assert _ids(reloaded) == [second["id"], first["id"], third["id"]]
    assert {n["id"]: n["color"] for n in reloaded.list()} == {
        first["id"]: "green",
        second["id"]: None,
        third["id"]: None,
    }
