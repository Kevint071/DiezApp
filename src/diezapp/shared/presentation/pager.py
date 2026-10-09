"""Pinned "‹ Página N de M ›" bar for paged lists.

Sits under the scrolling list rather than trailing it, so moving through a
long history never means scrolling to find the controls.
"""

import math
from collections.abc import Callable

import flet as ft


def page_count(total: int, size: int) -> int:
    return max(1, math.ceil(total / size))


class Pager:
    def __init__(self, colors: dict, on_go: Callable[[int], None]):
        self.colors = colors
        self.page_label = ft.Text(
            "", size=13, weight=ft.FontWeight.W_700, color=colors["on_surface"]
        )
        self.range_label = ft.Text("", size=11, color=colors["on_surface_variant"])
        self.prev_button = self._nav_button(
            ft.Icons.CHEVRON_LEFT_ROUNDED, lambda: on_go(-1), "Página anterior"
        )
        self.next_button = self._nav_button(
            ft.Icons.CHEVRON_RIGHT_ROUNDED, lambda: on_go(1), "Página siguiente"
        )
        self.control = ft.Container(
            visible=False,
            bgcolor=colors["surface"],
            border=ft.Border.only(top=ft.BorderSide(1, colors["outline"])),
            padding=ft.Padding.symmetric(vertical=10, horizontal=16),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    self.prev_button,
                    ft.Column(
                        expand=True,
                        spacing=1,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[self.page_label, self.range_label],
                    ),
                    self.next_button,
                ],
            ),
        )

    @staticmethod
    def _nav_button(icon, on_click, tooltip) -> ft.Container:
        return ft.Container(
            width=46,
            height=46,
            border_radius=23,
            alignment=ft.Alignment.CENTER,
            tooltip=tooltip,
            animate=ft.Animation(140, ft.AnimationCurve.EASE_OUT),
            on_click=lambda e: on_click(),
            content=ft.Icon(icon, size=22),
        )

    def _paint_nav(self, control: ft.Container, enabled: bool):
        # Disabled reads as a flat, low-contrast well rather than a filled
        # button, so the state is carried by shape and not by colour alone.
        control.disabled = not enabled
        control.bgcolor = self.colors["primary"] if enabled else self.colors["divider"]
        control.content.color = (
            self.colors["on_primary"] if enabled else self.colors["on_surface_variant"]
        )

    def paint(self, index: int, pages: int, start: int, shown: int, total: int):
        """``index`` is zero-based; ``start``/``shown`` describe the visible window."""
        self.page_label.value = f"Página {index + 1} de {pages}"
        self.range_label.value = f"{start + 1}–{start + shown} de {total}"
        self._paint_nav(self.prev_button, index > 0)
        self._paint_nav(self.next_button, index < pages - 1)
        self.control.visible = pages > 1
