import dataclasses
from datetime import date, timedelta

from flet.controls.base_control import BaseControl
from flet.utils.validation import validate

from diezapp.features.calculator.presentation.calculator_page import date_row_label
from diezapp.features.calculator.presentation.date_sheet import (
    WEEKS_SHOWN,
    DateSheet,
    month_weeks,
)
from diezapp.shared.datetime_utils import local_now
from diezapp.shared.presentation.theme import get_colors


class FakePage:
    theme_mode = "light"

    def __init__(self):
        self.shown = []
        self.popped = 0

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.shown.append(dialog)

    def pop_dialog(self):
        self.popped += 1


def _sheet(selected, picks=None):
    page = FakePage()
    on_select = picks.append if picks is not None else (lambda value: None)
    sheet = DateSheet(page, get_colors, selected, on_select)
    return page, sheet


def _walk_controls(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_controls(item, seen)
        return
    if not isinstance(value, BaseControl):
        return
    seen.add(id(value))
    yield value
    for field in dataclasses.fields(value):
        if not field.name.startswith("_"):
            yield from _walk_controls(getattr(value, field.name), seen)


def _day_badges(sheet):
    """(day number, badge container) for every rendered day of the month."""
    weeks = sheet.body.content.controls[1:]
    return [
        (int(cell.content.content.value), cell.content)
        for week in weeks
        for cell in week.controls
        if cell.content is not None
    ]


def test_date_row_label_names_today_yesterday_and_older_dates():
    today = date(2026, 10, 8)

    assert date_row_label(today, today) == "Hoy, 8 oct 2026"
    assert date_row_label(date(2026, 10, 7), today) == "Ayer, 7 oct 2026"
    assert date_row_label(date(2024, 3, 15), today) == "Vie, 15 mar 2024"


def test_month_weeks_is_monday_first_and_always_six_rows():
    weeks = month_weeks(date(2026, 2, 1))  # Feb 2026 starts on a Sunday

    assert len(weeks) == WEEKS_SHOWN
    assert weeks[0][:6] == [None] * 6
    assert weeks[0][6] == date(2026, 2, 1)


def test_tapping_a_day_selects_it_and_closes_the_sheet():
    picks = []
    page, sheet = _sheet(date(2024, 3, 15), picks)

    badge = dict(_day_badges(sheet))[2]
    badge.on_click(None)

    assert picks == [date(2024, 3, 2)]
    assert page.popped == 1


def test_future_days_cannot_be_picked_and_next_month_is_locked():
    today = local_now().date()
    _, sheet = _sheet(today)

    for day, badge in _day_badges(sheet):
        if day > today.day:
            assert badge.on_click is None
    assert sheet.next_btn.disabled is True


def test_picking_the_current_year_clamps_to_the_current_month():
    today = local_now().date()
    _, sheet = _sheet(date(today.year - 1, 12, 1))

    sheet._toggle_years()
    sheet._pick_year(today.year)

    assert sheet.mode == "months"
    assert sheet.month == date(today.year, min(12, today.month), 1)


def test_picking_a_year_shows_months_before_days():
    picks = []
    page, sheet = _sheet(date(2026, 10, 8), picks)

    sheet._toggle_years()
    sheet._pick_year(2024)
    assert sheet.mode == "months"
    assert sheet.title_text.value == "2024"
    assert page.popped == 0 and picks == []

    sheet._pick_month(3)
    assert sheet.mode == "days"
    assert sheet.month == date(2024, 3, 1)
    assert sheet.title_text.value == "Marzo 2024"


def test_future_months_of_the_current_year_cannot_be_picked():
    today = local_now().date()
    _, sheet = _sheet(today)

    sheet._toggle_years()
    sheet._pick_year(today.year)
    months = sheet.body.content.controls[0].controls

    for number, cell in enumerate(months, start=1):
        assert (cell.content.on_click is None) == (number > today.month)


def test_shortcuts_pick_today_and_yesterday():
    picks = []
    _, sheet = _sheet(date(2024, 3, 15), picks)
    today_chip, yesterday_chip = sheet.shortcuts.controls

    today_chip.on_click(None)
    yesterday_chip.on_click(None)

    today = local_now().date()
    assert picks == [today, today - timedelta(days=1)]


def test_sheet_tree_passes_flet_validation_in_both_modes():
    _, sheet = _sheet(date(2024, 3, 15))
    for control in _walk_controls(sheet.sheet):
        validate(control)

    sheet._toggle_years()
    for control in _walk_controls(sheet.sheet):
        validate(control)

    sheet._pick_year(2024)
    for control in _walk_controls(sheet.sheet):
        validate(control)
