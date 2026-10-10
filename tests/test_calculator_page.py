import asyncio
import dataclasses
from datetime import date

import flet as ft
import pytest
from flet.controls.base_control import BaseControl
from flet.utils.validation import validate

from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)
from diezapp.features.calculator.presentation.calculator_page import CalculatorView
from diezapp.shared.datetime_utils import local_now
from diezapp.shared.presentation.theme import get_colors


class FakePage:
    theme_mode = "light"

    def __init__(self):
        self.overlay = []
        self.dialogs = []

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)


class FakeCreateCalculation:
    def __init__(self):
        self.calls = []

    def execute(self, amount, fund_percentage, calculation_date=None):
        self.calls.append((amount, fund_percentage, calculation_date))


class FakeConflicts:
    def count(self, kind=None):
        return 0


@pytest.fixture(autouse=True)
def _stub_focus(monkeypatch):
    """`calculate` parks focus on the save button; the fake page is not mounted."""

    async def _no_focus(self):
        pass

    monkeypatch.setattr(ft.FilledButton, "focus", _no_focus)


def _run_calculate(view):
    asyncio.run(view.calculate(None))


def _calculated_view():
    create = FakeCreateCalculation()
    view = CalculatorView(
        FakePage(),
        {"fund_percentage": 10},
        get_colors,
        create,
        CalculateDistribution(),
        FakeConflicts(),
    )
    view.build_content()
    view.input_amount.value = "1.000"
    _run_calculate(view)
    return view, create


def test_calculation_shows_today_as_the_default_date():
    view, _ = _calculated_view()

    assert view.calculation_date == local_now().date()
    assert view.date_switcher.content.value.startswith("Hoy, ")


def test_saving_uses_the_picked_past_date():
    view, create = _calculated_view()

    view._set_calculation_date(date(2024, 3, 15))
    view._save_calculation(None)

    assert create.calls == [(1000.0, 10, date(2024, 3, 15))]
    assert view.date_switcher.content.value == "Vie, 15 mar 2024"


def test_reset_brings_the_date_back_to_today():
    view, _ = _calculated_view()
    view._set_calculation_date(date(2024, 3, 15))

    view.reset()

    assert view.calculation_date == local_now().date()


def test_saving_switches_the_button_to_a_disabled_saved_state():
    view, _ = _calculated_view()

    view._save_calculation(None)

    assert view.saved is True
    assert view.save_btn.disabled is True
    assert view.date_card.disabled is True


def test_recalculating_after_saving_allows_saving_again():
    view, _ = _calculated_view()
    view._save_calculation(None)

    view.input_amount.value = "2.000"
    _run_calculate(view)

    assert view.save_btn.disabled is False
    assert view.date_card.disabled is False
    assert view.bar.scale.scale_x == 1


def test_invalid_amount_flags_the_input_card_without_showing_results():
    view = CalculatorView(
        FakePage(),
        {"fund_percentage": 10},
        get_colors,
        FakeCreateCalculation(),
        CalculateDistribution(),
        FakeConflicts(),
    )
    view.input_amount.value = ""

    _run_calculate(view)

    assert view.input_amount.error
    assert view.results_container.visible is False


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


def _assert_tree_is_valid(view):
    # Same check Flet runs on page.update(); catches e.g. a button with no
    # icon/content, which only blows up once the real app renders the view.
    for control in _walk_controls(view.build_content()):
        validate(control)


def test_view_tree_passes_flet_validation_in_every_state():
    view = CalculatorView(
        FakePage(),
        {"fund_percentage": 10},
        get_colors,
        FakeCreateCalculation(),
        CalculateDistribution(),
        FakeConflicts(),
    )
    _assert_tree_is_valid(view)

    view.input_amount.value = "1.000"
    _run_calculate(view)
    _assert_tree_is_valid(view)

    view._save_calculation(None)
    _assert_tree_is_valid(view)


def test_calculate_arrow_is_hidden_until_an_amount_is_typed():
    view = CalculatorView(
        FakePage(),
        {"fund_percentage": 10},
        get_colors,
        FakeCreateCalculation(),
        CalculateDistribution(),
        FakeConflicts(),
    )
    assert view.calc_btn.disabled is True
    assert view.calc_btn.opacity == 0

    view.input_amount.value = "1500"
    view._format_input_number(None)
    assert view.input_amount.value == "1.500"
    assert view.calc_btn.disabled is False
    assert view.calc_btn.opacity == 1

    view.input_amount.value = ""
    view._format_input_number(None)
    assert view.calc_btn.disabled is True


def test_restante_bracket_appears_with_the_results():
    view, _ = _calculated_view()

    assert view.bar_bracket.opacity == 1

    view.reset()
    assert view.bar_bracket.opacity == 0


def _count_controls(value, counts):
    if isinstance(value, (list, tuple)):
        for item in value:
            _count_controls(item, counts)
        return
    if not isinstance(value, BaseControl):
        return
    counts[id(value)] = counts.get(id(value), 0) + 1
    if counts[id(value)] > 1:
        return
    for field in dataclasses.fields(value):
        if not field.name.startswith("_"):
            _count_controls(getattr(value, field.name), counts)


def test_no_control_is_mounted_in_two_places():
    # Regression: calc_btn sat both in the amount row and in the page column,
    # leaving an empty slot (and a dead arrow) between the input and results.
    view, _ = _calculated_view()
    counts = {}

    _count_controls(view.build_content(), counts)

    assert max(counts.values()) == 1


def test_date_and_save_live_in_the_bottom_action_bar():
    view, _ = _calculated_view()
    results_ids = {id(c) for c in _walk_controls(view.results_container)}
    bar_ids = {id(c) for c in _walk_controls(view.action_bar)}

    assert view.action_bar.visible is True
    assert view.action_bar.opacity == 1
    assert id(view.date_card) in bar_ids and id(view.save_btn) in bar_ids
    assert id(view.date_card) not in results_ids

    view.reset()
    assert view.action_bar.visible is False


def test_ink_containers_with_animation_do_not_carry_their_own_padding():
    # Flet applies `padding` twice on an ink + animate container (outer
    # AnimatedContainer and inner InkWell child) but once when it is disabled,
    # so the date card shrank on save and dragged the "Guardar" button along.
    view, _ = _calculated_view()

    offenders = [
        control
        for control in _walk_controls(view.build_content())
        if isinstance(control, ft.Container)
        and control.ink
        and control.animate is not None
        and control.padding is not None
    ]

    assert offenders == []
