from datetime import UTC, datetime

import flet as ft

from utils.scroll_divider import build_scroll_divider, make_scroll_divider_handler
from utils.storage import load_calculations

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
]
INDICATOR_SHORT = {"amount": "Monto", "sostenimiento": "Sost.", "envio_21": "21%"}


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _get_month_calculations(year: int, month: int) -> list:
    calculations = load_calculations()
    filtered = []
    for calc in calculations:
        try:
            calc_date = datetime.fromisoformat(calc.get("created_at", ""))
            if calc_date.year == year and calc_date.month == month:
                filtered.append(calc)
        except ValueError, TypeError:
            continue
    # Oldest first for progressive sum
    filtered.reverse()
    return filtered


def _month_totals(year: int, month: int) -> dict:
    calcs = _get_month_calculations(year, month)
    return {key: sum(calc.get(key, 0.0) for calc in calcs) for key, _ in INDICATORS}


def _average_totals(months: list) -> dict:
    if not months:
        return {key: 0.0 for key, _ in INDICATORS}
    sums = {key: 0.0 for key, _ in INDICATORS}
    for year, month in months:
        totals = _month_totals(year, month)
        for key in sums:
            sums[key] += totals[key]
    return {key: value / len(months) for key, value in sums.items()}


def _build_summary_card(c, totals: dict, on_detail) -> ft.Container:
    rows = [
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
        for key, label in INDICATORS
    ]

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


def build_breakdown_view(page: ft.Page, colors_fn, months: list):
    c = colors_fn(page)
    months = sorted(months or [])
    state = {"indicator": "envio_21"}

    body_container = ft.Container(expand=True)

    def _build_month_section(year: int, month: int, indicator_key: str):
        calcs = _get_month_calculations(year, month)
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

            rows.append(
                ft.Container(
                    padding=ft.Padding.symmetric(vertical=10, horizontal=16),
                    border=ft.Border(bottom=ft.BorderSide(1, c["divider"])),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row(
                                spacing=12,
                                controls=[
                                    ft.Text(
                                        date_str,
                                        size=12,
                                        color=c["on_surface_variant"],
                                        no_wrap=True,
                                    ),
                                    ft.Text(
                                        _format_currency(value),
                                        size=13,
                                        weight=ft.FontWeight.W_500,
                                        color=c["on_surface"],
                                        no_wrap=True,
                                    ),
                                ],
                            ),
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

        header = ft.Container(
            padding=ft.Padding.symmetric(vertical=8, horizontal=16),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=12,
                        controls=[
                            ft.Text(
                                "Fecha",
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=c["on_surface_variant"],
                                no_wrap=True,
                            ),
                            ft.Text(
                                INDICATOR_SHORT[indicator_key],
                                size=11,
                                weight=ft.FontWeight.W_600,
                                color=c["on_surface_variant"],
                                no_wrap=True,
                            ),
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
            bgcolor=c["hero_bg"],
            border_radius=12,
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            margin=ft.Margin.only(top=12, bottom=20),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(
                        "Total", size=14, weight=ft.FontWeight.W_600, color=c["hero_fg"]
                    ),
                    ft.Text(
                        _format_currency(running_total),
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=c["hero_fg"],
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
                average = grand_total / len(months)
                controls.append(
                    ft.Container(
                        bgcolor=c["primary"],
                        border_radius=12,
                        padding=ft.Padding.symmetric(vertical=14, horizontal=20),
                        margin=ft.Margin.only(top=4),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "Promedio",
                                    size=14,
                                    weight=ft.FontWeight.W_600,
                                    color=c["on_primary"],
                                ),
                                ft.Text(
                                    _format_currency(average),
                                    size=16,
                                    weight=ft.FontWeight.W_700,
                                    color=c["on_primary"],
                                ),
                            ],
                        ),
                    )
                )

        body_container.content = ft.Column(spacing=0, controls=controls)

    def _on_indicator_change(e):
        state["indicator"] = e.control.selected[0]
        _rebuild_body()
        page.update()

    indicator_selector = ft.SegmentedButton(
        segments=[ft.Segment(value=key, label=label) for key, label in INDICATORS],
        selected=[state["indicator"]],
        show_selected_icon=False,
        on_change=_on_indicator_change,
        width=float("inf"),
    )

    _rebuild_body()

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
                                    spacing=0,
                                    controls=[
                                        indicator_selector,
                                        ft.Container(height=16),
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


def build_monthly_summary_view(page: ft.Page, colors_fn):
    c = colors_fn(page)
    now = datetime.now(UTC).astimezone()
    state = {
        "year": now.year,
        "mode": "monthly",
        "monthly_selected": None,
        "selected_months": set(),
    }

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
                totals = _month_totals(year, month)
                summary_container.visible = True
                summary_container.content = _build_summary_card(
                    c, totals, _on_detail_tap([selected])
                )
                hint_text.value = ""
        else:
            selected_months = sorted(state["selected_months"])
            if not selected_months:
                summary_container.visible = False
                summary_container.content = None
                hint_text.value = "Selecciona uno o más meses"
            else:
                totals = _average_totals(selected_months)
                summary_container.visible = True
                summary_container.content = _build_summary_card(
                    c, totals, _on_detail_tap(selected_months)
                )
                count = len(selected_months)
                hint_text.value = (
                    f"{count} {'mes' if count == 1 else 'meses'} seleccionado"
                    f"{'' if count == 1 else 's'}"
                )

    def _on_mode_change(e):
        state["mode"] = e.control.selected[0]
        _refresh_grid()
        _refresh_summary()
        page.update()

    def _prev_year(e):
        state["year"] -= 1
        year_text.value = str(state["year"])
        if state["mode"] == "monthly":
            state["monthly_selected"] = None
        _refresh_grid()
        _refresh_summary()
        page.update()

    def _next_year(e):
        state["year"] += 1
        year_text.value = str(state["year"])
        if state["mode"] == "monthly":
            state["monthly_selected"] = None
        _refresh_grid()
        _refresh_summary()
        page.update()

    mode_selector = ft.SegmentedButton(
        segments=[
            ft.Segment(value="monthly", label="Balance mensual"),
            ft.Segment(value="general", label="Balance general"),
        ],
        selected=["monthly"],
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
