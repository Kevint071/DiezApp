import asyncio
import inspect
import json

import flet as ft
from flet_note_editor import (
    NoteEditor,
    NoteEditorChangeEvent,
    NoteEditorHistoryEvent,
)

from diezapp.features.notes.application.note_service import NoteService
from diezapp.features.notes.presentation.notes_page import (
    _preview,
    build_note_editor_view,
)
from diezapp.shared.presentation.theme import get_colors


class FakePage:
    theme_mode = "light"

    def update(self):
        pass

    def show_dialog(self, dialog):
        pass

    def pop_dialog(self):
        pass


class InMemoryNoteRepository:
    def __init__(self):
        self.notes = []

    def list(self):
        return [dict(note) for note in self.notes]

    def replace_all(self, notes):
        self.notes = [dict(note) for note in notes]

    def save(self, note):
        self.notes = [dict(note) if n["id"] == note["id"] else n for n in self.notes]


class FakeConflicts:
    def __init__(self, count=0):
        self._count = count

    def count(self, kind=None):
        return self._count


def _build(service, note=None, conflicts=0):
    captured = {"actions": None, "guard": None, "snacks": []}

    def _register(guard):
        captured["guard"] = guard

    view = build_note_editor_view(
        FakePage(),
        get_colors,
        note,
        notes_service=service,
        conflicts_service=FakeConflicts(conflicts),
        set_header_actions=lambda actions: captured.__setitem__("actions", actions),
        register_leave_guard=_register,
        on_deleted=lambda: None,
        show_snack=captured["snacks"].append,
    )
    editor = view.content
    assert isinstance(editor, NoteEditor)
    return editor, captured


def _fire(handler, event=None):
    """Dispatch like Flet does: only coroutine *functions* get awaited."""
    if inspect.iscoroutinefunction(handler):
        asyncio.run(handler(event))
    else:
        result = handler(event)
        assert not inspect.iscoroutine(result), "handler would never run in Flet"


def _type(editor, title, delta):
    """What the Dart side sends on every keystroke."""
    event = NoteEditorChangeEvent(
        name="change", control=editor, title=title, delta=json.dumps(delta)
    )
    _fire(editor.on_change, event)


def _history(editor, can_undo, can_redo):
    event = NoteEditorHistoryEvent(
        name="history_change", control=editor, can_undo=can_undo, can_redo=can_redo
    )
    _fire(editor.on_history_change, event)


def _icons(captured):
    return [
        getattr(control, "icon", None)
        for control in captured["actions"][0].content.controls
    ]


def test_editor_loads_the_note_as_a_delta():
    service = NoteService(InMemoryNoteRepository())
    note = service.add("Hola", "Título")

    editor, _ = _build(service, note)

    assert json.loads(editor.value) == [{"insert": "Hola\n"}]
    assert editor.title == "Título"
    assert editor.autofocus_title is False


def test_new_note_is_created_on_first_text_and_then_updated():
    service = NoteService(InMemoryNoteRepository())
    editor, _ = _build(service)
    assert editor.autofocus_title is True

    _type(editor, "", [{"insert": "\n"}])
    assert service.list() == []

    _type(editor, "Compra", [{"insert": "\n"}])
    bold = [{"insert": "pan", "attributes": {"bold": True}}, {"insert": "\n"}]
    _type(editor, "Compra", bold)

    notes = service.list()
    assert len(notes) == 1
    assert notes[0]["title"] == "Compra"
    assert notes[0]["content"] == "pan"
    assert json.loads(notes[0]["format"])["delta"] == bold


def test_leaving_an_emptied_note_discards_it():
    service = NoteService(InMemoryNoteRepository())
    note = service.add("Algo", "Título")
    editor, captured = _build(service, note)
    proceeded = []

    _type(editor, "", [{"insert": "\n"}])
    captured["guard"](lambda: proceeded.append(True), lambda: None)

    assert service.list() == []
    assert captured["snacks"] == ["Nota vacía descartada"]
    assert proceeded == [True]


def test_leaving_a_note_with_text_keeps_it():
    service = NoteService(InMemoryNoteRepository())
    note = service.add("Algo", "Título")
    _, captured = _build(service, note)

    captured["guard"](lambda: None, lambda: None)

    assert len(service.list()) == 1


def test_undo_and_redo_only_show_when_available():
    service = NoteService(InMemoryNoteRepository())
    note = service.add("Algo", "Título")
    editor, captured = _build(service, note)

    assert _icons(captured) == [ft.Icons.DELETE_OUTLINE_ROUNDED]

    _history(editor, True, False)
    assert _icons(captured) == [ft.Icons.UNDO_ROUNDED, ft.Icons.DELETE_OUTLINE_ROUNDED]

    _history(editor, False, True)
    assert _icons(captured) == [ft.Icons.REDO_ROUNDED, ft.Icons.DELETE_OUTLINE_ROUNDED]


def test_history_buttons_are_async_so_flet_awaits_them():
    service = NoteService(InMemoryNoteRepository())
    note = service.add("Algo", "Título")
    editor, captured = _build(service, note)
    _history(editor, True, True)

    undo, redo = captured["actions"][0].content.controls[:2]

    assert inspect.iscoroutinefunction(undo.on_click)
    assert inspect.iscoroutinefunction(redo.on_click)


def test_conflicts_make_the_editor_read_only():
    service = NoteService(InMemoryNoteRepository())
    note = service.add("Algo", "Título")

    editor, captured = _build(service, note, conflicts=1)

    assert editor.read_only is True
    assert _icons(captured) == [ft.Icons.DELETE_OUTLINE_ROUNDED]


def test_preview_shows_list_markers():
    note = {
        "content": "Compra\nPan",
        "format": json.dumps(
            {
                "v": 2,
                "delta": [
                    {"insert": "Compra\nPan"},
                    {"insert": "\n", "attributes": {"list": "checked"}},
                ],
            }
        ),
    }

    assert _preview(note) == "Compra\n☑ Pan"
