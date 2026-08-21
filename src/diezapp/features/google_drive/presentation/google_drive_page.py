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
from diezapp.features.google_drive.application.validate_drive_account import (
    ValidateDriveAccount,
)
from diezapp.features.google_drive.domain.repositories import BackupHistoryRepository
from diezapp.features.google_drive.presentation.google_drive_account_validation import (
    GoogleDriveAccountValidationController,
)
from diezapp.features.google_drive.presentation.google_drive_backup_controls import (
    build_frequency_cell,
    build_manual_backup_action,
)
from diezapp.features.google_drive.presentation.google_drive_folder_picker import (
    GoogleDriveFolderPicker,
)
from diezapp.features.google_drive.presentation.settings_google_drive_section import (
    _build_gdrive_backups_section,
)
from diezapp.features.local_backup.application.import_backup import (
    BackupImportService,
)
from diezapp.features.settings.presentation.settings_components import (
    build_settings_cell as _settings_cell,
)
from diezapp.infrastructure.google.drive_client import (
    delete_file,
    download_file,
    list_backup_files,
)
from diezapp.shared.datetime_utils import to_local_datetime
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)


def build_google_drive_view(
    page: ft.Page,
    colors_fn,
    account_service,
    oauth_flow: GoogleDriveOAuthFlow,
    navigate_to_account,
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
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    (divider := build_scroll_divider()),
                    ft.Column(
                        expand=True,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, colors),
                        controls=[
                            ft.Container(
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=_build_gdrive_backups_section(
                                    page,
                                    colors,
                                    show_snack,
                                    account_service,
                                    oauth_flow,
                                    navigate_to_account,
                                ),
                            )
                        ],
                    ),
                ],
            ),
        ),
    )


def build_google_drive_account_view(
    page: ft.Page,
    colors_fn,
    account_id,
    account_service,
    refresh_access_token: RefreshAccessToken,
    oauth_flow: GoogleDriveOAuthFlow,
    folder_service: DriveFolderService,
    account_validator: ValidateDriveAccount,
    schedule_settings: BackupScheduleSettings,
    backup_service: GoogleDriveBackupService,
    navigate_to_google_drive,
    navigate_to_history,
    show_snack,
):
    colors = colors_fn(page)
    account = next(
        (item for item in account_service.list_accounts() if item["id"] == account_id),
        None,
    )
    if account is None:
        return ft.Container(content=ft.Text("Cuenta no encontrada"))

    status = ft.Text("Verificando...", color=colors["on_surface_variant"])
    folder_label = ft.Text(
        f"Carpeta: {account.get('folder_name') or 'No hay carpeta configurada'}",
        color=colors["on_surface_variant"],
    )
    folder_labels = {account_id: folder_label}

    def apply_validation(current_account, validation):
        result = validation["status"]
        if result == "valid":
            status.value = "En línea"
            status.color = colors["primary"]
            folder_name = validation["folder_name"]
            if folder_name != current_account.get("folder_name"):
                account_service.set_account_folder(
                    current_account["id"], current_account.get("folder_id"), folder_name
                )
            folder_label.value = f"Carpeta: {folder_name}"
        elif result == "no_folder":
            status.value = "En línea"
            status.color = colors["primary"]
            account_service.set_account_folder(current_account["id"], None, None)
            folder_label.value = "Carpeta: No hay carpeta configurada"
        elif result == "unauthenticated":
            status.value = "Sin autenticación"
            status.color = ft.Colors.RED_600
        else:
            status.value = "Sin conexión"
            status.color = ft.Colors.RED_600
        page.update()

    validation_controller = GoogleDriveAccountValidationController(
        page,
        [account],
        refresh_access_token,
        account_validator,
        apply_validation,
    )
    folder_picker = GoogleDriveFolderPicker(
        page,
        colors,
        account_service,
        refresh_access_token,
        folder_service,
        validation_controller,
        show_snack,
        folder_labels,
    )

    async def reauthenticate(e):
        del e
        if not oauth_flow.is_configured():
            show_snack("OAuth de Google no configurado")
            return
        started = await oauth_flow.start(
            page.session.store, page.url, account_id=account["id"]
        )
        if not started:
            show_snack("No se pudo iniciar la reautenticación")

    def open_unlink(e):
        del e
        confirmed = False

        def after_dismiss(event):
            del event
            if confirmed:
                account_service.remove_account(account["id"])
                navigate_to_google_drive()

        def confirm(event):
            nonlocal confirmed
            confirmed = True
            page.pop_dialog()

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Desvincular cuenta"),
                content=ft.Text(
                    f"¿Seguro que quieres desvincular {account['google_account_email']}?"
                ),
                actions=[
                    ft.TextButton("No", on_click=lambda event: page.pop_dialog()),
                    ft.FilledButton("Sí", on_click=confirm),
                ],
                on_dismiss=after_dismiss,
            )
        )

    validation_controller.start()

    def section_label(value):
        return ft.Container(
            padding=ft.Padding.only(left=4, top=14, bottom=6),
            content=ft.Text(
                value.upper(),
                size=11,
                weight=ft.FontWeight.W_600,
                color=colors["on_surface_variant"],
            ),
        )

    detail_controls = [
        ft.Container(
            padding=ft.Padding.only(top=12, bottom=24),
            content=ft.Column(
                spacing=7,
                controls=[
                    ft.Icon(
                        ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                        size=38,
                        color=colors["primary"],
                    ),
                    ft.Text(
                        account["google_account_email"],
                        size=18,
                        weight=ft.FontWeight.W_600,
                        color=colors["on_surface"],
                    ),
                    ft.Row(
                        spacing=6,
                        controls=[
                            ft.Icon(ft.Icons.CIRCLE, size=9, color=colors["primary"]),
                            status,
                        ],
                    ),
                ],
            ),
        ),
        section_label("Configuración"),
        build_frequency_cell(
            page, colors, schedule_settings, show_snack, navigate_to_google_drive
        ),
        build_manual_backup_action(
            page,
            colors,
            account,
            refresh_access_token,
            backup_service,
            show_snack,
            navigate_to_google_drive,
        ),
        ft.Container(
            padding=ft.Padding.symmetric(horizontal=18),
            content=ft.Divider(height=1, color=colors["divider"]),
        ),
        _settings_cell(
            icon=ft.Icons.HISTORY_OUTLINED,
            title="Copias realizadas",
            colors=colors,
            on_click=lambda e: navigate_to_history(),
        ),
        section_label("Almacenamiento"),
        ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=18),
            on_click=folder_picker.open(account_id),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=14,
                        controls=[
                            ft.Icon(ft.Icons.FOLDER_OUTLINED, color=colors["primary"]),
                            folder_label,
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        color=colors["on_surface_variant"],
                    ),
                ],
            ),
        ),
        ft.Divider(height=1, thickness=1, color=colors["divider"]),
        ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=18),
            on_click=reauthenticate,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=14,
                        controls=[
                            ft.Icon(ft.Icons.LOCK_RESET, color=colors["primary"]),
                            ft.Column(
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        "Reautenticar cuenta",
                                        size=15,
                                        weight=ft.FontWeight.W_500,
                                        color=colors["on_surface"],
                                    ),
                                    ft.Text(
                                        "Volver a conectar con Google",
                                        size=12,
                                        color=colors["on_surface_variant"],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        color=colors["on_surface_variant"],
                    ),
                ],
            ),
        ),
        ft.Container(
            padding=ft.Padding.only(top=10, bottom=18, left=18, right=18),
            content=ft.TextButton(
                "Desvincular cuenta",
                icon=ft.Icons.LINK_OFF,
                on_click=open_unlink,
            ),
        ),
    ]

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    (divider := build_scroll_divider()),
                    ft.Column(
                        expand=True,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, colors),
                        controls=[
                            ft.Container(
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=ft.Column(
                                    spacing=0,
                                    controls=detail_controls,
                                ),
                            )
                        ],
                    ),
                ],
            ),
        ),
    )


