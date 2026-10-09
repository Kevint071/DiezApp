import dataclasses
from datetime import datetime

import flet as ft
from flet.controls.base_control import BaseControl
from flet.utils.validation import validate

from diezapp.features.calculations.presentation.calculation_detail_page import (
    build_calculation_detail_view,
    parse_amount,
)
from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)
from diezapp.shared.datetime_utils import to_local_iso
from diezapp.shared.presentation.theme import get_colors

LOCAL_TZ = datetime.now().astimezone().tzinfo


def _local_iso(*args):
    return to_local_iso(datetime(*args, tzinfo=LOCAL_TZ))


class FakePage:
    theme_mode = "light"

    def __init__(self):
        self.overlay = []
        self.dialogs = []
        self.tasks = []

    def update(self):
        pass

    def run_task(self, handler, *args, **kwargs):
        self.tasks.append(handler)

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


class FakeUpdate:
    def __init__(self):
        self.calls = []

    def execute(self, calculation_id, new_amount):
        self.calls.append((calculation_id, new_amount))
        distribution = CalculateDistribution().execute(new_amount, 10)
        return {
            **dataclasses.asdict(distribution),
            "updated_at": _local_iso(2026, 10, 9, 8, 10),
        }


class FakeDelete:
    def __init__(self):
        self.calls = []

    def execute(self, calculation_id):
        self.calls.append(calculation_id)
        return True


class FakeConflicts:
    def __init__(self, count=0):
        self._count = count

    def count(self, kind=None):
        return self._count


def _calc():
    distribution = CalculateDistribution().execute(1_000_000, 10)
    return {
        "id": "calc-1",
        "created_at": _local_iso(2026, 10, 8, 10, 32),
        **dataclasses.asdict(distribution),
        "fund_percentage": 10,
        "updated_at": None,
    }


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


class Screen:
    def __init__(self, conflicts=0):
        self.page = FakePage()
        self.calc = _calc()
        self.update = FakeUpdate()
        self.delete = FakeDelete()
        self.deleted = []
        self.actions = []
        self.guard = None
        self.view = build_calculation_detail_view(
            self.page,
            get_colors,
            self.calc,
            CalculateDistribution(),
            self.update,
            self.delete,
            FakeConflicts(conflicts),
            lambda: self.deleted.append(True),
            self._set_actions,
            self._register_guard,
        )

    def _set_actions(self, actions):
        self.actions = actions

    def _register_guard(self, guard):
        self.guard = guard

    def controls(self, kind):
        return [c for c in _walk(self.view) if isinstance(c, kind)]

    def texts(self):
        return [c.value for c in self.controls(ft.Text)]

    @property
    def field(self):
        return self.controls(ft.TextField)[0]

    def button(self, label):
        return next(
            b
            for b in self.controls(ft.FilledButton) + self.controls(ft.OutlinedButton)
            if b.content.value == label
        )

    def _action(self, tooltip):
        return next(
            a
            for a in self.actions
            if isinstance(a, ft.IconButton) and a.tooltip == tooltip
        )

    def tap_edit(self):
        self._action("Editar").on_click(None)

    def tap_delete(self):
        self._action("Eliminar").on_click(None)

    def type_amount(self, value):
        self.field.value = value
        self.field.on_change(None)


def test_detail_shows_everything_about_the_calculation():
    screen = Screen()
    texts = screen.texts()

    assert "$1.000.000" in texts
    assert "Envío" in texts and "$210.000" in texts
    assert "Fondo local" in texts and "Sostenimiento" in texts
    assert "Jue, 8 de octubre de 2026 a las 10:32" in texts
    # Preorder walk: the last column holding the field is the innermost one.
    edit_block = [
        c for c in screen.controls(ft.Column) if screen.field in list(_walk(c.controls))
    ][-1]
    assert edit_block.visible is False, "read-only until Editar is tapped"


def test_edit_recalculates_live_and_saves_the_new_amount():
    screen = Screen()
    screen.tap_edit()
    assert screen.actions == [], "app-bar actions step aside while editing"
    assert screen.button("Guardar").disabled is True, "nothing changed yet"

    screen.type_amount("2000000")

    assert screen.field.value == "2.000.000"
    assert "$420.000" in screen.texts(), "envío follows the typed amount"
    assert screen.button("Guardar").disabled is False

    screen.button("Guardar").on_click(None)

    assert screen.update.calls == [("calc-1", 2_000_000)]
    assert screen.calc["amount"] == 2_000_000
    assert "$2.000.000" in screen.texts()
    assert not any("ditado" in t for t in screen.texts() if t)
    assert screen.actions, "actions come back after saving"


def test_cancel_restores_the_stored_breakdown():
    screen = Screen()
    screen.tap_edit()
    screen.type_amount("5")

    screen.button("Cancelar").on_click(None)

    assert screen.update.calls == []
    assert "$1.000.000" in screen.texts()
    assert "$210.000" in screen.texts()


def test_leaving_with_an_unsaved_amount_asks_first():
    screen = Screen()
    proceeded = []

    screen.guard(lambda: proceeded.append(True), lambda: None)
    assert proceeded == [True], "nothing to lose outside edit mode"

    screen.tap_edit()
    screen.type_amount("3000")
    proceeded.clear()
    screen.guard(lambda: proceeded.append(True), lambda: None)

    assert proceeded == []
    assert len(screen.page.dialogs) == 1


def test_delete_asks_for_confirmation_then_reports_back():
    screen = Screen()
    screen.tap_delete()
    dialog = screen.page.dialogs[-1]
    confirm = dialog.actions[-1]

    confirm.on_click(None)

    assert screen.delete.calls == ["calc-1"]
    assert screen.deleted == [True]


def test_conflicts_block_editing_and_deleting():
    screen = Screen(conflicts=1)

    screen.tap_edit()
    screen.tap_delete()

    assert screen.page.dialogs == []
    assert len(screen.page.overlay) == 2
    assert screen.actions, "still in read mode"


def test_view_tree_passes_flet_validation_in_both_modes():
    screen = Screen()
    for control in [*_walk(screen.view), *_walk(screen.actions)]:
        validate(control)

    screen.tap_edit()
    screen.type_amount("1234")
    for control in _walk(screen.view):
        validate(control)


def test_parse_amount():
    assert parse_amount("1.500.000") == 1_500_000
    assert parse_amount("") is None


def test_header_actions_are_a_yellow_pencil_and_a_red_trash_icon():
    screen = Screen()
    colors = get_colors(screen.page)

    edit, delete = [a for a in screen.actions if isinstance(a, ft.IconButton)]

    assert (edit.icon, edit.icon_color) == (ft.Icons.EDIT_OUTLINED, colors["edit"])
    assert (delete.icon, delete.icon_color) == (
        ft.Icons.DELETE_OUTLINE,
        colors["error"],
    )
    assert not any(isinstance(a, ft.PopupMenuButton) for a in screen.actions)


def test_no_middle_dot_anywhere_on_the_page():
    screen = Screen()
    assert not any("·" in t for t in screen.texts() if t)
    screen.tap_edit()
    screen.type_amount("2000000")
    screen.button("Guardar").on_click(None)
    assert not any("·" in t for t in screen.texts() if t)
