import flet as ft


def outline_input_border(color: str, focused_color: str, radius: float = 12) -> dict:
    """Outlined field border tinted for both the resting and the focused state.

    Flet 1.0 dropped the implicit 2px focus width the old `focused_border_color`
    had, so it is set here explicitly to keep the same focus emphasis.
    """
    return {
        ft.ControlState.DEFAULT: ft.OutlineInputBorder(
            border_radius=radius,
            side=ft.BorderSide(width=1, color=color),
        ),
        ft.ControlState.FOCUSED: ft.OutlineInputBorder(
            border_radius=radius,
            side=ft.BorderSide(width=2, color=focused_color),
        ),
    }
