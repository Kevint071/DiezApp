from datetime import UTC, datetime

import flet as ft

from diezapp.features.monthly_summary.domain.monthly_summary_service import (
    MonthlySummaryService,
)
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)
from diezapp.shared.presentation.theme import get_navigation_bar_style

MONTHS = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]

# (field key in calc dict, display label) — drives the summary tiles and the
# indicator switch in the detail (breakdown) view.
INDICATORS = [
    ("amount", "Cantidad neta"),
    ("sostenimiento", "Sostenimiento"),
    ("envio_21", "21%"),
    ("fondo_local", "Fondo local"),
]
INDICATOR_NAV = [
    (
        "amount",
        "Cantidad neta",
        ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        ft.Icons.ACCOUNT_BALANCE_WALLET,
    ),
    (
        "sostenimiento",
        "Sostenimiento",
        ft.Icons.VOLUNTEER_ACTIVISM_OUTLINED,
        ft.Icons.VOLUNTEER_ACTIVISM,
    ),
    ("envio_21", "21%", ft.Icons.PERCENT_OUTLINED, ft.Icons.PERCENT),
    ("fondo_local", "Fondo local", ft.Icons.SAVINGS_OUTLINED, ft.Icons.SAVINGS),
]
INDICATOR_SHORT = {
    "amount": "Monto",
    "sostenimiento": "Sost.",
    "envio_21": "21%",
    "fondo_local": "Fondo local",
}


def _indicator_key_from_session(page: ft.Page) -> str:
    saved_indicator = page.session.store.get("monthly_breakdown_indicator")
    indicator_keys = {key for key, _ in INDICATORS}
    return saved_indicator if saved_indicator in indicator_keys else "envio_21"


def get_breakdown_title(page: ft.Page) -> str:
    indicator_key = _indicator_key_from_session(page)
    return f"Desglose de {dict(INDICATORS)[indicator_key]}"


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _load_monthly_state(page: ft.Page, current_year: int) -> dict:
    saved = page.session.store.get("monthly_summary_state") or {}
    selected_months = saved.get("selected_months", set())
    return {
        "year": saved.get("year", current_year),
        "mode": saved.get("mode", "monthly"),
        "monthly_selected": saved.get("monthly_selected"),
        "selected_months": set(selected_months),
    }


def _build_summary_card(c, totals: dict, on_detail, mode: str) -> ft.Container:
    def _build_rows(indicators):
        return [
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_500,
                        color=c["on_surface_variant"],
                    ),
                    ft.Text(
                        _format_currency(totals[key]),
                        size=14,
                        weight=ft.FontWeight.W_700,
                        color=c["on_surface"],
                        no_wrap=True,
                    ),
                ],
            )
            for key, label in indicators
        ]

    if mode == "general":
        rows = [
            ft.Text(
                "Promedio",
                size=12,
                weight=ft.FontWeight.W_700,
                color=c["primary"],
            ),
            *_build_rows(INDICATORS[:3]),
            ft.Container(height=4),
            ft.Text(
                "Suma total",
                size=12,
                weight=ft.FontWeight.W_700,
                color=c["primary"],
            ),
            *_build_rows(INDICATORS[3:]),
        ]
    else:
        rows = _build_rows(INDICATORS)

    detail_button = ft.OutlinedButton(
        "Detalles",
        on_click=on_detail,
        style=ft.ButtonStyle(
            color=c["primary"],
            side=ft.BorderSide(1, c["primary"]),
            shape=ft.RoundedRectangleBorder(radius=20),
            padding=ft.Padding.symmetric(vertical=8, horizontal=28),
            text_style=ft.TextStyle(size=13, weight=ft.FontWeight.W_600),
        ),
    )

    return ft.Container(
        content=ft.Column(
            spacing=12,
            controls=rows
            + [
                ft.Container(height=4),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[detail_button],
                ),
            ],
        ),
    )


