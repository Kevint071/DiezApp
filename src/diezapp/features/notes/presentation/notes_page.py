import json

import flet as ft
from flet_note_editor import NoteEditor

from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.notes.application.note_service import NoteService
from diezapp.features.notes.domain import note_document
from diezapp.shared.datetime_utils import to_local_datetime
from diezapp.shared.presentation.dialogs import (
    build_dialog,
    dialog_cancel_button,
    dialog_primary_button,
)
from diezapp.shared.presentation.input_border import outline_input_border

PREVIEW_LIMIT = 100


def _format_date(date_str: str) -> str:
    try:
        d = to_local_datetime(date_str)
        return d.strftime("%d/%m/%Y %I:%M %p")
    except ValueError, TypeError:
        return date_str


def _preview(note: dict) -> str:
    """Note text for the list card; list items keep their bullet or box."""
    return note_document.preview(
        note_document.to_delta(note.get("content"), note.get("format"))
    )


def _truncate(text: str) -> str:
    text = text.strip()
    if len(text) <= PREVIEW_LIMIT:
        return text
    truncated = text[:PREVIEW_LIMIT].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"


def build_notes_view(
    page: ft.Page,
    colors_fn,
    on_add,
    on_open,
    on_refresh,
    notes_service: NoteService,
    conflicts_service: ConflictService,
    set_header_actions=None,
):
    c = colors_fn(page)
    notes = notes_service.sort_for_display(notes_service.list())

    add_btn = ft.FilledButton(
        "Nueva nota",
        icon=ft.Icons.ADD_ROUNDED,
        on_click=lambda e: on_add(),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=8, horizontal=10),
            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
        ),
    )

    def _matches_query(note: dict, query: str) -> bool:
        q = query.strip().lower()
        if not q:
            return True
        return (
            q in (note.get("title") or "").lower()
            or q in (note.get("content") or "").lower()
        )

    def _build_item(note: dict):
        title = (note.get("title") or "").strip()
        display_date = note.get("updated_at") or note.get("created_at", "")
        content_controls = [
            ft.Text(
                _format_date(display_date),
                size=12,
                weight=ft.FontWeight.W_600,
                color=c["on_surface_variant"],
            ),
        ]
        if title:
            content_controls.append(
                ft.Text(
                    title,
                    size=15,
                    weight=ft.FontWeight.W_700,
                    color=c["on_surface"],
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        content_controls.append(
            ft.Text(
                _truncate(_preview(note)),
                size=14,
                weight=ft.FontWeight.W_400,
                color=c["on_surface_variant"] if title else c["on_surface"],
            )
        )
        return ft.Container(
            width=float("inf"),
            bgcolor=c["card_bg"],
            border_radius=12,
            padding=ft.Padding.all(16),
            margin=ft.Margin.only(right=24, left=24, bottom=12),
            ink=True,
            on_click=lambda e, n=note: on_open(n["id"]),
            content=ft.Column(
                spacing=6,
                controls=content_controls,
            ),
        )

    def _build_empty_state(icon, message: str):
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=72),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=48, color=c["on_surface_variant"]),
                    ft.Container(height=12),
                    ft.Text(
                        message,
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=c["on_surface_variant"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    def _build_list_content(query: str):
        if not notes:
            return _build_empty_state(
                ft.Icons.STICKY_NOTE_2_OUTLINED, "No hay notas guardadas"
            )
        filtered = [n for n in notes if _matches_query(n, query)]
        if not filtered:
            return _build_empty_state(
                ft.Icons.SEARCH_OFF_ROUNDED, "No se encontraron notas"
            )
        return ft.Column(
            expand=True,
            spacing=0,
            scroll=ft.Scrollbar(thickness=6, radius=4),
            controls=[_build_item(n) for n in filtered],
        )

    results_container = ft.Container(expand=True, content=_build_list_content(""))

    def _set_clear_btn_active(active: bool):
        clear_btn.opacity = 1 if active else 0
        clear_btn.disabled = not active

    def _clear_search(e):
        search_field.value = ""
        _set_clear_btn_active(False)
        results_container.content = _build_list_content("")
        page.update()

    def _on_search_change(e):
        query = search_field.value or ""
        _set_clear_btn_active(bool(query))
        results_container.content = _build_list_content(query)
        page.update()

    clear_btn = ft.IconButton(
        icon=ft.Icons.CLOSE_ROUNDED,
        icon_size=18,
        icon_color=c["on_surface_variant"],
        tooltip="Limpiar búsqueda",
        opacity=0,
        disabled=True,
        style=ft.ButtonStyle(padding=ft.Padding.all(4)),
        size_constraints=ft.BoxConstraints(
            min_width=32, min_height=32, max_width=32, max_height=32
        ),
        on_click=_clear_search,
    )

    search_field = ft.TextField(
        hint_text="Buscar por título o contenido",
        hint_style=ft.TextStyle(size=14, color=c["on_surface_variant"]),
        text_style=ft.TextStyle(size=14, color=c["on_surface"]),
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        width=float("inf"),
        border=outline_input_border(c["card_bg"], c["input_focused"]),
        filled=True,
        bgcolor=c["card_bg"],
        content_padding=ft.Padding.only(top=10, bottom=10, left=14, right=44),
        dense=True,
        cursor_color=c["primary"],
        on_change=_on_search_change,
    )

    search_field_stack = ft.Stack(
        controls=[
            search_field,
            ft.Container(
                content=clear_btn,
                alignment=ft.Alignment.CENTER,
                right=4,
                top=0,
                bottom=0,
            ),
        ],
    )

    if set_header_actions is not None:
        set_header_actions(
            [
                ft.Container(
                    padding=ft.Padding.only(right=24),
                    content=add_btn,
                )
            ]
        )

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=0, right=0, top=4, bottom=0),
            content=ft.Column(
                expand=True,
                spacing=16,
                controls=[
                    ft.Container(
                        margin=ft.Margin.symmetric(horizontal=24),
                        content=search_field_stack,
                        visible=bool(notes),
                    ),
                    results_container,
                ],
            ),
        ),
    )


