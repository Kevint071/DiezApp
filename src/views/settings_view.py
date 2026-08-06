import os
import tempfile
from datetime import UTC, datetime

import flet as ft

from utils.scroll_divider import build_scroll_divider, make_scroll_divider_handler
from utils.theme import (
    FOCUS_DARK,
    FOCUS_LIGHT,
    OUTLINE_LIGHT_INPUT,
    SURFACE_DARK,
    SURFACE_LIGHT,
)

_DESKTOP_PLATFORMS = {
    ft.PagePlatform.WINDOWS,
    ft.PagePlatform.MACOS,
    ft.PagePlatform.LINUX,
}


def _is_desktop(page: ft.Page) -> bool:
    return page.platform in _DESKTOP_PLATFORMS


def build_settings_view(
    page: ft.Page, state: dict, save_settings, navigate_to_settings, colors_fn
):
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
                    ft.Icon(
                        icon,
                        size=20,
                        color=c["on_primary"]
                        if is_selected
                        else c["on_surface_variant"],
                    ),
                    ft.Text(
                        label,
                        size=15,
                        weight=ft.FontWeight.W_500,
                        color=c["on_primary"] if is_selected else c["on_surface"],
                    ),
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
        except ValueError, TypeError:
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
        except ValueError, TypeError:
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

    # ── Backup section (export / import / conflicts, calcs + notes) ─
    def _show_snack(msg: str, keep_open: bool = True):
        snack = ft.SnackBar(content=ft.Text(msg), open=True)
        page.overlay.append(snack)
        if keep_open:
            page.update()

    # ── Export dialog (notas / cálculos / ambas) ────────────────────
    export_target_state = {"target": "both"}

    export_target_group = ft.RadioGroup(
        value="both",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="notes", label="Notas", fill_color=c["primary"]),
                ft.Radio(value="calcs", label="Cálculos", fill_color=c["primary"]),
                ft.Radio(value="both", label="Ambas", fill_color=c["primary"]),
            ],
        ),
        on_change=lambda e: export_target_state.update(target=e.control.value),
    )

    def _close_export_dialog(e):
        page.pop_dialog()

    async def _confirm_export(e):
        page.pop_dialog()
        from utils.backup import export_calculations, export_notes
        from utils.notes import load_notes
        from utils.storage import load_calculations

        target = export_target_state["target"]
        calcs = load_calculations() if target in ("calcs", "both") else []
        notes = load_notes() if target in ("notes", "both") else []

        if not calcs and not notes:
            _show_snack("No hay datos guardados para exportar")
            return

        now = datetime.now(UTC).astimezone()
        file_name = now.strftime("respaldo_%Y_%m_%d_%H_%M_%S.db")

        if _is_desktop(page):
            from utils.desktop_files import pick_save_path

            output_path = await pick_save_path(file_name)
            if not output_path:
                return
            if target in ("calcs", "both"):
                export_calculations(output_path, calcs)
            if target in ("notes", "both"):
                export_notes(output_path, notes)
            _show_snack(f"Copia guardada en {output_path}", keep_open=False)
            return

        output_path = os.path.join(tempfile.gettempdir(), file_name)
        if target in ("calcs", "both"):
            export_calculations(output_path, calcs)
        if target in ("notes", "both"):
            export_notes(output_path, notes)

        share = ft.Share()
        await share.share_files(
            [ft.ShareFile.from_path(output_path, name=file_name)],
            title="Exportar copia de seguridad",
        )

    export_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Exportar", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Text(
                    "¿Qué deseas exportar?", size=14, color=c["on_surface_variant"]
                ),
                export_target_group,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_export_dialog),
            ft.FilledTonalButton("Exportar", on_click=_confirm_export),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_export_dialog(e):
        export_target_group.value = "both"
        export_target_state["target"] = "both"
        page.show_dialog(export_dialog)

    backup_cell = _settings_cell(
        icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
        title="Exportar",
        subtitle="SQLite",
        colors=c,
        on_click=_open_export_dialog,
    )

    # ── Import dialog (notas / cálculos / ambas + reemplazar / mezclar) ─
    import_target_state = {"target": "both"}
    import_state = {"mode": "merge"}

    import_target_group = ft.RadioGroup(
        value="both",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="notes", label="Notas", fill_color=c["primary"]),
                ft.Radio(value="calcs", label="Cálculos", fill_color=c["primary"]),
                ft.Radio(value="both", label="Ambas", fill_color=c["primary"]),
            ],
        ),
        on_change=lambda e: import_target_state.update(target=e.control.value),
    )

    import_mode_group = ft.RadioGroup(
        value="merge",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(
                    value="replace", label="Reemplazar todo", fill_color=c["primary"]
                ),
                ft.Radio(
                    value="merge",
                    label="Mezclar con existentes",
                    fill_color=c["primary"],
                ),
            ],
        ),
        on_change=lambda e: import_state.update(mode=e.control.value),
    )

    def _close_import_dialog(e):
        page.pop_dialog()

    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    page.update()

    def _process_calc_import(imported_calcs: list, mode: str) -> dict:
        from utils.conflicts import calcs_differ, save_conflicts
        from utils.storage import load_calculations, save_calculations

        if mode == "replace":
            save_calculations(imported_calcs)
            return {"added": len(imported_calcs), "conflicts": 0}

        existing = load_calculations()
        existing_map = {calc["id"]: calc for calc in existing if "id" in calc}
        conflicts = []
        to_add = []
        for imp_calc in imported_calcs:
            imp_id = imp_calc.get("id")
            if imp_id and imp_id in existing_map:
                if calcs_differ(existing_map[imp_id], imp_calc):
                    conflicts.append(
                        {"existing": existing_map[imp_id], "imported": imp_calc}
                    )
            else:
                to_add.append(imp_calc)

        if conflicts:
            save_conflicts(conflicts, to_add, kind="calculations")
        else:
            save_calculations(existing + to_add)
        return {"added": len(to_add), "conflicts": len(conflicts)}

    def _process_notes_import(imported_notes: list, mode: str) -> dict:
        from utils.conflicts import notes_differ, save_conflicts
        from utils.notes import load_notes, save_notes

        if mode == "replace":
            save_notes(imported_notes)
            return {"added": len(imported_notes), "conflicts": 0}

        existing = load_notes()
        existing_map = {note["id"]: note for note in existing if "id" in note}
        conflicts = []
        to_add = []
        for imp_note in imported_notes:
            imp_id = imp_note.get("id")
            if imp_id and imp_id in existing_map:
                if notes_differ(existing_map[imp_id], imp_note):
                    conflicts.append(
                        {"existing": existing_map[imp_id], "imported": imp_note}
                    )
            else:
                to_add.append(imp_note)

        if conflicts:
            save_conflicts(conflicts, to_add, kind="notes")
        else:
            save_notes(existing + to_add)
        return {"added": len(to_add), "conflicts": len(conflicts)}

    async def _confirm_import(e):
        page.pop_dialog()
        from utils.conflicts import conflict_count

        target = import_target_state["target"]
        mode = import_state["mode"]

        if (target in ("calcs", "both") and conflict_count() > 0) or (
            target in ("notes", "both") and conflict_count(kind="notes") > 0
        ):
            _show_snack("Resuelve los conflictos antes de importar")
            return

        tmp_written = None
        if _is_desktop(page):
            from utils.desktop_files import pick_open_path

            source_path = await pick_open_path()
            if not source_path:
                return
        else:
            files = await file_picker.pick_files(
                dialog_title="Seleccionar archivo SQLite",
                allowed_extensions=["db"],
                allow_multiple=False,
            )
            if not files:
                return
            picked = files[0]
            source_path = picked.path
            if not source_path and picked.bytes:
                fd, tmp_written = tempfile.mkstemp(suffix=".db")
                with os.fdopen(fd, "wb") as f:
                    f.write(picked.bytes)
                source_path = tmp_written
            if not source_path:
                return

        from utils.backup import read_calculations, read_notes

        imported_calcs, imported_notes = [], []
        try:
            if target in ("calcs", "both"):
                try:
                    imported_calcs = read_calculations(source_path)
                except ValueError:
                    if target == "calcs":
                        raise
            if target in ("notes", "both"):
                try:
                    imported_notes = read_notes(source_path)
                except ValueError:
                    if target == "notes":
                        raise
        except ValueError:
            _show_snack("Archivo SQLite inválido")
            return
        finally:
            if tmp_written and os.path.exists(tmp_written):
                os.unlink(tmp_written)

        if not imported_calcs and not imported_notes:
            _show_snack("El archivo no contiene datos para importar")
            return

        messages = []
        has_conflicts = False
        if imported_calcs:
            result = _process_calc_import(imported_calcs, mode)
            if result["conflicts"]:
                has_conflicts = True
                messages.append(f"{result['conflicts']} conflictos de cálculos")
            elif mode == "replace":
                messages.append(f"{len(imported_calcs)} cálculos importados")
            else:
                messages.append(f"{result['added']} cálculos nuevos agregados")
        if imported_notes:
            result = _process_notes_import(imported_notes, mode)
            if result["conflicts"]:
                has_conflicts = True
                messages.append(f"{result['conflicts']} conflictos de notas")
            elif mode == "replace":
                messages.append(f"{len(imported_notes)} notas importadas")
            else:
                messages.append(f"{result['added']} notas nuevas agregadas")

        if has_conflicts:
            messages.append("Resuélvelos abajo")
        _show_snack(". ".join(messages), keep_open=False)
        navigate_to_settings()

    import_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Importar", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=8,
            controls=[
                ft.Text(
                    "¿Qué deseas importar?", size=14, color=c["on_surface_variant"]
                ),
                import_target_group,
                ft.Container(height=4),
                ft.Text(
                    "¿Cómo deseas importar?", size=14, color=c["on_surface_variant"]
                ),
                import_mode_group,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_import_dialog),
            ft.FilledTonalButton("Aceptar", on_click=_confirm_import),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_import_dialog(e):
        import_target_group.value = "both"
        import_target_state["target"] = "both"
        import_mode_group.value = "merge"
        import_state["mode"] = "merge"
        page.show_dialog(import_dialog)

    import_cell = _settings_cell(
        icon=ft.Icons.FILE_UPLOAD_OUTLINED,
        title="Importar",
        subtitle="SQLite",
        colors=c,
        on_click=_open_import_dialog,
    )

    # ── Conflict resolution (single entry point for calcs + notes) ──
    from utils.conflicts import conflict_count

    n_calc_conflicts = conflict_count()
    n_notes_conflicts = conflict_count(kind="notes")
    n_total_conflicts = n_calc_conflicts + n_notes_conflicts

    def _go_to_conflicts(kind: str):
        page.session.store.set("conflicts_kind", kind)
        page.navigate("/settings/conflicts")

    def _select_conflict_kind(kind):
        def _handler(e):
            page.pop_dialog()
            _go_to_conflicts(kind)

        return _handler

    def _conflict_kind_option(label, icon, subtitle, kind):
        return ft.Container(
            on_click=_select_conflict_kind(kind),
            border_radius=12,
            padding=ft.Padding.symmetric(vertical=10, horizontal=14),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Icon(icon, size=20, color=c["on_surface_variant"]),
                    ft.Column(
                        spacing=0,
                        controls=[
                            ft.Text(
                                label,
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=c["on_surface"],
                            ),
                            ft.Text(subtitle, size=12, color=c["on_surface_variant"]),
                        ],
                    ),
                ],
            ),
        )

    conflicts_chooser_dialog = ft.AlertDialog(
        title=ft.Text("Resolver conflictos", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=20, right=20, top=12, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=6,
            controls=[
                _conflict_kind_option(
                    "Cálculos",
                    ft.Icons.CALCULATE_OUTLINED,
                    f"{n_calc_conflicts} pendientes",
                    "calculations",
                ),
                _conflict_kind_option(
                    "Notas",
                    ft.Icons.NOTE_OUTLINED,
                    f"{n_notes_conflicts} pendientes",
                    "notes",
                ),
            ],
        ),
    )

    def _open_conflicts_entry(e):
        if n_calc_conflicts > 0 and n_notes_conflicts > 0:
            page.show_dialog(conflicts_chooser_dialog)
        elif n_calc_conflicts > 0:
            _go_to_conflicts("calculations")
        elif n_notes_conflicts > 0:
            _go_to_conflicts("notes")

    conflicts_cell = _settings_cell(
        icon=ft.Icons.SYNC_PROBLEM_OUTLINED,
        title="Conflictos",
        subtitle=f"{n_total_conflicts} pendientes"
        if n_total_conflicts > 0
        else "Sin conflictos",
        colors=c,
        on_click=_open_conflicts_entry if n_total_conflicts > 0 else lambda e: None,
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

    divider = build_scroll_divider()
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=12, left=0, right=0, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    divider,
                    ft.Column(
                        expand=True,
                        spacing=0,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, c),
                        controls=[
                            ft.Container(
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=ft.Column(
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
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )


def _settings_cell(icon, title, subtitle, colors, on_click):
    """Helper to build a consistent settings row.

    ``subtitle`` may be a plain string (wrapped in a new ``ft.Text``) or an
    existing ``ft.Text`` control, so callers that need to update the label
    later (e.g. live sync status) can keep a reference to it.
    """
    subtitle_control = (
        subtitle
        if isinstance(subtitle, ft.Text)
        else ft.Text(subtitle, size=14, color=colors["on_surface_variant"])
    )
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
                        ft.Text(
                            title,
                            size=15,
                            color=colors["on_surface"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                ),
                ft.Row(
                    spacing=4,
                    controls=[
                        subtitle_control,
                        ft.Icon(
                            ft.Icons.CHEVRON_RIGHT,
                            color=colors["on_surface_variant"],
                            size=20,
                        ),
                    ],
                ),
            ],
        ),
    )
