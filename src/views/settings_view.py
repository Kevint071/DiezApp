import asyncio
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import flet as ft
import httpx

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
    page: ft.Page,
    state: dict,
    save_settings,
    navigate_to_settings,
    colors_fn,
    navigate_to_google_drive,
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
    export_method_state = {"method": "share"}

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

    export_method_group = ft.RadioGroup(
        value="share",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="share", label="Compartir", fill_color=c["primary"]),
                ft.Radio(
                    value="save",
                    label="Guardar en el dispositivo",
                    fill_color=c["primary"],
                ),
            ],
        ),
        on_change=lambda e: export_method_state.update(method=e.control.value),
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
        method = export_method_state["method"]

        if method == "save" and _is_desktop(page):
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

        if method == "save":
            backup_bytes = await asyncio.to_thread(Path(output_path).read_bytes)
            saved_path = await file_picker.save_file(
                dialog_title="Guardar copia de seguridad",
                file_name=file_name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["db"],
                src_bytes=backup_bytes,
            )
            if saved_path:
                _show_snack("Copia guardada correctamente", keep_open=False)
            return

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
                ft.Text(
                    "¿Qué deseas hacer con el archivo?",
                    size=14,
                    color=c["on_surface_variant"],
                ),
                export_method_group,
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
        export_method_group.value = "share"
        export_method_state["method"] = "share"
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

    export_import_group = ft.Container(
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

    google_drive_cell = _settings_cell(
        icon=ft.Icons.CLOUD_OUTLINED,
        title="Copias de seguridad",
        subtitle="Google Drive",
        colors=c,
        on_click=lambda e: navigate_to_google_drive(),
    )
    google_drive_group = ft.Container(
        bgcolor=c["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=google_drive_cell,
    )

    divider = build_scroll_divider()
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=4, left=0, right=0, bottom=0),
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
                                            "Exportar e importar",
                                            size=13,
                                            weight=ft.FontWeight.W_600,
                                            color=c["on_surface_variant"],
                                        ),
                                        export_import_group,
                                        ft.Text(
                                            "Nube",
                                            size=13,
                                            weight=ft.FontWeight.W_600,
                                            color=c["on_surface_variant"],
                                        ),
                                        google_drive_group,
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )


