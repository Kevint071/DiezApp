import flet as ft

from utils.theme import (
    ON_SURFACE_LIGHT,
    ON_SURFACE_DARK,
)


def apply_settings_appbar(page: ft.Page, on_navigate_back, colors_fn):
    light = page.theme_mode == ft.ThemeMode.LIGHT
    fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
    page.appbar = ft.AppBar(
        leading=ft.Container(
            width=40,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: on_navigate_back(),
            content=ft.Image(
                src="chevron-left.svg",
                width=24,
                height=24,
                color=fg,
            ),
        ),
        title=ft.Text(
            "Configuración",
            color=fg,
            weight=ft.FontWeight.W_600,
            size=18,
            style=ft.TextStyle(height=1),
        ),
        center_title=False,
        leading_width=40,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
    )


def build_settings_view(page: ft.Page, state: dict, save_settings, navigate_to_settings, colors_fn):
    """Build the settings view.

    Args:
        page: The Flet page.
        state: Mutable dict with 'fund_percentage' key.
        save_settings: Function(theme_mode, fund_percentage) to persist settings.
        navigate_to_settings: Function to refresh the settings view.
        colors_fn: Function(page) returning contextual color dict.
    """
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT

    # Theme row
    theme_label = "Claro" if light else "Oscuro"

    def _on_theme_selected(mode: str):
        if mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
        else:
            page.theme_mode = ft.ThemeMode.DARK
        save_settings(mode, state["fund_percentage"])
        page.pop_dialog()
        navigate_to_settings()

    def _theme_option(label, icon, mode, is_selected):
        return ft.Container(
            on_click=lambda e: _on_theme_selected(mode),
            border_radius=12,
            padding=ft.Padding.symmetric(vertical=10, horizontal=12),
            bgcolor=c["primary"] if is_selected else ft.Colors.TRANSPARENT,
            content=ft.Row(
                spacing=10,
                controls=[
                    ft.Icon(icon, size=20, color=c["on_primary"] if is_selected else c["on_surface_variant"]),
                    ft.Text(label, size=14, weight=ft.FontWeight.W_500, color=c["on_primary"] if is_selected else c["on_surface"]),
                ],
            ),
        )

    theme_dialog = ft.AlertDialog(
        title=ft.Text("Tema", size=16, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=20, right=20, top=8, bottom=4),
        content=ft.Column(
            tight=True,
            spacing=4,
            controls=[
                _theme_option("Claro", ft.Icons.LIGHT_MODE_OUTLINED, "light", light),
                _theme_option("Oscuro", ft.Icons.DARK_MODE_OUTLINED, "dark", not light),
            ],
        ),
    )

    def _open_theme_dialog(e):
        page.show_dialog(theme_dialog)

    theme_cell = ft.Container(
        on_click=_open_theme_dialog,
        padding=ft.Padding.symmetric(vertical=14, horizontal=0),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Tema", size=15, color=c["on_surface"]),
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.Text(theme_label, size=14, color=c["on_surface_variant"]),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=c["on_surface_variant"], size=20),
                    ],
                ),
            ],
        ),
    )

    # Fund percentage row + modal
    fund_percentage = state["fund_percentage"]
    pct_label = ft.Text(f"{fund_percentage}%", size=14, color=c["on_surface_variant"])

    pct_field = ft.TextField(
        label="Porcentaje (1-30)",
        value=str(fund_percentage),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=14,
        on_submit=lambda e: _save_pct(e),
    )

    def _close_pct_dialog(e):
        page.pop_dialog()

    def _save_pct(e):
        try:
            val = int(pct_field.value)
        except (ValueError, TypeError):
            pct_field.error_text = "Ingresa un número válido"
            page.update()
            return
        if val < 1 or val > 30:
            pct_field.error_text = "El porcentaje debe estar entre 1% y 30%"
            page.update()
            return
        pct_field.error_text = None
        state["fund_percentage"] = val
        current_mode = "dark" if page.theme_mode == ft.ThemeMode.DARK else "light"
        save_settings(current_mode, val)
        page.pop_dialog()
        navigate_to_settings()

    pct_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Aporte al fondo local", size=17),
        content=pct_field,
        actions=[
            ft.TextButton("Cancelar", on_click=_close_pct_dialog),
            ft.TextButton("Guardar", on_click=_save_pct),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def _open_pct_dialog(e):
        pct_field.value = str(state["fund_percentage"])
        pct_field.error_text = None
        page.show_dialog(pct_dialog)

    fund_cell = ft.Container(
        on_click=_open_pct_dialog,
        padding=ft.Padding.symmetric(vertical=14, horizontal=0),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Aporte al fondo local", size=15, color=c["on_surface"]),
                ft.Row(
                    spacing=4,
                    controls=[
                        pct_label,
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=c["on_surface_variant"], size=20),
                    ],
                ),
            ],
        ),
    )

    # Group cells as a clean list without borders
    settings_group = ft.Column(
        spacing=0,
        controls=[
            theme_cell,
            fund_cell,
        ],
    )

    return ft.SafeArea(
        content=ft.Container(
            padding=ft.Padding.symmetric(vertical=20, horizontal=20),
            content=settings_group,
        ),
    )
