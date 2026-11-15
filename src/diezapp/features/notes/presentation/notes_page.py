import json

import flet as ft
from flet_note_editor import NoteEditor

from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.notes.application.note_service import NoteService
from diezapp.features.notes.domain import note_document
from diezapp.features.notes.presentation.note_colors import (
    NOTE_COLORS,
    note_bgcolor,
    note_muted,
)
from diezapp.shared.datetime_utils import to_local_datetime
from diezapp.shared.presentation.dialogs import (
    build_dialog,
    dialog_cancel_button,
    dialog_primary_button,
)
from diezapp.shared.presentation.input_border import outline_input_border
from diezapp.shared.presentation.theme import is_light

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
    show_snack=None,
):
    """The note cards, in the order the user gave them.

    Each card has a ⋮ menu (colour, reorder, select, delete). A long press
    starts selecting: checkboxes appear on the left and the bar above the
    list paints or deletes every selected note at once. "Reordenar" turns
    the list into a drag-and-drop one until "Listo".
    """
    c = colors_fn(page)
    light = is_light(page)
    notes = notes_service.list()
    state = {"query": "", "selected": [], "reordering": False}

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

    def _visible_notes() -> list[dict]:
        if state["reordering"]:
            return notes
        return [n for n in notes if _matches_query(n, state["query"])]

    def _reload():
        notes[:] = notes_service.list()
        ids = {n["id"] for n in notes}
        state["selected"] = [i for i in state["selected"] if i in ids]

    def _blocked() -> bool:
        """Changing notes while note conflicts wait would muddle them."""
        if conflicts_service.count(kind="notes") == 0:
            return False
        if show_snack is not None:
            show_snack("Resuelve los conflictos de notas primero", kind="warning")
        return True

    # ── Actions ────────────────────────────────────────────

    def _toggle(note_id: str):
        selected = state["selected"]
        if note_id in selected:
            selected.remove(note_id)
        else:
            selected.append(note_id)
        _render()

    def _start_selecting(note_id: str):
        if state["reordering"]:
            return
        if note_id not in state["selected"]:
            state["selected"].append(note_id)
        _render()

    def _clear_selection(e=None):
        state["selected"] = []
        _render()

    def _select_all(e):
        visible = [n["id"] for n in _visible_notes()]
        everything = all(i in state["selected"] for i in visible)
        state["selected"] = [] if everything else visible
        _render()

    def _start_reordering(e=None):
        if _blocked():
            return
        state["reordering"] = True
        state["selected"] = []
        state["query"] = ""
        search_field.value = ""
        _set_clear_btn_active(False)
        _render()

    def _stop_reordering(e=None):
        state["reordering"] = False
        _render()

    def _on_reorder(e: ft.OnReorderEvent):
        old, new = e.old_index, e.new_index
        if old is None or new is None or old == new:
            return
        note = notes.pop(old)
        notes.insert(new, note)
        notes_service.move(note["id"], new)
        list_view = e.control
        list_view.controls.insert(new, list_view.controls.pop(old))
        list_view.update()

    def _ask_color(note_ids: list[str]):
        if not note_ids or _blocked():
            return
        chosen = {n.get("color") for n in notes if n["id"] in note_ids}
        current = chosen.pop() if len(chosen) == 1 else "unset"

        def _apply(key):
            notes_service.set_color(note_ids, key)
            page.pop_dialog()
            state["selected"] = []
            _reload()
            _render()

        def _swatch(key, bgcolor, tooltip, icon=None):
            active = key == current
            return ft.Container(
                width=44,
                height=44,
                border_radius=22,
                bgcolor=bgcolor,
                border=ft.Border.all(
                    2.5 if active else 1, c["primary"] if active else c["outline"]
                ),
                alignment=ft.Alignment.CENTER,
                tooltip=tooltip,
                ink=True,
                on_click=lambda e, k=key: _apply(k),
                content=ft.Icon(
                    ft.Icons.CHECK_ROUNDED if active else icon,
                    size=20,
                    color=c["on_surface"],
                )
                if active or icon
                else None,
            )

        swatches = [
            _swatch(None, c["card_bg"], "Sin color", ft.Icons.FORMAT_COLOR_RESET),
            *(
                _swatch(key, lit if light else dark, label)
                for key, (label, lit, dark) in NOTE_COLORS.items()
            ),
        ]
        count = len(note_ids)
        page.show_dialog(
            build_dialog(
                c,
                title="Color de la nota" if count == 1 else f"Color de {count} notas",
                content=ft.Row(
                    wrap=True, spacing=12, run_spacing=12, controls=swatches
                ),
                actions=[
                    dialog_cancel_button("Cancelar", lambda e: page.pop_dialog(), c)
                ],
            )
        )

    def _ask_delete(note_ids: list[str]):
        if not note_ids or _blocked():
            return
        count = len(note_ids)

        def _do_delete(e):
            notes_service.delete_many(note_ids)
            page.pop_dialog()
            state["selected"] = []
            _reload()
            _render()

        page.show_dialog(
            build_dialog(
                c,
                modal=True,
                title="Eliminar nota" if count == 1 else f"Eliminar {count} notas",
                content="¿Estás seguro de que deseas eliminar esta nota?"
                if count == 1
                else f"¿Estás seguro de que deseas eliminar estas {count} notas?",
                actions=[
                    dialog_cancel_button("Cancelar", lambda e: page.pop_dialog(), c),
                    dialog_primary_button("Eliminar", _do_delete, c, destructive=True),
                ],
            )
        )

    # ── Cards ──────────────────────────────────────────────

    def _menu(note: dict, icon_color: str):
        def _item(icon, text, handler, color=None):
            return ft.PopupMenuItem(
                icon=ft.Icon(icon, size=20, color=color or c["on_surface"]),
                content=ft.Text(text, size=14, color=color or c["on_surface"]),
                on_click=handler,
            )

        note_id = note["id"]
        return ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT_ROUNDED,
            icon_color=icon_color,
            icon_size=20,
            tooltip="Opciones",
            bgcolor=c["card_bg"],
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=4,
            items=[
                _item(
                    ft.Icons.PALETTE_OUTLINED,
                    "Color",
                    lambda e: _ask_color([note_id]),
                ),
                _item(ft.Icons.SWAP_VERT_ROUNDED, "Reordenar", _start_reordering),
                _item(
                    ft.Icons.CHECK_BOX_OUTLINED,
                    "Seleccionar",
                    lambda e: _start_selecting(note_id),
                ),
                _item(
                    ft.Icons.DELETE_OUTLINE_ROUNDED,
                    "Eliminar",
                    lambda e: _ask_delete([note_id]),
                    color=c["error"],
                ),
            ],
        )

    def _build_item(note: dict):
        note_id = note["id"]
        selecting = bool(state["selected"])
        selected = note_id in state["selected"]
        reordering = state["reordering"]
        muted = note_muted(note.get("color"), light, c["on_surface_variant"])
        title = (note.get("title") or "").strip()
        display_date = note.get("updated_at") or note.get("created_at", "")
        content_controls = [
            ft.Text(
                _format_date(display_date),
                size=12,
                weight=ft.FontWeight.W_600,
                color=muted,
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
                color=muted if title else c["on_surface"],
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )

        if reordering:
            trailing = ft.ReorderableDragHandle(
                content=ft.Container(
                    padding=ft.Padding.all(4),
                    content=ft.Icon(
                        ft.Icons.DRAG_INDICATOR_ROUNDED, size=22, color=muted
                    ),
                ),
                mouse_cursor=ft.MouseCursor.GRAB,
            )
        elif selecting:
            trailing = None
        else:
            trailing = _menu(note, muted)

        if reordering:
            on_click = None
            on_long_press = None
        elif selecting:
            on_click = lambda e, i=note_id: _toggle(i)
            on_long_press = on_click
        else:
            on_click = lambda e, i=note_id: on_open(i)
            on_long_press = lambda e, i=note_id: _start_selecting(i)

        card = ft.Container(
            expand=True,
            bgcolor=note_bgcolor(note.get("color"), light, c["card_bg"]),
            border_radius=12,
            border=ft.Border.all(2, c["primary"]) if selected else None,
            padding=ft.Padding.only(left=16, top=14, right=8, bottom=16),
            ink=on_click is not None,
            on_click=on_click,
            on_long_press=on_long_press,
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Column(spacing=6, expand=True, controls=content_controls),
                    *([trailing] if trailing is not None else []),
                ],
            ),
        )
        controls = [card]
        if selecting:
            controls.insert(
                0,
                ft.Checkbox(
                    value=selected,
                    active_color=c["primary"],
                    on_change=lambda e, i=note_id: _toggle(i),
                ),
            )
        return ft.Container(
            key=note_id,
            margin=ft.Margin.only(left=12 if selecting else 24, right=24, bottom=12),
            content=ft.Row(spacing=0, controls=controls),
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

    def _build_list_content():
        if not notes:
            return _build_empty_state(
                ft.Icons.STICKY_NOTE_2_OUTLINED, "No hay notas guardadas"
            )
        visible = _visible_notes()
        if not visible:
            return _build_empty_state(
                ft.Icons.SEARCH_OFF_ROUNDED, "No se encontraron notas"
            )
        return ft.ReorderableListView(
            expand=True,
            spacing=0,
            show_default_drag_handles=False,
            on_reorder=_on_reorder,
            controls=[_build_item(n) for n in visible],
        )

    # ── Bar above the list ─────────────────────────────────

    def _set_clear_btn_active(active: bool):
        clear_btn.opacity = 1 if active else 0
        clear_btn.disabled = not active

    def _clear_search(e):
        search_field.value = ""
        state["query"] = ""
        _set_clear_btn_active(False)
        _render()

    def _on_search_change(e):
        state["query"] = search_field.value or ""
        _set_clear_btn_active(bool(state["query"]))
        _render()

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

    def _bar_button(icon, tooltip, handler, color=None):
        return ft.IconButton(
            icon=icon,
            icon_size=22,
            icon_color=color or c["on_surface"],
            tooltip=tooltip,
            on_click=handler,
        )

    def _action_bar(controls):
        return ft.Container(
            height=48,
            bgcolor=c["card_bg"],
            border_radius=12,
            padding=ft.Padding.symmetric(horizontal=4),
            content=ft.Row(
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=controls,
            ),
        )

    def _build_bar():
        if state["reordering"]:
            return _action_bar(
                [
                    ft.Container(width=8),
                    ft.Icon(
                        ft.Icons.DRAG_INDICATOR_ROUNDED,
                        size=20,
                        color=c["on_surface_variant"],
                    ),
                    ft.Container(width=8),
                    ft.Text(
                        "Arrastra las notas para ordenarlas",
                        size=14,
                        weight=ft.FontWeight.W_500,
                        color=c["on_surface"],
                        expand=True,
                    ),
                    ft.TextButton(
                        "Listo",
                        style=ft.ButtonStyle(color=c["primary"]),
                        on_click=_stop_reordering,
                    ),
                ]
            )
        if state["selected"]:
            count = len(state["selected"])
            return _action_bar(
                [
                    _bar_button(
                        ft.Icons.CLOSE_ROUNDED, "Cancelar selección", _clear_selection
                    ),
                    ft.Text(
                        "1 seleccionada" if count == 1 else f"{count} seleccionadas",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=c["on_surface"],
                        expand=True,
                    ),
                    _bar_button(ft.Icons.SELECT_ALL_ROUNDED, "Todas", _select_all),
                    _bar_button(
                        ft.Icons.PALETTE_OUTLINED,
                        "Color",
                        lambda e: _ask_color(list(state["selected"])),
                    ),
                    _bar_button(
                        ft.Icons.DELETE_OUTLINE_ROUNDED,
                        "Eliminar",
                        lambda e: _ask_delete(list(state["selected"])),
                        color=c["error"],
                    ),
                ]
            )
        return search_field_stack

    bar_container = ft.Container(
        margin=ft.Margin.symmetric(horizontal=24),
        content=_build_bar(),
        visible=bool(notes),
    )
    results_container = ft.Container(expand=True, content=_build_list_content())

    def _render():
        bar_container.content = _build_bar()
        bar_container.visible = bool(notes)
        results_container.content = _build_list_content()
        page.update()

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
                controls=[bar_container, results_container],
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
    formatting applies to the selection or the word under the caret. Undo and
    redo live in the editor too, on a row above its formatting bar. A new
    note only reaches the database once it has some text, and a note left
    completely empty is discarded on the way out (like Keep does).
    """
    c = colors_fn(page)
    state = {"note": note, "actions": None}
    read_only = conflicts_service.count(kind="notes") > 0

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
        _refresh_actions()

    def _on_change(e):
        _persist(e.title, json.loads(e.delta))

    def _build_actions():
        if state["note"] is None:
            return []
        return [
            ft.Container(
                padding=ft.Padding.only(right=8),
                content=ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE_ROUNDED,
                    icon_size=22,
                    icon_color=c["error"],
                    tooltip="Eliminar nota",
                    on_click=_confirm_delete,
                ),
            )
        ]

    def _refresh_actions():
        key = state["note"] is not None
        if key != state["actions"]:
            state["actions"] = key
            set_header_actions(_build_actions())

    def _confirm_delete(e):
        if conflicts_service.count(kind="notes") > 0:
            show_snack("Resuelve los conflictos antes de eliminar", kind="warning")
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

    header = None
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
    )

    _refresh_actions()
    if register_leave_guard is not None:
        register_leave_guard(_leave_guard)

    return ft.SafeArea(expand=True, content=editor)