def _build_gdrive_backups_section(
    page: ft.Page,
    c: dict,
    navigate_to_settings,
    show_snack,
    navigate_to_history,
):
    """Build the 'Copias de seguridad' (Google Drive) settings section.

    Rebuilt (via ``navigate_to_settings()``) after every mutating action —
    same pattern already used by the export/import dialogs above — rather
    than patching individual controls in place.
    """
    from utils.gdrive_auth import (
        can_add_account,
        ensure_fresh_access_token,
        is_configured,
        list_accounts,
        remove_account,
        set_account_folder,
        start_link_flow,
    )
    from utils.gdrive_backup import (
        get_interval_seconds,
        run_backup_now,
        set_interval_seconds,
    )
    from utils.gdrive_client import DriveApiError, create_folder, list_folders

    pending_message = page.session.store.get("gdrive_link_message")
    if pending_message:
        page.session.store.remove("gdrive_link_message")
        show_snack(pending_message, keep_open=False)

    accounts = list_accounts()

    async def _link_account(e):
        if not is_configured(page):
            show_snack("OAuth de Google no configurado")
            return
        started = await start_link_flow(page)
        if not started:
            show_snack("Ya hay 2 cuentas vinculadas")

    def _unlink_account(account_id):
        def _handler(e):
            remove_account(account_id)
            navigate_to_settings()

        return _handler

    folder_name_field = ft.TextField(label="Nombre de la carpeta")
    folder_dialog_state = {
        "account_id": None,
        "parent_id": "root",
        "parent_name": "Mi unidad",
        "stack": [],
    }
    folder_title = ft.Text("Seleccionar carpeta", size=17, weight=ft.FontWeight.W_600)
    folder_path = ft.Text("Mi unidad", size=13, color=c["on_surface_variant"])
    folder_loading = ft.ProgressRing(width=22, height=22, visible=False)
    folder_list = ft.Column(spacing=0, tight=True, scroll=ft.ScrollMode.AUTO)

    def _close_folder_dialog(e):
        page.pop_dialog()

    async def _load_folder_list(parent_id, parent_name):
        account_id = folder_dialog_state["account_id"]
        account = next((a for a in list_accounts() if a["id"] == account_id), None)
        if account is None:
            return
        access_token = await ensure_fresh_access_token(page, account)
        if not access_token:
            show_snack("No se pudo autenticar la cuenta")
            return
        folder_dialog_state["parent_id"] = parent_id
        folder_dialog_state["parent_name"] = parent_name
        path_names = [
            "Mi unidad"
        ] + [
            name
            for _, name in folder_dialog_state["stack"]
            if name != "Mi unidad"
        ]
        if parent_name != "Mi unidad":
            path_names.append(parent_name)
        folder_path.value = " / ".join(path_names)
        folder_loading.visible = True
        folder_list.controls = []
        page.update()
        try:
            folders = await list_folders(access_token, parent_id)
        except DriveApiError as error:
            show_snack(f"Drive {error.status_code} ({error.reason}): {error.message}")
            return
        except httpx.HTTPError:
            show_snack("No se pudo conectar con Google Drive")
            return
        finally:
            folder_loading.visible = False
            page.update()
        folder_list.controls = [
            ft.ListTile(
                leading=ft.Icon(ft.Icons.FOLDER_OUTLINED, color=c["primary"]),
                title=ft.Text(folder["name"]),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                on_click=lambda e, item=folder: _enter_folder(item),
            )
            for folder in folders
        ] or [
            ft.Container(
                padding=ft.Padding.symmetric(vertical=16),
                content=ft.Text("No hay subcarpetas", color=c["on_surface_variant"]),
            )
        ]
        page.update()

    async def _enter_folder(folder):
        folder_dialog_state["stack"].append(
            (folder_dialog_state["parent_id"], folder_dialog_state["parent_name"])
        )
        await _load_folder_list(folder["id"], folder["name"])

    async def _go_to_parent(e):
        if not folder_dialog_state["stack"]:
            return
        parent_id, parent_name = folder_dialog_state["stack"].pop()
        await _load_folder_list(parent_id, parent_name)

    def _select_current_folder(e):
        set_account_folder(
            folder_dialog_state["account_id"],
            folder_dialog_state["parent_id"],
            folder_dialog_state["parent_name"],
        )
        page.pop_dialog()
        navigate_to_settings()

    async def _create_folder(e):
        account_id = folder_dialog_state["account_id"]
        account = next((a for a in list_accounts() if a["id"] == account_id), None)
        folder_name = folder_name_field.value.strip()
        if not account or not folder_name:
            show_snack("Escribe un nombre para la carpeta")
            return
        access_token = await ensure_fresh_access_token(page, account)
        if not access_token:
            show_snack("No se pudo autenticar la cuenta")
            return
        try:
            folder_id = await create_folder(
                access_token, folder_name, folder_dialog_state["parent_id"]
            )
        except DriveApiError as error:
            show_snack(f"Drive {error.status_code} ({error.reason}): {error.message}")
            return
        except httpx.HTTPError:
            show_snack("No se pudo conectar con Google Drive")
            return
        set_account_folder(account_id, folder_id, folder_name)
        page.pop_dialog()
        navigate_to_settings()

    folder_dialog = ft.AlertDialog(
        title=ft.Column(spacing=2, controls=[folder_title, folder_path]),
        content=ft.Column(
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.IconButton(
                            ft.Icons.ARROW_BACK,
                            tooltip="Carpeta padre",
                            on_click=_go_to_parent,
                        ),
                        folder_loading,
                    ]
                ),
                ft.Container(
                    height=260,
                    width=360,
                    content=folder_list,
                ),
                ft.Divider(height=16),
                ft.Text("Crear carpeta en esta ubicación", size=13, color=c["on_surface_variant"]),
                folder_name_field,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_folder_dialog),
            ft.FilledTonalButton("Usar esta carpeta", on_click=_select_current_folder),
            ft.FilledButton("Crear", on_click=_create_folder),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_folder_dialog(account_id):
        def _handler(e):
            folder_dialog_state["account_id"] = account_id
            folder_dialog_state["parent_id"] = "root"
            folder_dialog_state["parent_name"] = "Mi unidad"
            folder_dialog_state["stack"] = []
            folder_name_field.value = "Respaldos DiezApp"
            folder_path.value = "Mi unidad"
            page.show_dialog(folder_dialog)
            page.run_task(_load_folder_list, "root", "Mi unidad")

        return _handler

    def _divider():
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=18, vertical=0),
            content=ft.Divider(height=1, color=c["divider"]),
        )

    def _account_row(account):
        has_folder = bool(account.get("folder_id"))
        subtitle = account["folder_name"] if has_folder else "Elegir carpeta"
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=10, horizontal=18),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Icon(
                        ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                        size=28,
                        color=c["primary"],
                    ),
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Text(
                                account["google_account_email"],
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=c["on_surface"],
                            ),
                            ft.Container(
                                on_click=_open_folder_dialog(account["id"]),
                                content=ft.Text(
                                    f"Carpeta: {subtitle}",
                                    size=13,
                                    color=c["on_surface_variant"]
                                    if has_folder
                                    else c["primary"],
                                ),
                            ),
                        ],
                    ),
                    ft.IconButton(
                        ft.Icons.LINK_OFF,
                        icon_size=20,
                        tooltip="Desvincular cuenta",
                        on_click=_unlink_account(account["id"]),
                    ),
                ],
            ),
        )

    # ── Frequency picker ─────────────────────────────────────────────
    interval_seconds = get_interval_seconds()
    d0, rem0 = divmod(interval_seconds or 0, 86400)
    h0, rem0 = divmod(rem0, 3600)
    m0, _rem0 = divmod(rem0, 60)

    days_field = ft.TextField(
        label="Días", value=str(d0), keyboard_type=ft.KeyboardType.NUMBER, width=90
    )
    hours_field = ft.TextField(
        label="Horas", value=str(h0), keyboard_type=ft.KeyboardType.NUMBER, width=90
    )
    minutes_field = ft.TextField(
        label="Minutos", value=str(m0), keyboard_type=ft.KeyboardType.NUMBER, width=90
    )

    def _close_freq_dialog(e):
        page.pop_dialog()

    def _confirm_freq(e):
        try:
            d, h, m = (
                int(days_field.value or 0),
                int(hours_field.value or 0),
                int(minutes_field.value or 0),
            )
        except ValueError:
            show_snack("Ingresa valores numéricos válidos")
            return
        total = d * 86400 + h * 3600 + m * 60
        if total <= 0:
            show_snack("La frecuencia debe ser mayor a 0")
            return
        set_interval_seconds(total)
        page.pop_dialog()
        navigate_to_settings()

    freq_dialog = ft.AlertDialog(
        title=ft.Text("Frecuencia de respaldo", size=17, weight=ft.FontWeight.W_600),
        content=ft.Row(spacing=8, controls=[days_field, hours_field, minutes_field]),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_freq_dialog),
            ft.FilledTonalButton("Guardar", on_click=_confirm_freq),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_freq_dialog(e):
        page.show_dialog(freq_dialog)

    def _format_interval(seconds):
        if not seconds:
            return "Sin configurar"
        d, rem = divmod(seconds, 86400)
        h, rem = divmod(rem, 3600)
        m, _rem = divmod(rem, 60)
        parts = [f"{v}{unit}" for v, unit in ((d, "d"), (h, "h"), (m, "min")) if v]
        return " ".join(parts) if parts else "Sin configurar"

    freq_cell = _settings_cell(
        icon=ft.Icons.SCHEDULE_OUTLINED,
        title="Frecuencia",
        subtitle=_format_interval(interval_seconds),
        colors=c,
        on_click=_open_freq_dialog,
    )

    # ── Manual "Respaldar ahora" button ──────────────────────────────
    backup_now_button = ft.IconButton(
        icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
        icon_size=22,
        tooltip="Respaldar ahora",
    )

    backup_accounts = [account for account in accounts if account.get("folder_id")]
    backup_account_checks = [
        ft.Checkbox(
            label=account["google_account_email"],
            value=True,
        )
        for account in backup_accounts
    ]

    def _close_backup_dialog(e):
        page.pop_dialog()

    async def _confirm_backup(e):
        selected_ids = {
            account["id"]
            for account, checkbox in zip(
                backup_accounts, backup_account_checks, strict=True
            )
            if checkbox.value
        }
        if not selected_ids:
            show_snack("Selecciona al menos una cuenta")
            return
        page.pop_dialog()
        await _run_backup(selected_ids)

    backup_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Respaldar ahora", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=12, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Text(
                    "Elige dónde guardar esta copia.",
                    size=14,
                    color=c["on_surface_variant"],
                ),
                *backup_account_checks,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_backup_dialog),
            ft.FilledButton("Respaldar", on_click=_confirm_backup),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    backup_action = ft.Container(
        padding=ft.Padding.symmetric(vertical=12, horizontal=18),
        content=ft.Row(
            spacing=12,
            controls=[
                ft.Icon(
                    ft.Icons.CLOUD_UPLOAD_OUTLINED,
                    size=24,
                    color=c["primary"],
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Respaldo manual",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=c["on_surface"],
                        ),
                        ft.Text(
                            "Guarda una copia en tus cuentas vinculadas",
                            size=12,
                            color=c["on_surface_variant"],
                        ),
                    ],
                ),
                backup_now_button,
            ],
        ),
    )

    async def _run_backup(selected_ids):
        backup_now_button.icon = ft.ProgressRing(width=16, height=16)
        backup_now_button.disabled = True
        page.update()
        result = await run_backup_now(page, selected_ids)
        status = result["status"]
        if status == "skipped":
            show_snack(result.get("message", "No hay cuentas configuradas"))
        elif status == "success":
            show_snack("Copia de seguridad completada", keep_open=False)
        elif status == "partial":
            show_snack("Copia parcial: alguna cuenta falló")
        else:
            show_snack("No se pudo completar la copia de seguridad")
        navigate_to_settings()

    def _open_backup_dialog(e):
        if not backup_accounts:
            show_snack("Configura una carpeta en al menos una cuenta")
            return
        for checkbox in backup_account_checks:
            checkbox.value = True
        page.show_dialog(backup_dialog)

    backup_now_button.on_click = _open_backup_dialog

    # ── Assemble section ──────────────────────────────────────────────
    account_header = ft.Container(
        padding=ft.Padding.only(top=18, bottom=12, left=18, right=18),
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            controls=[
                ft.Icon(
                    ft.Icons.CLOUD_OUTLINED,
                    size=36,
                    color=c["primary"],
                ),
                ft.Text(
                    "Cuentas de respaldo",
                    size=20,
                    weight=ft.FontWeight.W_600,
                    color=c["on_surface"],
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    "Aún no hay cuentas vinculadas"
                    if not accounts
                    else f"{len(accounts)} de 2 cuentas vinculadas",
                    size=13,
                    color=c["on_surface_variant"],
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
        ),
    )

    can_link_more = can_add_account()
    controls = [account_header]

    if can_link_more:
        connect_button = (
            ft.FilledButton(
                "Conectar Google",
                icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                on_click=_link_account,
            )
            if not accounts
            else ft.OutlinedButton(
                "Añadir cuenta",
                icon=ft.Icons.ADD,
                on_click=_link_account,
            )
        )
        controls.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=12, horizontal=18),
                alignment=ft.Alignment(0, 0),
                content=connect_button,
            )
        )

    if accounts:
        controls.append(_divider())
        controls.extend(
            control
            for account in accounts
            for control in (_account_row(account), _divider())
        )

    controls.append(freq_cell)
    controls.append(_divider())
    controls.append(backup_action)
    controls.append(_divider())
    controls.append(
        _settings_cell(
            icon=ft.Icons.HISTORY_OUTLINED,
            title="Copias realizadas",
            subtitle=None,
            colors=c,
            on_click=lambda e: navigate_to_history(),
        )
    )

    return ft.Column(spacing=0, controls=controls)


def _settings_cell(icon, title, subtitle=None, colors=None, on_click=None):
    """Helper to build a consistent settings row.

    ``subtitle`` may be a plain string (wrapped in a new ``ft.Text``) or an
    existing ``ft.Text`` control, so callers that need to update the label
    later (e.g. live sync status) can keep a reference to it.
    """
    trailing_controls = [
        ft.Icon(
            ft.Icons.CHEVRON_RIGHT,
            color=colors["on_surface_variant"],
            size=20,
        )
    ]
    if subtitle is not None:
        subtitle_control = (
            subtitle
            if isinstance(subtitle, ft.Text)
            else ft.Text(subtitle, size=14, color=colors["on_surface_variant"])
        )
        trailing_controls.insert(0, subtitle_control)
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
                    controls=trailing_controls,
                ),
            ],
        ),
    )
