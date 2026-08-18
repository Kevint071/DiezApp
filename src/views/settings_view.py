import flet as ft

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.local_backup.application.local_backup_service import (
    LocalBackupService,
)
from diezapp.features.notes.application.note_service import NoteService
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)
from views.settings_components import build_settings_cell as _settings_cell
from views.settings_local_backup_view import build_local_backup_section
from views.settings_preferences_view import build_preferences_section

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
    conflicts_service: ConflictService,
    backup_service: LocalBackupService,
    calculations_service: CalculationService,
    notes_service: NoteService,
):
    """Build the settings view."""
    c = colors_fn(page)

    settings_group = build_preferences_section(
        page=page,
        state=state,
        save_settings=save_settings,
        navigate_to_settings=navigate_to_settings,
        colors=c,
        settings_cell=_settings_cell,
    )

    export_import_group = build_local_backup_section(
        page=page,
        colors=c,
        navigate_to_settings=navigate_to_settings,
        settings_cell=_settings_cell,
        is_desktop=_is_desktop,
        conflicts_service=conflicts_service,
        backup_service=backup_service,
        calculations_service=calculations_service,
        notes_service=notes_service,
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
