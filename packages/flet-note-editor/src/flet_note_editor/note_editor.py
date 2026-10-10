from dataclasses import dataclass

import flet as ft


@dataclass
class NoteEditorChangeEvent(ft.Event["NoteEditor"]):
    """Fired on every edit of the title or the body."""

    title: str
    """Current title text."""

    delta: str
    """Body as a Quill Delta, JSON-encoded."""


@dataclass
class NoteEditorHistoryEvent(ft.Event["NoteEditor"]):
    """Fired when undo/redo become (un)available."""

    can_undo: bool
    can_redo: bool


@ft.control("NoteEditor")
class NoteEditor(ft.LayoutControl):
    """
    A title plus a rich text body (flutter_quill) with its own format bar.

    Formatting applies to the selection, or to the word under the caret when
    nothing is selected, like a word processor.
    """

    value: str = ""
    """Body as a Quill Delta, JSON-encoded. Kept in sync while typing."""

    title: str = ""
    """Title text. Kept in sync while typing."""

    header: ft.Control | None = None
    """Control shown above the title, scrolling with the note."""

    read_only: bool = False
    autofocus_title: bool = False
    title_hint: str = "Título"
    placeholder: str = "Escribe aquí…"

    text_color: ft.ColorValue | None = None
    muted_color: ft.ColorValue | None = None
    accent_color: ft.ColorValue | None = None
    accent_container_color: ft.ColorValue | None = None
    toolbar_color: ft.ColorValue | None = None
    divider_color: ft.ColorValue | None = None

    on_change: ft.EventHandler[NoteEditorChangeEvent] | None = None
    on_history_change: ft.EventHandler[NoteEditorHistoryEvent] | None = None

    async def undo(self):
        await self._invoke_method("undo")

    async def redo(self):
        await self._invoke_method("redo")

    async def focus(self):
        await self._invoke_method("focus")
