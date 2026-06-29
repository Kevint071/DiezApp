import flet as ft
import json
import os

from utils.theme import (
    LIGHT_THEME,
    DARK_THEME,
    APPBAR_BGCOLOR_LIGHT,
    APPBAR_BGCOLOR_DARK,
    PRIMARY,
    ON_PRIMARY,
    PRIMARY_CONTAINER,
    ON_PRIMARY_CONTAINER,
    SURFACE_LIGHT,
    SURFACE_VARIANT_LIGHT,
    ON_SURFACE_LIGHT,
    ON_SURFACE_VARIANT_LIGHT,
    OUTLINE_LIGHT,
    DIVIDER_LIGHT,
    SURFACE_DARK,
    SURFACE_VARIANT_DARK,
    ON_SURFACE_DARK,
    ON_SURFACE_VARIANT_DARK,
    OUTLINE_DARK,
    DIVIDER_DARK,
    PRIMARY_DARK,
    HERO_BG_DARK,
)

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")


def load_theme() -> str:
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            return data.get("theme_mode", "light")
    except (FileNotFoundError, json.JSONDecodeError):
        return "light"


def save_theme(mode: str):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"theme_mode": mode}, f)


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
        appbar_bg=APPBAR_BGCOLOR_LIGHT if light else APPBAR_BGCOLOR_DARK,
        appbar_fg=ON_PRIMARY if light else ON_SURFACE_DARK,
        card_bg=SURFACE_VARIANT_LIGHT if light else SURFACE_VARIANT_DARK,
        hero_bg=PRIMARY_CONTAINER if light else HERO_BG_DARK,
        hero_fg=ON_PRIMARY_CONTAINER if light else PRIMARY_DARK,
        input_border=OUTLINE_LIGHT if light else "#5A5A78",
        input_focused=PRIMARY if light else PRIMARY_DARK,
    )


def main(page: ft.Page):
    page.title = "DiezmApp"
    page.padding = ft.Padding.all(0)

    saved_theme = load_theme()
    page.theme_mode = ft.ThemeMode.DARK if saved_theme == "dark" else ft.ThemeMode.LIGHT
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME

    # ── Result texts ─────────────────────────────────────
    txt_rest = ft.Text(value="", size=32, weight=ft.FontWeight.BOLD)
    txt_rest_label = ft.Text(value="", size=13)
    txt_21 = ft.Text(value="", size=16, weight=ft.FontWeight.W_500)
    txt_79 = ft.Text(value="", size=16, weight=ft.FontWeight.W_500)
    txt_1_of_79 = ft.Text(value="", size=16, weight=ft.FontWeight.W_500)

    lbl_21 = ft.Text("21% Diezmo", size=13)
    lbl_79 = ft.Text("79% Restante", size=13)
    lbl_1_of_79 = ft.Text("1% del 79%", size=13)

    # ── Results container (hidden until first calc) ──────
    results_container = ft.Container(visible=False)

    def _build_results():
        c = _colors(page)

        hero_card = ft.Container(
            bgcolor=c["hero_bg"],
            border_radius=16,
            padding=ft.Padding.symmetric(vertical=24, horizontal=20),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                controls=[
                    ft.Text(
                        txt_rest_label.value,
                        size=13,
                        color=c["hero_fg"],
                        opacity=0.8,
                    ),
                    ft.Text(
                        txt_rest.value,
                        size=32,
                        weight=ft.FontWeight.BOLD,
                        color=c["hero_fg"],
                    ),
                ],
            ),
        )

        def _detail_row(label_ctrl: ft.Text, value_ctrl: ft.Text):
            label_ctrl.color = c["on_surface_variant"]
            value_ctrl.color = c["on_surface"]
            return ft.Container(
                padding=ft.Padding.symmetric(vertical=12, horizontal=16),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[label_ctrl, value_ctrl],
                ),
            )

        details = ft.Container(
            bgcolor=c["card_bg"],
            border_radius=12,
            border=ft.Border.all(1, c["outline"]),
            padding=ft.Padding.all(0),
            content=ft.Column(
                spacing=0,
                controls=[
                    _detail_row(lbl_21, txt_21),
                    ft.Divider(height=1, color=c["divider"]),
                    _detail_row(lbl_79, txt_79),
                    ft.Divider(height=1, color=c["divider"]),
                    _detail_row(lbl_1_of_79, txt_1_of_79),
                ],
            ),
        )

        results_container.content = ft.Column(spacing=12, controls=[hero_card, details])

    input_amount = ft.TextField(
        label="Cantidad neta ($)",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        on_submit=lambda e: calculate(e),
    )

    def calculate(e):
        try:
            amount = float(input_amount.value.replace(",", "."))
        except (ValueError, AttributeError):
            input_amount.error_text = "Ingresa un número válido"
            page.update()
            return

        input_amount.error_text = None
        val_21 = amount * 0.21
        val_79 = amount * 0.79
        val_1_of_79 = val_79 * 0.01
        val_rest = amount - val_21 - val_1_of_79

        txt_21.value = f"${val_21:,.2f}"
        txt_79.value = f"${val_79:,.2f}"
        txt_1_of_79.value = f"${val_1_of_79:,.2f}"
        txt_rest.value = f"${val_rest:,.2f}"
        txt_rest_label.value = "Neto final (100% − 21% − 1% del 79%)"

        _build_results()
        results_container.visible = True
        page.update()

    def _apply_appbar():
        c = _colors(page)
        theme_btn.icon = (
            ft.Icons.WB_SUNNY_OUTLINED if _is_light(page) else ft.Icons.WB_SUNNY
        )
        theme_btn.icon_color = c["appbar_fg"]
        page.appbar = ft.AppBar(
            title=ft.Text("DiezmApp", color=c["appbar_fg"], weight=ft.FontWeight.W_600),
            center_title=True,
            bgcolor=c["appbar_bg"],
            actions=[theme_btn],
        )

    def toggle_theme(e):
        if page.theme_mode == ft.ThemeMode.LIGHT:
            page.theme_mode = ft.ThemeMode.DARK
            save_theme("dark")
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            save_theme("light")
        _apply_appbar()
        if results_container.visible:
            _build_results()
        page.update()

    theme_btn = ft.IconButton(
        icon=ft.Icons.WB_SUNNY_OUTLINED if _is_light(page) else ft.Icons.WB_SUNNY,
        tooltip="Cambiar tema",
        on_click=toggle_theme,
    )

    calc_btn = ft.FilledButton(
        "Calcular",
        on_click=calculate,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        width=float("inf"),
    )

    _apply_appbar()

    page.add(
        ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.all(20),
                content=ft.Column(
                    spacing=16,
                    controls=[
                        input_amount,
                        calc_btn,
                        results_container,
                    ],
                ),
            ),
        ),
    )


if __name__ == "__main__":
    ft.run(main)
