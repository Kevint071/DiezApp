import flet as ft
from datetime import datetime

from utils.notes import load_notes, delete_note, update_note

PREVIEW_LIMIT = 100


def _format_date(date_str: str) -> str:
    try:
        d = datetime.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y %I:%M %p")
    except (ValueError, TypeError):
        return date_str


def _truncate(text: str) -> str:
    text = text.strip()
    if len(text) <= PREVIEW_LIMIT:
        return text
    truncated = text[:PREVIEW_LIMIT].rstrip()
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated.rstrip() + "…"


def build_notes_view(page: ft.Page, colors_fn, on_add, on_open, on_refresh, set_header_actions=None):
    c = colors_fn(page)
    notes = load_notes()

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

    def _build_item(note: dict):
        title = (note.get("title") or "").strip()
        content_controls = [
            ft.Text(
                _format_date(note.get("created_at", "")),
                size=12, weight=ft.FontWeight.W_600, color=c["on_surface_variant"],
            ),
        ]
        if title:
            content_controls.append(
                ft.Text(
                    title, size=15, weight=ft.FontWeight.W_700, color=c["on_surface"],
                    max_lines=1, overflow=ft.TextOverflow.ELLIPSIS,
                )
            )
        content_controls.append(
            ft.Text(
                _truncate(note.get("content", "")),
                size=14, weight=ft.FontWeight.W_400,
                color=c["on_surface_variant"] if title else c["on_surface"],
            )
        )
        return ft.Container(
            width=float("inf"),
            bgcolor=c["card_bg"],
            border_radius=12,
            padding=ft.Padding.all(16),
            margin=ft.Margin.only(bottom=12),
            ink=True,
            on_click=lambda e, n=note: on_open(n["id"]),
            content=ft.Column(
                spacing=6,
                controls=content_controls,
            ),
        )

    if not notes:
        list_content = ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=72),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.Icons.STICKY_NOTE_2_OUTLINED, size=48, color=c["on_surface_variant"]),
                    ft.Container(height=12),
                    ft.Text(
                        "No hay notas guardadas",
                        size=16, weight=ft.FontWeight.W_500, color=c["on_surface_variant"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )
    else:
        list_content = ft.Column(
            expand=True,
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            controls=[_build_item(n) for n in notes],
        )

    if set_header_actions is not None:
        set_header_actions([
            ft.Container(
                padding=ft.Padding.only(right=24),
                content=add_btn,
            )
        ])

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=16,
                controls=[
                    list_content,
                ],
            ),
        ),
    )


def build_new_note_view(page: ft.Page, colors_fn, on_save):
    c = colors_fn(page)

    title_field = ft.TextField(
        hint_text="Título",
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=8),
        text_size=20,
        text_style=ft.TextStyle(weight=ft.FontWeight.W_500, color=c["on_surface"]),
        hint_style=ft.TextStyle(size=20, weight=ft.FontWeight.W_500, color=c["on_surface_variant"]),
        cursor_color=c["primary"],
        autofocus=True,
    )

    content_field = ft.TextField(
        hint_text="Nota",
        multiline=True,
        min_lines=10,
        max_lines=20,
        expand=True,
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.symmetric(horizontal=0, vertical=8),
        text_size=14,
        text_style=ft.TextStyle(color=c["on_surface"]),
        hint_style=ft.TextStyle(size=14, color=c["on_surface_variant"]),
        cursor_color=c["primary"],
    )

    err_txt = ft.Text("", size=12, color="#DC2626", visible=False)

    def _save(e):
        from utils.conflicts import conflict_count
        if conflict_count(kind="notes") > 0:
            err_txt.value = "Resuelve los conflictos antes de guardar"
            err_txt.visible = True
            page.update()
            return
        title = (title_field.value or "").strip()
        text = (content_field.value or "").strip()
        if not text:
            err_txt.value = "Escribe algo antes de guardar"
            err_txt.visible = True
            page.update()
            return
        on_save(title, text)

    save_btn = ft.FilledButton(
        "Guardar nota",
        on_click=_save,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        width=float("inf"),
    )

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=16,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            title_field,
                            content_field,
                        ],
                    ),
                    err_txt,
                    save_btn,
                ],
            ),
        ),
    )