def build_note_editor_view(
    page: ft.Page,
    colors_fn,
    note: dict | None,
    *,
    notes_service: NoteService,
    conflicts_service: ConflictService,
    set_header_actions,
    register_leave_guard,
    on_deleted,
    show_snack,
):
    """A note that saves itself on every keystroke; ``note=None`` starts one.

    The editor itself is the ``NoteEditor`` extension (flutter_quill), so
    formatting applies to the selection or the word under the caret. A new
    note only reaches the database once it has some text, and a note left
    completely empty is discarded on the way out (like Keep does).
    """
    c = colors_fn(page)
    state = {
        "note": note,
        "can_undo": False,
        "can_redo": False,
        "actions": None,
    }
    read_only = conflicts_service.count(kind="notes") > 0

    status_text = ft.Text(
        size=12, weight=ft.FontWeight.W_500, color=c["on_surface_variant"]
    )
    status_row = ft.Row(
        spacing=6,
        controls=[
            ft.Icon(
                ft.Icons.CLOUD_DONE_OUTLINED,
                size=14,
                color=c["on_surface_variant"],
            ),
            status_text,
        ],
    )

    def _set_status():
        # A note that isn't saved yet shows nothing; the "Guardado" line
        # appears with the first save.
        current = state["note"]
        status_row.visible = current is not None
        if current is not None:
            saved_at = current.get("updated_at") or current.get("created_at", "")
            status_text.value = f"Guardado · {_format_date(saved_at)}"

    def _persist(title: str, delta: list):
        content, fmt = note_document.serialize(delta)
        current = state["note"]
        if current is None:
            if not title.strip() and not content.strip():
                return
            state["note"] = notes_service.add(content, title, fmt)
        else:
            state["note"] = (
                notes_service.update(current["id"], content, title, fmt) or current
            )
        _set_status()
        _refresh_actions()

    def _on_change(e):
        _persist(e.title, json.loads(e.delta))

    def _on_history_change(e):
        state["can_undo"] = e.can_undo
        state["can_redo"] = e.can_redo
        _refresh_actions()

    def _history_button(icon, tooltip, handler):
        return ft.IconButton(
            icon=icon,
            icon_size=22,
            tooltip=tooltip,
            icon_color=c["on_surface"],
            on_click=handler,
        )

    async def _undo(e):
        await editor.undo()

    async def _redo(e):
        await editor.redo()

    def _build_actions():
        # Undo/redo only appear once there is something to take back or redo.
        controls = []
        if state["can_undo"]:
            controls.append(_history_button(ft.Icons.UNDO_ROUNDED, "Deshacer", _undo))
        if state["can_redo"]:
            controls.append(_history_button(ft.Icons.REDO_ROUNDED, "Rehacer", _redo))
        if state["note"] is not None:
            controls.append(
                ft.PopupMenuButton(
                    icon=ft.Icons.MORE_VERT_ROUNDED,
                    icon_color=c["on_surface"],
                    tooltip="Más opciones",
                    bgcolor=c["card_bg"],
                    shape=ft.RoundedRectangleBorder(radius=14),
                    items=[
                        ft.PopupMenuItem(
                            icon=ft.Icon(
                                ft.Icons.DELETE_OUTLINE_ROUNDED, color=c["error"]
                            ),
                            content=ft.Text("Eliminar nota", color=c["error"]),
                            on_click=_confirm_delete,
                        )
                    ],
                )
            )
        return [
            ft.Container(
                padding=ft.Padding.only(right=8),
                content=ft.Row(spacing=0, controls=controls),
            )
        ]

    def _refresh_actions():
        key = (state["can_undo"], state["can_redo"], state["note"] is not None)
        if key != state["actions"]:
            state["actions"] = key
            set_header_actions(_build_actions())

    def _confirm_delete(e):
        if conflicts_service.count(kind="notes") > 0:
            show_snack("Resuelve los conflictos antes de eliminar")
            return

        def _do_delete(ev):
            notes_service.delete(state["note"]["id"])
            state["note"] = None
            page.pop_dialog()
            on_deleted()

        page.show_dialog(
            build_dialog(
                c,
                modal=True,
                title="Eliminar nota",
                content="¿Estás seguro de que deseas eliminar esta nota?",
                actions=[
                    dialog_cancel_button("Cancelar", lambda ev: page.pop_dialog(), c),
                    dialog_primary_button("Eliminar", _do_delete, c, destructive=True),
                ],
            )
        )

    def _leave_guard(proceed, cancel):
        current = state["note"]
        if (
            current is not None
            and not read_only
            and not (current.get("title") or "").strip()
            and not (current.get("content") or "").strip()
        ):
            notes_service.delete(current["id"])
            state["note"] = None
            show_snack("Nota vacía descartada")
        proceed()

    if read_only:
        header = ft.Container(
            border_radius=12,
            bgcolor=c["warning_bg"],
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(ft.Icons.LOCK_OUTLINE_ROUNDED, size=18, color=c["warning"]),
                    ft.Text(
                        "Resuelve los conflictos de notas para poder editar",
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=c["warning"],
                        expand=True,
                    ),
                ],
            ),
        )
    else:
        header = status_row

    source = note or {}
    editor = NoteEditor(
        expand=True,
        value=json.dumps(
            note_document.to_delta(source.get("content"), source.get("format"))
        ),
        title=source.get("title") or "",
        header=header,
        read_only=read_only,
        autofocus_title=note is None and not read_only,
        text_color=c["on_surface"],
        muted_color=c["on_surface_variant"],
        accent_color=c["primary"],
        accent_container_color=c["navigation_indicator"],
        toolbar_color=c["card_bg"],
        divider_color=c["header_divider"],
        on_change=_on_change,
        on_history_change=_on_history_change,
    )

    _set_status()
    _refresh_actions()
    if register_leave_guard is not None:
        register_leave_guard(_leave_guard)

    return ft.SafeArea(expand=True, content=editor)
