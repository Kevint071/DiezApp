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
# settings_view and storage are lazy-imported on first use to speed up startup

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
    page.title = "DiezApp"
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
        "Guardar",
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
        from utils.conflicts import conflict_count
        if conflict_count() > 0:
            snack = ft.SnackBar(content=ft.Text("Resuelve los conflictos antes de guardar"), open=True)
            page.overlay.append(snack)
            page.update()
            return
        from utils.storage import add_calculation
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

    def _apply_appbar(title="Inicio", show_back=False, on_back=None, actions=None):
        light = _is_light(page)
        fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
        leading = None
        if show_back and on_back:
            leading = ft.Container(
                width=40,
                height=40,
                alignment=ft.Alignment(-1, 0),
                padding=ft.Padding.only(left=14),
                on_click=lambda e: on_back(),
                content=ft.Image(
                    src="chevron-left.svg",
                    width=24,
                    height=24,
                    color=fg,
                ),
            )
        page.appbar = ft.AppBar(
            leading=leading,
            leading_width=40 if leading else 0,
            title=ft.Text(title, color=fg, weight=ft.FontWeight.W_600, size=18),
            center_title=False,
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
            elevation_on_scroll=0,
            actions=actions,
        )
        nav_bar.bgcolor = _colors(page)["surface"]

    def _set_appbar_actions(actions):
        if page.appbar:
            page.appbar.actions = actions
            page.update()

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

    def _build_calc_content():
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=0, right=0, top=8, bottom=24),
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    scroll=ft.Scrollbar(thickness=6, radius=4),
                    controls=[
                        ft.Container(
                            expand=True,
                            margin=ft.Margin.symmetric(horizontal=24),
                            content=ft.Column(
                                expand=True,
                                spacing=20,
                                controls=[
                                    input_amount,
                                    calc_btn,
                                    results_container,
                                    save_btn,
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )

    def _build_home_card(icon, title, subtitle, on_click):
        c = _colors(page)
        return ft.Container(
            bgcolor=c["card_bg"],
            border_radius=16,
            padding=ft.Padding.all(20),
            on_click=on_click,
            ink=True,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                controls=[
                    ft.Container(
                        width=48,
                        height=48,
                        border_radius=12,
                        bgcolor=ft.Colors.with_opacity(0.1, c["primary"]),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, color=c["primary"], size=24),
                    ),
                    ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(title, size=15, weight=ft.FontWeight.W_600, color=c["on_surface"]),
                            ft.Text(subtitle, size=12, weight=ft.FontWeight.W_400, color=c["on_surface_variant"]),
                        ],
                    ),
                ],
            ),
        )

    def _build_main_content():
        c = _colors(page)
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=0, right=0, top=4, bottom=24),
                content=ft.Column(
                    expand=True,
                    spacing=16,
                    scroll=ft.Scrollbar(thickness=6, radius=4),
                    controls=[
                        ft.Container(
                            expand=True,
                            margin=ft.Margin.symmetric(horizontal=24),
                            content=ft.Column(
                                expand=True,
                                spacing=16,
                                controls=[
                                    ft.Text("¿Qué deseas calcular?", size=14, weight=ft.FontWeight.W_500, color=c["on_surface_variant"]),
                                    _build_home_card(
                                        ft.Icons.PIE_CHART_OUTLINE_ROUNDED,
                                        "Distribución porcentual",
                                        "Calcula envío, fondo local y sostenimiento",
                                        lambda e: _navigate_to_calc(),
                                    ),
                                    _build_home_card(
                                        ft.Icons.CALENDAR_MONTH_ROUNDED,
                                        "Resumen mensual",
                                        "Sumatoria de envíos (21%) por mes",
                                        lambda e: _navigate_to_monthly(),
                                    ),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
        )

    main_content: ft.SafeArea | None = _build_main_content()

    # ── Bottom Navigation Bar ────────────────────────────
    nav_state = {"selected_index": 0}

    def _navigate_to_pdf_export():
        from views.saved_calculations_view import build_date_range_picker_view
        _apply_appbar("Exportar PDF")
        page.controls.clear()
        page.add(build_date_range_picker_view(page, _colors, on_show_filtered=_navigate_to_filtered_saved))

    def _navigate_to_filtered_saved(start, end):
        from views.saved_calculations_view import build_saved_calculations_view
        _apply_appbar("Vista previa", show_back=True, on_back=_navigate_to_pdf_export)
        nav_bar.selected_index = 2

        def _refresh():
            _navigate_to_filtered_saved(start, end)

        page.controls.clear()
        page.add(build_saved_calculations_view(page, _colors, _refresh, date_range=(start, end)))

    def _on_back_from_pdf_export():
        prev = nav_state.get("prev_index", 0)
        nav_bar.selected_index = prev
        if prev == 1:
            _navigate_to_saved()
        elif prev == 3:
            _navigate_to_notes()
        elif prev == 4:
            _navigate_to_settings()
        else:
            _navigate_to_main()
        page.update()

    def _on_nav_change(e):
        idx = e.control.selected_index
        nav_state["selected_index"] = idx
        if idx == 0:
            _navigate_to_main()
        elif idx == 1:
            _navigate_to_saved()
        elif idx == 2:
            nav_bar.selected_index = 2
            _navigate_to_pdf_export()
            return
        elif idx == 3:
            _navigate_to_notes()
        elif idx == 4:
            _navigate_to_settings()
        nav_state["prev_index"] = idx

    nav_bar = ft.NavigationBar(
        selected_index=0,
        on_change=_on_nav_change,
        label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_HIDE,
        shadow_color=ft.Colors.TRANSPARENT,
        indicator_color=ft.Colors.TRANSPARENT,
        overlay_color=ft.Colors.TRANSPARENT,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME_ROUNDED,
                label="Inicio",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.HISTORY_OUTLINED,
                selected_icon=ft.Icons.HISTORY_ROUNDED,
                label="Historial",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                selected_icon=ft.Icons.PICTURE_AS_PDF_ROUNDED,
                label="Exportar",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.STICKY_NOTE_2_OUTLINED,
                selected_icon=ft.Icons.STICKY_NOTE_2_ROUNDED,
                label="Notas",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS_ROUNDED,
                label="Ajustes",
            ),
        ],
    )

    page.navigation_bar = nav_bar

    def _navigate_to_settings():
        from views.settings_view import build_settings_view
        input_amount.value = ""
        results_container.visible = False
        save_btn.visible = False
        _apply_appbar("Configuración")
        page.controls.clear()
        page.add(build_settings_view(page, state, save_settings, _navigate_to_settings, _colors))

    def _navigate_to_saved():
        from views.saved_calculations_view import build_saved_calculations_view
        _apply_appbar("Cálculos guardados")
        page.controls.clear()
        page.add(build_saved_calculations_view(page, _colors, _navigate_to_saved))

    def _navigate_to_notes():
        from views.notes_view import build_notes_view
        _apply_appbar("Notas")
        page.controls.clear()
        page.add(build_notes_view(page, _colors, _navigate_to_new_note, _navigate_to_note_detail, _navigate_to_notes, _set_appbar_actions))

    def _navigate_to_new_note():
        from views.notes_view import build_new_note_view
        from utils.notes import add_note

        def _on_save(title, content):
            add_note(content, title)
            _navigate_to_notes()

        _apply_appbar("Nueva nota", show_back=True, on_back=_navigate_to_notes)
        page.controls.clear()
        page.add(build_new_note_view(page, _colors, _on_save))

    def _navigate_to_note_detail(note_id):
        from views.notes_view import build_note_detail_view
        from utils.notes import load_notes

        note = next((n for n in load_notes() if n["id"] == note_id), None)
        if note is None:
            _navigate_to_notes()
            return
        _apply_appbar("Nota", show_back=True, on_back=_navigate_to_notes)
        page.controls.clear()
        page.add(build_note_detail_view(page, _colors, note, _navigate_to_notes, _set_appbar_actions))

    def _navigate_to_calc():
        lbl_1_of_79.value = f"Fondo local ({state['fund_percentage']}%)"
        _apply_appbar("Distribución", show_back=True, on_back=_navigate_to_main)
        _apply_input_colors()
        page.controls.clear()
        page.add(_build_calc_content())
        if results_container.visible:
            _build_results()
            if input_amount.value:
                calculate(None)

    def _navigate_to_monthly():
        from views.monthly_summary_view import build_monthly_summary_view
        _apply_appbar("Resumen mensual", show_back=True, on_back=_navigate_to_main)
        page.controls.clear()
        page.add(build_monthly_summary_view(page, _colors, on_back=_navigate_to_main))

    def _navigate_to_main():
        nonlocal main_content
        _apply_appbar()
        main_content = _build_main_content()
        page.controls.clear()
        page.add(main_content)

    _apply_appbar()
    _apply_input_colors()

    page.add(main_content)


if __name__ == "__main__":
    ft.run(main)
