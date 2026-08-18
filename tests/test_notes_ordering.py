import time

import pytest

from diezapp.features.notes.application.note_service import NoteService
from diezapp.infrastructure.persistence.sqlite_note_repository import (
    SqliteNoteRepository,
)


def _sort_notes_for_display(notes):
    return NoteService.sort_for_display(notes)


@pytest.fixture
def notes_service():
    return NoteService(SqliteNoteRepository())


class TestSortNotesForDisplayPure:
    """Unit tests against plain dicts -- no DB involved."""

    def test_empty_list_returns_empty_list(self):
        assert _sort_notes_for_display([]) == []

    def test_single_note_returned_as_is(self):
        notes = [{"id": "1", "created_at": "2026-01-01T00:00:00", "updated_at": None}]
        assert _sort_notes_for_display(notes) == notes

    def test_all_unmodified_sorted_by_created_at_descending(self):
        oldest = {"id": "1", "created_at": "2026-01-01T00:00:00", "updated_at": None}
        middle = {"id": "2", "created_at": "2026-01-02T00:00:00", "updated_at": None}
        newest = {"id": "3", "created_at": "2026-01-03T00:00:00", "updated_at": None}
        result = _sort_notes_for_display([oldest, newest, middle])
        assert [n["id"] for n in result] == ["3", "2", "1"]

    def test_all_modified_sorted_by_updated_at_descending(self):
        a = {
            "id": "1",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-05T00:00:00",
        }
        b = {
            "id": "2",
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-10T00:00:00",
        }
        c = {
            "id": "3",
            "created_at": "2026-01-03T00:00:00",
            "updated_at": "2026-01-07T00:00:00",
        }
        result = _sort_notes_for_display([a, b, c])
        assert [n["id"] for n in result] == ["2", "3", "1"]

    def test_a_recently_created_note_ranks_above_an_older_edit(self):
        # A brand-new note (no updated_at) that was created after another
        # note's last edit must still be shown first: recency wins, being
        # "edited" doesn't give special priority.
        edited = {
            "id": "1",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-05T00:00:00",
        }
        newer_untouched = {
            "id": "2",
            "created_at": "2026-01-10T00:00:00",
            "updated_at": None,
        }
        older_untouched = {
            "id": "3",
            "created_at": "2026-01-02T00:00:00",
            "updated_at": None,
        }
        result = _sort_notes_for_display([older_untouched, edited, newer_untouched])
        assert [n["id"] for n in result] == ["2", "1", "3"]

    def test_mixed_modified_and_unmodified_notes_sorted_by_recency(self):
        edited_recent = {
            "id": "1",
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-20T00:00:00",
        }
        edited_older = {
            "id": "2",
            "created_at": "2026-01-02T00:00:00",
            "updated_at": "2026-01-15T00:00:00",
        }
        untouched_new = {
            "id": "3",
            "created_at": "2026-01-12T00:00:00",
            "updated_at": None,
        }
        untouched_old = {
            "id": "4",
            "created_at": "2026-01-03T00:00:00",
            "updated_at": None,
        }
        result = _sort_notes_for_display(
            [untouched_old, edited_older, untouched_new, edited_recent]
        )
        assert [n["id"] for n in result] == ["1", "2", "3", "4"]

    def test_missing_created_at_and_updated_at_do_not_raise(self):
        notes = [{"id": "1"}, {"id": "2", "created_at": "2026-01-01T00:00:00"}]
        result = _sort_notes_for_display(notes)
        assert {n["id"] for n in result} == {"1", "2"}


class TestSortNotesForDisplayWithRealNotes:
    """Integration tests through NoteService and its SQLite repository."""

    def test_new_note_has_no_updated_at(self, notes_service):
        note = notes_service.add("contenido", "Titulo")
        assert note["updated_at"] is None
        assert notes_service.list()[0]["updated_at"] is None

    def test_editing_a_note_sets_updated_at(self, notes_service):
        note = notes_service.add("contenido original", "Titulo")
        assert note["updated_at"] is None

        updated = notes_service.update(note["id"], "contenido editado", "Titulo")

        assert updated["updated_at"] is not None
        stored = next(n for n in notes_service.list() if n["id"] == note["id"])
        assert stored["updated_at"] is not None
        assert stored["content"] == "contenido editado"

    def test_editing_a_note_moves_it_to_the_top(self, notes_service):
        first = notes_service.add("contenido 1", "Nota 1")
        time.sleep(0.01)
        second = notes_service.add("contenido 2", "Nota 2")
        time.sleep(0.01)
        third = notes_service.add("contenido 3", "Nota 3")

        # Edit the oldest note; it should now be displayed first, ahead of
        # both never-edited notes (which keep newest-created-first order).
        notes_service.update(first["id"], "contenido 1 editado", "Nota 1")

        ordered = _sort_notes_for_display(notes_service.list())
        assert [n["id"] for n in ordered] == [first["id"], third["id"], second["id"]]

    def test_editing_the_second_time_re_sorts_by_latest_edit(self, notes_service):
        first = notes_service.add("contenido 1", "Nota 1")
        time.sleep(0.01)
        second = notes_service.add("contenido 2", "Nota 2")
        time.sleep(0.01)
        third = notes_service.add("contenido 3", "Nota 3")

        notes_service.update(first["id"], "contenido 1 editado", "Nota 1")
        time.sleep(0.01)
        notes_service.update(second["id"], "contenido 2 editado", "Nota 2")

        ordered = _sort_notes_for_display(notes_service.list())
        # second was edited most recently, so it now leads; first follows;
        # third was never touched so it stays last.
        assert [n["id"] for n in ordered] == [second["id"], first["id"], third["id"]]

    def test_never_edited_notes_keep_creation_order_after_edits(self, notes_service):
        first = notes_service.add("contenido 1", "Nota 1")
        time.sleep(0.01)
        second = notes_service.add("contenido 2", "Nota 2")
        time.sleep(0.01)
        third = notes_service.add("contenido 3", "Nota 3")
        time.sleep(0.01)
        fourth = notes_service.add("contenido 4", "Nota 4")

        notes_service.update(second["id"], "contenido 2 editado", "Nota 2")

        ordered = _sort_notes_for_display(notes_service.list())
        assert [n["id"] for n in ordered] == [
            second["id"],
            fourth["id"],
            third["id"],
            first["id"],
        ]

    def test_newly_created_note_ranks_above_an_earlier_edit(self, notes_service):
        note = notes_service.add("contenido", "Nota vieja")
        notes_service.update(note["id"], "contenido editado", "Nota vieja")
        time.sleep(0.01)
        brand_new = notes_service.add("contenido nuevo", "Nota nueva")

        ordered = _sort_notes_for_display(notes_service.list())
        assert [n["id"] for n in ordered] == [brand_new["id"], note["id"]]
