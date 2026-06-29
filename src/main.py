import flet as ft
import json
import os

from utils.theme import (
    LIGHT_THEME,
    DARK_THEME,
    PRIMARY,
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
        hero_fg=ON_PRIMARY_CONTAINER if light else PRIMARY_DARK,
        input_border=OUTLINE_LIGHT if light else "#5A5A78",
        input_focused=PRIMARY if light else PRIMARY_DARK,
    )


def main(page: ft.Page):
    page.title = "DiezmApp"
    page.padding = ft.Padding.all(0)

    settings = load_settings()
    page.theme_mode = ft.ThemeMode.DARK if settings["theme_mode"] == "dark" else ft.ThemeMode.LIGHT
    fund_percentage = settings["fund_percentage"]
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME

    # ── Result texts ─────────────────────────────────────
    txt_21 = ft.Text(value="", size=16, weight=ft.FontWeight.W_500)
    txt_79 = ft.Text(value="", size=16, weight=ft.FontWeight.W_500)
    txt_1_of_79 = ft.Text(value="", size=16, weight=ft.FontWeight.W_500)
    txt_rest = ft.Text(value="", size=16, weight=ft.FontWeight.W_600)

    lbl_21 = ft.Text("Envío (21%)", size=13)
    lbl_79 = ft.Text("Restante", size=13)
    lbl_1_of_79 = ft.Text(f"Aporte al fondo local ({fund_percentage}%)", size=13)
    lbl_rest = ft.Text("Sostenimiento", size=13, weight=ft.FontWeight.W_600)

    # ── Results container (hidden until first calc) ──────
    results_container = ft.Container(visible=False)

    def _build_results():
        c = _colors(page)

        def _detail_row(label_ctrl: ft.Text, value_ctrl: ft.Text, highlight=False):
            label_ctrl.color = c["hero_fg"] if highlight else c["on_surface_variant"]
            value_ctrl.color = c["hero_fg"] if highlight else c["on_surface"]
            return ft.Container(
                bgcolor=c["hero_bg"] if highlight else None,
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
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            padding=ft.Padding.all(0),
            content=ft.Column(
                spacing=0,
                controls=[
                    _detail_row(lbl_21, txt_21),
                    ft.Divider(height=1, color=c["divider"]),
                    _detail_row(lbl_79, txt_79),
                    ft.Divider(height=1, color=c["divider"]),
                    _detail_row(lbl_1_of_79, txt_1_of_79),
                    ft.Divider(height=1, color=c["divider"]),
                    _detail_row(lbl_rest, txt_rest, highlight=True),
                ],
            ),
        )

        results_container.content = details

    input_amount = ft.TextField(
        label="Cantidad neta ($)",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=12,
        expand=True,
        on_submit=lambda e: calculate(e),
    )

    def format_currency(value: float) -> str:
        return f"${value:,.0f}".replace(",", ".")

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
        val_1_of_79 = val_79 * (fund_percentage / 100)
        val_rest = amount - val_21 - val_1_of_79

        txt_21.value = format_currency(val_21)
        txt_79.value = format_currency(val_79)
        txt_1_of_79.value = format_currency(val_1_of_79)
        txt_rest.value = format_currency(val_rest)

        _build_results()
        results_container.visible = True
        page.update()

    def _apply_appbar():
        light = _is_light(page)
        fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
        settings_btn.icon_color = fg
        page.appbar = ft.AppBar(
            title=ft.Text("DiezmApp", color=fg, weight=ft.FontWeight.W_600, size=18),
            center_title=False,
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
            actions=[settings_btn],
        )

    def _apply_settings_appbar():
        light = _is_light(page)
        fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
        page.appbar = ft.AppBar(
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=fg,
                on_click=lambda e: _navigate_to_main(),
            ),
            title=ft.Text("Configuración", color=fg, weight=ft.FontWeight.W_600, size=18),
            center_title=False,
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
        )

    # ── Settings view ────────────────────────────────────
    def _build_settings_view():
        nonlocal fund_percentage
        c = _colors(page)

        # Theme row
        theme_label = "Claro" if _is_light(page) else "Oscuro"

        def _on_theme_selected(mode: str):
            nonlocal fund_percentage
            if mode == "light":
                page.theme_mode = ft.ThemeMode.LIGHT
            else:
                page.theme_mode = ft.ThemeMode.DARK
            save_settings(mode, fund_percentage)
            page.pop_dialog()
            _navigate_to_settings()

        theme_dialog = ft.AlertDialog(
            title=ft.Text("Seleccionar tema", size=17),
            content=ft.Column(
                tight=True,
                controls=[
                    ft.ListTile(
                        title=ft.Text("Claro"),
                        leading=ft.Icon(ft.Icons.LIGHT_MODE_OUTLINED),
                        on_click=lambda e: _on_theme_selected("light"),
                    ),
                    ft.ListTile(
                        title=ft.Text("Oscuro"),
                        leading=ft.Icon(ft.Icons.DARK_MODE_OUTLINED),
                        on_click=lambda e: _on_theme_selected("dark"),
                    ),
                ],
            ),
        )

        def _open_theme_dialog(e):
            page.show_dialog(theme_dialog)

        theme_row = ft.Container(
            on_click=_open_theme_dialog,
            border_radius=12,
            bgcolor=c["card_bg"],
            border=ft.Border.all(1, c["outline"]),
            padding=ft.Padding.symmetric(vertical=14, horizontal=16),
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
        pct_label = ft.Text(f"{fund_percentage}%", size=14, color=c["on_surface_variant"])

        pct_field = ft.TextField(
            label="Porcentaje (1-30)",
            value=str(fund_percentage),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=12,
        )

        def _close_pct_dialog(e):
            page.pop_dialog()

        def _save_pct(e):
            nonlocal fund_percentage
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
            fund_percentage = val
            current_mode = "dark" if page.theme_mode == ft.ThemeMode.DARK else "light"
            save_settings(current_mode, fund_percentage)
            page.pop_dialog()
            _navigate_to_settings()

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
            pct_field.value = str(fund_percentage)
            pct_field.error_text = None
            page.show_dialog(pct_dialog)

        fund_row = ft.Container(
            on_click=_open_pct_dialog,
            border_radius=12,
            bgcolor=c["card_bg"],
            border=ft.Border.all(1, c["outline"]),
            padding=ft.Padding.symmetric(vertical=14, horizontal=16),
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

        return ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.all(20),
                content=ft.Column(
                    spacing=16,
                    controls=[theme_row, fund_row],
                ),
            ),
        )

    # ── Navigation ───────────────────────────────────────
    calc_btn = ft.FilledButton(
        "Calcular",
        on_click=calculate,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=12)),
        width=float("inf"),
    )

    main_content = ft.SafeArea(
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
    )

    def _navigate_to_settings():
        _apply_settings_appbar()
        page.controls.clear()
        page.add(_build_settings_view())

    def _navigate_to_main():
        nonlocal fund_percentage
        lbl_1_of_79.value = f"Aporte al fondo local ({fund_percentage}%)"
        _apply_appbar()
        page.controls.clear()
        page.add(main_content)
        if results_container.visible:
            _build_results()
            # Recalculate with new percentage if there's a value
            if input_amount.value:
                calculate(None)

    def _open_settings(e):
        _navigate_to_settings()

    settings_btn = ft.IconButton(
        icon=ft.Icons.SETTINGS_OUTLINED,
        tooltip="Configuración",
        on_click=_open_settings,
    )

    _apply_appbar()

    page.add(main_content)


if __name__ == "__main__":
    ft.run(main)
