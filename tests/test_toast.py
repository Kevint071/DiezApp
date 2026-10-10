import flet as ft

from diezapp.shared.presentation.theme import get_colors
from diezapp.shared.presentation.toast import MAX_WIDTH, show_toast


class FakePage:
    theme_mode = ft.ThemeMode.LIGHT

    def __init__(self, width=None):
        self.width = width
        self.overlay = []
        self.updates = 0

    def update(self):
        self.updates += 1


def _texts(control):
    found = []
    if isinstance(control, ft.Text):
        found.append(control.value)
    for child in getattr(control, "controls", None) or []:
        found += _texts(child)
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        found += _texts(content)
    return found


def _badge_icon(toast):
    row = toast.content.controls[0].content
    return row.controls[0].content


def test_toast_carries_message_and_detail_lines():
    page = FakePage()
    toast = show_toast(page, "PDF guardado", kind="success", detail="C:/x.pdf")

    assert toast in page.overlay
    assert toast.open is True
    assert _texts(toast.content) == ["PDF guardado", "C:/x.pdf"]
    assert page.updates == 1


def test_each_kind_has_its_own_icon_and_accent():
    page = FakePage()
    colors = get_colors(page)
    icons = set()
    for kind, accent in (
        ("success", colors["primary"]),
        ("warning", colors["warning"]),
        ("error", colors["error"]),
        ("info", colors["secondary"]),
    ):
        icon = _badge_icon(show_toast(page, "x", kind=kind))
        assert icon.color == accent
        icons.add(icon.icon)
    # Color is never the only signal: every kind has a distinct icon.
    assert len(icons) == 4


def test_bad_news_and_details_stay_longer():
    page = FakePage()
    success = show_toast(page, "x", kind="success")
    error = show_toast(page, "x", kind="error")
    detailed = show_toast(page, "x", kind="success", detail="more")

    assert error.duration > success.duration
    assert detailed.duration > success.duration


def test_new_toast_closes_the_previous_one():
    page = FakePage()
    first = show_toast(page, "uno")
    second = show_toast(page, "dos")

    assert first.open is False
    assert second.open is True


def test_dismissed_toast_leaves_the_overlay():
    page = FakePage()
    toast = show_toast(page, "x")
    toast.on_dismiss(None)

    assert toast not in page.overlay


def test_update_false_defers_rendering_to_the_caller():
    page = FakePage()
    show_toast(page, "x", update=False)

    assert page.updates == 0


def test_toast_is_a_card_on_wide_windows_and_full_width_on_phones():
    assert show_toast(FakePage(width=1200), "x").width == MAX_WIDTH
    phone = show_toast(FakePage(width=390), "x")
    assert phone.width is None
    assert phone.margin is not None
