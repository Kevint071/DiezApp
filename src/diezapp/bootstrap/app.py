import flet as ft
from utils.app_settings import load_settings
from utils.theme import DARK_THEME, LIGHT_THEME


def configure_page(page: ft.Page) -> dict:
    """Apply application-wide page settings and return session state."""
    page.title = "DiezApp"
    page.padding = ft.Padding.all(0)

    settings = load_settings()
    page.theme_mode = (
        ft.ThemeMode.DARK if settings["theme_mode"] == "dark" else ft.ThemeMode.LIGHT
    )
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME
    return {"fund_percentage": settings["fund_percentage"]}