_HISTORY_STATUS_LABELS = {
    "success": "Completado",
    "partial": "Parcial",
    "failed": "Fallido",
}


def _history_status_color(status: str, colors: dict):
    return {
        "success": colors["primary"],
        "partial": ft.Colors.ORANGE_600,
        "failed": ft.Colors.RED_600,
    }.get(status, colors["on_surface_variant"])


def _build_history_entry(entry: dict, colors: dict) -> ft.Container:
    status = entry["status"]
    color = _history_status_color(status, colors)
    failed_accounts = [
        detail for detail in entry["details"] if not detail.get("ok", True)
    ]

    return ft.Container(
        padding=ft.Padding.symmetric(vertical=10),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            to_local_datetime(entry["started_at"]).strftime(
                                "%d/%m/%Y %H:%M"
                            ),
                            size=13,
                            color=colors["on_surface"],
                        ),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=10, vertical=3),
                            bgcolor=ft.Colors.with_opacity(0.12, color),
                            border_radius=12,
                            content=ft.Text(
                                _HISTORY_STATUS_LABELS.get(status, status),
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=color,
                            ),
                        ),
                    ],
                ),
                *(
                    [
                        ft.Text(
                            f"{detail['email']}: "
                            f"{detail.get('error', 'Error desconocido')}",
                            size=11,
                            color=colors["on_surface_variant"],
                        )
                        for detail in failed_accounts
                    ]
                    if failed_accounts
                    else []
                ),
            ],
        ),
    )


def _build_history_section(
    colors: dict, history_repository: BackupHistoryRepository
) -> ft.Column:
    entries = history_repository.list(limit=10)
    if not entries:
        return ft.Column()

    controls = [
        ft.Text(
            "Historial de respaldos",
            size=16,
            weight=ft.FontWeight.W_600,
            color=colors["on_surface"],
        ),
    ]
    for index, entry in enumerate(entries):
        controls.append(_build_history_entry(entry, colors))
        if index < len(entries) - 1:
            controls.append(ft.Divider(height=1, color=colors["divider"]))
    controls.append(ft.Container(height=20))
    return ft.Column(spacing=0, controls=controls)


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

    content = ft.Column(spacing=12)
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
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    (divider := build_scroll_divider()),
                    ft.Column(
                        expand=True,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, colors),
                        controls=[
                            ft.Container(
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=ft.Column(
                                    spacing=12,
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
                                                    on_click=lambda e: page.run_task(
                                                        load_backups
                                                    ),
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            "Explora tus carpetas, importa una copia o "
                                            "elimina las que ya no necesites.",
                                            size=13,
                                            color=colors["on_surface_variant"],
                                        ),
                                        _build_history_section(
                                            colors, history_repository
                                        ),
                                        content,
                                    ],
                                ),
                            )
                        ],
                    ),
                ],
            ),
        ),
    )
