from datetime import timedelta

import flet as ft
import httpx
from diezapp.infrastructure.google.drive_client import (
    DriveApiError,
    create_folder,
    delete_folder,
    list_folders,
)

from views.settings_components import build_settings_cell as _settings_cell


def _build_gdrive_backups_section(
    page: ft.Page,
    c: dict,
    navigate_to_settings,
    show_snack,
    navigate_to_history,
    account_service,
):
    """Build the 'Copias de seguridad' (Google Drive) settings section.

    Rebuilt (via ``navigate_to_settings()``) after every mutating action —
    same pattern already used by the export/import dialogs above — rather
    than patching individual controls in place.
    """
    from utils.gdrive_auth import (
        ensure_fresh_access_token,
        is_configured,
        start_link_flow,
    )
    from utils.gdrive_backup import (
        get_interval_seconds,
        get_last_backup_at,
        run_backup_now,
        set_interval_seconds,
    )

    pending_message = page.session.store.get("gdrive_link_message")
    if pending_message:
        page.session.store.remove("gdrive_link_message")
        show_snack(pending_message, keep_open=False)

    accounts = account_service.list_accounts()

    async def _link_account(e):
        if not is_configured(page):
            show_snack("OAuth de Google no configurado")
            return
        started = await start_link_flow(page)
        if not started:
            show_snack("Ya hay 2 cuentas vinculadas")

    def _unlink_account(account_id):
        def _handler(e):
            account_service.remove_account(account_id)
            navigate_to_settings()

        return _handler

    folder_name_field = ft.TextField(label="Nombre de la carpeta")
    folder_dialog_state = {
        "account_id": None,
        "parent_id": "root",
        "parent_name": "Mi unidad",
    }
    folder_selection = {"id": None, "name": None}
    folder_title = ft.Text("Seleccionar carpeta", size=17, weight=ft.FontWeight.W_600)
    folder_path = ft.Text("Mi unidad", size=13, color=c["on_surface_variant"])
    folder_loading = ft.ProgressRing(width=22, height=22, visible=False)
    folder_list = ft.Column(spacing=0, tight=True, scroll=ft.ScrollMode.AUTO)
    folder_delete_state = {"active": False, "selected": set()}
    current_folders = []
    folder_labels = {}

    def _close_folder_dialog(e):
        page.pop_dialog()

    async def _load_folder_list():
        account_id = folder_dialog_state["account_id"]
        account = next(
            (a for a in account_service.list_accounts() if a["id"] == account_id),
            None,
        )
        if account is None:
            return
        access_token = await ensure_fresh_access_token(page, account)
        if not access_token:
            show_snack("No se pudo autenticar la cuenta")
            return
        folder_dialog_state["parent_id"] = "root"
        folder_dialog_state["parent_name"] = "Mi unidad"
        folder_path.value = "Mi unidad"
        folder_loading.visible = True
        folder_list.controls = []
        page.update()
        try:
            folders = await list_folders(access_token, "root")
        except DriveApiError as error:
            show_snack(f"Drive {error.status_code} ({error.reason}): {error.message}")
            return
        except httpx.HTTPError:
            show_snack("No se pudo conectar con Google Drive")
            return
        finally:
            folder_loading.visible = False
            page.update()
        current_folders[:] = folders
        _render_folder_list(current_folders)
        page.update()

    def _render_folder_list(folders):
        if folder_delete_state["active"]:
            folder_list.controls = [
                ft.ListTile(
                    leading=ft.Checkbox(
                        value=folder["id"] in folder_delete_state["selected"],
                        on_change=lambda e, folder_id=folder["id"]: (
                            folder_delete_state["selected"].add(folder_id)
                            if e.control.value
                            else folder_delete_state["selected"].discard(folder_id)
                        ),
                    ),
                    title=ft.Text(folder["name"]),
                )
                for folder in folders
            ]
        else:
            folder_list.controls = [
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.FOLDER_OUTLINED, color=c["primary"]),
                    title=ft.Text(folder["name"]),
                    selected=folder["id"] == folder_selection["id"],
                    selected_tile_color=c["navigation_indicator"],
                    on_click=lambda e, item=folder: _select_folder(item),
                    trailing=ft.Icon(
                        ft.Icons.CHECK,
                        color=c["primary"],
                        visible=folder["id"] == folder_selection["id"],
                    ),
                )
                for folder in folders
            ]
        if not folder_list.controls:
            folder_list.controls = [
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=16),
                    content=ft.Text(
                        "No hay subcarpetas", color=c["on_surface_variant"]
                    ),
                )
            ]

    def _set_folder_delete_mode(active):
        folder_delete_state["active"] = active
        if not active:
            folder_delete_state["selected"].clear()
        _render_folder_list(current_folders)
        _update_folder_dialog_actions()
        page.update()

    async def _delete_selected_folders(e):
        selected_ids = set(folder_delete_state["selected"])
        if not selected_ids:
            show_snack("Selecciona al menos una carpeta")
            return
        account = next(
            (
                a
                for a in account_service.list_accounts()
                if a["id"] == folder_dialog_state["account_id"]
            ),
            None,
        )
        if account is None:
            return
        access_token = await ensure_fresh_access_token(page, account)
        if not access_token:
            show_snack("No se pudo autenticar la cuenta")
            return
        try:
            for folder_id in selected_ids:
                await delete_folder(access_token, folder_id)
        except DriveApiError as error:
            show_snack(f"Drive {error.status_code} ({error.reason}): {error.message}")
            return
        except httpx.HTTPError:
            show_snack("No se pudo conectar con Google Drive")
            return
        if account.get("folder_id") in selected_ids:
            account_service.set_account_folder(account["id"], None, None)
        current_folders[:] = [
            folder for folder in current_folders if folder["id"] not in selected_ids
        ]
        if folder_selection["id"] in selected_ids:
            folder_selection["id"] = None
            folder_selection["name"] = None
        folder_delete_state["selected"].clear()
        folder_delete_state["active"] = False
        _render_folder_list(current_folders)
        _update_folder_dialog_actions()
        page.update()
        show_snack("Carpetas eliminadas", keep_open=False)

    folder_actions = ft.Row(spacing=0, controls=[])

    def _update_folder_dialog_actions():
        if folder_delete_state["active"]:
            folder_actions.controls = [
                ft.IconButton(
                    ft.Icons.CLOSE,
                    tooltip="Cancelar eliminación",
                    icon_color=c["on_surface_variant"],
                    width=40,
                    height=40,
                    padding=0,
                    on_click=lambda e: _set_folder_delete_mode(False),
                ),
                ft.IconButton(
                    ft.Icons.CHECK,
                    tooltip="Eliminar seleccionadas",
                    icon_color=c["primary"],
                    width=40,
                    height=40,
                    padding=0,
                    on_click=lambda e: page.run_task(_delete_selected_folders, e),
                ),
            ]
        else:
            folder_actions.controls = [
                ft.IconButton(
                    ft.Icons.ADD,
                    tooltip="Crear carpeta",
                    icon_color=c["primary"],
                    width=40,
                    height=40,
                    padding=0,
                    on_click=lambda e: _open_create_folder_dialog(),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE,
                    tooltip="Eliminar carpetas",
                    icon_color=ft.Colors.RED_600,
                    width=40,
                    height=40,
                    padding=0,
                    on_click=lambda e: _set_folder_delete_mode(True),
                ),
            ]
        use_folder_button.disabled = folder_selection["id"] is None

    def _select_folder(folder):
        if folder_selection["id"] == folder["id"]:
            folder_selection["id"] = None
            folder_selection["name"] = None
        else:
            folder_selection["id"] = folder["id"]
            folder_selection["name"] = folder["name"]
        _render_folder_list(current_folders)
        _update_folder_dialog_actions()
        page.update()

    use_folder_button = ft.FilledButton(
        "Usar carpeta",
        disabled=True,
        style=ft.ButtonStyle(
            bgcolor={
                ft.ControlState.DEFAULT: "#047857",
                ft.ControlState.DISABLED: c["outline"],
            },
            color={
                ft.ControlState.DEFAULT: "#FFFFFF",
                ft.ControlState.DISABLED: c["on_surface_variant"],
            },
        ),
    )

    def _select_current_folder(e):
        if folder_selection["id"] is None:
            return
        account_service.set_account_folder(
            folder_dialog_state["account_id"],
            folder_selection["id"],
            folder_selection["name"],
        )
        page.pop_dialog()
        folder_label = folder_labels.get(folder_dialog_state["account_id"])
        if folder_label:
            folder_label.value = f"Carpeta: {folder_selection['name']}"
            folder_label.color = c["on_surface_variant"]
        page.update()

    use_folder_button.on_click = _select_current_folder

    async def _create_folder(e):
        account_id = folder_dialog_state["account_id"]
        account = next(
            (a for a in account_service.list_accounts() if a["id"] == account_id),
            None,
        )
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
        current_folders.append({"id": folder_id, "name": folder_name})
        _select_folder(current_folders[-1])
        folder_name_field.value = ""
        page.pop_dialog()
        page.update()

    def _close_create_folder_dialog(e):
        page.pop_dialog()

    create_folder_dialog = ft.AlertDialog(
        modal=True,
        bgcolor=c["surface"],
        title=ft.Text("Nueva carpeta", color=c["on_surface"]),
        content=folder_name_field,
        actions=[
            ft.TextButton("Cancelar", on_click=_close_create_folder_dialog),
            ft.FilledButton("Crear", on_click=_create_folder),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _open_create_folder_dialog():
        folder_name_field.value = ""
        page.show_dialog(create_folder_dialog)

    folder_dialog = ft.AlertDialog(
        bgcolor=c["surface"],
        title=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=3,
                    controls=[
                        folder_title,
                        ft.Text(
                            "Elige dónde guardar tus respaldos",
                            size=12,
                            color=c["on_surface_variant"],
                        ),
                        folder_path,
                    ],
                ),
                folder_actions,
            ],
        ),
        content=ft.Column(
            tight=True,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Container(expand=True),
                        folder_loading,
                    ],
                ),
                ft.Container(
                    height=260,
                    width=360,
                    content=folder_list,
                ),
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_folder_dialog),
            use_folder_button,
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_folder_dialog(account_id):
        def _handler(e):
            folder_dialog_state["account_id"] = account_id
            folder_dialog_state["parent_id"] = "root"
            folder_dialog_state["parent_name"] = "Mi unidad"
            folder_delete_state["active"] = False
            folder_delete_state["selected"].clear()
            current_folders.clear()
            folder_selection["id"] = None
            folder_selection["name"] = None
            folder_name_field.value = "Respaldos DiezApp"
            folder_path.value = "Mi unidad"
            _update_folder_dialog_actions()
            page.show_dialog(folder_dialog)
            page.run_task(_load_folder_list)

        return _handler

    def _divider():
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=18, vertical=0),
            content=ft.Divider(height=1, color=c["divider"]),
        )

    def _open_unlink_dialog(account_id, email):
        confirmed = False

        def _after_dismiss(e):
            # Flet termina de desmontar el diálogo antes de reconstruir la vista.
            if confirmed:
                account_service.remove_account(account_id)
                navigate_to_settings()

        def _close(e):
            page.pop_dialog()

        def _confirm(e):
            nonlocal confirmed
            confirmed = True
            page.pop_dialog()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Desvincular cuenta", size=17, weight=ft.FontWeight.W_600),
            content=ft.Text(f"¿Seguro que quieres desvincular {email}?"),
            actions=[
                ft.TextButton("No", on_click=_close),
                ft.FilledButton("Sí", on_click=_confirm),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            on_dismiss=_after_dismiss,
        )
        page.show_dialog(dialog)

    def _account_row(account):
        has_folder = bool(account.get("folder_id"))
        subtitle = account["folder_name"] if has_folder else "Elegir carpeta"
        folder_label = ft.Text(
            f"Carpeta: {subtitle}",
            size=13,
            color=c["on_surface_variant"] if has_folder else c["primary"],
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
                                on_click=_open_folder_dialog(account["id"]),
                                content=folder_label,
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

    def _format_local_datetime(value):
        if value is None:
            return "Sin copias aún"
        return value.astimezone().strftime("%d/%m/%Y %H:%M")

    last_backup_at = get_last_backup_at()
    next_backup_at = (
        last_backup_at + timedelta(seconds=interval_seconds)
        if last_backup_at and interval_seconds
        else None
    )
    backup_status = ft.Container(
        padding=ft.Padding.symmetric(vertical=10, horizontal=18),
        content=ft.Column(
            spacing=4,
            controls=[
                ft.Text(
                    f"Última copia: {_format_local_datetime(last_backup_at)}",
                    size=13,
                    color=c["on_surface_variant"],
                ),
                ft.Text(
                    f"Próxima copia: {_format_local_datetime(next_backup_at)}"
                    if interval_seconds
                    else "Próxima copia: Sin configurar",
                    size=13,
                    color=c["on_surface_variant"],
                ),
            ],
        ),
    )

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

    def _refresh_backup_accounts():
        backup_accounts[:] = [
            account
            for account in account_service.list_accounts()
            if account.get("folder_id")
        ]
        backup_account_checks[:] = [
            ft.Checkbox(
                label=account["google_account_email"],
                value=True,
            )
            for account in backup_accounts
        ]
        backup_dialog.content.controls = [
            backup_dialog.content.controls[0],
            *backup_account_checks,
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
        _refresh_backup_accounts()
        if not backup_accounts:
            show_snack("Configura una carpeta en al menos una cuenta")
            return
        for checkbox in backup_account_checks:
            checkbox.value = True
        page.show_dialog(backup_dialog)

    backup_now_button.on_click = _open_backup_dialog

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

    can_link_more = account_service.can_add_account()
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
    controls.append(backup_status)
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
