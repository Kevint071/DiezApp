import asyncio
import contextlib
import traceback

import flet as ft

from utils.app_settings import load_settings, save_settings
from utils.theme import (
    DARK_THEME,
    LIGHT_THEME,
    get_colors,
    get_navigation_bar_style,
)
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

    def _guard_navigate(route):
        _guard_navigation(lambda: page.navigate(route))

    calculator = CalculatorView(page, state, get_colors)

    def _build_appbar(title="Inicio", show_back=False, back_route=None, actions=None):
        c = get_colors(page)
        fg = c["on_surface"]
        leading = None
        if show_back and back_route:
            leading = ft.Container(
                width=40,
                height=40,
                alignment=ft.Alignment(-1, 0),
                padding=ft.Padding.only(left=14),
                on_click=lambda e, _r=back_route: _guard_navigate(_r),
                content=ft.Image(
                    src="chevron-left.svg",
                    width=24,
                    height=24,
                    color=fg,
                ),
            )
        nav_bar.bgcolor = ft.Colors.TRANSPARENT
        return ft.AppBar(
            leading=leading,
            leading_width=40 if leading else 0,
            title=ft.Text(title, color=fg, weight=ft.FontWeight.W_600, size=18),
            center_title=False,
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
            elevation_on_scroll=0,
            actions=actions,
        )

    # ── Bottom Navigation Bar ────────────────────────────
    nav_state = {"selected_index": 0}
    _NAV_ROUTES = ["/", "/saved", "/pdf-export", "/notes", "/settings"]
    navigation_colors = get_colors(page)
    navigation_style = get_navigation_bar_style(navigation_colors)
    navigation_style["bgcolor"] = ft.Colors.TRANSPARENT
    navigation_style["label_padding"] = ft.Padding.all(0)
    navigation_style["label_behavior"] = ft.NavigationBarLabelBehavior.ALWAYS_HIDE

    def _on_nav_change(e):
        idx = e.control.selected_index
        prev_idx = nav_state["selected_index"]

        def _perform():
            nav_state["selected_index"] = idx
            page.navigate(_NAV_ROUTES[idx])

        def _cancel():
            nav_bar.selected_index = prev_idx
            page.update()

        _guard_navigation(_perform, _cancel)

    nav_bar = ft.NavigationBar(
        selected_index=0,
        on_change=_on_nav_change,
        **navigation_style,
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

    # ── Root (bottom-nav tab) view ───────────────────────
    # A single persistent View instance reused (mutated in place) for every
    # root/tab, instead of a fresh ft.View per tab: since Flutter's
    # Navigator sees the SAME page identity, switching tabs never gets
    # treated as a route push/pop and so never plays a page-transition
    # animation, no matter which platform default (or theme override) is
    # active. Only genuine drill-down routes below still append brand-new
    # ft.View instances, so those keep their normal push/pop animation.
    root_view = ft.View(route="/", padding=0, navigation_bar=nav_bar)

    def _apply_root(route: str, appbar: ft.AppBar, content: ft.Control) -> ft.View:
        root_view.route = route
        root_view.appbar = appbar
        root_view.controls = [content]
        return root_view

    def _build_main_view() -> ft.View:
        content = build_home_view(
            page,
            get_colors,
            lambda: page.navigate("/calculator"),
            lambda: page.navigate("/monthly"),
        )
        return _apply_root("/", _build_appbar("Inicio"), content)

    def _build_saved_view() -> ft.View:
        from views.saved_calculations_view import build_saved_calculations_view

        # `page.navigate` no-ops when the target route equals the current
        # one, so refreshing in place must call the route handler directly.
        content = build_saved_calculations_view(
            page, get_colors, lambda: route_change()
        )
        return _apply_root("/saved", _build_appbar("Cálculos guardados"), content)

    def _build_pdf_export_view() -> ft.View:
        from views.saved_calculations_view import build_date_range_picker_view

        def _on_show_filtered(start, end):
            page.session.store.set("pdf_export_range", (start, end))
            page.navigate("/pdf-export/preview")

        content = build_date_range_picker_view(
            page, get_colors, on_show_filtered=_on_show_filtered
        )
        return _apply_root("/pdf-export", _build_appbar("Exportar PDF"), content)

    def _build_notes_view() -> ft.View:
        from views.notes_view import build_notes_view

        appbar = _build_appbar("Notas")

        def _set_actions(actions):
            appbar.actions = actions
            page.update()

        def _open_note(note_id):
            page.session.store.set("note_id", note_id)
            page.navigate("/notes/detail")

        content = build_notes_view(
            page,
            get_colors,
            lambda: page.navigate("/notes/new"),
            _open_note,
            lambda: route_change(),
            _set_actions,
        )
        return _apply_root("/notes", appbar, content)

    def _build_settings_view() -> ft.View:
        from views.settings_view import build_settings_view

        calculator.reset()
        content = build_settings_view(
            page,
            state,
            save_settings,
            lambda: route_change(),
            get_colors,
            lambda: page.navigate("/google-drive"),
        )
        return _apply_root("/settings", _build_appbar("Configuración"), content)

    def _build_google_drive_view() -> ft.View:
        from views.google_drive_view import build_google_drive_view

        content = build_google_drive_view(
            page,
            get_colors,
            lambda: route_change(),
            lambda: page.navigate("/google-drive/history"),
        )
        return ft.View(
            route="/google-drive",
            padding=0,
            appbar=_build_appbar(
                "Copias de seguridad", show_back=True, back_route="/settings"
            ),
            controls=[content],
        )

    def _build_google_drive_history_view() -> ft.View:
        from views.google_drive_view import build_google_drive_history_view

        return ft.View(
            route="/google-drive/history",
            padding=0,
            appbar=_build_appbar(
                "Copias realizadas", show_back=True, back_route="/google-drive"
            ),
            controls=[build_google_drive_history_view(page, get_colors)],
        )

    # ── Nested (drill-down) views ─────────────────────────
    def _build_pdf_preview_view() -> ft.View:
        from views.saved_calculations_view import build_saved_calculations_view

        start, end = page.session.store.get("pdf_export_range")
        content = build_saved_calculations_view(
            page,
            get_colors,
            lambda: route_change(),
            date_range=(start, end),
        )
        return ft.View(
            route="/pdf-export/preview",
            padding=0,
            appbar=_build_appbar(
                "Vista previa", show_back=True, back_route="/pdf-export"
            ),
            controls=[content],
        )

    def _build_new_note_view() -> ft.View:
        from utils.notes import add_note
        from views.notes_view import build_new_note_view

        def _on_save(title, content):
            add_note(content, title)
            page.navigate("/notes")

        content = build_new_note_view(page, get_colors, _on_save)
        return ft.View(
            route="/notes/new",
            padding=0,
            appbar=_build_appbar("Nueva nota", show_back=True, back_route="/notes"),
            controls=[content],
        )

    def _build_note_detail_view() -> ft.View:
        from utils.notes import load_notes
        from views.notes_view import build_note_detail_view

        note_id = page.session.store.get("note_id")
        note = next((n for n in load_notes() if n["id"] == note_id), None)
        if note is None:
            return _build_notes_view()

        appbar = _build_appbar("Nota", show_back=True, back_route="/notes")

        def _set_actions(actions):
            appbar.actions = actions
            page.update()

        content = build_note_detail_view(
            page,
            get_colors,
            note,
            lambda: page.navigate("/notes"),
            _set_actions,
            _register_leave_guard,
        )
        view = ft.View(
            route="/notes/detail", padding=0, appbar=appbar, controls=[content]
        )

        # Unsaved-changes guard needs to intercept the pop attempt itself
        # (rather than react after the fact), so this view can't rely on
        # the default can_pop=True + on_view_pop flow like the others.
        view.can_pop = False

        async def _on_confirm_pop(ev):
            await view.confirm_pop(False)
            _guard_navigate("/notes")

        view.on_confirm_pop = _on_confirm_pop
        return view

    def _build_calc_view() -> ft.View:
        calculator.reset()
        calculator.prepare_for_show()
        content = calculator.build_content()
        view = ft.View(
            route="/calculator",
            padding=0,
            appbar=_build_appbar("Distribución", show_back=True, back_route="/"),
            controls=[content],
        )
        return view

    def _build_monthly_view() -> ft.View:
        from views.monthly_summary_view import build_monthly_summary_view

        content = build_monthly_summary_view(page, get_colors)
        return ft.View(
            route="/monthly",
            padding=0,
            appbar=_build_appbar("Detalle Balances", show_back=True, back_route="/"),
            controls=[content],
        )

    def _build_monthly_breakdown_view() -> ft.View:
        from views.monthly_summary_view import (
            build_breakdown_view,
            get_breakdown_title,
        )

        months = page.session.store.get("monthly_breakdown_months") or []
        appbar = _build_appbar(
            get_breakdown_title(page),
            show_back=True,
            back_route="/monthly",
        )

        def _on_indicator_change(label):
            appbar.title.value = f"Desglose de {label}"

        content, indicator_navigation = build_breakdown_view(
            page,
            get_colors,
            months,
            on_indicator_change=_on_indicator_change,
        )
        return ft.View(
            route="/monthly/breakdown",
            padding=0,
            appbar=appbar,
            navigation_bar=indicator_navigation,
            controls=[content],
        )

    # ── Central route dispatcher ──────────────────────────
    def route_change(e=None):
        leave_guard["check"] = None
        route = page.route

        if route.startswith("/callback"):
            # Redirect from the diezmapp-api backend OAuth proxy (custom-scheme
            # deep link, see utils/gdrive_auth.py + pyproject.toml's
            # [tool.flet.*.deep_linking]).
            page.run_task(_handle_gdrive_callback)
            return

        current_navigation_colors = get_colors(page)
        nav_bar.bgcolor = ft.Colors.TRANSPARENT
        nav_bar.indicator_color = current_navigation_colors["navigation_indicator"]

        if route in ("/google-drive", "/google-drive/history"):
            root_idx, root_view = 4, _build_google_drive_view()
        elif route.startswith("/notes"):
            root_idx, root_view = 3, _build_notes_view()
        elif route.startswith("/settings"):
            root_idx, root_view = 4, _build_settings_view()
        elif route.startswith("/pdf-export"):
            root_idx, root_view = 2, _build_pdf_export_view()
        elif route.startswith("/saved"):
            root_idx, root_view = 1, _build_saved_view()
        else:
            root_idx, root_view = 0, _build_main_view()

        nav_bar.selected_index = root_idx
        nav_state["selected_index"] = root_idx

        new_views = [root_view]

        if route == "/calculator":
            new_views.append(_build_calc_view())
        elif route == "/monthly":
            new_views.append(_build_monthly_view())
        elif route == "/monthly/breakdown":
            new_views.append(_build_monthly_view())
            new_views.append(_build_monthly_breakdown_view())
        elif route == "/notes/new":
            new_views.append(_build_new_note_view())
        elif route == "/notes/detail":
            new_views.append(_build_note_detail_view())
        elif route == "/pdf-export/preview":
            new_views.append(_build_pdf_preview_view())
        elif route == "/google-drive/history":
            new_views.append(_build_google_drive_history_view())
        elif route in ("/settings/conflicts", "/settings/conflicts/detail"):
            from views.conflicts_view import (
                build_conflict_detail_view_route,
                build_conflicts_grid_view,
            )

            kind = page.session.store.get("conflicts_kind") or "calculations"
            new_views.append(
                build_conflicts_grid_view(page, get_colors, kind, "/settings")
            )
            if route == "/settings/conflicts/detail":
                idx = page.session.store.get("conflict_index")
                new_views.append(
                    build_conflict_detail_view_route(page, get_colors, kind, idx)
                )

        page.views = new_views
        page.update()

    async def on_view_pop(e):
        if e.view is not None and e.view in page.views:
            page.views.remove(e.view)
        if page.views:
            await page.push_route(page.views[-1].route)

    async def _handle_gdrive_callback():
        from utils.gdrive_auth import complete_folder_picker, complete_link_flow

        query_params = dict(page.query.to_dict)
        if query_params.get("picker") == "1":
            result = await complete_folder_picker(page, query_params)
        else:
            result = await complete_link_flow(page, query_params)
        page.session.store.set("gdrive_link_message", result["message"])
        page.navigate("/google-drive")

    async def _gdrive_scheduler():
        """Startup catch-up + in-app interval loop, both calling run_backup_now()
        (design.md Decision 4: exactly one code path for "a backup happens")."""
        from utils.gdrive_backup import run_backup_now, seconds_until_due

        if seconds_until_due() is not None and seconds_until_due() <= 0:
            await run_backup_now(page)
        while True:
            remaining = seconds_until_due()
            await asyncio.sleep(60 if remaining is None else max(1, min(remaining, 60)))
            if seconds_until_due() is not None and seconds_until_due() <= 0:
                await run_backup_now(page)

    page.on_route_change = route_change
    page.on_view_pop = on_view_pop

    route_change()
    page.run_task(_gdrive_scheduler)


if __name__ == "__main__":
    ft.run(main)
