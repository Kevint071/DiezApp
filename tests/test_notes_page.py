import flet as ft

from diezapp.features.notes.presentation.notes_page import build_notes_view

COLORS = {
    key: "#000000"
    for key in (
        "on_surface_variant",
        "on_surface",
        "primary",
        "card_bg",
        "input_focused",
        "error",
        "outline",
        "surface",
        "button",
        "on_button",
    )
}


class FakePage:
    theme_mode = ft.ThemeMode.LIGHT

    def __init__(self):
        self.dialogs = []

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        self.dialogs.pop()


class FakeNotes:
    def __init__(self, notes):
        self._notes = notes
        self.deleted = []
        self.painted = []

    def list(self):
        return [dict(n) for n in self._notes]

    def delete_many(self, ids):
        self.deleted.append(list(ids))
        self._notes = [n for n in self._notes if n["id"] not in ids]

    def set_color(self, ids, color):
        self.painted.append((list(ids), color))
        for n in self._notes:
            if n["id"] in ids:
                n["color"] = color

    def move(self, note_id, index):
        pass


class FakeConflicts:
    def __init__(self, count=0):
        self._count = count

    def count(self, kind=None):
        return self._count


def _build(notes, *, conflicts=0, page=None, snacks=None):
    service = FakeNotes(notes)
    view = build_notes_view(
        page or FakePage(),
        lambda page: COLORS,
        lambda: None,
        lambda note_id: None,
        lambda: None,
        service,
        FakeConflicts(conflicts),
        set_header_actions=None,
        show_snack=(lambda message, **kw: snacks.append(message))
        if snacks is not None
        else None,
    )
    return view, service


def _column(view):
    """The search bar and the list, under the floating "+" button."""
    return view.content.controls[0].content


def _bar(view):
    return _column(view).controls[0]


def _bar_controls(view):
    return _bar(view).content.content.controls


def _list(view):
    return _column(view).controls[1].content


def _card(item):
    return item.content.controls[-1]


def _note(note_id, **extra):
    return {"id": note_id, "content": f"nota {note_id}", "created_at": "2026-01-01"}


def test_new_note_is_a_round_plus_button_in_the_bottom_right_corner():
    added = []
    actions = []
    view = build_notes_view(
        FakePage(),
        lambda page: COLORS,
        lambda: added.append(True),
        lambda note_id: None,
        lambda: None,
        FakeNotes([]),
        FakeConflicts(),
        set_header_actions=actions.append,
    )
    corner = view.content.controls[-1]
    fab = corner.content

    assert isinstance(fab, ft.FloatingActionButton)
    assert isinstance(fab.shape, ft.CircleBorder)
    assert fab.icon.icon == ft.Icons.ADD_ROUNDED
    assert (corner.right, corner.bottom) == (20, 20)
    assert actions == [[]]
    fab.on_click(None)
    assert added == [True]


def test_empty_notes_hides_the_whole_search_bar_container_not_the_field_inside_it():
    """The search field sits in a Stack alongside a positioned clear button.

    Hiding the TextField itself (rather than the Container wrapping the
    whole Stack) leaves the Stack with no non-positioned child to size
    itself against, which collapses the layout and blanks the entire
    view -- not just the search bar. Regression for that bug.
    """
    view, _ = _build([])
    search_bar_container = _bar(view)
    search_field = search_bar_container.content.controls[0]

    assert search_bar_container.visible is False
    assert search_field.visible is not False


def test_notes_present_shows_the_search_bar():
    view, _ = _build([_note("1")])

    assert _bar(view).visible is not False
    assert isinstance(_bar(view).content, ft.Stack)


def test_notes_keep_the_stored_order_and_wear_their_colour():
    view, _ = _build([_note("b") | {"color": "blue"}, _note("a")])
    items = _list(view).controls

    assert [item.key for item in items] == ["b", "a"]
    assert _card(items[0]).bgcolor == "#DBEAFE"
    assert _card(items[1]).bgcolor == COLORS["card_bg"]


def test_long_press_selects_and_shows_checkboxes():
    view, _ = _build([_note("1"), _note("2")])

    _card(_list(view).controls[0]).on_long_press(None)

    items = _list(view).controls
    assert [type(item.content.controls[0]) for item in items] == [
        ft.Checkbox,
        ft.Checkbox,
    ]
    assert items[0].content.controls[0].value is True
    assert items[1].content.controls[0].value is False
    assert "1 seleccionada" in [
        c.value for c in _bar_controls(view) if isinstance(c, ft.Text)
    ]

    # In selection mode a tap toggles instead of opening the note.
    _card(items[1]).on_click(None)
    assert _list(view).controls[1].content.controls[0].value is True

    # Unselecting everything leaves the mode.
    _card(_list(view).controls[0]).on_click(None)
    _card(_list(view).controls[1]).on_click(None)
    assert isinstance(_bar(view).content, ft.Stack)


def test_selected_notes_are_deleted_together_after_confirming():
    page = FakePage()
    view, service = _build([_note("1"), _note("2"), _note("3")], page=page)
    _card(_list(view).controls[0]).on_long_press(None)
    _card(_list(view).controls[2]).on_click(None)

    delete_button = _bar_controls(view)[-1]
    delete_button.on_click(None)
    confirm = page.dialogs[-1].actions[-1]
    confirm.on_click(None)

    assert service.deleted == [["1", "3"]]
    assert [item.key for item in _list(view).controls] == ["2"]
    assert isinstance(_bar(view).content, ft.Stack)


def test_selected_notes_are_painted_together():
    page = FakePage()
    view, service = _build([_note("1"), _note("2")], page=page)
    _card(_list(view).controls[0]).on_long_press(None)
    _card(_list(view).controls[1]).on_click(None)

    palette_button = _bar_controls(view)[-2]
    palette_button.on_click(None)
    swatches = page.dialogs[-1].content.controls
    swatches[1].on_click(None)  # the first colour after "Sin color"

    assert service.painted == [(["1", "2"], "red")]
    assert _card(_list(view).controls[0]).bgcolor == "#FDE2E1"


def test_reordering_shows_drag_handles_and_moves_notes():
    view, _ = _build([_note("1"), _note("2"), _note("3")])
    menu = _card(_list(view).controls[0]).content.controls[-1]
    reorder_item = next(i for i in menu.items if i.content.value == "Reordenar")

    reorder_item.on_click(None)
    list_view = _list(view)
    handles = [_card(item).content.controls[-1] for item in list_view.controls]
    assert all(isinstance(h, ft.ReorderableDragHandle) for h in handles)

    list_view.update = lambda: None
    event = ft.OnReorderEvent(
        name="reorder", control=list_view, data=None, old_index=0, new_index=2
    )
    list_view.on_reorder(event)

    assert [item.key for item in list_view.controls] == ["2", "3", "1"]


def test_changes_wait_while_note_conflicts_are_pending():
    page = FakePage()
    snacks = []
    view, service = _build([_note("1")], conflicts=1, page=page, snacks=snacks)
    menu = _card(_list(view).controls[0]).content.controls[-1]
    delete_item = next(i for i in menu.items if i.content.value == "Eliminar")

    delete_item.on_click(None)

    assert page.dialogs == []
    assert service.deleted == []
    assert snacks == ["Resuelve los conflictos de notas primero"]
