"""Shared look for every modal in the app.

Dialogs used to set their own background, padding and button kind, so the same
question looked different depending on where it was asked from. Everything here
funnels through `build_dialog` so a modal only has to say what it asks, not how
it looks.
"""

import flet as ft

DIALOG_RADIUS = 20
BUTTON_RADIUS = 12
TITLE_SIZE = 17
BODY_SIZE = 14

CONTENT_PADDING = ft.Padding.only(left=24, right=24, top=16, bottom=8)
# Dialogs whose body is a list of tappable options sit tighter, because each
# option already carries its own padding.
OPTION_CONTENT_PADDING = ft.Padding.only(left=20, right=20, top=12, bottom=8)
TITLE_PADDING = ft.Padding.only(left=24, right=24, top=24, bottom=0)
ACTIONS_PADDING = ft.Padding.only(left=16, right=16, top=8, bottom=16)


def dialog_title(text: str, colors: dict) -> ft.Text:
    return ft.Text(
        text,
        size=TITLE_SIZE,
        weight=ft.FontWeight.W_600,
        color=colors["on_surface"],
    )


def dialog_body_text(text: str, colors: dict) -> ft.Text:
    return ft.Text(text, size=BODY_SIZE, color=colors["on_surface_variant"])


def dialog_cancel_button(text: str, on_click, colors: dict) -> ft.TextButton:
    """The way out of a dialog stays neutral so the primary action leads."""
    return ft.TextButton(
        text,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=colors["on_surface_variant"],
            shape=ft.RoundedRectangleBorder(radius=BUTTON_RADIUS),
            padding=ft.Padding.symmetric(vertical=12, horizontal=16),
            text_style=ft.TextStyle(size=BODY_SIZE, weight=ft.FontWeight.W_500),
        ),
    )


def dialog_secondary_button(text: str, on_click, colors: dict) -> ft.OutlinedButton:
    """A third choice that is a real action, not just a way out."""
    return ft.OutlinedButton(
        text,
        on_click=on_click,
        style=ft.ButtonStyle(
            color=colors["on_surface"],
            side=ft.BorderSide(1, colors["outline"]),
            shape=ft.RoundedRectangleBorder(radius=BUTTON_RADIUS),
            padding=ft.Padding.symmetric(vertical=12, horizontal=16),
            text_style=ft.TextStyle(size=BODY_SIZE, weight=ft.FontWeight.W_500),
        ),
    )


def dialog_primary_button(
    text: str,
    on_click,
    colors: dict,
    *,
    destructive: bool = False,
    disabled: bool = False,
) -> ft.FilledButton:
    """A solid button; red when the action destroys something.

    Only the destructive and disabled colors are pinned. The default green comes
    from the page theme, which already carries a readable `on_primary` for both
    light and dark mode.
    """
    bgcolor = {ft.ControlState.DISABLED: colors["outline"]}
    color = {ft.ControlState.DISABLED: colors["on_surface_variant"]}
    if destructive:
        bgcolor[ft.ControlState.DEFAULT] = colors["error"]
        color[ft.ControlState.DEFAULT] = colors["surface"]
    return ft.FilledButton(
        text,
        on_click=on_click,
        disabled=disabled,
        style=ft.ButtonStyle(
            bgcolor=bgcolor,
            color=color,
            shape=ft.RoundedRectangleBorder(radius=BUTTON_RADIUS),
            padding=ft.Padding.symmetric(vertical=12, horizontal=20),
            text_style=ft.TextStyle(size=BODY_SIZE, weight=ft.FontWeight.W_600),
        ),
    )


def build_dialog(
    colors: dict,
    *,
    title,
    content,
    actions=None,
    modal: bool = False,
    on_dismiss=None,
    content_padding: ft.Padding | None = None,
) -> ft.AlertDialog:
    """Build an AlertDialog wearing the shared surface, padding and shape.

    `title` and `content` accept plain strings for the common case and controls
    when a dialog needs its own layout.
    """
    if isinstance(title, str):
        title = dialog_title(title, colors)
    if isinstance(content, str):
        content = ft.Column(tight=True, controls=[dialog_body_text(content, colors)])
    return ft.AlertDialog(
        modal=modal,
        bgcolor=colors["card_bg"],
        shape=ft.RoundedRectangleBorder(radius=DIALOG_RADIUS),
        title=title,
        title_padding=TITLE_PADDING,
        content_padding=content_padding or CONTENT_PADDING,
        content=content,
        actions=actions,
        actions_padding=ACTIONS_PADDING,
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        on_dismiss=on_dismiss,
    )
