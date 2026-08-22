from diezapp.features.notes.presentation.notes_page import build_notes_view

COLORS = {
    key: "#000000"
    for key in (
        "on_surface_variant",
        "on_surface",
        "primary",
        "card_bg",
        "input_focused",
    )
}


class FakePage:
    theme_mode = "light"

    def update(self):
        pass


class FakeNotes:
    def __init__(self, notes):
        self._notes = notes

    def list(self):
        return self._notes

    def sort_for_display(self, notes):
        return list(notes)


class FakeConflicts:
    def count(self, kind=None):
        return 0


def _build(notes):
    return build_notes_view(
        FakePage(),
        lambda page: COLORS,
        lambda: None,
        lambda note_id: None,
        lambda: None,
        FakeNotes(notes),
        FakeConflicts(),
        set_header_actions=None,
    )


def _search_bar_container(view):
    return view.content.content.controls[0]


def test_empty_notes_hides_the_whole_search_bar_container_not_the_field_inside_it():
    """The search field sits in a Stack alongside a positioned clear button.

    Hiding the TextField itself (rather than the Container wrapping the
    whole Stack) leaves the Stack with no non-positioned child to size
    itself against, which collapses the layout and blanks the entire
    view -- not just the search bar. Regression for that bug.
    """
    view = _build([])
    search_bar_container = _search_bar_container(view)
    search_field = search_bar_container.content.controls[0]

    assert search_bar_container.visible is False
    assert search_field.visible is not False


def test_notes_present_shows_the_search_bar():
    view = _build([{"id": "1", "content": "hola", "created_at": "2026-01-01"}])
    search_bar_container = _search_bar_container(view)

    assert search_bar_container.visible is not False
