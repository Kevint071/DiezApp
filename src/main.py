import contextlib
import traceback

import flet as ft

from utils.app_settings import load_settings, save_settings
from utils.back_nav import install_back_handler, set_back_action
from utils.theme import DARK_THEME, LIGHT_THEME, get_colors
from views.calculator_view import CalculatorView
from views.home_view import build_home_view

# settings_view and other secondary views are lazy-imported on first use to
# speed up startup.


def main(page: ft.Page):
    """Entry point Flet calls to build the page. Any exception here (or any
    hang before the first `page.add`) would otherwise leave the app stuck on
    the native splash screen with no visible feedback, so the build is
    guarded and any failure is rendered directly on-screen."""
    try:
        _main(page)
    except Exception as e:  # noqa: BLE001 — guard de último recurso, cualquier error de build debe mostrarse en pantalla
        _show_fatal_error(page, e)


def _show_fatal_error(page: ft.Page, exc: BaseException):
    """Render the traceback directly on-screen as a last resort, in case adb
    is not attached (this replaces the infinite splash with visible text)."""
    with contextlib.suppress(Exception):
        page.controls.clear()
        page.add(
            ft.Container(
                padding=20,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Text(
                            "Error al iniciar la app",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.RED,
                        ),
                        ft.Text(str(exc), selectable=True, size=13),
                        ft.Text(traceback.format_exc(), selectable=True, size=11),
                    ],
                ),
            )
        )
        page.update()


def _main(page: ft.Page):
    page.title = "DiezApp"
    page.padding = ft.Padding.all(0)

    settings = load_settings()
    page.theme_mode = (
        ft.ThemeMode.DARK if settings["theme_mode"] == "dark" else ft.ThemeMode.LIGHT
    )
    state = {"fund_percentage": settings["fund_percentage"]}
    page.theme = LIGHT_THEME
    page.dark_theme = DARK_THEME

    # ── Leave guard (unsaved-changes protection) ─────────
    leave_guard = {"check": None}

    def _register_leave_guard(fn):
        leave_guard["check"] = fn

    def _guard_navigation(proceed, cancel=None):
        guard = leave_guard["check"]
        if guard:
            guard(proceed, cancel or (lambda: None))
        else:
            proceed()

    install_back_handler(page)

    calculator = CalculatorView(page, state, get_colors)

    def _apply_appbar(title="Inicio", show_back=False, on_back=None, actions=None):
        leave_guard["check"] = None
        set_back_action(
            page,
            (lambda _ob=on_back: _guard_navigation(_ob))
            if (show_back and on_back)
            else None,
        )
        c = get_colors(page)
        fg = c["on_surface"]
        leading = None
        if show_back and on_back:
            leading = ft.Container(
                width=40,
                height=40,
                alignment=ft.Alignment(-1, 0),
                padding=ft.Padding.only(left=14),
                on_click=lambda e, _on_back=on_back: _guard_navigation(_on_back),
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
        nav_bar.bgcolor = c["surface"]

    def _set_appbar_actions(actions):
        if page.appbar:
            page.appbar.actions = actions
            page.update()

    # ── Navigation ───────────────────────────────────────
    main_content: ft.SafeArea | None = None

    # ── Bottom Navigation Bar ────────────────────────────
    nav_state = {"selected_index": 0}

    def _navigate_to_pdf_export():
        from views.saved_calculations_view import build_date_range_picker_view

        _apply_appbar("Exportar PDF")
        page.controls.clear()
        page.add(
            build_date_range_picker_view(
                page, get_colors, on_show_filtered=_navigate_to_filtered_saved
            )
        )

    def _navigate_to_filtered_saved(start, end):
        from views.saved_calculations_view import build_saved_calculations_view

        _apply_appbar("Vista previa", show_back=True, on_back=_navigate_to_pdf_export)
        nav_bar.selected_index = 2

        def _refresh():
            _navigate_to_filtered_saved(start, end)

        page.controls.clear()
        page.add(
            build_saved_calculations_view(
                page, get_colors, _refresh, date_range=(start, end)
            )
        )

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
        prev_idx = nav_state["selected_index"]

        def _perform():
            nav_state["selected_index"] = idx
            if idx == 0:
                _navigate_to_main()
            elif idx == 1:
                _navigate_to_saved()
            elif idx == 2:
                nav_bar.selected_index = 2
                _navigate_to_pdf_export()
                nav_state["prev_index"] = idx
                return
            elif idx == 3:
                _navigate_to_notes()
            elif idx == 4:
                _navigate_to_settings()
            nav_state["prev_index"] = idx

        def _cancel():
            nav_bar.selected_index = prev_idx
            page.update()

        _guard_navigation(_perform, _cancel)

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

        calculator.reset()
        _apply_appbar("Configuración")
        page.controls.clear()
        page.add(
            build_settings_view(
                page, state, save_settings, _navigate_to_settings, get_colors
            )
        )

    def _navigate_to_saved():
        from views.saved_calculations_view import build_saved_calculations_view

        _apply_appbar("Cálculos guardados")
        page.controls.clear()
        page.add(build_saved_calculations_view(page, get_colors, _navigate_to_saved))

    def _navigate_to_notes():
        from views.notes_view import build_notes_view

        _apply_appbar("Notas")
        page.controls.clear()
        page.add(
            build_notes_view(
                page,
                get_colors,
                _navigate_to_new_note,
                _navigate_to_note_detail,
                _navigate_to_notes,
                _set_appbar_actions,
            )
        )

    def _navigate_to_new_note():
        from utils.notes import add_note
        from views.notes_view import build_new_note_view

        def _on_save(title, content):
            add_note(content, title)
            _navigate_to_notes()

        _apply_appbar("Nueva nota", show_back=True, on_back=_navigate_to_notes)
        page.controls.clear()
        page.add(build_new_note_view(page, get_colors, _on_save))

    def _navigate_to_note_detail(note_id):
        from utils.notes import load_notes
        from views.notes_view import build_note_detail_view

        note = next((n for n in load_notes() if n["id"] == note_id), None)
        if note is None:
            _navigate_to_notes()
            return
        _apply_appbar("Nota", show_back=True, on_back=_navigate_to_notes)
        page.controls.clear()
        page.add(
            build_note_detail_view(
                page,
                get_colors,
                note,
                _navigate_to_notes,
                _set_appbar_actions,
                _register_leave_guard,
            )
        )

    def _navigate_to_calc():
        _apply_appbar("Distribución", show_back=True, on_back=_navigate_to_main)
        calculator.prepare_for_show()
        page.controls.clear()
        page.add(calculator.build_content())
        calculator.refresh_after_show()

    def _navigate_to_monthly():
        from views.monthly_summary_view import build_monthly_summary_view

        _apply_appbar("Resumen mensual", show_back=True, on_back=_navigate_to_main)
        page.controls.clear()
        page.add(
            build_monthly_summary_view(page, get_colors, on_back=_navigate_to_main)
        )

    def _navigate_to_main():
        nonlocal main_content
        _apply_appbar()
        main_content = build_home_view(
            page, get_colors, _navigate_to_calc, _navigate_to_monthly
        )
        page.controls.clear()
        page.add(main_content)

    _apply_appbar()
    calculator.prepare_for_show()

    main_content = build_home_view(
        page, get_colors, _navigate_to_calc, _navigate_to_monthly
    )
    page.add(main_content)


if __name__ == "__main__":
    ft.run(main)
