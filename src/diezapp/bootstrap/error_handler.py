import contextlib
import traceback

import flet as ft


def show_fatal_error(page: ft.Page, exc: BaseException) -> None:
    """Render a startup failure on-screen instead of leaving the splash open."""
    with contextlib.suppress(Exception):
        page.controls.clear()
        page.add(
            ft.Container(
                padding=20,
                content=ft.Column(
                    scroll=ft.ScrollMode.AUTO,
                    controls=[
                        ft.Text(
                            "Error al iniciar la app",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.RED,
                        ),
                        ft.Text(str(exc), selectable=True, size=13),
                        ft.Text(traceback.format_exc(), selectable=True, size=11),
                    ],
                ),
            )
        )
        page.update()
