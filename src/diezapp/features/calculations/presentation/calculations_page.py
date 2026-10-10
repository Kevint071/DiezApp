"""Saved calculations: the paged history list and the PDF date-range picker.

The history shows one compact row per calculation (date + cantidad neta),
grouped by month; the full breakdown, editing and deletion live in the detail
view. Only one page of rows is ever built, which keeps a long history from
landing on Flet all at once.
"""

import calendar
import os
from collections.abc import Callable
from datetime import date

import flet as ft

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.presentation.calculation_components import (
    format_currency,
)
from diezapp.features.pdf_export.application.pdf_export_service import PdfExportService
from diezapp.shared.datetime_utils import local_now, to_local_datetime
from diezapp.shared.presentation.date_labels import (
    MONTHS_LONG,
    MONTHS_SHORT,
    WEEKDAYS_SHORT,
    clock,
)
from diezapp.shared.presentation.pager import Pager, page_count
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)
from diezapp.shared.presentation.share_files import share_local_file
from diezapp.shared.presentation.theme import ON_SURFACE_DARK, ON_SURFACE_LIGHT

PAGE_SIZE = 20


def build_date_range_picker_view(
    page: ft.Page,
    colors_fn,
    calculations_service: CalculationService,
    on_show_filtered=None,
):
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT
    today = local_now().date()

    MONTH_NAMES = [
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
    DAY_NAMES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
    CELL = 40
    BADGE = 34  # selection/today indicator diameter — smaller than CELL for a floating, minimal look

    state = {
        "start": None,
        "end": None,
        "month": today.replace(day=1),
        "picking": False,
        "picker_year": today.year,
    }

    # Calculations per local day, so the calendar can mark days with data and
    # the footer can preview what the range holds before leaving the screen.
    by_day: dict[date, tuple[int, float]] = {}
    for calc in calculations_service.list():
        moment = _created_at(calc)
        if moment is None:
            continue
        count, total = by_day.get(moment.date(), (0, 0.0))
        by_day[moment.date()] = (count + 1, total + (calc.get("amount") or 0))

    def _range_stats(s, e):
        hits = [v for d, v in by_day.items() if s <= d <= e]
        return sum(n for n, _ in hits), sum(t for _, t in hits)

    def _get_range():
        s, e = state["start"], state["end"]
        return (e, s) if s and e and s > e else (s, e)

    def _pos(d):
        s, e = _get_range()
        if d == s and e and s != e:
            return "start"
        if d == s:
            return "solo"
        if e and d == e:
            return "end"
        if s and e and s < d < e:
            return "range"
        if d == today:
            return "today"
        return "normal"

    def _on_tap(d):
        s, e = state["start"], state["end"]
        if s is None or e is not None:
            state["start"], state["end"] = d, None
        elif d == s:
            state["end"] = d
        elif d < s:
            state["start"], state["end"] = d, s
        else:
            state["end"] = d
        _refresh()

    def _cell(d):
        if d is None:
            return ft.Container(width=CELL, height=CELL)
        p = _pos(d)
        _, e = _get_range()
        half = CELL // 2
        layers = []
        # ── Range track (slim pill, vertically centered — no edge-to-edge fill) ──
        if p == "range":
            layers.append(
                ft.Container(
                    width=CELL,
                    height=CELL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=CELL,
                        height=BADGE,
                        bgcolor=ft.Colors.with_opacity(0.10, c["primary"]),
                    ),
                )
            )
        elif p == "start" and e:
            layers.append(
                ft.Container(
                    width=CELL,
                    height=CELL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Row(
                        spacing=0,
                        controls=[
                            ft.Container(width=half, height=BADGE),
                            ft.Container(
                                width=CELL - half,
                                height=BADGE,
                                bgcolor=ft.Colors.with_opacity(0.10, c["primary"]),
                            ),
                        ],
                    ),
                )
            )
        elif p == "end":
            layers.append(
                ft.Container(
                    width=CELL,
                    height=CELL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Row(
                        spacing=0,
                        controls=[
                            ft.Container(
                                width=half,
                                height=BADGE,
                                bgcolor=ft.Colors.with_opacity(0.10, c["primary"]),
                            ),
                            ft.Container(width=CELL - half, height=BADGE),
                        ],
                    ),
                )
            )
        # ── Badge (floating circle, smaller than the cell) ────────────────
        if p in ("start", "end", "solo"):
            layers.append(
                ft.Container(
                    width=CELL,
                    height=CELL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=BADGE,
                        height=BADGE,
                        border_radius=BADGE // 2,
                        bgcolor=c["primary"],
                    ),
                )
            )
        elif p == "today":
            layers.append(
                ft.Container(
                    width=CELL,
                    height=CELL,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=BADGE,
                        height=BADGE,
                        border_radius=BADGE // 2,
                        border=ft.Border.all(1.2, c["primary"]),
                    ),
                )
            )
        # ── Day number ───────────────────────────────────
        if p in ("start", "end", "solo"):
            txt_color = "#FFFFFF" if light else "#064E3B"
            weight = ft.FontWeight.W_600
        elif p in ("range", "today"):
            txt_color = c["primary"]
            weight = ft.FontWeight.W_500
        else:
            txt_color = c["on_surface"]
            weight = ft.FontWeight.W_400
        layers.append(
            ft.Container(
                width=CELL,
                height=CELL,
                alignment=ft.Alignment.CENTER,
                # The font's line box carries extra leading above the digits,
                # so a plain centre lands them ~1.5px low in the badge/track.
                # A full 1.5px lift reads high, so this splits the difference.
                padding=ft.Padding.only(bottom=2),
                content=ft.Text(
                    str(d.day),
                    size=13,
                    color=txt_color,
                    weight=weight,
                    text_align=ft.TextAlign.CENTER,
                ),
            )
        )
        if d in by_day:
            layers.append(
                ft.Container(
                    width=CELL,
                    height=CELL,
                    alignment=ft.Alignment(0, 0.62),
                    content=ft.Container(
                        width=4,
                        height=4,
                        border_radius=2,
                        bgcolor=txt_color
                        if p in ("start", "end", "solo")
                        else c["primary"],
                    ),
                )
            )
        return ft.Container(
            width=CELL,
            height=CELL,
            content=ft.Stack(width=CELL, height=CELL, controls=layers),
            on_click=lambda e, day=d: _on_tap(day),
        )

    def _grid():
        m = state["month"]
        first_wd = m.weekday()
        days_in = calendar.monthrange(m.year, m.month)[1]
        raw = [None] * first_wd + [
            date(m.year, m.month, n) for n in range(1, days_in + 1)
        ]
        while len(raw) % 7:
            raw.append(None)
        header = ft.Row(
            spacing=0,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=CELL,
                    height=28,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        name,
                        size=11,
                        weight=ft.FontWeight.W_500,
                        color=ft.Colors.with_opacity(0.7, c["on_surface_variant"]),
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
                for name in DAY_NAMES
            ],
        )
        rows = [header]
        for i in range(0, len(raw), 7):
            rows.append(
                ft.Row(
                    spacing=0,
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[_cell(d) for d in raw[i : i + 7]],
                )
            )
        return ft.Column(spacing=4, controls=rows)

    def _month_bounds(m):
        return m, m.replace(day=calendar.monthrange(m.year, m.month)[1])

    def _select_month(e):
        # Tapping the month name picks it whole: the common monthly report in
        # one tap, without a row of preset chips competing for space.
        state["start"], state["end"] = _month_bounds(state["month"])
        _refresh()

    def _month_grid():
        # Month/year jump panel. Only moves the calendar: the range in progress
        # is left alone, so a start picked in one year can end in another.
        y = state["picker_year"]
        s, e = _get_range()
        with_data = {(d.year, d.month) for d in by_day}
        on_badge = "#FFFFFF" if light else "#064E3B"

        def _month_cell(n):
            m = date(y, n, 1)
            last = _month_bounds(m)[1]
            current = m == state["month"]
            if s and e:
                in_range = m <= e and last >= s
            else:
                in_range = bool(s) and (s.year, s.month) == (y, n)
            if current:
                bg, fg = c["primary"], on_badge
            elif in_range:
                bg, fg = ft.Colors.with_opacity(0.10, c["primary"]), c["primary"]
            else:
                bg, fg = None, c["on_surface"]
            this_month = (today.year, today.month) == (y, n)
            return ft.Container(
                expand=True,
                height=48,
                border_radius=24,
                bgcolor=bg,
                border=ft.Border.all(1.2, c["primary"])
                if this_month and not current
                else None,
                alignment=ft.Alignment.CENTER,
                on_click=lambda ev, target=m: _jump(target),
                content=ft.Column(
                    spacing=3,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            MONTHS_SHORT[n - 1].capitalize(),
                            size=14,
                            weight=ft.FontWeight.W_600
                            if current or in_range
                            else ft.FontWeight.W_500,
                            color=fg,
                        ),
                        ft.Container(
                            width=4,
                            height=4,
                            border_radius=2,
                            bgcolor=(on_badge if current else c["primary"])
                            if (y, n) in with_data
                            else None,
                        ),
                    ],
                ),
            )

        return ft.Column(
            spacing=8,
            controls=[
                ft.Row(spacing=8, controls=[_month_cell(n) for n in range(i, i + 3)])
                for i in range(1, 13, 3)
            ],
        )

    def _toggle_picker(e):
        state["picking"] = not state["picking"]
        state["picker_year"] = state["month"].year
        _refresh()

    def _jump(m):
        state["month"] = m
        state["picking"] = False
        _refresh()

    def _date_slot(align_end: bool):
        big = ft.Text("—", size=24, weight=ft.FontWeight.W_700, no_wrap=True)
        small = ft.Text(size=12, weight=ft.FontWeight.W_500, no_wrap=True)
        column = ft.Column(
            spacing=2,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.END
            if align_end
            else ft.CrossAxisAlignment.START,
            controls=[big, small],
        )
        return {"big": big, "small": small, "column": column}

    def _dot():
        return ft.Container(width=8, height=8, border_radius=4)

    # ── Static controls ───────────────────────────────────
    m0 = state["month"]
    month_lbl = ft.Text(
        MONTH_NAMES[m0.month - 1],
        size=17,
        weight=ft.FontWeight.W_700,
        color=c["on_surface"],
    )
    year_lbl = ft.Text(
        str(m0.year), size=17, weight=ft.FontWeight.W_700, color=c["on_surface"]
    )
    year_icon = ft.Icon(
        ft.Icons.ARROW_DROP_DOWN_ROUNDED, size=22, color=c["on_surface_variant"]
    )
    slots = {"start": _date_slot(False), "end": _date_slot(True)}
    span_txt = ft.Text(size=12, weight=ft.FontWeight.W_600, no_wrap=True)
    span_line = ft.Container(expand=True, height=1.5)
    span_dots = (_dot(), _dot())
    grid_box = ft.Container(content=_grid())
    count_txt = ft.Text(size=13, color=c["on_surface_variant"])
    total_txt = ft.Text(size=17, weight=ft.FontWeight.W_700, color=c["on_surface"])
    export_btn = ft.FilledButton(
        "Ver cálculos",
        disabled=True,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        width=float("inf"),
    )

    def _paint_range():
        s, e = state["start"], state["end"]
        # The slot the next tap fills gets its caption in the accent colour.
        active = "start" if s is None else "end" if e is None else None
        for key, day, hint in (("start", s, "Inicio"), ("end", e, "Fin")):
            slot = slots[key]
            if day:
                slot["big"].value = f"{day.day} {MONTHS_SHORT[day.month - 1]}"
                weekday = WEEKDAYS_SHORT[day.weekday()].capitalize()
                slot["small"].value = f"{weekday} · {day.year}"
            else:
                slot["big"].value = "—"
                slot["small"].value = hint
            slot["big"].color = c["on_surface"] if day else c["outline"]
            slot["small"].color = (
                c["primary"] if key == active else c["on_surface_variant"]
            )
        # The connector fills in as the range does: hollow → half → solid.
        for dot, filled in zip(span_dots, (s is not None, e is not None)):
            dot.bgcolor = c["primary"] if filled else None
            dot.border = None if filled else ft.Border.all(1.5, c["outline"])
        span_line.bgcolor = c["primary"] if s and e else c["outline"]
        if s and e:
            n = (e - s).days + 1
            span_txt.value = "1 día" if n == 1 else f"{n} días"
            span_txt.color = c["primary"]
        else:
            span_txt.value = "Elige el fin" if s else "Elige el inicio"
            span_txt.color = c["on_surface_variant"]
        month_lbl.color = (
            c["primary"] if (s, e) == _month_bounds(state["month"]) else c["on_surface"]
        )
        if s and e:
            n_calcs, total = _range_stats(s, e)
            if n_calcs:
                count_txt.value = "1 cálculo" if n_calcs == 1 else f"{n_calcs} cálculos"
                total_txt.value = format_currency(total)
                export_btn.content = (
                    "Ver 1 cálculo" if n_calcs == 1 else f"Ver {n_calcs} cálculos"
                )
            else:
                count_txt.value = "Sin cálculos en este rango"
                total_txt.value = ""
                export_btn.content = "Ver cálculos"
        else:
            n_calcs = 0
            count_txt.value = "Toca dos días, o el mes entero"
            total_txt.value = ""
            export_btn.content = "Ver cálculos"
        export_btn.disabled = n_calcs == 0

    def _refresh():
        m = state["month"]
        picking = state["picking"]
        month_lbl.value = MONTH_NAMES[m.month - 1]
        month_btn.visible = not picking
        year_lbl.value = str(state["picker_year"] if picking else m.year)
        year_lbl.color = c["primary"] if picking else c["on_surface"]
        year_icon.icon = (
            ft.Icons.ARROW_DROP_UP_ROUNDED
            if picking
            else ft.Icons.ARROW_DROP_DOWN_ROUNDED
        )
        grid_box.content = _month_grid() if picking else _grid()
        _paint_range()
        page.update()

    def _prev(e):
        if state["picking"]:
            state["picker_year"] -= 1
            _refresh()
            return
        m = state["month"]
        state["month"] = (
            m.replace(month=m.month - 1)
            if m.month > 1
            else m.replace(year=m.year - 1, month=12)
        )
        _refresh()

    def _next(e):
        if state["picking"]:
            state["picker_year"] += 1
            _refresh()
            return
        m = state["month"]
        state["month"] = (
            m.replace(month=m.month + 1)
            if m.month < 12
            else m.replace(year=m.year + 1, month=1)
        )
        _refresh()

    def _export(e):
        s, en = _get_range()
        if s and en and on_show_filtered:
            on_show_filtered(s, en)

    export_btn.on_click = _export
    _paint_range()

    # Boarding-pass style: start and end at the edges, the span between them.
    # The dates keep their natural width and the connector takes what's left,
    # so a narrow screen shortens the line instead of squeezing the text.
    range_pass = ft.Row(
        spacing=14,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            slots["start"]["column"],
            ft.Column(
                expand=True,
                spacing=6,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    span_txt,
                    ft.Row(
                        spacing=0,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[span_dots[0], span_line, span_dots[1]],
                    ),
                    # Mirrors the label's height so the line sits on the
                    # vertical centre of the dates.
                    ft.Container(height=16),
                ],
            ),
            slots["end"]["column"],
        ],
    )

    def _nav_button(icon, handler):
        return ft.IconButton(
            icon=icon,
            icon_size=20,
            icon_color=c["on_surface"],
            on_click=handler,
            width=36,
            height=36,
            style=ft.ButtonStyle(
                padding=ft.Padding.all(0),
                shape=ft.CircleBorder(),
                bgcolor=c["card_bg"],
                side=ft.BorderSide(1, c["outline"]),
            ),
        )

    # Month name and year are separate targets: the name picks that month
    # whole, the year opens the month/year jump panel.
    month_btn = ft.Container(
        border_radius=8,
        padding=ft.Padding.symmetric(horizontal=6, vertical=4),
        ink=True,
        tooltip="Elegir el mes entero",
        on_click=_select_month,
        content=month_lbl,
    )
    year_btn = ft.Container(
        border_radius=8,
        padding=ft.Padding.only(left=4, right=2, top=4, bottom=4),
        ink=True,
        tooltip="Cambiar mes o año",
        on_click=_toggle_picker,
        content=ft.Row(
            spacing=0,
            tight=True,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[year_lbl, year_icon],
        ),
    )

    calendar_section = ft.Column(
        spacing=12,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=0,
                        controls=[month_btn, year_btn],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            _nav_button(ft.Icons.CHEVRON_LEFT_ROUNDED, _prev),
                            _nav_button(ft.Icons.CHEVRON_RIGHT_ROUNDED, _next),
                        ],
                    ),
                ],
            ),
            grid_box,
        ],
    )

    divider = build_scroll_divider()
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=0, right=0, top=4, bottom=0),
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
                                    spacing=16,
                                    controls=[
                                        # ── Date range ──────────────────────────────
                                        range_pass,
                                        calendar_section,
                                        ft.Container(expand=True),
                                        ft.Column(
                                            spacing=12,
                                            controls=[
                                                ft.Container(
                                                    height=1, bgcolor=c["outline"]
                                                ),
                                                ft.Row(
                                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                                    controls=[count_txt, total_txt],
                                                ),
                                                export_btn,
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )


def apply_saved_calculations_appbar(
    page: ft.Page, on_navigate_back, colors_fn, has_calculations: bool
):
    light = page.theme_mode == ft.ThemeMode.LIGHT
    fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK

    page.appbar = ft.AppBar(
        leading=ft.Container(
            width=40,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: on_navigate_back(),
            content=ft.Image(
                src="chevron-left.svg",
                width=24,
                height=24,
                color=fg,
            ),
        ),
        title=ft.Text(
            "Cálculos guardados",
            color=fg,
            weight=ft.FontWeight.W_700,
            size=17,
        ),
        center_title=False,
        leading_width=40,
        title_spacing=0,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
        elevation_on_scroll=0,
    )


def _created_at(calc: Calculation):
    try:
        return to_local_datetime(calc.get("created_at", ""))
    except ValueError, TypeError:
        return None


def filter_by_date_range(
    calculations: list[Calculation], date_range: tuple[date, date] | None
) -> list[Calculation]:
    if not date_range:
        return calculations
    start_date, end_date = date_range
    return [
        calc
        for calc in calculations
        if (moment := _created_at(calc)) is not None
        and start_date <= moment.date() <= end_date
    ]


def month_key(calc: Calculation) -> tuple[int, int] | None:
    moment = _created_at(calc)
    return (moment.year, moment.month) if moment else None


def month_totals(calculations: list[Calculation]) -> dict:
    """``{(year, month): (count, total amount)}`` over the whole list.

    Headers show the whole month even when it spills over two pages, so the
    figures never change depending on where the page break falls.
    """
    totals: dict = {}
    for calc in calculations:
        key = month_key(calc)
        count, total = totals.get(key, (0, 0.0))
        totals[key] = (count + 1, total + (calc.get("amount") or 0))
    return totals


def group_by_month(window: list[Calculation]) -> list[tuple]:
    """Split a newest-first window into consecutive ``(key, calcs)`` runs."""
    groups: list[tuple] = []
    for calc in window:
        key = month_key(calc)
        if groups and groups[-1][0] == key:
            groups[-1][1].append(calc)
        else:
            groups.append((key, [calc]))
    return groups


def group_by_day(calcs: list[Calculation]) -> list[tuple]:
    """Split a newest-first run into consecutive ``(local date, calcs)`` runs."""
    groups: list[tuple] = []
    for calc in calcs:
        moment = _created_at(calc)
        day = moment.date() if moment else None
        if groups and groups[-1][0] == day:
            groups[-1][1].append(calc)
        else:
            groups.append((day, [calc]))
    return groups


def day_caption(day: date | None, today: date) -> str:
    """Small label under the day number, e.g. ``HOY``, ``AYER`` or ``JUE``."""
    if day is None:
        return "—"
    if day == today:
        return "HOY"
    if (today - day).days == 1:
        return "AYER"
    return WEEKDAYS_SHORT[day.weekday()].upper()


def month_title(key: tuple[int, int] | None) -> str:
    if key is None:
        return "Sin fecha"
    year, month = key
    return f"{MONTHS_LONG[month - 1].capitalize()} {year}"


def count_label(count: int) -> str:
    return f"{count} {'cálculo' if count == 1 else 'cálculos'}"


def build_saved_calculations_view(
    page: ft.Page,
    colors_fn,
    calculations_service: CalculationService,
    pdf_export_service: PdfExportService,
    on_open: Callable[[str], None],
    date_range=None,
    initial_page: int = 0,
    on_page_change: Callable[[int], None] | None = None,
):
    """Paged, month-grouped history. Tapping a row calls ``on_open(id)``.

    ``initial_page``/``on_page_change`` let the caller keep the page across a
    round-trip to the detail view, since the route rebuilds this view.
    """
    c = colors_fn(page)
    calculations = filter_by_date_range(calculations_service.list(), date_range)

    if not calculations:
        if date_range:
            title, hint = (
                "No hay cálculos en el rango seleccionado",
                "Prueba con otras fechas en el calendario.",
            )
        else:
            title, hint = (
                "No hay cálculos guardados",
                (
                    "Los cálculos que guardes en la calculadora aparecerán aquí, "
                    "agrupados por mes."
                ),
            )
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(top=72, left=32, right=32, bottom=24),
                alignment=ft.Alignment.TOP_CENTER,
                content=ft.Column(
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=80,
                            height=80,
                            border_radius=40,
                            border=ft.Border.all(1, c["outline"]),
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.EVENT_BUSY_OUTLINED
                                if date_range
                                else ft.Icons.CALCULATE_OUTLINED,
                                size=34,
                                color=c["on_surface_variant"],
                            ),
                        ),
                        ft.Container(height=20),
                        ft.Text(
                            title,
                            size=17,
                            weight=ft.FontWeight.W_600,
                            color=c["on_surface"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=6),
                        ft.Text(
                            hint,
                            size=14,
                            color=c["on_surface_variant"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
        )

    totals = month_totals(calculations)
    state = {"page": initial_page}
    today = local_now().date()
    TILE = 44
    ROW_PAD = 16
    # Text column starts past the tile, so same-day separators can indent to it.
    TEXT_INSET = ROW_PAD + TILE + 14

    # ── Primitives ────────────────────────────────────────
    def separator(new_day: bool):
        # A new day runs edge to edge; rows of the same day indent past the
        # tile, so the eye reads them as one block under a single date.
        # `divider` collapses into `card_bg` in dark mode, hence `outline`.
        return ft.Container(
            padding=ft.Padding.only(
                left=ROW_PAD if new_day else TEXT_INSET, right=ROW_PAD
            ),
            content=ft.Divider(height=1, thickness=1, color=c["outline"]),
        )

    def date_tile(day: date | None):
        # Today gets the tinted tile so "now" is findable at a glance.
        is_today = day == today
        return ft.Container(
            width=TILE,
            height=TILE,
            border_radius=12,
            bgcolor=c["hero_bg"] if is_today else c["surface"],
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                spacing=0,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        str(day.day) if day else "?",
                        size=16,
                        weight=ft.FontWeight.W_700,
                        color=c["hero_fg"] if is_today else c["on_surface"],
                    ),
                    ft.Text(
                        day_caption(day, today),
                        size=9,
                        weight=ft.FontWeight.W_700,
                        color=c["hero_fg"] if is_today else c["on_surface_variant"],
                        style=ft.TextStyle(letter_spacing=0.6),
                    ),
                ],
            ),
        )

    # ── Row: date tile · net amount over time and fund · chevron ──
    def calc_row(calc: Calculation, show_date: bool):
        moment = _created_at(calc)
        day = moment.date() if moment else None
        # Later rows of the same day keep the tile's width so amounts align.
        leading = date_tile(day) if show_date else ft.Container(width=TILE)
        details = [clock(moment) if moment else "--:--"]
        if calc.get("fund_percentage") is not None:
            details.append(f"Fondo {calc['fund_percentage']}%")
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=12, horizontal=ROW_PAD),
            ink=True,
            ink_color=ft.Colors.with_opacity(0.12, c["primary"]),
            on_click=lambda e, calc_id=calc["id"]: on_open(calc_id),
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    leading,
                    ft.Column(
                        expand=True,
                        spacing=2,
                        tight=True,
                        controls=[
                            ft.Text(
                                format_currency(calc.get("amount") or 0),
                                size=17,
                                weight=ft.FontWeight.W_600,
                                color=c["on_surface"],
                                style=ft.TextStyle(letter_spacing=-0.2),
                            ),
                            ft.Text(
                                "  ·  ".join(details),
                                size=12,
                                color=c["on_surface_variant"],
                            ),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT_ROUNDED,
                        size=20,
                        color=c["on_surface_variant"],
                    ),
                ],
            ),
        )

    def month_section(key, calcs: list[Calculation], first: bool):
        count, total = totals.get(key, (len(calcs), 0.0))
        rows: list[ft.Control] = []
        for day_index, (_, items) in enumerate(group_by_day(calcs)):
            for index, calc in enumerate(items):
                if day_index or index:
                    rows.append(separator(new_day=index == 0))
                rows.append(calc_row(calc, show_date=index == 0))
        return ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(
                        left=4, right=4, top=8 if first else 24, bottom=10
                    ),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Column(
                                spacing=2,
                                tight=True,
                                controls=[
                                    ft.Text(
                                        month_title(key),
                                        size=15,
                                        weight=ft.FontWeight.W_700,
                                        color=c["on_surface"],
                                    ),
                                    ft.Text(
                                        count_label(count),
                                        size=12,
                                        color=c["on_surface_variant"],
                                    ),
                                ],
                            ),
                            ft.Column(
                                spacing=2,
                                tight=True,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                controls=[
                                    ft.Text(
                                        "Total",
                                        size=12,
                                        color=c["on_surface_variant"],
                                    ),
                                    ft.Text(
                                        format_currency(total),
                                        size=15,
                                        weight=ft.FontWeight.W_700,
                                        # AA-safe green for text.
                                        color=c["button"],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                # Each month is one card, so where a month ends is never in doubt.
                ft.Container(
                    bgcolor=c["card_bg"],
                    border_radius=16,
                    border=ft.Border.all(1, c["outline"]),
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    padding=ft.Padding.symmetric(vertical=4),
                    content=ft.Column(spacing=0, controls=rows),
                ),
            ],
        )

    # ── Paging ────────────────────────────────────────────
    list_column = ft.Column(spacing=0)
    pager = Pager(c, lambda delta: go_to(state["page"] + delta))

    def total_pages():
        return page_count(len(calculations), PAGE_SIZE)

    def paint_page():
        pages = total_pages()
        state["page"] = max(0, min(state["page"], pages - 1))
        start = state["page"] * PAGE_SIZE
        window = calculations[start : start + PAGE_SIZE]
        list_column.controls = [
            month_section(key, calcs, first=index == 0)
            for index, (key, calcs) in enumerate(group_by_month(window))
        ]
        pager.paint(state["page"], pages, start, len(window), len(calculations))

    def go_to(index: int):
        state["page"] = max(0, min(total_pages() - 1, index))
        paint_page()
        if on_page_change is not None:
            on_page_change(state["page"])
        page.update()
        # A new page starts at its first row, not wherever the old one was left.
        page.run_task(scroll_column.scroll_to, offset=0, duration=260)

    paint_page()

    divider = build_scroll_divider()
    scroll_column = ft.Column(
        expand=True,
        spacing=0,
        scroll=ft.Scrollbar(thickness=6, radius=4),
        on_scroll=make_scroll_divider_handler(divider, c),
        controls=[
            ft.Container(
                margin=ft.Margin.only(left=12, right=12, bottom=24),
                content=list_column,
            )
        ],
    )
    bottom: list[ft.Control] = [pager.control]

    if date_range:
        # Filtered mode: the list previews what goes into the PDF.
        async def _export_filtered(e):
            pdf_path = pdf_export_service.export_calculations(calculations)
            await share_local_file(
                page,
                pdf_path,
                pdf_path.split(os.sep)[-1],
                title="Exportar cálculos",
            )

        bottom.append(
            ft.Container(
                padding=ft.Padding.only(left=20, right=20, top=8, bottom=20),
                content=ft.FilledButton(
                    "Exportar PDF",
                    icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                    on_click=_export_filtered,
                    height=52,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=14),
                        bgcolor=c["button"],
                        color=c["on_button"],
                        elevation=0,
                        text_style=ft.TextStyle(size=15, weight=ft.FontWeight.W_700),
                    ),
                    width=float("inf"),
                ),
            )
        )

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[divider, scroll_column, *bottom],
            ),
        ),
    )
