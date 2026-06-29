import flet as ft
import json
import os

from utils.theme import (
    LIGHT_THEME,
    DARK_THEME,
    PRIMARY,
    ON_PRIMARY,
    PRIMARY_CONTAINER,
    ON_PRIMARY_CONTAINER,
    SURFACE_LIGHT,
    SURFACE_VARIANT_LIGHT,
    ON_SURFACE_LIGHT,
    ON_SURFACE_VARIANT_LIGHT,
    OUTLINE_LIGHT,
    OUTLINE_LIGHT_INPUT,
    DIVIDER_LIGHT,
    SURFACE_DARK,
    SURFACE_VARIANT_DARK,
    ON_SURFACE_DARK,
    ON_SURFACE_VARIANT_DARK,
    OUTLINE_DARK,
    OUTLINE_DARK_INPUT,
    DIVIDER_DARK,
    PRIMARY_DARK,
    HERO_BG_DARK,
    PRIMARY_LIGHT,
    FOCUS_LIGHT,
    FOCUS_DARK,
)
from views.settings_view import apply_settings_appbar, build_settings_view
from views.saved_calculations_view import apply_saved_calculations_appbar, build_saved_calculations_view
from utils.storage import add_calculation

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_settings() -> dict:
    """Load theme_mode and fund_percentage from settings.json."""
    defaults = {"theme_mode": "light", "fund_percentage": 1}
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            return {
                "theme_mode": data.get("theme_mode", defaults["theme_mode"]),
                "fund_percentage": data.get("fund_percentage", defaults["fund_percentage"]),
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return defaults


def save_settings(theme_mode: str, fund_percentage: int):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"theme_mode": theme_mode, "fund_percentage": fund_percentage}, f)


def _is_light(page: ft.Page) -> bool:
    return page.theme_mode == ft.ThemeMode.LIGHT


def _colors(page: ft.Page):
    """Return a dict of contextual colors for the current theme mode."""
    light = _is_light(page)
    return dict(
        surface=SURFACE_LIGHT if light else SURFACE_DARK,
        surface_variant=SURFACE_VARIANT_LIGHT if light else SURFACE_VARIANT_DARK,
        on_surface=ON_SURFACE_LIGHT if light else ON_SURFACE_DARK,
        on_surface_variant=ON_SURFACE_VARIANT_LIGHT if light else ON_SURFACE_VARIANT_DARK,
        outline=OUTLINE_LIGHT if light else OUTLINE_DARK,
        divider=DIVIDER_LIGHT if light else DIVIDER_DARK,
        card_bg=SURFACE_VARIANT_LIGHT if light else SURFACE_VARIANT_DARK,
        hero_bg=PRIMARY_CONTAINER if light else HERO_BG_DARK,
        hero_fg=ON_PRIMARY_CONTAINER if light else "#A7F3D0",
        input_border=OUTLINE_LIGHT_INPUT if light else OUTLINE_DARK_INPUT,
        input_focused=FOCUS_LIGHT if light else FOCUS_DARK,
        primary=PRIMARY if light else PRIMARY_DARK,
        primary_light=PRIMARY_LIGHT if light else "#34D399",
        on_primary=ON_PRIMARY if light else "#F1F5F9",
    )


