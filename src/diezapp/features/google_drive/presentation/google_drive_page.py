import asyncio
import os
import tempfile
from pathlib import Path

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

    status_text = ft.Text(
        "Verificando...", size=13, weight=ft.FontWeight.W_600, color=colors["on_surface_variant"]
    )
    status_dot = ft.Icon(ft.Icons.CIRCLE, size=8, color=colors["on_surface_variant"])
    status_chip = ft.Container(
        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
        border_radius=20,
        bgcolor=colors["divider"],
        content=ft.Row(spacing=6, tight=True, controls=[status_dot, status_text]),
    )
    error_bg = ft.Colors.with_opacity(0.14, ft.Colors.RED)
    folder_label = ft.Text(
        account.get("folder_name") or "No hay carpeta configurada",
        size=12,
        color=colors["on_surface_variant"],
        max_lines=1,
        overflow=ft.TextOverflow.ELLIPSIS,
    )
    folder_labels = {account_id: folder_label}

    def apply_validation(current_account, validation):
        result = validation["status"]
        if result == "valid":
            status_text.value = "En línea"
            status_text.color = status_dot.color = colors["primary"]
            status_chip.bgcolor = colors["hero_bg"]
            folder_name = validation["folder_name"]
            if folder_name != current_account.get("folder_name"):
                account_service.set_account_folder(
                    current_account["id"], current_account.get("folder_id"), folder_name
                )
            folder_label.value = folder_name
        elif result == "no_folder":
            status_text.value = "En línea"
            status_text.color = status_dot.color = colors["primary"]
            status_chip.bgcolor = colors["hero_bg"]
            account_service.set_account_folder(current_account["id"], None, None)
            folder_label.value = "No hay carpeta configurada"
        elif result == "unauthenticated":
            status_text.value = "Sin autenticación"
            status_text.color = status_dot.color = ft.Colors.RED_600
            status_chip.bgcolor = error_bg
        else:
            status_text.value = "Sin conexión"
            status_text.color = status_dot.color = ft.Colors.RED_600
            status_chip.bgcolor = error_bg
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
            padding=ft.Padding.only(left=4, top=20, bottom=8),
            content=ft.Text(
                value.upper(),
                size=11,
                weight=ft.FontWeight.W_600,
                color=colors["on_surface_variant"],
            ),
        )

    def danger_cell(icon, title, on_click):
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=18),
            on_click=on_click,
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Icon(icon, size=22, color=ft.Colors.RED_600),
                    ft.Text(
                        title,
                        size=15,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.RED_600,
                    ),
                ],
            ),
        )

    def nav_cell(icon, title, subtitle, on_click):
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=18),
            on_click=on_click,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=14,
                        expand=True,
                        controls=[
                            ft.Icon(icon, size=22, color=colors["primary"]),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(
                                        title,
                                        size=15,
                                        weight=ft.FontWeight.W_500,
                                        color=colors["on_surface"],
                                    ),
                                    subtitle
                                    if isinstance(subtitle, ft.Text)
                                    else ft.Text(
                                        subtitle,
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
        )

    def card(*controls):
        rows = []
        for index, control in enumerate(controls):
            if index:
                rows.append(
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=18),
                        content=ft.Divider(height=1, color=colors["divider"]),
                    )
                )
            rows.append(control)
        return ft.Container(
            bgcolor=colors["card_bg"],
            border_radius=16,
            padding=ft.Padding.symmetric(vertical=6, horizontal=0),
            content=ft.Column(spacing=0, controls=rows),
        )

    header_card = ft.Container(
        bgcolor=colors["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=18, horizontal=18),
        content=ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=52,
                    height=52,
                    border_radius=26,
                    bgcolor=colors["hero_bg"],
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(
                        ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                        size=28,
                        color=colors["primary"],
                    ),
                ),
                ft.Column(
                    expand=True,
                    spacing=6,
                    controls=[
                        ft.Text(
                            account["google_account_email"],
                            size=16,
                            weight=ft.FontWeight.W_600,
                            color=colors["on_surface"],
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        status_chip,
                    ],
                ),
            ],
        ),
    )

    detail_controls = [
        ft.Container(padding=ft.Padding.only(top=16), content=header_card),
        section_label("Configuración"),
        card(
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
            _settings_cell(
                icon=ft.Icons.HISTORY_OUTLINED,
                title="Copias realizadas",
                colors=colors,
                on_click=lambda e: navigate_to_history(),
            ),
        ),
        section_label("Almacenamiento"),
        card(
            nav_cell(
                ft.Icons.FOLDER_OUTLINED,
                "Carpeta de respaldo",
                folder_label,
                folder_picker.open(account_id),
            ),
        ),
        section_label("Cuenta"),
        card(
            danger_cell(ft.Icons.LINK_OFF, "Desvincular cuenta", open_unlink),
        ),
        ft.Container(height=24),
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


_DESKTOP_PLATFORMS = {
    ft.PagePlatform.WINDOWS,
    ft.PagePlatform.MACOS,
    ft.PagePlatform.LINUX,
}


def _is_desktop(page: ft.Page) -> bool:
    return page.platform in _DESKTOP_PLATFORMS


def build_google_drive_history_view(
    page: ft.Page,
    colors_fn,
    account_service,
    refresh_access_token: RefreshAccessToken,
    local_backup,
    calculations_service,
    notes_service,
    conflicts_service,
    navigate_to_detail,
):
    """Build the Drive backup browser and its import/delete actions."""
    colors = colors_fn(page)

    content = ft.Column(spacing=12)

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

    def avatar(icon, size=40, icon_size=20, bgcolor=None):
        return ft.Container(
            width=size,
            height=size,
            border_radius=size / 2,
            bgcolor=bgcolor or colors["hero_bg"],
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(icon, size=icon_size, color=colors["primary"]),
        )

    def count_badge(count: int):
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            border_radius=20,
            bgcolor=colors["divider"],
            content=ft.Text(
                f"{count} {'copia' if count == 1 else 'copias'}",
                size=12,
                weight=ft.FontWeight.W_600,
                color=colors["on_surface_variant"],
            ),
        )

    def inline_status(icon, message, color):
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=18),
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(icon, size=18, color=color),
                    ft.Text(message, size=13, color=color),
                ],
            ),
        )

    def file_row(account, file, is_last):
        row = ft.Container(
            padding=ft.Padding.symmetric(vertical=12, horizontal=18),
            on_click=lambda e, a=account, f=file: navigate_to_detail(a, f),
            content=ft.Row(
                spacing=14,
                controls=[
                    ft.Icon(
                        ft.Icons.INSERT_DRIVE_FILE_OUTLINED,
                        size=22,
                        color=colors["on_surface_variant"],
                    ),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(
                                file["name"],
                                size=14,
                                weight=ft.FontWeight.W_500,
                                color=colors["on_surface"],
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                f"{format_modified(file.get('modifiedTime'))} · "
                                f"{format_size(file.get('size'))}",
                                size=12,
                                color=colors["on_surface_variant"],
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        color=colors["on_surface_variant"],
                    ),
                ],
            ),
        )
        if is_last:
            return row
        return ft.Column(
            spacing=0,
            controls=[
                row,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18),
                    content=ft.Divider(height=1, color=colors["divider"]),
                ),
            ],
        )

    def account_group(account, files):
        header_row_controls = [
            ft.Row(
                spacing=12,
                expand=True,
                controls=[
                    avatar(ft.Icons.FOLDER_OUTLINED),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(
                                account.get("folder_name") or "Carpeta de copias",
                                size=15,
                                weight=ft.FontWeight.W_600,
                                color=colors["on_surface"],
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                            ft.Text(
                                account["google_account_email"],
                                size=12,
                                color=colors["on_surface_variant"],
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                    ),
                ],
            )
        ]
        if isinstance(files, list):
            header_row_controls.append(count_badge(len(files)))
        header = ft.Container(
            padding=ft.Padding.symmetric(vertical=14, horizontal=18),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=header_row_controls,
            ),
        )
        body_divider = ft.Container(
            padding=ft.Padding.symmetric(horizontal=18),
            content=ft.Divider(height=1, color=colors["divider"]),
        )
        if isinstance(files, Exception):
            body = inline_status(
                ft.Icons.ERROR_OUTLINE, "No se pudo leer esta carpeta", ft.Colors.RED_600
            )
        elif not files:
            body = inline_status(
                ft.Icons.INBOX_OUTLINED,
                "No hay copias guardadas",
                colors["on_surface_variant"],
            )
        else:
            body = ft.Column(
                spacing=0,
                controls=[
                    file_row(account, file, index == len(files) - 1)
                    for index, file in enumerate(files)
                ],
            )
        return ft.Container(
            bgcolor=colors["card_bg"],
            border_radius=16,
            padding=ft.Padding.symmetric(vertical=6, horizontal=0),
            content=ft.Column(spacing=0, controls=[header, body_divider, body]),
        )

    def empty_state(icon, message):
        return ft.Container(
            expand=True,
            alignment=ft.Alignment.TOP_CENTER,
            padding=ft.Padding.only(top=56),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(icon, size=44, color=colors["on_surface_variant"]),
                    ft.Container(height=12),
                    ft.Text(
                        message,
                        size=14,
                        color=colors["on_surface_variant"],
                        text_align=ft.TextAlign.CENTER,
                    ),
                ],
            ),
        )

    async def load_backups():
        content.controls = [
            ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=ft.Padding.only(top=56),
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                    controls=[
                        ft.ProgressRing(color=colors["primary"]),
                        ft.Text(
                            "Buscando carpetas y copias...",
                            size=13,
                            color=colors["on_surface_variant"],
                        ),
                    ],
                ),
            )
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
        controls = [account_group(account, files) for account, files in groups]
        content.controls = controls or [
            empty_state(
                ft.Icons.CLOUD_OFF_OUTLINED,
                "Vincula una carpeta de Google Drive para ver tus copias aquí.",
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
                                                    "Historial de copias",
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


def build_google_drive_backup_detail_view(
    page: ft.Page,
    colors_fn,
    refresh_access_token: RefreshAccessToken,
    local_backup,
    calculations_service,
    notes_service,
    conflicts_service,
    account: dict,
    file: dict,
    navigate_back,
):
    """Build the detail view for a single Google Drive backup file."""
    colors = colors_fn(page)
    import_service = BackupImportService(
        calculations_service, notes_service, conflicts_service
    )
    file_picker = ft.FilePicker()
    page.services.append(file_picker)

    def show_snack(message: str, keep_open: bool = True):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        page.overlay.append(snack)
        if keep_open:
            page.update()

    def format_size(value: str | None) -> str:
        try:
            size = int(value or 0)
        except ValueError:
            return "Tamaño desconocido"
        if size < 1024 * 1024:
            return f"{max(1, size // 1024)} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    def format_date(value: str | None) -> str:
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

    async def download_to_temp() -> str:
        token = await refresh_access_token.execute(account)
        if not token:
            raise ValueError("No se pudo renovar el acceso a Google Drive")
        descriptor, temp_path = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        await download_file(token, file["id"], temp_path)
        return temp_path

    async def download_copy(e):
        del e
        try:
            if _is_desktop(page):
                from diezapp.infrastructure.files.desktop_file_picker import (
                    pick_save_path,
                )

                output_path = await pick_save_path(file["name"])
                if not output_path:
                    return
                token = await refresh_access_token.execute(account)
                if not token:
                    raise ValueError("No se pudo renovar el acceso a Google Drive")
                await download_file(token, file["id"], output_path)
                show_snack(f"Copia guardada en {output_path}", keep_open=False)
                return

            temp_path = None
            try:
                temp_path = await download_to_temp()
                backup_bytes = await asyncio.to_thread(Path(temp_path).read_bytes)
                saved_path = await file_picker.save_file(
                    dialog_title="Guardar copia de seguridad",
                    file_name=file["name"],
                    file_type=ft.FilePickerFileType.CUSTOM,
                    allowed_extensions=["db"],
                    src_bytes=backup_bytes,
                )
                if saved_path:
                    show_snack("Copia guardada correctamente", keep_open=False)
            finally:
                await remove_temp_file(temp_path)
        except Exception as error:  # noqa: BLE001 - Drive errors are user-facing
            show_snack(f"No se pudo descargar la copia: {error}")

    async def share_copy(e):
        del e
        temp_path = None
        try:
            temp_path = await download_to_temp()
            share = ft.Share()
            await share.share_files(
                [ft.ShareFile.from_path(temp_path, name=file["name"])],
                title="Compartir copia de seguridad",
            )
        except Exception as error:  # noqa: BLE001 - Drive errors are user-facing
            show_snack(f"No se pudo compartir la copia: {error}")
        finally:
            await remove_temp_file(temp_path)

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

    def open_import_dialog(e):
        del e

        def close(e):
            page.pop_dialog()

        async def import_copy(e):
            del e
            page.pop_dialog()
            temp_path = None
            try:
                temp_path = await download_to_temp()
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
                    ft.FilledButton(
                        "Importar y agregar",
                        on_click=lambda e: page.run_task(import_copy, e),
                    ),
                ],
            )
        )

    async def remove_copy():
        try:
            token = await refresh_access_token.execute(account)
            if not token:
                raise ValueError("No se pudo renovar el acceso a Google Drive")
            await delete_file(token, file["id"])
            show_snack("Copia eliminada de Google Drive")
            navigate_back()
        except ValueError as error:
            show_snack(str(error))
        except Exception as error:  # noqa: BLE001 - Drive errors are user-facing
            show_snack(f"No se pudo eliminar la copia: {error}")

    def confirm_delete(e):
        del e

        def close(e):
            page.pop_dialog()

        def remove(e):
            del e
            page.pop_dialog()
            page.run_task(remove_copy)

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

    action_divider = ft.Container(
        padding=ft.Padding.symmetric(horizontal=18, vertical=0),
        content=ft.Divider(height=1, color=colors["divider"]),
    )

    header = ft.Container(
        padding=ft.Padding.only(top=12, bottom=20),
        content=ft.Column(
            spacing=6,
            controls=[
                ft.Icon(
                    ft.Icons.INSERT_DRIVE_FILE_OUTLINED,
                    size=38,
                    color=colors["primary"],
                ),
                ft.Text(
                    file["name"],
                    size=18,
                    weight=ft.FontWeight.W_600,
                    color=colors["on_surface"],
                ),
                ft.Text(
                    f"{format_size(file.get('size'))} · Creado el "
                    f"{format_date(file.get('createdTime') or file.get('modifiedTime'))}",
                    size=13,
                    color=colors["on_surface_variant"],
                ),
                ft.Text(
                    account["google_account_email"],
                    size=12,
                    color=colors["on_surface_variant"],
                ),
            ],
        ),
    )

    actions = ft.Container(
        bgcolor=colors["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[
                _settings_cell(
                    icon=ft.Icons.DOWNLOAD_OUTLINED,
                    title="Descargar",
                    colors=colors,
                    on_click=lambda e: page.run_task(download_copy, e),
                ),
                action_divider,
                _settings_cell(
                    icon=ft.Icons.SHARE_OUTLINED,
                    title="Compartir",
                    colors=colors,
                    on_click=lambda e: page.run_task(share_copy, e),
                ),
                action_divider,
                _settings_cell(
                    icon=ft.Icons.FILE_UPLOAD_OUTLINED,
                    title="Importar",
                    colors=colors,
                    on_click=open_import_dialog,
                ),
                action_divider,
                _settings_cell(
                    icon=ft.Icons.DELETE_OUTLINE,
                    title="Eliminar",
                    colors=colors,
                    on_click=confirm_delete,
                ),
            ],
        ),
    )

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
                                    controls=[header, actions],
                                ),
                            )
                        ],
                    ),
                ],
            ),
        ),
    )
