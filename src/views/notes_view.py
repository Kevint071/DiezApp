import flet as ft
from datetime import datetime

from utils.theme import FOCUS_LIGHT, FOCUS_DARK, OUTLINE_LIGHT_INPUT
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
            padding=ft.Padding.symmetric(vertical=12, horizontal=16),
            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
        ),
    )

    def _build_item(note: dict):
        return ft.Container(
            width=float("inf"),
            bgcolor=c["card_bg"],
            border_radius=12,
            padding=ft.Padding.all(16),
            margin=ft.Margin.only(bottom=12),
            ink=True,
            on_click=lambda e, n=note: on_open(n["id"]),
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text(
                        _format_date(note.get("created_at", "")),
                        size=12, weight=ft.FontWeight.W_600, color=c["on_surface_variant"],
                    ),
                    ft.Text(
                        _truncate(note.get("content", "")),
                        size=14, weight=ft.FontWeight.W_400, color=c["on_surface"],
                    ),
                ],
            ),
        )

    if not notes:
        list_content = ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=60),
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
                content=ft.Container(
                    width=140,
                    content=add_btn,
                ),
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
    light = page.theme_mode == ft.ThemeMode.LIGHT
    c = colors_fn(page)
    focus_color = FOCUS_LIGHT if light else FOCUS_DARK
    input_border = OUTLINE_LIGHT_INPUT if light else c["outline"]

    content_field = ft.TextField(
        hint_text="Escribe tu nota...",
        multiline=True,
        min_lines=10,
        max_lines=20,
        expand=True,
        border_radius=12,
        border_color=input_border,
        focused_border_color=focus_color,
        content_padding=ft.Padding.all(16),
        text_size=14,
        autofocus=True,
    )

    err_txt = ft.Text("", size=12, color="#DC2626", visible=False)

    def _save(e):
        from utils.conflicts import conflict_count
        if conflict_count(kind="notes") > 0:
            err_txt.value = "Resuelve los conflictos antes de guardar"
            err_txt.visible = True
            page.update()
            return
        text = (content_field.value or "").strip()
        if not text:
            err_txt.value = "Escribe algo antes de guardar"
            err_txt.visible = True
            page.update()
            return
        on_save(text)

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
                    content_field,
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

    content_text = ft.Text(
        note.get("content", ""), size=15, weight=ft.FontWeight.W_400,
        color=c["on_surface"], selectable=True,
        width=float("inf"),
        style=ft.TextStyle(height=1.3),
    )
    content_field = ft.TextField(
        value=note.get("content", ""),
        multiline=True,
        min_lines=_initial_lines,
        max_lines=20,
        width=float("inf"),
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.all(0),
        dense=True,
        text_size=15,
        text_style=ft.TextStyle(weight=ft.FontWeight.W_400, color=c["on_surface"], height=1.3),
        strut_style=ft.StrutStyle(size=15, height=1.3, weight=ft.FontWeight.W_400, force_strut_height=True),
        cursor_color=c["primary"],
        visible=False,
    )

    content_box = ft.Container(
        width=float("inf"),
        bgcolor=ft.Colors.TRANSPARENT,
        border=ft.Border.all(1, c["outline"]),
        border_radius=16,
        padding=ft.Padding.all(20),
        content=ft.Column(
            controls=[content_text, content_field],
        ),
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
        content_field.value = note.get("content", "")
        content_text.visible = False
        content_field.visible = True
        content_box.border = ft.Border.all(1.5, c["primary"])
        err_txt.visible = False
        set_header_actions(edit_actions)
        page.update()

    def _cancel_edit(e):
        state["editing"] = False
        content_text.visible = True
        content_field.visible = False
        content_box.border = ft.Border.all(1, c["outline"])
        err_txt.visible = False
        set_header_actions(view_actions)
        page.update()

    def _save_edit(e):
        text = (content_field.value or "").strip()
        if not text:
            err_txt.value = "La nota no puede estar vacía"
            err_txt.visible = True
            page.update()
            return
        update_note(note["id"], text)
        note["content"] = text
        content_text.value = text
        state["editing"] = False
        content_text.visible = True
        content_field.visible = False
        content_box.border = ft.Border.all(1, c["outline"])
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
                    content_box,
                    err_txt,
                ],
            ),
        ),
    )
