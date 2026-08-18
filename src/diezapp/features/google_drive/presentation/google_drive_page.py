import asyncio
import os
import tempfile

import flet as ft

from diezapp.features.google_drive.application.backup_schedule_settings import (
    BackupScheduleSettings,
)
from diezapp.features.google_drive.application.drive_folder_service import (
    DriveFolderService,
)
from diezapp.features.google_drive.application.oauth_flow import GoogleDriveOAuthFlow
from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)
from diezapp.features.google_drive.application.run_backup import (
    GoogleDriveBackupService,
)
from diezapp.features.google_drive.domain.repositories import BackupHistoryRepository
from diezapp.features.google_drive.presentation.settings_google_drive_section import (
    _build_gdrive_backups_section,
)
from diezapp.features.local_backup.application.import_backup import (
    BackupImportService,
)
from diezapp.infrastructure.google.drive_client import (
    delete_file,
    download_file,
    list_backup_files,
)
from diezapp.shared.datetime_utils import to_local_datetime


def build_google_drive_view(
    page: ft.Page,
    colors_fn,
    refresh_view,
    navigate_to_history,
    account_service,
    url_opener,
    schedule_settings: BackupScheduleSettings,
    backup_service: GoogleDriveBackupService,
    refresh_access_token: RefreshAccessToken,
    oauth_flow: GoogleDriveOAuthFlow,
    folder_service: DriveFolderService,
):
    """Build the dedicated Google Drive account and backup management view."""
    colors = colors_fn(page)

    def show_snack(message: str, keep_open: bool = True):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        page.overlay.append(snack)
        if keep_open:
            page.update()

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=4, left=24, right=24),
            content=_build_gdrive_backups_section(
                page,
                colors,
                refresh_view,
                show_snack,
                navigate_to_history,
                account_service,
                url_opener,
                schedule_settings,
                backup_service,
                refresh_access_token,
                oauth_flow,
                folder_service,
            ),
        ),
    )


