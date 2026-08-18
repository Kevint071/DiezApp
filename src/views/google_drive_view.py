from datetime import datetime

import flet as ft

from diezapp.features.google_drive.application.backup_schedule_settings import (
    BackupScheduleSettings,
)
from diezapp.features.google_drive.application.oauth_flow import GoogleDriveOAuthFlow
from diezapp.features.google_drive.application.refresh_access_token import (
    RefreshAccessToken,
)
from diezapp.features.google_drive.application.run_backup import (
    GoogleDriveBackupService,
)
from diezapp.features.google_drive.domain.repositories import BackupHistoryRepository
from views.settings_google_drive_section import _build_gdrive_backups_section


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
            ),
        ),
    )


def build_google_drive_history_view(
    page: ft.Page, colors_fn, history_repository: BackupHistoryRepository
):
    """Build the dedicated list of completed backup attempts."""
    colors = colors_fn(page)

    status_labels = {"success": "Éxito", "partial": "Parcial", "failed": "Error"}
    rows = []
    for entry in history_repository.list(limit=50):
        try:
            timestamp = (
                datetime.fromisoformat(entry["started_at"])
                .astimezone()
                .strftime("%d/%m/%Y %H:%M")
            )
        except ValueError:
            timestamp = entry["started_at"]
        status = entry["status"]
        status_color = (
            colors["primary"]
            if status == "success"
            else ft.Colors.RED
            if status == "failed"
            else colors["on_surface_variant"]
        )
        destinations = (
            ", ".join(result.get("email", "") for result in entry["details"])
            or "Sin destino"
        )
        rows.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=12, horizontal=4),
                border=ft.Border.only(bottom=ft.BorderSide(1, colors["divider"])),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Column(
                            expand=True,
                            spacing=3,
                            controls=[
                                ft.Text(timestamp, color=colors["on_surface"], size=14),
                                ft.Text(
                                    destinations,
                                    color=colors["on_surface_variant"],
                                    size=12,
                                ),
                            ],
                        ),
                        ft.Text(
                            status_labels.get(status, status),
                            color=status_color,
                            size=12,
                            weight=ft.FontWeight.W_600,
                        ),
                    ],
                ),
            )
        )

    if not rows:
        rows.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=24),
                content=ft.Text(
                    "Todavía no hay copias realizadas",
                    color=colors["on_surface_variant"],
                ),
            )
        )

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=12, left=24, right=24),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text(
                        "Historial de respaldos",
                        size=20,
                        weight=ft.FontWeight.W_600,
                        color=colors["on_surface"],
                    ),
                    ft.Text(
                        "Consulta cuándo y en qué cuentas se guardó cada copia.",
                        size=13,
                        color=colors["on_surface_variant"],
                    ),
                    ft.Container(height=12),
                    *rows,
                ],
            ),
        ),
    )
