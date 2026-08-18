import flet as ft

from diezapp.bootstrap.dependencies import AppDependencies
from diezapp.bootstrap.lifecycle import run_google_drive_scheduler
from diezapp.features.calculator.presentation.calculator_page import CalculatorView
from diezapp.features.home.presentation.home_page import build_home_view
from diezapp.features.settings.domain.models import AppSettings
from diezapp.navigation import routes
from diezapp.navigation.navigation_state import NavigationState
from diezapp.navigation.oauth_callback_handler import OAuthCallbackHandler
from diezapp.navigation.router import AppRouter
from diezapp.shared.presentation.theme import (
    get_colors,
    get_navigation_bar_style,
)

# settings_view and other secondary views are lazy-imported on first use to
# speed up startup.


def build_app(page: ft.Page, dependencies: AppDependencies, state: AppSettings):

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

    calculator = CalculatorView(
        page,
        state,
        get_colors,
        dependencies.create_calculation,
        dependencies.calculate_distribution,
        dependencies.conflicts,
    )

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
    nav_state = NavigationState()
    _NAV_ROUTES = routes.ROOT_ROUTES
    navigation_colors = get_colors(page)
    navigation_style = get_navigation_bar_style(navigation_colors)
    navigation_style["bgcolor"] = ft.Colors.TRANSPARENT
    navigation_style["label_padding"] = ft.Padding.all(0)
    navigation_style["label_behavior"] = ft.NavigationBarLabelBehavior.ALWAYS_HIDE

    def _on_nav_change(e):
        router.handle_navigation_change(e, _NAV_ROUTES)

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
            lambda: page.navigate(routes.CALCULATOR),
            lambda: page.navigate(routes.MONTHLY),
        )
        return _apply_root(routes.HOME, _build_appbar("Inicio"), content)

    def _build_saved_view() -> ft.View:
        from diezapp.features.calculations.presentation.calculations_page import (
            build_saved_calculations_view,
        )

        # `page.navigate` no-ops when the target route equals the current
        # one, so refreshing in place must call the route handler directly.
        content = build_saved_calculations_view(
            page,
            get_colors,
            lambda: route_change(),
            dependencies.calculations,
            dependencies.update_calculation,
            dependencies.delete_calculation,
            dependencies.conflicts,
            dependencies.pdf_export,
        )
        return _apply_root(routes.SAVED, _build_appbar("Cálculos guardados"), content)

    def _build_pdf_export_view() -> ft.View:
        from diezapp.features.calculations.presentation.calculations_page import (
            build_date_range_picker_view,
        )

        def _on_show_filtered(start, end):
            page.session.store.set("pdf_export_range", (start, end))
            page.navigate(routes.PDF_PREVIEW)

        content = build_date_range_picker_view(
            page,
            get_colors,
            dependencies.calculations,
            on_show_filtered=_on_show_filtered,
        )
        return _apply_root(routes.PDF_EXPORT, _build_appbar("Exportar PDF"), content)

    def _build_notes_view() -> ft.View:
        from diezapp.features.notes.presentation.notes_page import build_notes_view

        appbar = _build_appbar("Notas")

        def _set_actions(actions):
            appbar.actions = actions
            page.update()

        def _open_note(note_id):
            page.session.store.set("note_id", note_id)
            page.navigate(routes.NOTES_DETAIL)

        content = build_notes_view(
            page,
            get_colors,
            lambda: page.navigate(routes.NOTES_NEW),
            _open_note,
            lambda: route_change(),
            dependencies.notes,
            dependencies.conflicts,
            _set_actions,
        )
        return _apply_root(routes.NOTES, appbar, content)

    def _build_settings_view() -> ft.View:
        from diezapp.features.settings.presentation.settings_page import (
            build_settings_view,
        )

        calculator.reset()
        content = build_settings_view(
            page,
            state,
            dependencies.settings.save,
            lambda: route_change(),
            get_colors,
            lambda: page.navigate(routes.GOOGLE_DRIVE),
            dependencies.conflicts,
            dependencies.local_backup,
            dependencies.calculations,
            dependencies.notes,
        )
        return _apply_root(routes.SETTINGS, _build_appbar("Configuración"), content)

    def _build_google_drive_view() -> ft.View:
        from diezapp.features.google_drive.presentation.google_drive_page import (
            build_google_drive_view,
        )

        content = build_google_drive_view(
            page,
            get_colors,
            lambda: route_change(),
            lambda: page.navigate(routes.GOOGLE_DRIVE_HISTORY),
            dependencies.google_drive_link,
            dependencies.google_drive_url_opener,
            dependencies.google_drive_schedule_settings,
            dependencies.google_drive_backup,
            dependencies.google_drive_refresh_token,
            dependencies.google_drive_oauth,
            dependencies.google_drive_folders,
        )
        return ft.View(
            route=routes.GOOGLE_DRIVE,
            padding=0,
            appbar=_build_appbar(
                "Copias de seguridad", show_back=True, back_route=routes.SETTINGS
            ),
            controls=[content],
        )

    def _build_google_drive_history_view() -> ft.View:
        from diezapp.features.google_drive.presentation.google_drive_page import (
            build_google_drive_history_view,
        )

        return ft.View(
            route=routes.GOOGLE_DRIVE_HISTORY,
            padding=0,
            appbar=_build_appbar(
                "Copias realizadas", show_back=True, back_route=routes.GOOGLE_DRIVE
            ),
            controls=[
                build_google_drive_history_view(
                    page,
                    get_colors,
                    dependencies.google_drive_history,
                    dependencies.google_drive_link,
                    dependencies.google_drive_refresh_token,
                    dependencies.local_backup,
                    dependencies.calculations,
                    dependencies.notes,
                    dependencies.conflicts,
                )
            ],
        )

    # ── Nested (drill-down) views ─────────────────────────
    def _build_pdf_preview_view() -> ft.View:
        from diezapp.features.calculations.presentation.calculations_page import (
            build_saved_calculations_view,
        )

        start, end = page.session.store.get("pdf_export_range")
        content = build_saved_calculations_view(
            page,
            get_colors,
            lambda: route_change(),
            dependencies.calculations,
            dependencies.update_calculation,
            dependencies.delete_calculation,
            dependencies.conflicts,
            dependencies.pdf_export,
            date_range=(start, end),
        )
        return ft.View(
            route=routes.PDF_PREVIEW,
            padding=0,
            appbar=_build_appbar(
                "Vista previa", show_back=True, back_route=routes.PDF_EXPORT
            ),
            controls=[content],
        )

    def _build_new_note_view() -> ft.View:
        from diezapp.features.notes.presentation.notes_page import build_new_note_view

        def _on_save(title, content):
            dependencies.notes.add(content, title)
            page.navigate(routes.NOTES)

        content = build_new_note_view(
            page, get_colors, _on_save, dependencies.conflicts
        )
        return ft.View(
            route=routes.NOTES_NEW,
            padding=0,
            appbar=_build_appbar("Nueva nota", show_back=True, back_route=routes.NOTES),
            controls=[content],
        )

    def _build_note_detail_view() -> ft.View:
        from diezapp.features.notes.presentation.notes_page import (
            build_note_detail_view,
        )

        note_id = page.session.store.get("note_id")
        note = next((n for n in dependencies.notes.list() if n["id"] == note_id), None)
        if note is None:
            return _build_notes_view()

        appbar = _build_appbar("Nota", show_back=True, back_route=routes.NOTES)

        def _set_actions(actions):
            appbar.actions = actions
            page.update()

        content = build_note_detail_view(
            page,
            get_colors,
            note,
            lambda: page.navigate(routes.NOTES),
            _set_actions,
            dependencies.notes,
            dependencies.conflicts,
            _register_leave_guard,
        )
        view = ft.View(
            route=routes.NOTES_DETAIL, padding=0, appbar=appbar, controls=[content]
        )

        # Unsaved-changes guard needs to intercept the pop attempt itself
        # (rather than react after the fact), so this view can't rely on
        # the default can_pop=True + on_view_pop flow like the others.
        view.can_pop = False

        async def _on_confirm_pop(ev):
            await view.confirm_pop(False)
            _guard_navigate(routes.NOTES)

        view.on_confirm_pop = _on_confirm_pop
        return view

    def _build_calc_view() -> ft.View:
        calculator.reset()
        calculator.prepare_for_show()
        content = calculator.build_content()
        view = ft.View(
            route=routes.CALCULATOR,
            padding=0,
            appbar=_build_appbar(
                "Distribución", show_back=True, back_route=routes.HOME
            ),
            controls=[content],
        )
        return view

    def _build_monthly_view() -> ft.View:
        from diezapp.features.monthly_summary.presentation.monthly_summary_page import (
            build_monthly_summary_view,
        )

        content = build_monthly_summary_view(
            page, get_colors, dependencies.monthly_summary
        )
        return ft.View(
            route=routes.MONTHLY,
            padding=0,
            appbar=_build_appbar(
                "Detalle Balances", show_back=True, back_route=routes.HOME
            ),
            controls=[content],
        )

    def _build_monthly_breakdown_view() -> ft.View:
        from diezapp.features.monthly_summary.presentation.monthly_summary_page import (
            build_breakdown_view,
            get_breakdown_title,
        )

        months = page.session.store.get("monthly_breakdown_months") or []
        appbar = _build_appbar(
            get_breakdown_title(page),
            show_back=True,
            back_route=routes.MONTHLY,
        )

        def _on_indicator_change(label):
            appbar.title.value = f"Desglose de {label}"

        content, indicator_navigation = build_breakdown_view(
            page,
            get_colors,
            months,
            dependencies.monthly_summary,
            on_indicator_change=_on_indicator_change,
        )
        return ft.View(
            route=routes.MONTHLY_BREAKDOWN,
            padding=0,
            appbar=appbar,
            navigation_bar=indicator_navigation,
            controls=[content],
        )

    def _build_root(route: str) -> tuple[int, ft.View]:
        current_navigation_colors = get_colors(page)
        nav_bar.bgcolor = ft.Colors.TRANSPARENT
        nav_bar.indicator_color = current_navigation_colors["navigation_indicator"]

        if route in (routes.GOOGLE_DRIVE, routes.GOOGLE_DRIVE_HISTORY):
            return 4, _build_google_drive_view()
        elif route.startswith(routes.NOTES):
            return 3, _build_notes_view()
        elif route.startswith(routes.SETTINGS):
            return 4, _build_settings_view()
        elif route.startswith(routes.PDF_EXPORT):
            return 2, _build_pdf_export_view()
        elif route.startswith(routes.SAVED):
            return 1, _build_saved_view()
        else:
            return 0, _build_main_view()

    def _build_nested(route: str) -> list[ft.View]:
        if route == routes.CALCULATOR:
            return [_build_calc_view()]
        elif route == routes.MONTHLY:
            return [_build_monthly_view()]
        elif route == routes.MONTHLY_BREAKDOWN:
            return [_build_monthly_view(), _build_monthly_breakdown_view()]
        elif route == routes.NOTES_NEW:
            return [_build_new_note_view()]
        elif route == routes.NOTES_DETAIL:
            return [_build_note_detail_view()]
        elif route == routes.PDF_PREVIEW:
            return [_build_pdf_preview_view()]
        elif route == routes.GOOGLE_DRIVE_HISTORY:
            return [_build_google_drive_history_view()]
        elif route in (routes.SETTINGS_CONFLICTS, routes.SETTINGS_CONFLICT_DETAIL):
            from diezapp.features.conflicts.presentation.conflicts_page import (
                build_conflict_detail_view_route,
                build_conflicts_grid_view,
            )

            kind = page.session.store.get("conflicts_kind") or "calculations"
            views = [
                build_conflicts_grid_view(
                    page,
                    get_colors,
                    kind,
                    routes.SETTINGS,
                    dependencies.conflicts,
                    dependencies.calculations,
                    dependencies.notes,
                )
            ]
            if route == routes.SETTINGS_CONFLICT_DETAIL:
                idx = page.session.store.get("conflict_index")
                views.append(
                    build_conflict_detail_view_route(
                        page,
                        get_colors,
                        kind,
                        idx,
                        dependencies.conflicts,
                    )
                )
            return views
        return []

    callback_handler = OAuthCallbackHandler(
        page,
        dependencies.google_drive_oauth,
        lambda message: page.session.store.set("gdrive_link_message", message),
    )

    router = AppRouter(
        page,
        nav_bar,
        _build_root,
        _build_nested,
        callback_handler.handle,
        nav_state,
        _guard_navigation,
    )

    def route_change(event=None):
        leave_guard["check"] = None
        router.handle_route_change(event)

    page.on_route_change = route_change
    page.on_view_pop = router.handle_view_pop

    route_change()

    async def start_google_drive_scheduler():
        await run_google_drive_scheduler(
            dependencies.google_drive_scheduler,
            dependencies.google_drive_backup,
            dependencies.google_drive_refresh_token,
        )

    page.run_task(start_google_drive_scheduler)
