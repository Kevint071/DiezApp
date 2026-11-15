import flet as ft
import pytest

from diezapp.features.notes.presentation.note_colors import (
    NOTE_COLORS,
    note_bgcolor,
    note_muted,
)
from diezapp.shared.presentation.theme import get_colors


class FakePage:
    def __init__(self, theme_mode):
        self.theme_mode = theme_mode


def _luminance(hex_color: str) -> float:
    hex_color = hex_color.lstrip("#")
    channels = [int(hex_color[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("mode", [ft.ThemeMode.LIGHT, ft.ThemeMode.DARK])
@pytest.mark.parametrize("key", list(NOTE_COLORS))
def test_card_text_stays_readable_on_every_note_colour(mode, key):
    c = get_colors(FakePage(mode))
    light = mode == ft.ThemeMode.LIGHT
    bg = note_bgcolor(key, light, c["card_bg"])
    muted = note_muted(key, light, c["on_surface_variant"])

    assert _contrast(c["on_surface"], bg) >= 7
    assert _contrast(muted, bg) >= 4.5


def test_unknown_or_missing_colour_uses_the_default_card():
    assert note_bgcolor(None, True, "#FFFFFF") == "#FFFFFF"
    assert note_bgcolor("gone", False, "#1E293B") == "#1E293B"
    assert note_muted(None, True, "#64748B") == "#64748B"
