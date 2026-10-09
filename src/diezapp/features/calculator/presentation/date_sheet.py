"""Bottom-sheet calendar for picking a calculation's date.

Replaces the stock Material DatePicker dialog: it sits within thumb reach,
follows the app's palette, offers "Hoy"/"Ayer" shortcuts, and lets old dates
be reached quickly through a year grid instead of paging month by month.
"""

import calendar
from datetime import date, timedelta

import flet as ft

from diezapp.shared.datetime_utils import local_now
from diezapp.shared.presentation.date_labels import MONTHS_LONG

FIRST_YEAR = 2000
DAY_NAMES = ("Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do")
CELL_HEIGHT = 38
BADGE = 34
WEEKDAY_ROW_HEIGHT = 24
WEEKS_SHOWN = 6  # always six rows so the sheet never jumps between months
BODY_HEIGHT = WEEKDAY_ROW_HEIGHT + WEEKS_SHOWN * CELL_HEIGHT


def _month_title(month: date) -> str:
    return f"{MONTHS_LONG[month.month - 1].capitalize()} {month.year}"


def month_weeks(month: date) -> list[list[date | None]]:
    """Monday-first weeks of `month`, padded with None to six rows."""
    weeks = [
        [date(month.year, month.month, d) if d else None for d in week]
        for week in calendar.Calendar(firstweekday=0).monthdayscalendar(
            month.year, month.month
        )
    ]
    while len(weeks) < WEEKS_SHOWN:
        weeks.append([None] * 7)
    return weeks


