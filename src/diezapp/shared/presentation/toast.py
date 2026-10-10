"""Shared feedback toast for every confirmation, warning and error in the app.

Each screen used to drop a bare `ft.SnackBar` into the overlay: grey, untyped,
and never removed afterwards. `show_toast` replaces them with one floating card
that says what kind of news it carries (icon + accent color, never color
alone), pops in, and counts down its own lifetime with a thin bar along its
bottom edge so the user can tell how long it will stay.
"""

from typing import Literal

import flet as ft

from diezapp.shared.presentation.theme import get_colors

ToastKind = Literal["success", "info", "warning", "error"]

TOAST_RADIUS = 16
BADGE_SIZE = 36
BADGE_RADIUS = 12
MAX_WIDTH = 440
GUTTER = 16

_ICONS = {
    "success": ft.Icons.CHECK_ROUNDED,
    "info": ft.Icons.INFO_OUTLINE_ROUNDED,
    "warning": ft.Icons.PRIORITY_HIGH_ROUNDED,
    "error": ft.Icons.CLOSE_ROUNDED,
}
# Bad news stays longer: it usually asks the user to do something about it.
_DURATIONS_MS = {"success": 3500, "info": 3500, "warning": 5000, "error": 6000}
_DETAIL_EXTRA_MS = 1500


def _accent(colors: dict, kind: ToastKind) -> tuple[str, str]:
    """Return the (icon color, badge tint) pair for ``kind``."""
    if kind == "success":
        return colors["primary"], colors["hero_bg"]
    if kind == "warning":
        return colors["warning"], colors["warning_bg"]
    if kind == "error":
        return colors["error"], colors["error_bg"]
    # There is no neutral tint token; a wash of the teal secondary reads as info.
    return colors["secondary"], ft.Colors.with_opacity(0.14, colors["secondary"])


def show_toast(
    page: ft.Page,
    message: str,
    *,
    kind: ToastKind = "info",
    detail: str | None = None,
    update: bool = True,
) -> ft.SnackBar:
    """Show a floating toast; ``detail`` adds a muted second line (e.g. a path).

    Pass ``update=False`` when a navigation follows right away: the route change
    already sends the overlay to the client, so updating here would render twice.
    """
    colors = get_colors(page)
    accent, tint = _accent(colors, kind)
    duration_ms = _DURATIONS_MS[kind] + (_DETAIL_EXTRA_MS if detail else 0)

    badge = ft.Container(
        width=BADGE_SIZE,
        height=BADGE_SIZE,
        border_radius=BADGE_RADIUS,
        bgcolor=tint,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(_ICONS[kind], size=20, color=accent),
        scale=0.5,
        rotate=ft.Rotate(-0.35),
        animate_scale=ft.Animation(480, ft.AnimationCurve.ELASTIC_OUT),
        animate_rotation=ft.Animation(420, ft.AnimationCurve.EASE_OUT_BACK),
    )
    lines: list[ft.Control] = [
        ft.Text(
            message,
            size=14,
            weight=ft.FontWeight.W_600,
            color=colors["on_surface"],
        )
    ]
    if detail:
        lines.append(
            ft.Text(
                detail,
                size=12,
                color=colors["on_surface_variant"],
                max_lines=2,
                overflow=ft.TextOverflow.ELLIPSIS,
            )
        )
    texts = ft.Column(
        spacing=2,
        tight=True,
        expand=True,
        controls=lines,
        offset=ft.Offset(0.04, 0),
        animate_offset=ft.Animation(360, ft.AnimationCurve.EASE_OUT_CUBIC),
    )
    countdown = ft.Container(
        height=3,
        bgcolor=accent,
        scale=ft.Scale(scale_x=1, scale_y=1, alignment=ft.Alignment.CENTER_LEFT),
        animate_scale=ft.Animation(duration_ms, ft.AnimationCurve.LINEAR),
    )

    def animate_in(e):
        badge.scale = 1
        badge.rotate = ft.Rotate(0)
        texts.offset = ft.Offset(0, 0)
        countdown.scale = ft.Scale(
            scale_x=0, scale_y=1, alignment=ft.Alignment.CENTER_LEFT
        )
        toast.update()

    def forget(e):
        if toast in page.overlay:
            page.overlay.remove(toast)
            page.update()

    toast = ft.SnackBar(
        content=ft.Column(
            spacing=0,
            tight=True,
            controls=[
                ft.Container(
                    padding=ft.Padding.only(left=12, top=12, right=16, bottom=12),
                    content=ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[badge, texts],
                    ),
                ),
                countdown,
            ],
        ),
        behavior=ft.SnackBarBehavior.FLOATING,
        bgcolor=colors["card_bg"],
        elevation=6,
        shape=ft.RoundedRectangleBorder(
            radius=TOAST_RADIUS, side=ft.BorderSide(1, colors["outline"])
        ),
        padding=0,
        duration=duration_ms,
        on_visible=animate_in,
        on_dismiss=forget,
        open=True,
    )
    # On a phone the toast spans the screen; on a wide window it stays a card.
    if page.width and page.width >= MAX_WIDTH + 2 * GUTTER:
        toast.width = MAX_WIDTH
    else:
        toast.margin = ft.Margin.only(left=GUTTER, right=GUTTER, bottom=GUTTER)

    # The newest message wins: close whatever toast is still on screen.
    for previous in page.overlay:
        if isinstance(previous, ft.SnackBar) and previous.open:
            previous.open = False
    page.overlay.append(toast)
    if update:
        page.update()
    return toast
