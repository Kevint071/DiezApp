"""Home ("Inicio") screen: entry cards linking to the calculator and the
monthly summary."""

import flet as ft

from utils.scroll_divider import build_scroll_divider, make_scroll_divider_handler


def _build_home_card(page: ft.Page, colors_fn, icon, title, subtitle, on_click):
    c = colors_fn(page)
    return ft.Container(
        bgcolor=c["card_bg"],
        border_radius=16,
        padding=ft.Padding.all(20),
        on_click=on_click,
        ink=True,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=16,
            controls=[
                ft.Container(
                    width=48,
                    height=48,
                    border_radius=12,
                    bgcolor=ft.Colors.with_opacity(0.1, c["primary"]),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=c["primary"], size=24),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(
                            title,
                            size=15,
                            weight=ft.FontWeight.W_600,
                            color=c["on_surface"],
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            subtitle,
                            size=12,
                            weight=ft.FontWeight.W_400,
                            color=c["on_surface_variant"],
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
            ],
        ),
    )


def build_home_view(page: ft.Page, colors_fn, on_open_calculator, on_open_monthly):
    c = colors_fn(page)
    divider = build_scroll_divider()
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=0, right=0, top=4, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    divider,
                    ft.Column(
                        expand=True,
                        spacing=16,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, c),
                        controls=[
                            ft.Container(
                                expand=True,
                                margin=ft.Margin.symmetric(horizontal=24),
                                content=ft.Column(
                                    expand=True,
                                    spacing=16,
                                    controls=[
                                        ft.Text(
                                            "¿Qué deseas calcular?",
                                            size=14,
                                            weight=ft.FontWeight.W_500,
                                            color=c["on_surface_variant"],
                                        ),
                                        _build_home_card(
                                            page,
                                            colors_fn,
                                            ft.Icons.PIE_CHART_OUTLINE_ROUNDED,
                                            "Distribución porcentual",
                                            "Calcula envío, fondo local y sostenimiento",
                                            lambda e: on_open_calculator(),
                                        ),
                                        _build_home_card(
                                            page,
                                            colors_fn,
                                            ft.Icons.CALENDAR_MONTH_ROUNDED,
                                            "Detalle Balances",
                                            "Cantidad neta, sostenimiento y 21% por mes",
                                            lambda e: on_open_monthly(),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ),
    )
