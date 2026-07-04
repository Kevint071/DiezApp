import json
import os
import tempfile
from datetime import datetime

import flet as ft

from utils.theme import (
    ON_SURFACE_LIGHT,
    ON_SURFACE_DARK,
    FOCUS_LIGHT,
    FOCUS_DARK,
    OUTLINE_LIGHT_INPUT,
    SURFACE_LIGHT,
    SURFACE_DARK,
)


def apply_settings_appbar(page: ft.Page, on_navigate_back, colors_fn):
    light = page.theme_mode == ft.ThemeMode.LIGHT
    fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
    page.appbar = ft.AppBar(
        leading=ft.Container(
            width=40,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: on_navigate_back(),
            content=ft.Image(
                src="chevron-left.svg",
                width=24,
                height=24,
                color=fg,
            ),
        ),
        title=ft.Text(
            "Configuración",
            color=fg,
            weight=ft.FontWeight.W_700,
            size=17,
        ),
        center_title=False,
        leading_width=40,
        title_spacing=0,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
    )


def build_settings_view(page: ft.Page, state: dict, save_settings, navigate_to_settings, colors_fn):
    """Build the settings view."""
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT

    # Theme row
    theme_label = "Claro" if light else "Oscuro"

    def _on_theme_selected(mode: str):
        if mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = SURFACE_LIGHT
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = SURFACE_DARK
        save_settings(mode, state["fund_percentage"])
        page.pop_dialog()
        navigate_to_settings()

    def _theme_option(label, icon, mode, is_selected):
        return ft.Container(
            on_click=lambda e: _on_theme_selected(mode),
            border_radius=12,
            padding=ft.Padding.symmetric(vertical=12, horizontal=14),
            bgcolor=c["primary"] if is_selected else ft.Colors.TRANSPARENT,
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Icon(icon, size=20, color=c["on_primary"] if is_selected else c["on_surface_variant"]),
                    ft.Text(label, size=15, weight=ft.FontWeight.W_500, color=c["on_primary"] if is_selected else c["on_surface"]),
                ],
            ),
        )

    theme_dialog = ft.AlertDialog(
        title=ft.Text("Tema", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=20, right=20, top=12, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=6,
            controls=[
                _theme_option("Claro", ft.Icons.LIGHT_MODE_OUTLINED, "light", light),
                _theme_option("Oscuro", ft.Icons.DARK_MODE_OUTLINED, "dark", not light),
            ],
        ),
    )

    def _open_theme_dialog(e):
        page.show_dialog(theme_dialog)

    theme_cell = _settings_cell(
        icon=ft.Icons.PALETTE_OUTLINED,
        title="Tema",
        subtitle=theme_label,
        colors=c,
        on_click=_open_theme_dialog,
    )

    # Fund percentage row + modal
    fund_percentage = state["fund_percentage"]

    focus_color = FOCUS_LIGHT if light else FOCUS_DARK
    input_border = OUTLINE_LIGHT_INPUT if light else c["outline"]

    def _on_pct_change(e):
        raw = pct_field.value.strip()
        if not raw:
            pct_field.error = None
            pct_dialog.update()
            return
        try:
            val = int(raw)
        except (ValueError, TypeError):
            pct_field.error = "Ingresa un número válido"
            pct_dialog.update()
            return
        if val < 1 or val > 30:
            pct_field.error = "Debe ser entre 1% y 30%"
        else:
            pct_field.error = None
        pct_dialog.update()

    pct_field = ft.TextField(
        label="Porcentaje",
        value=str(fund_percentage),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        content_padding=ft.Padding.symmetric(vertical=14, horizontal=14),
        suffix=ft.Text("%", color=c["on_surface_variant"]),
        border_color=input_border,
        focused_border_color=focus_color,
        on_submit=lambda e: _save_pct(e),
        on_change=_on_pct_change,
    )

    def _close_pct_dialog(e):
        page.pop_dialog()

    def _save_pct(e):
        raw = pct_field.value.strip()
        try:
            val = int(raw)
        except (ValueError, TypeError):
            pct_field.error = "Ingresa un número válido"
            pct_dialog.update()
            return
        if val < 1 or val > 30:
            pct_field.error = "Debe ser entre 1% y 30%"
            pct_dialog.update()
            return
        pct_field.error = None
        state["fund_percentage"] = val
        current_mode = "dark" if page.theme_mode == ft.ThemeMode.DARK else "light"
        save_settings(current_mode, val)
        page.pop_dialog()
        navigate_to_settings()

    pct_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Aporte al fondo local", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=0,
            controls=[pct_field],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_pct_dialog),
            ft.FilledTonalButton("Guardar", on_click=_save_pct),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_pct_dialog(e):
        pct_field.value = str(state["fund_percentage"])
        pct_field.error = None
        page.show_dialog(pct_dialog)

    fund_cell = _settings_cell(
        icon=ft.Icons.SAVINGS_OUTLINED,
        title="Fondo local",
        subtitle=f"{fund_percentage}%",
        colors=c,
        on_click=_open_pct_dialog,
    )

    # Section header + grouped cells
    settings_group = ft.Container(
        bgcolor=c["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[
                theme_cell,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=0),
                    content=ft.Divider(height=1, color=c["divider"]),
                ),
                fund_cell,
            ],
        ),
    )

    # ── Backup section ─────────────────────────────────────────────
    async def _export_json_backup(e):
        from utils.storage import load_calculations
        calculations = load_calculations()
        if not calculations:
            snack = ft.SnackBar(content=ft.Text("No hay cálculos guardados"), open=True)
            page.overlay.append(snack)
            page.update()
            return
        now = datetime.now()
        file_name = now.strftime("calculos_%Y_%m_%d_%H_%M_%S.json")
        tmp_dir = tempfile.gettempdir()
        output_path = os.path.join(tmp_dir, file_name)
        data = {"calculations": calculations}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        share = ft.Share()
        await share.share_files(
            [ft.ShareFile.from_path(output_path, name=file_name)],
            title="Exportar copia de seguridad",
        )

    backup_cell = _settings_cell(
        icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
        title="Exportar cálculos",
        subtitle="JSON",
        colors=c,
        on_click=_export_json_backup,
    )

    # ── Import ─────────────────────────────────────────────────────
    import_state = {"mode": "merge"}

    radio_group = ft.RadioGroup(
        value="merge",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="replace", label="Reemplazar todo", fill_color=c["primary"]),
                ft.Radio(value="merge", label="Mezclar con existentes", fill_color=c["primary"]),
            ],
        ),
        on_change=lambda e: _on_radio_change(e),
    )

    def _on_radio_change(e):
        import_state["mode"] = e.control.value

    def _close_import_dialog(e):
        page.pop_dialog()

    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    page.update()

    def _calcs_differ(a: dict, b: dict) -> bool:
        keys = ["amount", "envio_21", "restante", "fondo_local", "sostenimiento", "fund_percentage"]
        return any(a.get(k) != b.get(k) for k in keys)

    async def _confirm_import(e):
        page.pop_dialog()
        files = await file_picker.pick_files(
            dialog_title="Seleccionar archivo JSON",
            allowed_extensions=["json"],
            allow_multiple=False,
        )
        if not files:
            return
        picked = files[0]
        raw = None
        if picked.bytes:
            raw = picked.bytes.decode("utf-8")
        elif picked.path:
            with open(picked.path, "r", encoding="utf-8") as f:
                raw = f.read()
        if not raw:
            return
        try:
            imported = json.loads(raw)
            imported_calcs = imported.get("calculations", [])
        except (json.JSONDecodeError, AttributeError):
            snack = ft.SnackBar(content=ft.Text("Archivo JSON inválido"), open=True)
            page.overlay.append(snack)
            page.update()
            return

        if not imported_calcs:
            snack = ft.SnackBar(content=ft.Text("El archivo no contiene cálculos"), open=True)
            page.overlay.append(snack)
            page.update()
            return

        from utils.storage import load_calculations, save_calculations
        from utils.conflicts import save_conflicts

        if import_state["mode"] == "replace":
            save_calculations(imported_calcs)
            snack = ft.SnackBar(content=ft.Text(f"{len(imported_calcs)} cálculos importados (reemplazo)"), open=True)
            page.overlay.append(snack)
            page.update()
        else:
            # Merge mode - detect conflicts by id
            existing = load_calculations()
            existing_map = {calc["id"]: calc for calc in existing if "id" in calc}
            conflicts = []
            to_add = []
            for imp_calc in imported_calcs:
                imp_id = imp_calc.get("id")
                if imp_id and imp_id in existing_map:
                    ex_calc = existing_map[imp_id]
                    if _calcs_differ(ex_calc, imp_calc):
                        conflicts.append({"existing": ex_calc, "imported": imp_calc})
                else:
                    to_add.append(imp_calc)

            if conflicts:
                # Save conflicts to file for later resolution
                save_conflicts(conflicts, to_add)
                snack = ft.SnackBar(
                    content=ft.Text(f"{len(conflicts)} conflictos detectados. Resuélvelos abajo."),
                    open=True,
                )
                page.overlay.append(snack)
                navigate_to_settings()
            else:
                # No conflicts, just add new ones
                merged = existing + to_add
                save_calculations(merged)
                snack = ft.SnackBar(
                    content=ft.Text(f"{len(to_add)} cálculos nuevos agregados"),
                    open=True,
                )
                page.overlay.append(snack)
                page.update()

    import_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Importar cálculos", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Text("¿Cómo deseas importar?", size=14, color=c["on_surface_variant"]),
                radio_group,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_import_dialog),
            ft.FilledTonalButton("Aceptar", on_click=_confirm_import),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_import_dialog(e):
        from utils.conflicts import conflict_count
        if conflict_count() > 0:
            snack = ft.SnackBar(content=ft.Text("Resuelve los conflictos antes de importar"), open=True)
            page.overlay.append(snack)
            page.update()
            return
        radio_group.value = "merge"
        import_state["mode"] = "merge"
        page.show_dialog(import_dialog)

    import_cell = _settings_cell(
        icon=ft.Icons.FILE_UPLOAD_OUTLINED,
        title="Importar cálculos",
        subtitle="JSON",
        colors=c,
        on_click=_open_import_dialog,
    )

    # ── Conflict resolution ────────────────────────────────────────
    from utils.conflicts import conflict_count
    n_conflicts = conflict_count()

    def _navigate_to_conflicts(e):
        from views.conflicts_view import build_conflicts_view, apply_conflicts_appbar
        apply_conflicts_appbar(page, navigate_to_settings)
        page.controls.clear()
        page.add(build_conflicts_view(page, colors_fn, on_back=navigate_to_settings))

    conflicts_cell = _settings_cell(
        icon=ft.Icons.SYNC_PROBLEM_OUTLINED,
        title="Resolver conflictos",
        subtitle=f"{n_conflicts} pendientes" if n_conflicts > 0 else "Sin conflictos",
        colors=c,
        on_click=_navigate_to_conflicts if n_conflicts > 0 else lambda e: None,
    )

    # ── Notes backup (export / import / conflicts) ─────────────────
    async def _export_notes_backup(e):
        from utils.notes import load_notes
        notes = load_notes()
        if not notes:
            snack = ft.SnackBar(content=ft.Text("No hay notas guardadas"), open=True)
            page.overlay.append(snack)
            page.update()
            return
        now = datetime.now()
        file_name = now.strftime("notas_%Y_%m_%d_%H_%M_%S.json")
        tmp_dir = tempfile.gettempdir()
        output_path = os.path.join(tmp_dir, file_name)
        data = {"notes": notes}
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        share = ft.Share()
        await share.share_files(
            [ft.ShareFile.from_path(output_path, name=file_name)],
            title="Exportar notas",
        )

    notes_backup_cell = _settings_cell(
        icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
        title="Exportar notas",
        subtitle="JSON",
        colors=c,
        on_click=_export_notes_backup,
    )

    notes_import_state = {"mode": "merge"}

    notes_radio_group = ft.RadioGroup(
        value="merge",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="replace", label="Reemplazar todo", fill_color=c["primary"]),
                ft.Radio(value="merge", label="Mezclar con existentes", fill_color=c["primary"]),
            ],
        ),
        on_change=lambda e: notes_import_state.update(mode=e.control.value),
    )

    def _close_notes_import_dialog(e):
        page.pop_dialog()

    notes_file_picker = ft.FilePicker()
    page.services.append(notes_file_picker)
    page.update()

    def _notes_differ(a: dict, b: dict) -> bool:
        return a.get("content") != b.get("content")

    async def _confirm_notes_import(e):
        page.pop_dialog()
        files = await notes_file_picker.pick_files(
            dialog_title="Seleccionar archivo JSON",
            allowed_extensions=["json"],
            allow_multiple=False,
        )
        if not files:
            return
        picked = files[0]
        raw = None
        if picked.bytes:
            raw = picked.bytes.decode("utf-8")
        elif picked.path:
            with open(picked.path, "r", encoding="utf-8") as f:
                raw = f.read()
        if not raw:
            return
        try:
            imported = json.loads(raw)
            imported_notes = imported.get("notes", [])
        except (json.JSONDecodeError, AttributeError):
            snack = ft.SnackBar(content=ft.Text("Archivo JSON inválido"), open=True)
            page.overlay.append(snack)
            page.update()
            return

        if not imported_notes:
            snack = ft.SnackBar(content=ft.Text("El archivo no contiene notas"), open=True)
            page.overlay.append(snack)
            page.update()
            return

        from utils.notes import load_notes, save_notes
        from utils.conflicts import save_conflicts

        if notes_import_state["mode"] == "replace":
            save_notes(imported_notes)
            snack = ft.SnackBar(content=ft.Text(f"{len(imported_notes)} notas importadas (reemplazo)"), open=True)
            page.overlay.append(snack)
            page.update()
        else:
            # Merge mode - detect conflicts by id
            existing = load_notes()
            existing_map = {note["id"]: note for note in existing if "id" in note}
            conflicts = []
            to_add = []
            for imp_note in imported_notes:
                imp_id = imp_note.get("id")
                if imp_id and imp_id in existing_map:
                    ex_note = existing_map[imp_id]
                    if _notes_differ(ex_note, imp_note):
                        conflicts.append({"existing": ex_note, "imported": imp_note})
                else:
                    to_add.append(imp_note)

            if conflicts:
                save_conflicts(conflicts, to_add, kind="notes")
                snack = ft.SnackBar(
                    content=ft.Text(f"{len(conflicts)} conflictos detectados. Resuélvelos abajo."),
                    open=True,
                )
                page.overlay.append(snack)
                navigate_to_settings()
            else:
                merged = existing + to_add
                save_notes(merged)
                snack = ft.SnackBar(
                    content=ft.Text(f"{len(to_add)} notas nuevas agregadas"),
                    open=True,
                )
                page.overlay.append(snack)
                page.update()

    notes_import_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Importar notas", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Text("¿Cómo deseas importar?", size=14, color=c["on_surface_variant"]),
                notes_radio_group,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_notes_import_dialog),
            ft.FilledTonalButton("Aceptar", on_click=_confirm_notes_import),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_notes_import_dialog(e):
        from utils.conflicts import conflict_count
        if conflict_count(kind="notes") > 0:
            snack = ft.SnackBar(content=ft.Text("Resuelve los conflictos antes de importar"), open=True)
            page.overlay.append(snack)
            page.update()
            return
        notes_radio_group.value = "merge"
        notes_import_state["mode"] = "merge"
        page.show_dialog(notes_import_dialog)

    notes_import_cell = _settings_cell(
        icon=ft.Icons.FILE_UPLOAD_OUTLINED,
        title="Importar notas",
        subtitle="JSON",
        colors=c,
        on_click=_open_notes_import_dialog,
    )

    from utils.conflicts import conflict_count as _notes_conflict_count
    n_notes_conflicts = _notes_conflict_count(kind="notes")

    def _navigate_to_notes_conflicts(e):
        from views.conflicts_view import build_conflicts_view, apply_conflicts_appbar
        apply_conflicts_appbar(page, navigate_to_settings, kind="notes")
        page.controls.clear()
        page.add(build_conflicts_view(page, colors_fn, on_back=navigate_to_settings, kind="notes"))

    notes_conflicts_cell = _settings_cell(
        icon=ft.Icons.SYNC_PROBLEM_OUTLINED,
        title="Resolver conflictos",
        subtitle=f"{n_notes_conflicts} pendientes" if n_notes_conflicts > 0 else "Sin conflictos",
        colors=c,
        on_click=_navigate_to_notes_conflicts if n_notes_conflicts > 0 else lambda e: None,
    )

    notes_backup_group = ft.Container(
        bgcolor=c["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[
                notes_backup_cell,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=0),
                    content=ft.Divider(height=1, color=c["divider"]),
                ),
                notes_import_cell,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=0),
                    content=ft.Divider(height=1, color=c["divider"]),
                ),
                notes_conflicts_cell,
            ],
        ),
    )

    backup_group = ft.Container(
        bgcolor=c["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[
                backup_cell,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=0),
                    content=ft.Divider(height=1, color=c["divider"]),
                ),
                import_cell,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=0),
                    content=ft.Divider(height=1, color=c["divider"]),
                ),
                conflicts_cell,
            ],
        ),
    )

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=12, left=24, right=24, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=12,
                controls=[
                    ft.Text(
                        "General",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=c["on_surface_variant"],
                    ),
                    settings_group,
                    ft.Text(
                        "Copia de seguridad",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=c["on_surface_variant"],
                    ),
                    backup_group,
                    ft.Text(
                        "Notas",
                        size=13,
                        weight=ft.FontWeight.W_600,
                        color=c["on_surface_variant"],
                    ),
                    notes_backup_group,
                ],
            ),
        ),
    )


def _settings_cell(icon, title, subtitle, colors, on_click):
    """Helper to build a consistent settings row."""
    return ft.Container(
        on_click=on_click,
        padding=ft.Padding.symmetric(vertical=14, horizontal=18),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=14,
                    controls=[
                        ft.Icon(icon, size=22, color=colors["primary"]),
                        ft.Text(title, size=15, color=colors["on_surface"], weight=ft.FontWeight.W_500),
                    ],
                ),
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.Text(subtitle, size=14, color=colors["on_surface_variant"]),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=colors["on_surface_variant"], size=20),
                    ],
                ),
            ],
        ),
    )