class DateSheet:
    def __init__(self, page: ft.Page, colors_fn, selected: date, on_select):
        self.page = page
        self.colors_fn = colors_fn
        self.on_select = on_select
        self.today = local_now().date()
        self.selected = min(selected, self.today)
        self.month = self.selected.replace(day=1)
        self.mode = "days"

        self.title_text = ft.Text("", size=15, weight=ft.FontWeight.W_600)
        self.title_chevron = ft.Icon(
            ft.Icons.EXPAND_MORE_ROUNDED,
            size=20,
            rotate=ft.Rotate(0),
            animate_rotation=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
        )
        self.prev_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
            tooltip="Mes anterior",
            icon_size=22,
            width=40,
            height=40,
            on_click=lambda e: self._shift_month(-1),
        )
        self.next_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
            tooltip="Mes siguiente",
            icon_size=22,
            width=40,
            height=40,
            on_click=lambda e: self._shift_month(1),
        )
        self.body = ft.AnimatedSwitcher(
            content=ft.Container(),
            duration=200,
            reverse_duration=120,
            transition=ft.AnimatedSwitcherTransition.FADE,
        )
        self.heading = ft.Text(
            "Fecha del cálculo", size=18, weight=ft.FontWeight.W_700, expand=True
        )
        self.shortcuts = ft.Row(spacing=6, tight=True)
        self.title_btn = ft.Container(
            border_radius=10,
            padding=ft.Padding.symmetric(vertical=6, horizontal=10),
            ink=True,
            tooltip="Elegir año",
            on_click=self._toggle_years,
            content=ft.Row(
                tight=True, spacing=4, controls=[self.title_text, self.title_chevron]
            ),
        )
        self.sheet = ft.BottomSheet(
            content=ft.Container(
                padding=ft.Padding.only(left=20, right=20, top=0, bottom=16),
                content=ft.Column(
                    tight=True,
                    spacing=0,
                    controls=[
                        ft.Row(
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[self.heading, self.shortcuts],
                        ),
                        ft.Container(height=8),
                        ft.Row(
                            spacing=0,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                self.title_btn,
                                ft.Container(expand=True),
                                self.prev_btn,
                                self.next_btn,
                            ],
                        ),
                        ft.Container(
                            height=BODY_HEIGHT,
                            clip_behavior=ft.ClipBehavior.HARD_EDGE,
                            content=self.body,
                        ),
                    ],
                ),
            ),
            # Without this the sheet is capped at 9/16 of the screen height and
            # clips its content (the last month row was cut at the bottom edge).
            scrollable=True,
            show_drag_handle=True,
            use_safe_area=True,
            shape=ft.RoundedRectangleBorder(
                radius=ft.BorderRadius.only(top_left=28, top_right=28)
            ),
        )
        self._render()

    def show(self):
        self.page.show_dialog(self.sheet)

    # ── Actions ──

    def _pick(self, value: date):
        self.selected = value
        self.page.pop_dialog()
        self.on_select(value)

    def _shift_month(self, step: int):
        year, month = self.month.year, self.month.month + step
        if month == 0:
            year, month = year - 1, 12
        elif month == 13:
            year, month = year + 1, 1
        candidate = date(year, month, 1)
        if date(FIRST_YEAR, 1, 1) <= candidate <= self.today.replace(day=1):
            self.month = candidate
            self._refresh()

    def _toggle_years(self, e=None):
        # days → years → (year picked) months → (month picked) days. Tapping the
        # title from the year grid backs out to days; from months, to years.
        self.mode = {"days": "years", "years": "days", "months": "years"}[self.mode]
        self._refresh()

    def _pick_year(self, year: int):
        month = self.month.month
        if year == self.today.year:
            month = min(month, self.today.month)
        self.month = date(year, month, 1)
        self.mode = "months"
        self._refresh()

    def _pick_month(self, month: int):
        self.month = date(self.month.year, month, 1)
        self.mode = "days"
        self._refresh()

    def _refresh(self):
        self._render()
        self.page.update()

    # ── Rendering ──

    def _render(self):
        c = self.colors_fn(self.page)
        in_days = self.mode == "days"
        at_latest = self.month >= self.today.replace(day=1)
        at_first = self.month <= date(FIRST_YEAR, 1, 1)

        self.sheet.bgcolor = c["card_bg"]
        self.title_text.value = (
            _month_title(self.month) if in_days else str(self.month.year)
        )
        self.title_text.color = c["on_surface"]
        self.title_chevron.color = c["on_surface_variant"]
        self.title_chevron.rotate.angle = 0 if in_days else 3.1416
        for btn, disabled in ((self.prev_btn, at_first), (self.next_btn, at_latest)):
            btn.disabled = disabled or not in_days
            btn.icon_color = c["on_surface"]
            btn.disabled_color = ft.Colors.with_opacity(0.3, c["on_surface_variant"])
        self.prev_btn.opacity = self.next_btn.opacity = 1 if in_days else 0

        self.heading.color = c["on_surface"]
        self.title_btn.ink_color = ft.Colors.with_opacity(0.08, c["primary"])
        self.shortcuts.controls = [
            self._shortcut(c, "Hoy", self.today),
            self._shortcut(c, "Ayer", self.today - timedelta(days=1)),
        ]
        self.body.content = {
            "days": self._build_days,
            "years": self._build_years,
            "months": self._build_months,
        }[self.mode](c)

    def _shortcut(self, c, label: str, value: date) -> ft.Container:
        active = self.selected == value
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=6, horizontal=14),
            border_radius=999,
            bgcolor=c["navigation_indicator"] if active else None,
            border=None if active else ft.Border.all(1, c["outline"]),
            ink=True,
            on_click=lambda e: self._pick(value),
            content=ft.Text(
                label,
                size=13,
                weight=ft.FontWeight.W_600,
                color=c["primary"] if active else c["on_surface_variant"],
            ),
        )

    def _build_days(self, c) -> ft.Column:
        def _cell(day: date | None) -> ft.Container:
            if day is None:
                return ft.Container(expand=1, height=CELL_HEIGHT)
            is_selected = day == self.selected
            is_today = day == self.today
            is_future = day > self.today
            if is_selected:
                bg, fg, border = c["button"], c["on_button"], None
            elif is_today:
                bg, fg = None, c["primary"]
                border = ft.Border.all(1.5, c["primary"])
            else:
                bg, fg, border = None, c["on_surface"], None
            return ft.Container(
                expand=1,
                height=CELL_HEIGHT,
                alignment=ft.Alignment.CENTER,
                content=ft.Container(
                    width=BADGE,
                    height=BADGE,
                    border_radius=999,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=bg,
                    border=border,
                    opacity=0.3 if is_future else 1,
                    ink=not is_future,
                    ink_color=ft.Colors.with_opacity(0.12, c["primary"]),
                    on_click=None if is_future else (lambda e, d=day: self._pick(d)),
                    content=ft.Text(
                        str(day.day),
                        size=14,
                        weight=ft.FontWeight.W_700
                        if is_selected or is_today
                        else ft.FontWeight.W_400,
                        color=fg,
                    ),
                ),
            )

        weekday_row = ft.Row(
            spacing=0,
            height=WEEKDAY_ROW_HEIGHT,
            controls=[
                ft.Container(
                    expand=1,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        name,
                        size=12,
                        weight=ft.FontWeight.W_500,
                        color=c["on_surface_variant"],
                    ),
                )
                for name in DAY_NAMES
            ],
        )
        return ft.Column(
            key=f"days-{self.month.isoformat()}",
            spacing=0,
            controls=[weekday_row]
            + [
                ft.Row(spacing=0, controls=[_cell(d) for d in week])
                for week in month_weeks(self.month)
            ],
        )

    @staticmethod
    def _grid_cell(
        c, label: str, active: bool, col: int, height: int, on_click, faded=False
    ) -> ft.Container:
        """A year/month tile.

        The fill lives on the outer container and the ripple on an inner one:
        a container with both `bgcolor` and `ink` paints its fill on the
        sheet's Material, which ignores the grid's scroll viewport and clip,
        so a selected tile bled down to the bottom edge of the screen.
        """
        return ft.Container(
            col={"xs": col},
            height=height,
            border_radius=12,
            bgcolor=c["button"] if active else None,
            opacity=0.3 if faded else 1,
            content=ft.Container(
                border_radius=12,
                alignment=ft.Alignment.CENTER,
                ink=not faded,
                ink_color=ft.Colors.with_opacity(0.12, c["primary"]),
                on_click=on_click,
                content=ft.Text(
                    label,
                    size=14,
                    weight=ft.FontWeight.W_700 if active else ft.FontWeight.W_500,
                    color=c["on_button"] if active else c["on_surface"],
                ),
            ),
        )

    def _build_months(self, c) -> ft.Column:
        year = self.month.year

        def _month(number: int) -> ft.Container:
            is_future = (year, number) > (self.today.year, self.today.month)
            return self._grid_cell(
                c,
                MONTHS_LONG[number - 1].capitalize(),
                active=(year, number) == (self.selected.year, self.selected.month),
                col=4,
                height=52,
                on_click=None
                if is_future
                else (lambda e, m=number: self._pick_month(m)),
                faded=is_future,
            )

        return ft.Column(
            key=f"months-{year}",
            controls=[
                ft.ResponsiveRow(
                    spacing=8,
                    run_spacing=8,
                    controls=[_month(m) for m in range(1, 13)],
                )
            ],
        )

    def _build_years(self, c) -> ft.Column:
        def _year(year: int) -> ft.Container:
            return self._grid_cell(
                c,
                str(year),
                active=year == self.month.year,
                col=3,
                height=40,
                on_click=lambda e, y=year: self._pick_year(y),
            )

        # Most recent first: old dates are the exception, not the rule.
        return ft.Column(
            key="years",
            scroll=ft.ScrollMode.AUTO,
            controls=[
                ft.ResponsiveRow(
                    spacing=8,
                    run_spacing=8,
                    controls=[
                        _year(y) for y in range(self.today.year, FIRST_YEAR - 1, -1)
                    ],
                )
            ],
        )


def show_date_sheet(page: ft.Page, colors_fn, selected: date, on_select) -> DateSheet:
    sheet = DateSheet(page, colors_fn, selected, on_select)
    sheet.show()
    return sheet