def main(page: ft.Page):
    page.title = "DiezmApp"
    page.padding = ft.Padding.all(0)

    settings = load_settings()
    page.theme_mode = ft.ThemeMode.DARK if settings["theme_mode"] == "dark" else ft.ThemeMode.LIGHT
    state = {"fund_percentage": settings["fund_percentage"]}
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME

    # ── Result texts ─────────────────────────────────────
    txt_21 = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)
    txt_79 = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)
    txt_1_of_79 = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)
    txt_rest = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)

    lbl_21 = ft.Text("Envío (21%)", size=13, weight=ft.FontWeight.W_500)
    lbl_79 = ft.Text("Restante", size=13, weight=ft.FontWeight.W_500)
    lbl_1_of_79 = ft.Text(f"Fondo local ({state['fund_percentage']}%)", size=13, weight=ft.FontWeight.W_500)
    lbl_rest = ft.Text("Sostenimiento", size=13, weight=ft.FontWeight.W_500)

    # ── Results container (hidden until first calc) ──────
    results_container = ft.Container(visible=False)

    # ── Save button (hidden until first calc) ────────────
    save_btn = ft.OutlinedButton(
        "Guardar cálculo",
        icon=ft.Icons.SAVE_OUTLINED,
        visible=False,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        width=float("inf"),
    )

    def _build_results():
        c = _colors(page)

        def _result_tile(label_ctrl: ft.Text, value_ctrl: ft.Text):
            label_ctrl.color = c["on_surface_variant"]
            value_ctrl.color = c["primary"]
            return ft.Container(
                bgcolor=c["card_bg"],
                border_radius=14,
                padding=ft.Padding.symmetric(vertical=12, horizontal=16),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[label_ctrl, value_ctrl],
                ),
            )

        results_container.content = ft.Column(
            spacing=10,
            controls=[
                ft.Container(height=8),
                ft.Text(
                    "Distribución",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=c["on_surface_variant"],
                ),
                _result_tile(lbl_21, txt_21),
                _result_tile(lbl_79, txt_79),
                _result_tile(lbl_1_of_79, txt_1_of_79),
                _result_tile(lbl_rest, txt_rest),
            ],
        )

    def _format_input_number(e):
        """Format the input with dots as thousand separators while typing."""
        raw = input_amount.value.replace(".", "").replace(",", "")
        if not raw:
            return
        # Keep only digits
        digits = "".join(c for c in raw if c.isdigit())
        if not digits:
            input_amount.value = ""
            page.update()
            return
        # Format with dots every 3 digits
        formatted = ""
        for i, d in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                formatted = "." + formatted
            formatted = d + formatted
        input_amount.value = formatted
        page.update()

    input_amount = ft.TextField(
        label="Cantidad neta ($)",
        label_style=ft.TextStyle(weight=ft.FontWeight.W_400),
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        content_padding=ft.Padding.symmetric(vertical=14, horizontal=14),
        text_size=15,
        expand=True,
        on_submit=lambda e: calculate(e),
        on_change=_format_input_number,
    )

    def _apply_input_colors():
        c = _colors(page)
        input_amount.border_color = c["input_border"]
        input_amount.focused_border_color = c["input_focused"]

    def format_currency(value: float) -> str:
        return f"${value:,.0f}".replace(",", ".")

    def calculate(e):
        try:
            amount = float(input_amount.value.replace(".", "").replace(",", "."))
        except (ValueError, AttributeError):
            input_amount.error = "Ingresa un número válido"
            page.update()
            return

        input_amount.error = None
        val_21 = amount * 0.21
        val_79 = amount * 0.79
        val_1_of_79 = val_79 * (state["fund_percentage"] / 100)
        val_rest = amount - val_21 - val_1_of_79

        txt_21.value = format_currency(val_21)
        txt_79.value = format_currency(val_79)
        txt_1_of_79.value = format_currency(val_1_of_79)
        txt_rest.value = format_currency(val_rest)

        _build_results()
        results_container.visible = True
        save_btn.visible = True
        page.update()

    def _save_calculation(e):
        try:
            amount = float(input_amount.value.replace(".", "").replace(",", "."))
        except (ValueError, AttributeError):
            return
        val_21 = amount * 0.21
        val_79 = amount * 0.79
        val_1_of_79 = val_79 * (state["fund_percentage"] / 100)
        val_rest = amount - val_21 - val_1_of_79
        add_calculation(amount, val_21, val_79, val_1_of_79, val_rest, state["fund_percentage"])
        save_btn.visible = False
        page.update()

    save_btn.on_click = _save_calculation

    def _apply_appbar():
        light = _is_light(page)
        fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
        settings_btn.icon_color = fg
        history_btn.icon_color = fg
        page.appbar = ft.AppBar(
            title=ft.Text("DiezmApp", color=fg, weight=ft.FontWeight.W_600, size=18),
            center_title=False,
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
            actions=[history_btn, settings_btn, ft.Container(width=8)],
        )

    # ── Navigation ───────────────────────────────────────
    calc_btn = ft.FilledButton(
        "Calcular",
        on_click=calculate,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        width=float("inf"),
    )

    def _build_main_content():
        return ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
                content=ft.Column(
                    spacing=20,
                    controls=[
                        input_amount,
                        calc_btn,
                        results_container,
                        save_btn,
                    ],
                ),
            ),
        )

    main_content = _build_main_content()

    def _navigate_to_settings():
        input_amount.value = ""
        results_container.visible = False
        save_btn.visible = False
        apply_settings_appbar(page, _navigate_to_main, _colors)
        page.controls.clear()
        page.add(build_settings_view(page, state, save_settings, _navigate_to_settings, _colors))

    def _navigate_to_saved():
        from utils.storage import load_calculations as _load_calcs
        has_calcs = len(_load_calcs()) > 0
        apply_saved_calculations_appbar(page, _navigate_to_main, _colors, has_calcs)
        page.controls.clear()
        page.add(build_saved_calculations_view(page, _colors, _navigate_to_saved))

    def _navigate_to_main():
        nonlocal main_content
        lbl_1_of_79.value = f"Fondo local ({state['fund_percentage']}%)"
        _apply_appbar()
        _apply_input_colors()
        main_content = _build_main_content()
        page.controls.clear()
        page.add(main_content)
        if results_container.visible:
            _build_results()
            if input_amount.value:
                calculate(None)

    def _open_settings(e):
        _navigate_to_settings()

    def _open_saved(e):
        _navigate_to_saved()

    settings_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS_OUTLINED,
        tooltip="Configuración",
        on_click=_open_settings,
    )

    history_btn = ft.IconButton(
        icon=ft.Icons.HISTORY,
        tooltip="Cálculos guardados",
        on_click=_open_saved,
    )

    _apply_appbar()
    _apply_input_colors()

    page.add(main_content)


if __name__ == "__main__":
    ft.run(main)