def build_note_detail_view(page: ft.Page, colors_fn, note: dict, on_delete, set_header_actions):
    c = colors_fn(page)

    state = {"editing": False}

    _initial_lines = max(1, note.get("content", "").count("\n") + 1)
    _has_title = bool((note.get("title") or "").strip())

    title_text = ft.Text(
        note.get("title", ""), size=20, weight=ft.FontWeight.W_500,
        color=c["on_surface"], selectable=True,
        width=float("inf"),
        visible=_has_title,
    )
    title_field = ft.TextField(
        value=note.get("title", ""),
        hint_text="Título",
        width=float("inf"),
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.only(bottom=4),
        dense=True,
        text_size=20,
        text_style=ft.TextStyle(weight=ft.FontWeight.W_700, color=c["on_surface"]),
        hint_style=ft.TextStyle(size=20, weight=ft.FontWeight.W_700, color=c["on_surface_variant"]),
        cursor_color=c["primary"],
        visible=False,
    )

    content_text = ft.Text(
        note.get("content", ""), size=15, weight=ft.FontWeight.W_400,
        color=c["on_surface"], selectable=True,
        width=float("inf"),
        style=ft.TextStyle(height=1.3),
    )
    content_field = ft.TextField(
        value=note.get("content", ""),
        hint_text="Nota",
        multiline=True,
        min_lines=_initial_lines,
        max_lines=20,
        width=float("inf"),
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.all(0),
        dense=True,
        text_size=15,
        text_style=ft.TextStyle(weight=ft.FontWeight.W_400, color=c["on_surface"], height=1.3),
        hint_style=ft.TextStyle(size=15, color=c["on_surface_variant"]),
        strut_style=ft.StrutStyle(size=15, height=1.3, weight=ft.FontWeight.W_400, force_strut_height=True),
        cursor_color=c["primary"],
        visible=False,
    )

    note_column = ft.Column(
        width=float("inf"),
        spacing=6,
        controls=[title_text, title_field, content_text, content_field],
    )

    err_txt = ft.Text("", size=12, color="#DC2626", visible=False)

    def _confirm_delete(e):
        from utils.conflicts import conflict_count
        if conflict_count(kind="notes") > 0:
            snack = ft.SnackBar(content=ft.Text("Resuelve los conflictos antes de eliminar"), open=True)
            page.overlay.append(snack)
            page.update()
            return

        def _do_delete(ev):
            delete_note(note["id"])
            page.pop_dialog()
            on_delete()

        def _cancel_delete(ev):
            page.pop_dialog()

        page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Eliminar nota", size=17, weight=ft.FontWeight.W_600),
            content=ft.Text("¿Estás seguro de que deseas eliminar esta nota?"),
            actions=[
                ft.TextButton("Cancelar", on_click=_cancel_delete),
                ft.FilledTonalButton("Eliminar", on_click=_do_delete),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ))

    def _enter_edit(e):
        from utils.conflicts import conflict_count
        if conflict_count(kind="notes") > 0:
            snack = ft.SnackBar(content=ft.Text("Resuelve los conflictos antes de editar"), open=True)
            page.overlay.append(snack)
            page.update()
            return
        state["editing"] = True
        title_field.value = note.get("title", "")
        content_field.value = note.get("content", "")
        title_text.visible = False
        title_field.visible = True
        content_text.visible = False
        content_field.visible = True
        err_txt.visible = False
        set_header_actions(edit_actions)
        page.update()

    def _cancel_edit(e):
        state["editing"] = False
        title_text.visible = bool((note.get("title") or "").strip())
        title_field.visible = False
        content_text.visible = True
        content_field.visible = False
        err_txt.visible = False
        set_header_actions(view_actions)
        page.update()

    def _save_edit(e):
        title = (title_field.value or "").strip()
        text = (content_field.value or "").strip()
        if not text:
            err_txt.value = "La nota no puede estar vacía"
            err_txt.visible = True
            page.update()
            return
        update_note(note["id"], text, title)
        note["content"] = text
        note["title"] = title
        content_text.value = text
        title_text.value = title
        state["editing"] = False
        title_text.visible = bool(title)
        title_field.visible = False
        content_text.visible = True
        content_field.visible = False
        err_txt.visible = False
        set_header_actions(view_actions)
        page.update()

    view_actions = [
        ft.Container(
            padding=ft.Padding.only(right=8),
            content=ft.Row(
                spacing=0,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.EDIT_OUTLINED, icon_color=c["on_surface"], icon_size=20,
                        tooltip="Editar", on_click=_enter_edit,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE, icon_color="#D32F2F", icon_size=20,
                        tooltip="Eliminar", on_click=_confirm_delete,
                    ),
                ],
            ),
        ),
    ]
    edit_actions = [
        ft.Container(
            padding=ft.Padding.only(right=8),
            content=ft.Row(
                spacing=0,
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.CHECK_CIRCLE, icon_color=c["primary"], icon_size=22,
                        tooltip="Guardar cambios", on_click=_save_edit,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CANCEL, icon_color=c["on_surface_variant"], icon_size=22,
                        tooltip="Descartar cambios", on_click=_cancel_edit,
                    ),
                ],
            ),
        ),
    ]

    set_header_actions(view_actions)

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                spacing=16,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    note_column,
                    err_txt,
                ],
            ),
        ),
    )
