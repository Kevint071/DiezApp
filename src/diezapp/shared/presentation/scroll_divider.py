import flet as ft


def build_scroll_divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=ft.Colors.TRANSPARENT)


def make_scroll_divider_handler(divider: ft.Container, colors: dict):
    def _handler(e: ft.OnScrollEvent):
        target = colors["header_divider"] if e.pixels > 1 else ft.Colors.TRANSPARENT
        if divider.bgcolor != target:
            divider.bgcolor = target
            divider.update()

    return _handler
