import asyncio
import os
import tempfile
from pathlib import Path

import flet as ft

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.local_backup.application.import_backup import BackupImportService
from diezapp.features.local_backup.application.local_backup_service import (
    LocalBackupService,
)
from diezapp.features.notes.application.note_service import NoteService
from diezapp.shared.datetime_utils import local_now


def build_local_backup_section(
    page: ft.Page,
    colors: dict,
    navigate_to_settings,
    settings_cell,
    is_desktop,
    conflicts_service: ConflictService,
    backup_service: LocalBackupService,
    calculations_service: CalculationService,
    notes_service: NoteService,
):
    """Build export, import and conflict controls for the local SQLite backup."""

    def show_snack(message: str, keep_open: bool = True):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        page.overlay.append(snack)
        if keep_open:
            page.update()

    import_service = BackupImportService(
        calculations_service, notes_service, conflicts_service
    )

    export_target = {"value": "both"}
    export_method = {"value": "share"}
    export_targets = ft.RadioGroup(
        value="both",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="notes", label="Notas", fill_color=colors["primary"]),
                ft.Radio(value="calcs", label="Cálculos", fill_color=colors["primary"]),
                ft.Radio(value="both", label="Ambas", fill_color=colors["primary"]),
            ],
        ),
        on_change=lambda e: export_target.update(value=e.control.value),
    )
    export_methods = ft.RadioGroup(
        value="share",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(
                    value="share", label="Compartir", fill_color=colors["primary"]
                ),
                ft.Radio(
                    value="save",
                    label="Guardar en el dispositivo",
                    fill_color=colors["primary"],
                ),
            ],
        ),
        on_change=lambda e: export_method.update(value=e.control.value),
    )

    async def confirm_export(e):
        page.pop_dialog()

        target = export_target["value"]
        calculations = (
            calculations_service.list() if target in ("calcs", "both") else []
        )
        notes = notes_service.list() if target in ("notes", "both") else []
        if not calculations and not notes:
            show_snack("No hay datos guardados para exportar")
            return

        file_name = local_now().strftime("respaldo_%Y_%m_%d_%H_%M_%S.db")
        method = export_method["value"]
        if method == "save" and is_desktop(page):
            from diezapp.infrastructure.files.desktop_file_picker import pick_save_path

            output_path = await pick_save_path(file_name)
            if not output_path:
                return
            if target in ("calcs", "both"):
                backup_service.export_calculations(output_path, calculations)
            if target in ("notes", "both"):
                backup_service.export_notes(output_path, notes)
            show_snack(f"Copia guardada en {output_path}", keep_open=False)
            return

        output_path = os.path.join(tempfile.gettempdir(), file_name)
        if target in ("calcs", "both"):
            backup_service.export_calculations(output_path, calculations)
        if target in ("notes", "both"):
            backup_service.export_notes(output_path, notes)
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
                show_snack("Copia guardada correctamente", keep_open=False)
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
                    "¿Qué deseas exportar?", size=14, color=colors["on_surface_variant"]
                ),
                export_targets,
                ft.Text(
                    "¿Qué deseas hacer con el archivo?",
                    size=14,
                    color=colors["on_surface_variant"],
                ),
                export_methods,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledTonalButton("Exportar", on_click=confirm_export),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def open_export_dialog(e):
        export_targets.value = "both"
        export_target["value"] = "both"
        export_methods.value = "share"
        export_method["value"] = "share"
        page.show_dialog(export_dialog)

    export_cell = settings_cell(
        icon=ft.Icons.FILE_DOWNLOAD_OUTLINED,
        title="Exportar",
        subtitle="SQLite",
        colors=colors,
        on_click=open_export_dialog,
    )

    import_target = {"value": "both"}
    import_mode = {"value": "merge"}
    import_targets = ft.RadioGroup(
        value="both",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(value="notes", label="Notas", fill_color=colors["primary"]),
                ft.Radio(value="calcs", label="Cálculos", fill_color=colors["primary"]),
                ft.Radio(value="both", label="Ambas", fill_color=colors["primary"]),
            ],
        ),
        on_change=lambda e: import_target.update(value=e.control.value),
    )
    import_modes = ft.RadioGroup(
        value="merge",
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Radio(
                    value="replace",
                    label="Reemplazar todo",
                    fill_color=colors["primary"],
                ),
                ft.Radio(
                    value="merge",
                    label="Mezclar con existentes",
                    fill_color=colors["primary"],
                ),
            ],
        ),
        on_change=lambda e: import_mode.update(value=e.control.value),
    )
    file_picker = ft.FilePicker()
    page.services.append(file_picker)
    page.update()

    async def confirm_import(e):
        page.pop_dialog()

        target = import_target["value"]
        mode = import_mode["value"]
        if (target in ("calcs", "both") and conflicts_service.count() > 0) or (
            target in ("notes", "both") and conflicts_service.count(kind="notes") > 0
        ):
            show_snack("Resuelve los conflictos antes de importar")
            return

        temp_path = None
        if is_desktop(page):
            from diezapp.infrastructure.files.desktop_file_picker import pick_open_path

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
                fd, temp_path = tempfile.mkstemp(suffix=".db")
                with os.fdopen(fd, "wb") as output:
                    output.write(picked.bytes)
                source_path = temp_path
            if not source_path:
                return

        imported_calculations, imported_notes = [], []
        try:
            if target in ("calcs", "both"):
                try:
                    imported_calculations = backup_service.read_calculations(
                        source_path
                    )
                except ValueError:
                    if target == "calcs":
                        raise
            if target in ("notes", "both"):
                try:
                    imported_notes = backup_service.read_notes(source_path)
                except ValueError:
                    if target == "notes":
                        raise
        except ValueError:
            show_snack("Archivo SQLite inválido")
            return
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        if not imported_calculations and not imported_notes:
            show_snack("El archivo no contiene datos para importar")
            return

        messages, has_conflicts = [], False
        result = import_service.import_data(imported_calculations, imported_notes, mode)
        if result["calculation_conflicts"]:
            has_conflicts = True
            messages.append(f"{result['calculation_conflicts']} conflictos de cálculos")
        elif imported_calculations:
            label = "importados" if mode == "replace" else "nuevos agregados"
            messages.append(f"{result['calculations']} cálculos {label}")
        if result["note_conflicts"]:
            has_conflicts = True
            messages.append(f"{result['note_conflicts']} conflictos de notas")
        elif imported_notes:
            label = "importadas" if mode == "replace" else "nuevas agregadas"
            messages.append(f"{result['notes']} notas {label}")
        if has_conflicts:
            messages.append("Resuélvelos abajo")
        show_snack(". ".join(messages), keep_open=False)
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
                    "¿Qué deseas importar?", size=14, color=colors["on_surface_variant"]
                ),
                import_targets,
                ft.Container(height=4),
                ft.Text(
                    "¿Cómo deseas importar?",
                    size=14,
                    color=colors["on_surface_variant"],
                ),
                import_modes,
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledTonalButton("Aceptar", on_click=confirm_import),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def open_import_dialog(e):
        import_targets.value = "both"
        import_target["value"] = "both"
        import_modes.value = "merge"
        import_mode["value"] = "merge"
        page.show_dialog(import_dialog)

    import_cell = settings_cell(
        icon=ft.Icons.FILE_UPLOAD_OUTLINED,
        title="Importar",
        subtitle="SQLite",
        colors=colors,
        on_click=open_import_dialog,
    )

    calc_conflicts = conflicts_service.count()
    note_conflicts = conflicts_service.count(kind="notes")
    total_conflicts = calc_conflicts + note_conflicts

    def go_to_conflicts(kind: str):
        page.session.store.set("conflicts_kind", kind)
        page.navigate("/settings/conflicts")

    def select_conflict_kind(kind):
        def handler(e):
            page.pop_dialog()
            go_to_conflicts(kind)

        return handler

    def conflict_option(label, icon, subtitle, kind):
        return ft.Container(
            on_click=select_conflict_kind(kind),
            border_radius=12,
            padding=ft.Padding.symmetric(vertical=10, horizontal=14),
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Icon(icon, size=20, color=colors["on_surface_variant"]),
                    ft.Column(
                        spacing=0,
                        controls=[
                            ft.Text(
                                label,
                                size=15,
                                weight=ft.FontWeight.W_500,
                                color=colors["on_surface"],
                            ),
                            ft.Text(
                                subtitle, size=12, color=colors["on_surface_variant"]
                            ),
                        ],
                    ),
                ],
            ),
        )

    conflicts_dialog = ft.AlertDialog(
        title=ft.Text("Resolver conflictos", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=20, right=20, top=12, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=6,
            controls=[
                conflict_option(
                    "Cálculos",
                    ft.Icons.CALCULATE_OUTLINED,
                    f"{calc_conflicts} pendientes",
                    "calculations",
                ),
                conflict_option(
                    "Notas",
                    ft.Icons.NOTE_OUTLINED,
                    f"{note_conflicts} pendientes",
                    "notes",
                ),
            ],
        ),
    )

    def open_conflicts(e):
        if calc_conflicts > 0 and note_conflicts > 0:
            page.show_dialog(conflicts_dialog)
        elif calc_conflicts > 0:
            go_to_conflicts("calculations")
        elif note_conflicts > 0:
            go_to_conflicts("notes")

    conflicts_cell = settings_cell(
        icon=ft.Icons.SYNC_PROBLEM_OUTLINED,
        title="Conflictos",
        subtitle=f"{total_conflicts} pendientes"
        if total_conflicts > 0
        else "Sin conflictos",
        colors=colors,
        on_click=open_conflicts if total_conflicts > 0 else lambda e: None,
    )
    divider = ft.Container(
        padding=ft.Padding.symmetric(horizontal=18, vertical=0),
        content=ft.Divider(height=1, color=colors["divider"]),
    )
    return ft.Container(
        bgcolor=colors["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[export_cell, divider, import_cell, divider, conflicts_cell],
        ),
    )
