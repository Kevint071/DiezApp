import dataclasses
from datetime import date, datetime, timedelta

from flet.controls.base_control import BaseControl
from flet.utils.validation import validate

from diezapp.features.calculations.presentation.calculations_page import (
    PAGE_SIZE,
    build_saved_calculations_view,
    filter_by_date_range,
    group_by_month,
    month_totals,
)
from diezapp.shared.datetime_utils import to_local_iso
from diezapp.shared.presentation.theme import get_colors

LOCAL_TZ = datetime.now().astimezone().tzinfo


def _local(*args):
    return datetime(*args, tzinfo=LOCAL_TZ)


class FakePage:
    theme_mode = "light"

    def __init__(self):
        self.tasks = []

    def update(self):
        pass

    def run_task(self, handler, *args, **kwargs):
        self.tasks.append(handler)


class FakeCalculations:
    def __init__(self, calculations):
        self._calculations = calculations

    def list(self):
        return self._calculations


def _calc(index, moment, amount=1000.0, updated_at=None):
    return {
        "id": f"calc-{index}",
        "created_at": to_local_iso(moment),
        "amount": amount,
        "envio_21": amount * 0.21,
        "restante": amount * 0.79,
        "fondo_local": amount * 0.079,
        "sostenimiento": amount * 0.711,
        "fund_percentage": 10,
        "updated_at": updated_at,
    }


def _history(count):
    """``count`` calculations, newest first, two per day going back."""
    start = _local(2026, 10, 8, 18, 0)
    return [_calc(i, start - timedelta(days=i // 2)) for i in range(count)]


def _walk(value, seen=None):
    seen = set() if seen is None else seen
    if id(value) in seen:
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item, seen)
        return
    if not isinstance(value, BaseControl):
        return
    seen.add(id(value))
    yield value
    for field in dataclasses.fields(value):
        if not field.name.startswith("_"):
            yield from _walk(getattr(value, field.name), seen)


def _rows(view):
    """Tappable rows currently built (one per calculation on the page)."""
    return [
        control
        for control in _walk(view)
        if getattr(control, "on_click", None) is not None
        and getattr(control, "ink", False)
    ]


def _texts(view):
    return [c.value for c in _walk(view) if type(c).__name__ == "Text"]


def _build(calculations, **kwargs):
    page = FakePage()
    opened = []
    view = build_saved_calculations_view(
        page,
        get_colors,
        FakeCalculations(calculations),
        pdf_export_service=None,
        on_open=opened.append,
        **kwargs,
    )
    return page, view, opened


def _pager_buttons(view):
    return [
        c
        for c in _walk(view)
        if getattr(c, "tooltip", None) in ("Página anterior", "Página siguiente")
    ]


def test_only_one_page_of_rows_is_built_for_a_long_history():
    _, view, _ = _build(_history(1000))

    assert len(_rows(view)) == PAGE_SIZE
    assert "Página 1 de 50" in _texts(view)
    assert f"1–{PAGE_SIZE} de 1000" in _texts(view)


def test_next_page_shows_the_following_window_and_reports_it():
    changes = []
    page, view, _ = _build(_history(45), on_page_change=changes.append)
    _, next_button = _pager_buttons(view)

    next_button.on_click(None)

    assert changes == [1]
    assert "Página 2 de 3" in _texts(view)
    assert "21–40 de 45" in _texts(view)
    assert page.tasks, "a page change scrolls back to the top"


def test_initial_page_is_restored_and_clamped():
    _, view, _ = _build(_history(45), initial_page=2)
    assert "41–45 de 45" in _texts(view)
    assert len(_rows(view)) == 5

    _, view, _ = _build(_history(45), initial_page=99)
    assert "Página 3 de 3" in _texts(view)


def test_pager_is_hidden_when_everything_fits_on_one_page():
    _, view, _ = _build(_history(3))
    prev_button = _pager_buttons(view)[0]
    hidden = [c for c in _walk(view) if c.visible is False and prev_button in _walk(c)]

    assert hidden, "the pager bar should be hidden"


def test_tapping_a_row_opens_that_calculation():
    calculations = _history(3)
    _, view, opened = _build(calculations)

    _rows(view)[1].on_click(None)

    assert opened == ["calc-1"]


def test_rows_show_only_net_amount_and_when():
    calc = _calc(0, _local(2026, 10, 8, 10, 32), amount=1_500_000, updated_at="x")
    _, view, _ = _build([calc])
    texts = _texts(view)

    assert "$1.500.000" in texts
    assert "Jue · 10:32" in texts
    assert "· editado" in texts
    # The breakdown lives in the detail view, not the list.
    assert not any("Envío" in t for t in texts if t)


def test_month_header_totals_cover_the_whole_month_across_pages():
    october = [_calc(i, _local(2026, 10, 8, 10, 0), amount=100) for i in range(25)]
    september = [_calc(25, _local(2026, 9, 30, 10, 0), amount=50)]
    _, view, _ = _build(october + september, initial_page=1)
    texts = _texts(view)

    assert "Octubre 2026" in texts
    assert "25 cálculos · $2.500" in texts
    assert "Septiembre 2026" in texts
    assert "1 cálculo · $50" in texts


def test_group_by_month_keeps_consecutive_runs():
    calcs = [
        _calc(0, _local(2026, 10, 2)),
        _calc(1, _local(2026, 10, 1)),
        _calc(2, _local(2026, 9, 30)),
    ]
    groups = group_by_month(calcs)

    assert [(key, [c["id"] for c in items]) for key, items in groups] == [
        ((2026, 10), ["calc-0", "calc-1"]),
        ((2026, 9), ["calc-2"]),
    ]
    assert month_totals(calcs)[(2026, 10)] == (2, 2000.0)


def test_filter_by_date_range_is_inclusive_and_skips_bad_dates():
    calcs = [
        _calc(0, _local(2026, 10, 8)),
        _calc(1, _local(2026, 10, 1)),
        _calc(2, _local(2026, 9, 30)),
        {**_calc(3, _local(2026, 10, 2)), "created_at": "not a date"},
    ]
    kept = filter_by_date_range(calcs, (date(2026, 10, 1), date(2026, 10, 8)))

    assert [c["id"] for c in kept] == ["calc-0", "calc-1"]


def test_view_tree_passes_flet_validation():
    for kwargs in ({}, {"date_range": (date(2026, 1, 1), date(2026, 12, 31))}):
        _, view, _ = _build(_history(30), **kwargs)
        for control in _walk(view):
            validate(control)


def test_empty_history_shows_the_empty_state():
    _, view, _ = _build([])

    assert "No hay cálculos guardados" in _texts(view)