def build_google_drive_history_view(
    page: ft.Page,
    colors_fn,
    history_repository: BackupHistoryRepository,
    account_service,
    refresh_access_token: RefreshAccessToken,
    local_backup,
    calculations_service,
    notes_service,
    conflicts_service,
):
    """Build the Drive backup browser and its import/delete actions."""
    colors = colors_fn(page)

    content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=12)
    import_service = BackupImportService(
        calculations_service, notes_service, conflicts_service
    )

    def show_snack(message: str):
        page.overlay.append(ft.SnackBar(content=ft.Text(message), open=True))
        page.update()

    def format_size(value: str | None) -> str:
        try:
            size = int(value or 0)
        except ValueError:
            return "Tamaño desconocido"
        if size < 1024 * 1024:
            return f"{max(1, size // 1024)} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def format_modified(value: str | None) -> str:
        if not value:
            return "Fecha desconocida"
        try:
            return to_local_datetime(value).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return value

    async def remove_temp_file(path: str | None):
        if not path:
            return
        for attempt in range(5):
            try:
                os.unlink(path)
                return
            except FileNotFoundError:
                return
            except PermissionError:
                if attempt < 4:
                    await asyncio.sleep(0.1)

    def show_import_options(calculations: list, notes: list):
        def close(e):
            page.pop_dialog()

        def import_with_mode(mode: str):
            def handler(e):
                page.pop_dialog()
                result = import_service.import_data(calculations, notes, mode)
                calculation_conflicts = result["calculation_conflicts"]
                note_conflicts = result["note_conflicts"]
                if calculation_conflicts or note_conflicts:
                    parts = []
                    if calculation_conflicts:
                        parts.append(f"{calculation_conflicts} de cálculos")
                    if note_conflicts:
                        parts.append(f"{note_conflicts} de notas")
                    page.session.store.set(
                        "conflicts_kind",
                        "calculations" if calculation_conflicts else "notes",
                    )
                    show_snack(
                        "Se detectaron conflictos "
                        + " y ".join(parts)
                        + ". Puedes resolverlos en Conflictos."
                    )
                    page.navigate("/settings/conflicts")
                    return
                if mode == "replace":
                    message = (
                        f"Reemplazados {len(calculations)} cálculos y "
                        f"{len(notes)} notas"
                    )
                else:
                    message = (
                        f"Agregados {result['calculations']} cálculos y "
                        f"{result['notes']} notas nuevos"
                    )
                show_snack(message)

            return handler

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("¿Cómo quieres importar?"),
                content=ft.Text(
                    "Mezclar conserva tus datos y permite resolver choques. "
                    "Reemplazar todo borra el contenido actual de cálculos y notas."
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=close),
                    ft.OutlinedButton(
                        "Mezclar y revisar conflictos",
                        on_click=import_with_mode("merge"),
                    ),
                    ft.FilledButton(
                        "Reemplazar todo", on_click=import_with_mode("replace")
                    ),
                ],
                actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

    def add_import_dialog(account, file):
        def close(e):
            page.pop_dialog()

        async def import_copy(e):
            page.pop_dialog()
            temp_path = None
            try:
                token = await refresh_access_token.execute(account)
                if not token:
                    raise ValueError("No se pudo renovar el acceso a Google Drive")
                descriptor, temp_path = tempfile.mkstemp(suffix=".db")
                os.close(descriptor)
                await download_file(token, file["id"], temp_path)
                calculations = local_backup.read_calculations(temp_path)
                notes = local_backup.read_notes(temp_path)
                await remove_temp_file(temp_path)
                temp_path = None
                show_import_options(calculations, notes)
            except Exception as error:  # noqa: BLE001 - import errors are user-facing
                show_snack(f"No se pudo importar la copia: {error}")
            finally:
                await remove_temp_file(temp_path)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Importar copia"),
                content=ft.Text(
                    "Se agregarán los cálculos y notas que todavía no existan en la app."
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=close),
                    ft.FilledButton("Importar y agregar", on_click=import_copy),
                ],
            )
        )

    async def remove_copy(account, file):
        try:
            token = await refresh_access_token.execute(account)
            if not token:
                raise ValueError("No se pudo renovar el acceso a Google Drive")
            await delete_file(token, file["id"])
            show_snack("Copia eliminada de Google Drive")
            await load_backups()
        except ValueError as error:
            show_snack(str(error))
        except Exception as error:  # noqa: BLE001 - Drive errors are user-facing
            show_snack(f"No se pudo eliminar la copia: {error}")

    async def confirm_remove(account, file):
        def close(e):
            page.pop_dialog()

        async def remove(e):
            page.pop_dialog()
            await remove_copy(account, file)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar copia"),
                content=ft.Text(f"¿Quieres enviar «{file['name']}» a la papelera?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=close),
                    ft.FilledButton("Eliminar", on_click=remove),
                ],
            )
        )

    async def load_backups():
        content.controls = [
            ft.ProgressRing(),
            ft.Text(
                "Buscando carpetas y copias...", color=colors["on_surface_variant"]
            ),
        ]
        page.update()
        groups = []
        for account in account_service.list_accounts():
            if not account.get("folder_id"):
                continue
            try:
                token = await refresh_access_token.execute(account)
                if not token:
                    continue
                files = await list_backup_files(token, account["folder_id"])
                groups.append((account, files))
            except Exception as error:  # noqa: BLE001 - one account must not hide others
                groups.append((account, error))
        controls = []
        for account, files in groups:
            account_controls = [
                ft.Text(
                    account.get("folder_name") or "Carpeta de copias",
                    size=16,
                    weight=ft.FontWeight.W_600,
                    color=colors["on_surface"],
                ),
                ft.Text(
                    account["google_account_email"],
                    size=12,
                    color=colors["on_surface_variant"],
                ),
            ]
            if isinstance(files, Exception):
                account_controls.append(
                    ft.Text("No se pudo leer esta carpeta", color=ft.Colors.RED)
                )
            elif not files:
                account_controls.append(
                    ft.Text(
                        "No hay copias guardadas", color=colors["on_surface_variant"]
                    )
                )
            else:
                for file in files:
                    account_controls.append(
                        ft.Container(
                            padding=ft.Padding.symmetric(vertical=8),
                            content=ft.Row(
                                controls=[
                                    ft.Icon(
                                        ft.Icons.FOLDER_OUTLINED,
                                        color=colors["primary"],
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                file["name"], color=colors["on_surface"]
                                            ),
                                            ft.Text(
                                                f"{format_modified(file.get('modifiedTime'))} · {format_size(file.get('size'))}",
                                                size=12,
                                                color=colors["on_surface_variant"],
                                            ),
                                        ],
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DOWNLOAD_OUTLINED,
                                        tooltip="Importar y agregar",
                                        on_click=lambda e, a=account, f=file: (
                                            add_import_dialog(a, f)
                                        ),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="Eliminar copia",
                                        on_click=lambda e, a=account, f=file: (
                                            page.run_task(confirm_remove, a, f)
                                        ),
                                    ),
                                ],
                            ),
                        )
                    )
            controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=ft.Padding.all(16),
                        content=ft.Column(controls=account_controls),
                    )
                )
            )
        content.controls = controls or [
            ft.Text(
                "Vincula una carpeta de Google Drive para ver tus copias aquí.",
                color=colors["on_surface_variant"],
            )
        ]
        page.update()

    page.run_task(load_backups)
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=12, left=24, right=24),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Mis copias",
                                size=20,
                                weight=ft.FontWeight.W_600,
                                color=colors["on_surface"],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH,
                                tooltip="Actualizar carpetas",
                                on_click=lambda e: page.run_task(load_backups),
                            ),
                        ],
                    ),
                    ft.Text(
                        "Explora tus carpetas, importa una copia o elimina las que ya no necesites.",
                        size=13,
                        color=colors["on_surface_variant"],
                    ),
                    ft.Container(height=12),
                    content,
                ],
            ),
        ),
    )
