import flet as ft
import pytest

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
def test_filled_button_text_meets_wcag_aa(mode):
    # Regression: dark mode put near-white text on mint green (1.75:1).
    c = get_colors(FakePage(mode))

    assert _contrast(c["button"], c["on_button"]) >= 4.5
