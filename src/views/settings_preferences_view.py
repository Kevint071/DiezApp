import flet as ft

from diezapp.shared.presentation.theme import (
    FOCUS_DARK,
    FOCUS_LIGHT,
    OUTLINE_LIGHT_INPUT,
    SURFACE_DARK,
    SURFACE_LIGHT,
)


def build_preferences_section(
    page: ft.Page,
    state: dict,
    save_settings,
    navigate_to_settings,
    colors: dict,
    settings_cell,
):
    """Build the general settings group and its preference dialogs."""
    light = page.theme_mode == ft.ThemeMode.LIGHT

    def _on_theme_selected(mode: str):
        if mode == "light":
            page.theme_mode = ft.ThemeMode.LIGHT
            page.bgcolor = SURFACE_LIGHT
        else:
            page.theme_mode = ft.ThemeMode.DARK
            page.bgcolor = SURFACE_DARK
        save_settings(mode, state["fund_percentage"])
        page.pop_dialog()
        navigate_to_settings()

    def _theme_option(label, icon, mode, is_selected):
        return ft.Container(
            on_click=lambda e: _on_theme_selected(mode),
            border_radius=12,
            padding=ft.Padding.symmetric(vertical=12, horizontal=14),
            bgcolor=colors["primary"] if is_selected else ft.Colors.TRANSPARENT,
            content=ft.Row(
                spacing=12,
                controls=[
                    ft.Icon(
                        icon,
                        size=20,
                        color=colors["on_primary"]
                        if is_selected
                        else colors["on_surface_variant"],
                    ),
                    ft.Text(
                        label,
                        size=15,
                        weight=ft.FontWeight.W_500,
                        color=colors["on_primary"]
                        if is_selected
                        else colors["on_surface"],
                    ),
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

    theme_cell = settings_cell(
        icon=ft.Icons.PALETTE_OUTLINED,
        title="Tema",
        subtitle="Claro" if light else "Oscuro",
        colors=colors,
        on_click=_open_theme_dialog,
    )

    focus_color = FOCUS_LIGHT if light else FOCUS_DARK
    input_border = OUTLINE_LIGHT_INPUT if light else colors["outline"]
    percentage_field = ft.TextField(
        label="Porcentaje",
        value=str(state["fund_percentage"]),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        content_padding=ft.Padding.symmetric(vertical=14, horizontal=14),
        suffix=ft.Text("%", color=colors["on_surface_variant"]),
        border_color=input_border,
        focused_border_color=focus_color,
    )

    def _validate_percentage(e):
        raw = percentage_field.value.strip()
        if not raw:
            percentage_field.error = None
        else:
            try:
                value = int(raw)
            except ValueError, TypeError:
                percentage_field.error = "Ingresa un número válido"
            else:
                percentage_field.error = (
                    None if 1 <= value <= 30 else "Debe ser entre 1% y 30%"
                )
        percentage_dialog.update()

    def _save_percentage(e):
        raw = percentage_field.value.strip()
        try:
            value = int(raw)
        except ValueError, TypeError:
            percentage_field.error = "Ingresa un número válido"
            percentage_dialog.update()
            return
        if value < 1 or value > 30:
            percentage_field.error = "Debe ser entre 1% y 30%"
            percentage_dialog.update()
            return
        state["fund_percentage"] = value
        current_mode = "dark" if page.theme_mode == ft.ThemeMode.DARK else "light"
        save_settings(current_mode, value)
        page.pop_dialog()
        navigate_to_settings()

    percentage_field.on_submit = _save_percentage
    percentage_field.on_change = _validate_percentage
    percentage_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Aporte al fondo local", size=17, weight=ft.FontWeight.W_600),
        content_padding=ft.Padding.only(left=24, right=24, top=16, bottom=8),
        content=ft.Column(tight=True, spacing=0, controls=[percentage_field]),
        actions=[
            ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
            ft.FilledTonalButton("Guardar", on_click=_save_percentage),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def _open_percentage_dialog(e):
        percentage_field.value = str(state["fund_percentage"])
        percentage_field.error = None
        page.show_dialog(percentage_dialog)

    fund_cell = settings_cell(
        icon=ft.Icons.SAVINGS_OUTLINED,
        title="Fondo local",
        subtitle=f"{state['fund_percentage']}%",
        colors=colors,
        on_click=_open_percentage_dialog,
    )
    divider = ft.Container(
        padding=ft.Padding.symmetric(horizontal=18, vertical=0),
        content=ft.Divider(height=1, color=colors["divider"]),
    )
    return ft.Container(
        bgcolor=colors["card_bg"],
        border_radius=16,
        padding=ft.Padding.symmetric(vertical=6, horizontal=0),
        content=ft.Column(spacing=0, controls=[theme_cell, divider, fund_cell]),
    )