def build_breakdown_view(
    page: ft.Page,
    colors_fn,
    months: list,
    monthly_summary: MonthlySummaryService,
    on_indicator_change=None,
):
    c = colors_fn(page)
    months = sorted(months or [])
    state = {"indicator": _indicator_key_from_session(page)}

    body_container = ft.Container(expand=True)

    def _build_month_section(year: int, month: int, indicator_key: str):
        calcs = monthly_summary.month_calculations(year, month)
        rows = []
        running_total = 0.0

        for calc in calcs:
            value = calc.get(indicator_key, 0.0)
            running_total += value
            try:
                d = datetime.fromisoformat(calc.get("created_at", ""))
                date_str = d.strftime("%d/%m")
            except ValueError, TypeError:
                date_str = "—"

            row_columns = [
                ft.Text(
                    date_str,
                    size=12,
                    color=c["on_surface_variant"],
                    no_wrap=True,
                )
            ]
            if indicator_key == "fondo_local":
                row_columns.append(
                    ft.Text(
                        f"{calc.get('fund_percentage', 0)}%",
                        size=12,
                        color=c["on_surface_variant"],
                        no_wrap=True,
                    )
                )
            row_columns.append(
                ft.Text(
                    _format_currency(value),
                    size=13,
                    weight=ft.FontWeight.W_500,
                    color=c["on_surface"],
                    no_wrap=True,
                )
            )

            rows.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=10, horizontal=16),
                    border=ft.Border(bottom=ft.BorderSide(1, c["divider"])),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(spacing=12, controls=row_columns),
                            ft.Text(
                                _format_currency(running_total),
                                size=13,
                                weight=ft.FontWeight.W_600,
                                color=c["primary"],
                                no_wrap=True,
                            ),
                        ],
                    ),
                )
            )

        header_columns = [
            ft.Text(
                "Fecha",
                size=11,
                weight=ft.FontWeight.W_600,
                color=c["on_surface_variant"],
                no_wrap=True,
            )
        ]
        if indicator_key == "fondo_local":
            header_columns.append(
                ft.Text(
                    "%",
                    size=11,
                    weight=ft.FontWeight.W_600,
                    color=c["on_surface_variant"],
                    no_wrap=True,
                )
            )
        header_columns.append(
            ft.Text(
                "Cantidad"
                if indicator_key == "fondo_local"
                else INDICATOR_SHORT[indicator_key],
                size=11,
                weight=ft.FontWeight.W_600,
                color=c["on_surface_variant"],
                no_wrap=True,
            )
        )

        header = ft.Container(
            padding=ft.Padding.symmetric(vertical=8, horizontal=16),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            *header_columns,
                        ],
                    ),
                    ft.Text(
                        "Acumulado",
                        size=11,
                        weight=ft.FontWeight.W_600,
                        color=c["on_surface_variant"],
                        no_wrap=True,
                    ),
                ],
            ),
        )

        footer = ft.Container(
            border=ft.Border(
                top=ft.BorderSide(1, c["divider"]),
                bottom=ft.BorderSide(1, c["divider"]),
            ),
            padding=ft.Padding.symmetric(vertical=12, horizontal=16),
            margin=ft.Margin.only(top=8, bottom=20),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        "Total",
                        size=12,
                        weight=ft.FontWeight.W_700,
                        color=c["primary"],
                    ),
                    ft.Text(
                        _format_currency(running_total),
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=c["on_surface"],
                    ),
                ],
            ),
        )

        month_content = (
            [header] + rows + [footer]
            if rows
            else [
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=20),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Sin cálculos en este mes",
                        size=14,
                        color=c["on_surface_variant"],
                    ),
                )
            ]
        )

        section = [
            ft.Text(
                f"{MONTHS[month - 1]} {year}",
                size=15,
                weight=ft.FontWeight.W_600,
                color=c["on_surface"],
            ),
            ft.Container(height=8),
        ] + month_content
        return section, running_total

    def _rebuild_body():
        indicator_key = state["indicator"]
        controls = []
        grand_total = 0.0

        if not months:
            controls.append(
                ft.Container(
                    padding=ft.Padding.only(top=40),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        "Sin meses seleccionados",
                        size=14,
                        color=c["on_surface_variant"],
                    ),
                )
            )
        else:
            for year, month in months:
                section_controls, total = _build_month_section(
                    year, month, indicator_key
                )
                controls.extend(section_controls)
                grand_total += total

            if len(months) > 1:
                controls.append(
                    ft.Container(
                        border=ft.Border(
                            top=ft.BorderSide(2, c["primary"]),
                            bottom=ft.BorderSide(1, c["divider"]),
                        ),
                        padding=ft.Padding.symmetric(vertical=14, horizontal=16),
                        margin=ft.Margin.only(top=8, bottom=24),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "Suma total"
                                    if indicator_key == "fondo_local"
                                    else "Promedio",
                                    size=12,
                                    weight=ft.FontWeight.W_700,
                                    color=c["primary"],
                                ),
                                ft.Text(
                                    _format_currency(
                                        grand_total
                                        if indicator_key == "fondo_local"
                                        else grand_total / len(months)
                                    ),
                                    size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=c["on_surface"],
                                ),
                            ],
                        ),
                    )
                )

        body_container.content = ft.Column(spacing=0, controls=controls)

    selected_index = next(
        index
        for index, (key, _, _, _) in enumerate(INDICATOR_NAV)
        if key == state["indicator"]
    )

    def _on_indicator_change(e):
        key = INDICATOR_NAV[e.control.selected_index][0]
        state["indicator"] = key
        page.session.store.set("monthly_breakdown_indicator", key)
        if on_indicator_change:
            on_indicator_change(dict(INDICATORS)[key])
        _rebuild_body()
        page.update()

    indicator_navigation_style = get_navigation_bar_style(c)
    indicator_navigation_style["label_padding"] = ft.Padding.all(0)
    indicator_navigation = ft.NavigationBar(
        selected_index=selected_index,
        on_change=_on_indicator_change,
        bgcolor=ft.Colors.TRANSPARENT,
        **indicator_navigation_style,
        destinations=[
            ft.NavigationBarDestination(
                icon=icon,
                selected_icon=selected_icon,
                label=label,
            )
            for _, label, icon, selected_icon in INDICATOR_NAV
        ],
    )
    indicator_navigation.label_behavior = ft.NavigationBarLabelBehavior.ALWAYS_HIDE

    _rebuild_body()

    divider = build_scroll_divider()
    content = ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=0, right=0, top=8, bottom=0),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    divider,
                    ft.Column(
                        expand=True,
                        spacing=0,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, c),
                        controls=[
                            ft.Container(
                                expand=True,
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=ft.Column(
                                    spacing=0,
                                    controls=[
                                        body_container,
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )
    return content, indicator_navigation


def build_monthly_summary_view(
    page: ft.Page, colors_fn, monthly_summary: MonthlySummaryService
):
    c = colors_fn(page)
    now = datetime.now(UTC).astimezone()
    state = _load_monthly_state(page, now.year)

    def _save_monthly_state():
        page.session.store.set(
            "monthly_summary_state",
            {
                "year": state["year"],
                "mode": state["mode"],
                "monthly_selected": state["monthly_selected"],
                "selected_months": set(state["selected_months"]),
            },
        )

    year_text = ft.Text(
        str(state["year"]),
        size=16,
        weight=ft.FontWeight.W_600,
        color=c["on_surface"],
    )

    hint_text = ft.Text(
        "Selecciona un mes",
        size=13,
        weight=ft.FontWeight.W_400,
        color=c["on_surface_variant"],
        text_align=ft.TextAlign.CENTER,
    )

    summary_container = ft.Container(width=360, visible=False)
    months_grid = ft.GridView(
        runs_count=4,
        spacing=10,
        run_spacing=10,
        child_aspect_ratio=1.8,
        controls=[],
    )

    def _is_selected(idx: int) -> bool:
        month = idx + 1
        if state["mode"] == "monthly":
            return state["monthly_selected"] == (state["year"], month)
        return (state["year"], month) in state["selected_months"]

    def _on_month_tap(idx):
        def handler(e):
            month = idx + 1
            if state["mode"] == "monthly":
                state["monthly_selected"] = (state["year"], month)
            else:
                key = (state["year"], month)
                if key in state["selected_months"]:
                    state["selected_months"].discard(key)
                else:
                    state["selected_months"].add(key)
            _save_monthly_state()
            _refresh_grid()
            _refresh_summary()
            page.update()

        return handler

    def _build_month_chip(idx: int) -> ft.Container:
        selected = _is_selected(idx)
        return ft.Container(
            bgcolor=ft.Colors.with_opacity(0.15, c["primary"])
            if selected
            else c["card_bg"],
            border=ft.Border.all(1.5, c["primary"]) if selected else None,
            border_radius=10,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(vertical=10, horizontal=4),
            on_click=_on_month_tap(idx),
            ink=True,
            content=ft.Text(
                MONTHS[idx][:3],
                size=13,
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
                color=c["primary"] if selected else c["on_surface"],
                text_align=ft.TextAlign.CENTER,
            ),
        )

    def _refresh_grid():
        months_grid.controls = [_build_month_chip(i) for i in range(12)]

    def _on_detail_tap(months_list):
        def handler(e):
            _save_monthly_state()
            page.session.store.set("monthly_breakdown_months", months_list)
            page.navigate("/monthly/breakdown")

        return handler

    def _refresh_summary():
        if state["mode"] == "monthly":
            selected = state["monthly_selected"]
            if not selected:
                summary_container.visible = False
                summary_container.content = None
                hint_text.value = "Selecciona un mes"
            else:
                year, month = selected
                totals = monthly_summary.month_totals(year, month)
                summary_container.visible = True
                summary_container.content = _build_summary_card(
                    c, totals, _on_detail_tap([selected]), "monthly"
                )
                hint_text.value = ""
        else:
            selected_months = sorted(state["selected_months"])
            if not selected_months:
                summary_container.visible = False
                summary_container.content = None
                hint_text.value = "Selecciona uno o más meses"
            else:
                totals = monthly_summary.general_totals(selected_months)
                summary_container.visible = True
                summary_container.content = _build_summary_card(
                    c, totals, _on_detail_tap(selected_months), "general"
                )
                count = len(selected_months)
                hint_text.value = (
                    f"{count} {'mes' if count == 1 else 'meses'} seleccionado"
                    f"{'' if count == 1 else 's'}"
                )

    def _on_mode_change(e):
        state["mode"] = e.control.selected[0]
        _save_monthly_state()
        _refresh_grid()
        _refresh_summary()
        page.update()

    def _prev_year(e):
        state["year"] -= 1
        year_text.value = str(state["year"])
        if state["mode"] == "monthly":
            state["monthly_selected"] = None
        _save_monthly_state()
        _refresh_grid()
        _refresh_summary()
        page.update()

    def _next_year(e):
        state["year"] += 1
        year_text.value = str(state["year"])
        if state["mode"] == "monthly":
            state["monthly_selected"] = None
        _save_monthly_state()
        _refresh_grid()
        _refresh_summary()
        page.update()

    mode_selector = ft.SegmentedButton(
        segments=[
            ft.Segment(value="monthly", label="Balance mensual"),
            ft.Segment(value="general", label="Balance general"),
        ],
        selected=[state["mode"]],
        show_selected_icon=False,
        on_change=_on_mode_change,
    )

    year_selector = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
        controls=[
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
                icon_size=20,
                icon_color=c["on_surface_variant"],
                on_click=_prev_year,
            ),
            year_text,
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
                icon_size=20,
                icon_color=c["on_surface_variant"],
                on_click=_next_year,
            ),
        ],
    )

    _refresh_grid()
    _refresh_summary()

    divider = build_scroll_divider()
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=0, right=0, top=8, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    divider,
                    ft.Column(
                        expand=True,
                        spacing=0,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, c),
                        controls=[
                            ft.Container(
                                expand=True,
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=ft.Column(
                                    expand=True,
                                    spacing=20,
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        mode_selector,
                                        year_selector,
                                        hint_text,
                                        ft.Container(width=360, content=months_grid),
                                        summary_container,
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )
