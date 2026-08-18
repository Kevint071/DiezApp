import flet as ft

from diezapp.features.settings.application.settings_service import SettingsService
from diezapp.features.settings.domain.models import AppSettings
from diezapp.shared.presentation.theme import DARK_THEME, LIGHT_THEME


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
