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

    state = {"start": None, "end": None, "editing": None, "month": today.replace(day=1)}

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

    def _edit(key):
        # Only a full range has a bound worth re-picking on its own.
        if state["start"] and state["end"]:
            state["editing"] = key
            _refresh()

    def _on_tap(d):
        s, e = state["start"], state["end"]
        if state["editing"]:
            other = e if state["editing"] == "start" else s
            state["start"], state["end"] = sorted((d, other))
            state["editing"] = None
        elif s is None or e is not None:
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
                content=ft.Text(
                    str(d.day),
                    size=13,
                    color=txt_color,
                    weight=weight,
                    text_align=ft.TextAlign.CENTER,
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

    def _range_field(key: str, label: str, placeholder: str):
        label_txt = ft.Text(label, size=12, weight=ft.FontWeight.W_500)
        value = ft.Text(placeholder, size=16)
        box = ft.Container(
            expand=True,
            border_radius=12,
            # Constant border width (only the colour changes) so selecting a
            # segment never shifts the layout.
            border=ft.Border.all(1.5, ft.Colors.TRANSPARENT),
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            on_click=lambda e: _edit(key),
            content=ft.Column(spacing=2, controls=[label_txt, value]),
        )
        return {"box": box, "label": label_txt, "value": value, "hint": placeholder}

    def _format_day(d: date) -> str:
        return f"{d.day} {MONTHS_SHORT[d.month - 1]} {d.year}"

    # ── Static controls ───────────────────────────────────
    m0 = state["month"]
    month_lbl = ft.Text(
        f"{MONTH_NAMES[m0.month - 1]} {m0.year}",
        size=17,
        weight=ft.FontWeight.W_700,
        color=c["on_surface"],
    )
    fields = {
        "start": _range_field("start", "Desde", "Elige inicio"),
        "end": _range_field("end", "Hasta", "Elige fin"),
    }
    days_txt = ft.Text("", size=12, weight=ft.FontWeight.W_600, color=c["primary"])
    days_pill = ft.Container(
        visible=False,
        bgcolor=c["hero_bg"],
        border_radius=20,
        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        content=days_txt,
    )
    grid_box = ft.Container(content=_grid())
    err_txt = ft.Text(
        "",
        size=12,
        color="#DC2626",
        visible=False,
        text_align=ft.TextAlign.CENTER,
    )
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
        # Which bound the next tap will set; none while a full range is showing
        # (the next tap starts over), so nothing is highlighted then.
        if state["editing"]:
            active = state["editing"]
        elif s is None:
            active = "start"
        elif e is None:
            active = "end"
        else:
            active = None
        for key, day in (("start", s), ("end", e)):
            field, on = fields[key], key == active
            field["box"].bgcolor = c["hero_bg"] if on else None
            field["box"].border = ft.Border.all(
                1.5, c["primary"] if on else ft.Colors.TRANSPARENT
            )
            field["label"].color = c["hero_fg"] if on else c["on_surface_variant"]
            field["value"].value = _format_day(day) if day else field["hint"]
            field["value"].color = c["on_surface"] if day else c["on_surface_variant"]
            field["value"].weight = ft.FontWeight.W_600 if day else ft.FontWeight.W_400
        if s and e:
            n = (e - s).days + 1
            days_txt.value = "1 día" if n == 1 else f"{n} días"
        days_pill.visible = bool(s and e)

    _paint_range()

    def _refresh():
        m = state["month"]
        month_lbl.value = f"{MONTH_NAMES[m.month - 1]} {m.year}"
        grid_box.content = _grid()
        s, e = state["start"], state["end"]
        _paint_range()
        export_btn.disabled = not (s and e)
        err_txt.visible = False
        page.update()

    def _prev(e):
        m = state["month"]
        state["month"] = (
            m.replace(month=m.month - 1)
            if m.month > 1
            else m.replace(year=m.year - 1, month=12)
        )
        _refresh()

    def _next(e):
        m = state["month"]
        state["month"] = (
            m.replace(month=m.month + 1)
            if m.month < 12
            else m.replace(year=m.year + 1, month=1)
        )
        _refresh()

    def _export(e):
        s, en = _get_range()
        if not s or not en:
            return
        calculations = calculations_service.list()
        has_calcs = False
        for calc in calculations:
            try:
                cd = to_local_datetime(calc.get("created_at", "")).date()
                if s <= cd <= en:
                    has_calcs = True
                    break
            except ValueError, TypeError:
                continue
        if not has_calcs:
            err_txt.value = "No hay cálculos en el rango seleccionado"
            err_txt.visible = True
            page.update()
            return
        if on_show_filtered:
            on_show_filtered(s, en)

    export_btn.on_click = _export

    range_card = ft.Column(
        spacing=10,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(
                bgcolor=c["card_bg"],
                border=ft.Border.all(1, c["outline"]),
                border_radius=16,
                padding=6,
                content=ft.Row(
                    spacing=6,
                    controls=[fields["start"]["box"], fields["end"]["box"]],
                ),
            ),
            # Fixed height so the calendar doesn't jump when the count appears.
            ft.Container(height=28, alignment=ft.Alignment.CENTER, content=days_pill),
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
                bgcolor=c["surface"],
            ),
        )

    calendar_card = ft.Container(
        bgcolor=c["card_bg"],
        border=ft.Border.all(1, c["outline"]),
        border_radius=16,
        padding=ft.Padding.only(left=8, right=8, top=12, bottom=12),
        content=ft.Column(
            spacing=12,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=8, right=4),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            month_lbl,
                            ft.Row(
                                spacing=8,
                                controls=[
                                    _nav_button(ft.Icons.CHEVRON_LEFT_ROUNDED, _prev),
                                    _nav_button(ft.Icons.CHEVRON_RIGHT_ROUNDED, _next),
                                ],
                            ),
                        ],
                    ),
                ),
                grid_box,
            ],
        ),
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
                                        range_card,
                                        calendar_card,
                                        err_txt,
                                        ft.Container(expand=True),
                                        export_btn,
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
        empty_msg = (
            "No hay cálculos en el rango seleccionado"
            if date_range
            else "No hay cálculos guardados"
        )
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(top=80, left=24, right=24, bottom=24),
                alignment=ft.Alignment.TOP_CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(
                            ft.Icons.CALCULATE_OUTLINED,
                            size=48,
                            color=c["on_surface_variant"],
                        ),
                        ft.Container(height=12),
                        ft.Text(
                            empty_msg,
                            size=16,
                            weight=ft.FontWeight.W_500,
                            color=c["on_surface_variant"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
        )

    totals = month_totals(calculations)
    state = {"page": initial_page}

    # ── Primitives ────────────────────────────────────────
    def hairline():
        # `divider` collapses into `card_bg` in dark mode, so in-card separators
        # use `outline`, which keeps contrast in both themes.
        return ft.Container(
            padding=ft.Padding.only(left=76, right=16),
            content=ft.Divider(height=1, thickness=1, color=c["outline"]),
        )

    def date_tile(moment):
        return ft.Container(
            width=48,
            height=48,
            border_radius=12,
            bgcolor=c["hero_bg"],
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                spacing=0,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        str(moment.day) if moment else "--",
                        size=17,
                        weight=ft.FontWeight.W_700,
                        color=c["primary"],
                    ),
                    ft.Text(
                        MONTHS_SHORT[moment.month - 1].upper() if moment else "",
                        size=10,
                        weight=ft.FontWeight.W_600,
                        color=c["primary"],
                    ),
                ],
            ),
        )

    # ── Row: only the net amount and when; the rest is one tap away ──
    def calc_row(calc: Calculation):
        moment = _created_at(calc)
        caption = (
            f"{WEEKDAYS_SHORT[moment.weekday()].capitalize()} a las {clock(moment)}"
            if moment
            else "Sin fecha"
        )
        caption_controls = [
            ft.Text(caption, size=12, color=c["on_surface_variant"]),
        ]
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=10, horizontal=14),
            ink=True,
            on_click=lambda e, calc_id=calc["id"]: on_open(calc_id),
            content=ft.Row(
                spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    date_tile(moment),
                    ft.Column(
                        expand=True,
                        spacing=2,
                        controls=[
                            ft.Text(
                                format_currency(calc.get("amount") or 0),
                                size=16,
                                weight=ft.FontWeight.W_700,
                                color=c["on_surface"],
                            ),
                            ft.Row(spacing=4, controls=caption_controls),
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=20,
                        color=c["on_surface_variant"],
                    ),
                ],
            ),
        )

    def month_section(key, calcs: list[Calculation]):
        count, total = totals.get(key, (len(calcs), 0.0))
        rows: list[ft.Control] = []
        for index, calc in enumerate(calcs):
            if index:
                rows.append(hairline())
            rows.append(calc_row(calc))
        return ft.Column(
            spacing=0,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=4, right=4, top=18, bottom=8),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                month_title(key),
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=c["on_surface"],
                            ),
                            ft.Text(
                                f"{count_label(count)}, {format_currency(total)}",
                                size=12,
                                color=c["on_surface_variant"],
                            ),
                        ],
                    ),
                ),
                ft.Container(
                    bgcolor=c["card_bg"],
                    border_radius=16,
                    clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                    padding=ft.Padding.symmetric(vertical=4),
                    content=ft.Column(spacing=0, controls=rows),
                ),
            ],
        )

    # ── Paging ────────────────────────────────────────────
    list_column = ft.Column(spacing=0)
    pager = Pager(c, lambda delta: go(delta))

    def total_pages():
        return page_count(len(calculations), PAGE_SIZE)

    def paint_page():
        pages = total_pages()
        state["page"] = max(0, min(state["page"], pages - 1))
        start = state["page"] * PAGE_SIZE
        window = calculations[start : start + PAGE_SIZE]
        list_column.controls = [
            month_section(key, calcs) for key, calcs in group_by_month(window)
        ]
        pager.paint(state["page"], pages, start, len(window), len(calculations))

    def go(delta):
        state["page"] = max(0, min(total_pages() - 1, state["page"] + delta))
        paint_page()
        if on_page_change is not None:
            on_page_change(state["page"])
        page.update()
        # A new page starts at its first row, not wherever the old one was left.
        page.run_task(scroll_column.scroll_to, offset=0, duration=260)

    paint_page()

    if date_range:
        start_date, end_date = date_range
        summary = (
            f"{count_label(len(calculations))} del "
            f"{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}"
        )
    else:
        summary = f"{count_label(len(calculations))} guardados"

    divider = build_scroll_divider()
    scroll_column = ft.Column(
        expand=True,
        spacing=0,
        scroll=ft.Scrollbar(thickness=6, radius=4),
        on_scroll=make_scroll_divider_handler(divider, c),
        controls=[
            ft.Container(
                margin=ft.Margin.only(left=20, right=20, bottom=20),
                content=ft.Column(
                    spacing=0,
                    controls=[
                        ft.Container(
                            padding=ft.Padding.only(left=4, top=8),
                            content=ft.Text(
                                summary, size=12, color=c["on_surface_variant"]
                            ),
                        ),
                        list_column,
                    ],
                ),
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
                padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
                content=ft.FilledButton(
                    "Exportar PDF",
                    icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
                    on_click=_export_filtered,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        padding=ft.Padding.symmetric(vertical=14, horizontal=20),
                        text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
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
