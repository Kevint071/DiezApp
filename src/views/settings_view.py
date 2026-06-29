import flet as ft

from utils.theme import (
    ON_SURFACE_LIGHT,
    ON_SURFACE_DARK,
    FOCUS_LIGHT,
    FOCUS_DARK,
    OUTLINE_LIGHT_INPUT,
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
            weight=ft.FontWeight.W_700,
            size=17,
        ),
        center_title=False,
        leading_width=40,
        title_spacing=0,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
    )


def build_settings_view(page: ft.Page, state: dict, save_settings, navigate_to_settings, colors_fn):
    """Build the settings view."""
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
            padding=ft.Padding.symmetric(vertical=12, horizontal=14),
            bgcolor=c["primary"] if is_selected else ft.Colors.TRANSPARENT,
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Icon(icon, size=20, color=c["on_primary"] if is_selected else c["on_surface_variant"]),
                    ft.Text(label, size=15, weight=ft.FontWeight.W_500, color=c["on_primary"] if is_selected else c["on_surface"]),
                ],
            ),
        )

    theme_dialog = ft.AlertDialog(
        title=ft.Text("Tema", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=20, right=20, top=12, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=6,
            controls=[
                _theme_option("Claro", ft.Icons.LIGHT_MODE_OUTLINED, "light", light),
                _theme_option("Oscuro", ft.Icons.DARK_MODE_OUTLINED, "dark", not light),
            ],
        ),
    )

    def _open_theme_dialog(e):
        page.show_dialog(theme_dialog)

    theme_cell = _settings_cell(
        icon=ft.Icons.PALETTE_OUTLINED,
        title="Tema",
        subtitle=theme_label,
        colors=c,
        on_click=_open_theme_dialog,
    )

    # Fund percentage row + modal
    fund_percentage = state["fund_percentage"]

    focus_color = FOCUS_LIGHT if light else FOCUS_DARK
    input_border = OUTLINE_LIGHT_INPUT if light else c["outline"]

    def _on_pct_change(e):
        raw = pct_field.value.strip()
        if not raw:
            pct_field.error = None
            pct_dialog.update()
            return
        try:
            val = int(raw)
        except (ValueError, TypeError):
            pct_field.error = "Ingresa un número válido"
            pct_dialog.update()
            return
        if val < 1 or val > 30:
            pct_field.error = "Debe ser entre 1% y 30%"
        else:
            pct_field.error = None
        pct_dialog.update()

    pct_field = ft.TextField(
        label="Porcentaje",
        value=str(fund_percentage),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        content_padding=ft.Padding.symmetric(vertical=14, horizontal=14),
        suffix=ft.Text("%", color=c["on_surface_variant"]),
        border_color=input_border,
        focused_border_color=focus_color,
        on_submit=lambda e: _save_pct(e),
        on_change=_on_pct_change,
    )

    def _close_pct_dialog(e):
        page.pop_dialog()

    def _save_pct(e):
        raw = pct_field.value.strip()
        try:
            val = int(raw)
        except (ValueError, TypeError):
            pct_field.error = "Ingresa un número válido"
            pct_dialog.update()
            return
        if val < 1 or val > 30:
            pct_field.error = "Debe ser entre 1% y 30%"
            pct_dialog.update()
            return
        pct_field.error = None
        state["fund_percentage"] = val
        current_mode = "dark" if page.theme_mode == ft.ThemeMode.DARK else "light"
        save_settings(current_mode, val)
        page.pop_dialog()
        navigate_to_settings()

    pct_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Aporte al fondo local", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(
            tight=True,
            spacing=0,
            controls=[pct_field],
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_close_pct_dialog),
            ft.FilledTonalButton("Guardar", on_click=_save_pct),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_pct_dialog(e):
        pct_field.value = str(state["fund_percentage"])
        pct_field.error = None
        page.show_dialog(pct_dialog)

    fund_cell = _settings_cell(
        icon=ft.Icons.SAVINGS_OUTLINED,
        title="Fondo local",
        subtitle=f"{fund_percentage}%",
        colors=c,
        on_click=_open_pct_dialog,
    )

    # Section header + grouped cells
    settings_group = ft.Container(
        bgcolor=c["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(
            spacing=0,
            controls=[
                theme_cell,
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=18, vertical=0),
                    content=ft.Divider(height=1, color=c["divider"]),
                ),
                fund_cell,
            ],
        ),
    )

    return ft.SafeArea(
        content=ft.Container(
            padding=ft.Padding.only(top=12, left=24, right=24, bottom=24),
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
                ],
            ),
        ),
    )


def _settings_cell(icon, title, subtitle, colors, on_click):
    """Helper to build a consistent settings row."""
    return ft.Container(
        on_click=on_click,
        padding=ft.Padding.symmetric(vertical=14, horizontal=18),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=14,
                    controls=[
                        ft.Icon(icon, size=22, color=colors["primary"]),
                        ft.Text(title, size=15, color=colors["on_surface"], weight=ft.FontWeight.W_500),
                    ],
                ),
                ft.Row(
                    spacing=4,
                    controls=[
                        ft.Text(subtitle, size=14, color=colors["on_surface_variant"]),
                        ft.Icon(ft.Icons.CHEVRON_RIGHT, color=colors["on_surface_variant"], size=20),
                    ],
                ),
            ],
        ),
    )
