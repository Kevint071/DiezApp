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
from diezapp.features.settings.presentation.settings_components import (
    build_settings_cell as _settings_cell,
)


def _build_gdrive_backups_section(
    page: ft.Page,
    c: dict,
    navigate_to_settings,
    show_snack,
    navigate_to_history,
    account_service,
    url_opener,
    schedule_settings: BackupScheduleSettings,
    backup_service: GoogleDriveBackupService,
    refresh_access_token: RefreshAccessToken,
    oauth_flow: GoogleDriveOAuthFlow,
    folder_service: DriveFolderService,
    account_validator: ValidateDriveAccount,
):
    del url_opener
    pending_message = page.session.store.get("gdrive_link_message")
    if pending_message:
        page.session.store.remove("gdrive_link_message")
        show_snack(pending_message, keep_open=False)

    accounts = account_service.list_accounts()
    folder_labels = {}
    pending_validation = {account["id"] for account in accounts}

    async def _link_account(e):
        del e
        if not oauth_flow.is_configured():
            show_snack("OAuth de Google no configurado")
            return
        started = await oauth_flow.start(page.session.store, page.url)
        if not started:
            show_snack("Ya hay 2 cuentas vinculadas")

    def _set_account_label(account, text, color):
        label = folder_labels.get(account["id"])
        if label:
            label.value = text
            label.color = color

    def _apply_account_validation(account, validation):
        pending_validation.discard(account["id"])
        status = validation["status"]
        if status == "valid":
            folder_name = validation["folder_name"]
            if folder_name != account.get("folder_name"):
                account_service.set_account_folder(
                    account["id"], account.get("folder_id"), folder_name
                )
            _set_account_label(
                account, f"Carpeta: {folder_name}", c["on_surface_variant"]
            )
        elif status == "no_folder":
            account_service.set_account_folder(account["id"], None, None)
            _set_account_label(account, "Carpeta: Elegir carpeta", c["primary"])
        elif status == "folder_unavailable":
            _set_account_label(
                account,
                "No se pudo verificar la carpeta",
                c["on_surface_variant"],
            )
        elif status == "access_unavailable":
            _set_account_label(
                account,
                "No se pudo verificar la cuenta",
                c["on_surface_variant"],
            )
        else:
            _set_account_label(account, "Cuenta no autenticada", ft.Colors.RED_600)
        return status

    validation_controller = GoogleDriveAccountValidationController(
        page,
        accounts,
        refresh_access_token,
        account_validator,
        _apply_account_validation,
    )
    folder_picker = GoogleDriveFolderPicker(
        page,
        c,
        account_service,
        refresh_access_token,
        folder_service,
        validation_controller,
        show_snack,
        folder_labels,
    )

    def _open_unlink_dialog(account_id, email):
        confirmed = False

        def _after_dismiss(e):
            del e
            if confirmed:
                account_service.remove_account(account_id)
                navigate_to_settings()

        def _confirm(e):
            nonlocal confirmed
            confirmed = True
            page.pop_dialog()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Desvincular cuenta", size=17, weight=ft.FontWeight.W_600),
            content=ft.Text(f"¿Seguro que quieres desvincular {email}?"),
            actions=[
                ft.TextButton("No", on_click=lambda e: page.pop_dialog()),
                ft.FilledButton("Sí", on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=_after_dismiss,
        )
        page.show_dialog(dialog)

    def _account_row(account):
        has_folder = bool(account.get("folder_id"))
        is_pending = account["id"] in pending_validation
        subtitle = (
            "Verificando..."
            if is_pending
            else account["folder_name"]
            if has_folder
            else "Elegir carpeta"
        )
        folder_label = ft.Text(
            f"Carpeta: {subtitle}",
            size=13,
            color=c["on_surface_variant"] if has_folder or is_pending else c["primary"],
        )
        folder_labels[account["id"]] = folder_label
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
                                content=folder_label,
                                on_click=folder_picker.open(account["id"]),
                            ),
                        ],
                    ),
                    ft.IconButton(
                        ft.Icons.LINK_OFF,
                        icon_size=20,
                        tooltip="Desvincular cuenta",
                        on_click=lambda e: _open_unlink_dialog(
                            account["id"], account["google_account_email"]
                        ),
                    ),
                ],
            ),
        )

    account_header = ft.Container(
        padding=ft.Padding.only(top=18, bottom=12, left=18, right=18),
        alignment=ft.Alignment(0, 0),
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
            controls=[
                ft.Icon(ft.Icons.CLOUD_OUTLINED, size=36, color=c["primary"]),
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

    def _divider():
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=18),
            content=ft.Divider(height=1, color=c["divider"]),
        )

    controls = [account_header]
    if account_service.can_add_account():
        controls.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=12, horizontal=18),
                alignment=ft.Alignment(0, 0),
                content=(
                    ft.FilledButton(
                        "Conectar Google",
                        icon=ft.Icons.ACCOUNT_CIRCLE_OUTLINED,
                        on_click=_link_account,
                    )
                    if not accounts
                    else ft.OutlinedButton(
                        "Añadir cuenta", icon=ft.Icons.ADD, on_click=_link_account
                    )
                ),
            )
        )
    if accounts:
        controls.append(_divider())
        controls.extend(
            control
            for account in accounts
            for control in (_account_row(account), _divider())
        )

    controls.extend(
        [
            build_frequency_cell(
                page,
                c,
                schedule_settings,
                show_snack,
                navigate_to_settings,
            ),
            _divider(),
            build_manual_backup_action(
                page,
                c,
                account_service,
                refresh_access_token,
                backup_service,
                show_snack,
                navigate_to_settings,
            ),
            _divider(),
            _settings_cell(
                icon=ft.Icons.HISTORY_OUTLINED,
                title="Copias realizadas",
                subtitle=None,
                colors=c,
                on_click=lambda e: navigate_to_history(),
            ),
        ]
    )

    validation_controller.start()
    return ft.Column(spacing=0, controls=controls)
