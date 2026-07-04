"""Reusable "on-scroll" hairline divider for headers.

Material 3's default top app bar tints itself (surface-tint overlay) when
content scrolls underneath it. This app disables that tint
(`elevation_on_scroll=0` on every `ft.AppBar`) and instead uses a neutral
1dp divider that fades in only once the body has scrolled away from the top.
This mirrors the pattern used by native Android apps (Gmail, Settings) to
give a depth cue without any hue/tone shift between light and dark themes.
"""

import flet as ft


def build_scroll_divider() -> ft.Container:
    """A 1dp divider, initially invisible, meant to sit right above a
    scrollable body (just under the page's AppBar)."""
    return ft.Container(
        height=1,
        bgcolor=ft.Colors.TRANSPARENT,
    )


def make_scroll_divider_handler(divider: ft.Container, colors: dict):
    """Returns an `on_scroll` handler that reveals `divider` once the
    attached scrollable control has scrolled past its top edge."""

    def _handler(e: ft.OnScrollEvent):
        # Only reveal the divider after the body has moved a little. This
        # avoids the short flash that could look like a dark line in light mode.
        target = colors["divider"] if e.pixels > 1 else ft.Colors.TRANSPARENT
        if divider.bgcolor != target:
            divider.bgcolor = target
            divider.update()

    return _handler
