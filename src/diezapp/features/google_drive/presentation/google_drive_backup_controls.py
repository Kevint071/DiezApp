import flet as ft

from diezapp.features.google_drive.application.backup_schedule_settings import (
    BackupScheduleSettings,
)
from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)
from diezapp.features.google_drive.application.run_backup import (
    GoogleDriveBackupService,
)
from diezapp.features.settings.presentation.settings_components import (
    build_settings_cell as _settings_cell,
)


def _format_interval(seconds):
    if not seconds:
        return "Sin configurar"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = [
        f"{value}{unit}"
        for value, unit in ((days, "d"), (hours, "h"), (minutes, "min"))
        if value
    ]
    return " ".join(parts) if parts else "Sin configurar"


def build_frequency_cell(
    page: ft.Page,
    colors: dict,
    schedule_settings: BackupScheduleSettings,
    show_snack,
):
    interval_seconds = schedule_settings.get_interval_seconds()
    days, remainder = divmod(interval_seconds or 0, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    fields = [
        ft.TextField(
            label=label,
            value=str(value),
            keyboard_type=ft.KeyboardType.NUMBER,
            width=90,
        )
        for label, value in (
            ("Días", days),
            ("Horas", hours),
            ("Minutos", minutes),
        )
    ]

    subtitle_text = ft.Text(
        _format_interval(interval_seconds), size=14, color=colors["on_surface_variant"]
    )

    def _confirm(e):
        del e
        try:
            values = [int(field.value or 0) for field in fields]
        except ValueError:
            show_snack("Ingresa valores numéricos válidos")
            return
        total = values[0] * 86400 + values[1] * 3600 + values[2] * 60
        if total <= 0:
            show_snack("La frecuencia debe ser mayor a 0")
            return
        schedule_settings.set_interval_seconds(total)
        subtitle_text.value = _format_interval(total)
        page.pop_dialog()
        page.update()

    dialog = ft.AlertDialog(
        title=ft.Text("Frecuencia de respaldo", size=17, weight=ft.FontWeight.W_600),
        content=ft.Row(spacing=8, controls=fields),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledTonalButton("Guardar", on_click=_confirm),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    return _settings_cell(
        icon=ft.Icons.SCHEDULE_OUTLINED,
        title="Frecuencia",
        subtitle=subtitle_text,
        colors=colors,
        on_click=lambda e: page.show_dialog(dialog),
    )


def build_manual_backup_action(
    page: ft.Page,
    colors: dict,
    account,
    refresh_access_token: RefreshAccessToken,
    backup_service: GoogleDriveBackupService,
    show_snack,
):
    backup_now_button = ft.FilledTonalButton(
        "Respaldar ahora",
        icon=ft.Icons.CLOUD_UPLOAD_OUTLINED,
    )

    async def _run_backup():
        backup_now_button.icon = ft.ProgressRing(width=16, height=16)
        backup_now_button.disabled = True
        page.update()
        result = await backup_service.run(refresh_access_token.execute, {account["id"]})
        status = result["status"]
        if status == "skipped":
            show_snack(result.get("message", "No hay cuentas configuradas"))
        elif status == "success":
            show_snack("Copia de seguridad completada", keep_open=False)
        elif status == "partial":
            show_snack("Copia parcial: alguna cuenta falló")
        else:
            show_snack("No se pudo completar la copia de seguridad")
        backup_now_button.icon = ft.Icons.CLOUD_UPLOAD_OUTLINED
        backup_now_button.disabled = False
        page.update()

    async def _confirm_backup(e):
        del e
        page.pop_dialog()
        await _run_backup()

    backup_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Respaldar ahora", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=12, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                ft.Text(
                    "¿Harás un backup seguro?",
                    size=14,
                    color=colors["on_surface_variant"],
                )
            ],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledButton("Respaldar", on_click=_confirm_backup),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_backup_dialog(e):
        del e
        page.show_dialog(backup_dialog)

    backup_now_button.on_click = _open_backup_dialog
    backup_now_button.style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=ft.Padding.symmetric(vertical=8, horizontal=12),
        text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
    )
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=12, horizontal=18),
        content=ft.Row(
            spacing=12,
            controls=[
                ft.Icon(
                    ft.Icons.CLOUD_UPLOAD_OUTLINED, size=22, color=colors["primary"]
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(
                            "Respaldo manual",
                            size=15,
                            weight=ft.FontWeight.W_500,
                            color=colors["on_surface"],
                        ),
                        ft.Text(
                            "Guarda una copia en tus cuentas vinculadas",
                            size=12,
                            color=colors["on_surface_variant"],
                        ),
                    ],
                ),
                backup_now_button,
            ],
        ),
    )
