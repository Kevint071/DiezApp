from collections.abc import Callable

import flet as ft

from diezapp.bootstrap.dependencies import AppDependencies, create_dependencies
from diezapp.bootstrap.error_handler import show_fatal_error
from diezapp.features.settings.application.settings_service import SettingsService
from diezapp.features.settings.domain.models import AppSettings
from diezapp.features.settings.presentation.theme import DARK_THEME, LIGHT_THEME

AppBuilder = Callable[[ft.Page, AppDependencies, AppSettings], None]


def configure_page(page: ft.Page, settings_service: SettingsService) -> AppSettings:
    """Apply application-wide page settings and return session state."""
    page.title = "DiezApp"
    page.padding = ft.Padding.all(0)

    settings = settings_service.load()
    page.theme_mode = (
        ft.ThemeMode.DARK if settings["theme_mode"] == "dark" else ft.ThemeMode.LIGHT
    )
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME
    return settings


def create_app(page: ft.Page, build_app: AppBuilder | None = None) -> None:
    """Create application dependencies, configure the page, and build the UI."""
    try:
        if build_app is None:
            from diezapp.bootstrap.composition import build_app

        dependencies = create_dependencies()
        settings = configure_page(page, dependencies.settings)
        build_app(page, dependencies, settings)
    except Exception as error:  # noqa: BLE001 - startup failures must be visible
        show_fatal_error(page, error)
