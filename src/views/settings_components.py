import flet as ft


def build_settings_cell(icon, title, subtitle=None, colors=None, on_click=None):
    """Build a consistent settings row shared by settings sections."""
    trailing_controls = [
        ft.Icon(
            ft.Icons.CHEVRON_RIGHT,
            color=colors["on_surface_variant"],
            size=20,
        )
    ]
    if subtitle is not None:
        subtitle_control = (
            subtitle
            if isinstance(subtitle, ft.Text)
            else ft.Text(subtitle, size=14, color=colors["on_surface_variant"])
        )
        trailing_controls.insert(0, subtitle_control)
    return ft.Container(
        on_click=on_click,
        padding=ft.Padding.symmetric(vertical=14, horizontal=18),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=14,
                    controls=[
                        ft.Icon(icon, size=22, color=colors["primary"]),
                        ft.Text(
                            title,
                            size=15,
                            color=colors["on_surface"],
                            weight=ft.FontWeight.W_500,
                        ),
                    ],
                ),
                ft.Row(spacing=4, controls=trailing_controls),
            ],
        ),
    )
