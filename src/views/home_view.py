"""Home ("Inicio") screen: entry cards linking to the calculator and the
monthly summary."""

import flet as ft

from utils.scroll_divider import build_scroll_divider, make_scroll_divider_handler


def _build_home_card(page: ft.Page, colors_fn, icon, title, subtitle, accent, on_click):
    c = colors_fn(page)
    return ft.Container(
        border_radius=14,
        padding=ft.Padding.symmetric(vertical=12, horizontal=14),
        on_click=on_click,
        ink=True,
        ink_color=ft.Colors.with_opacity(0.08, accent),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=14,
            controls=[
                ft.Container(
                    width=44,
                    height=44,
                    border_radius=13,
                    bgcolor=ft.Colors.with_opacity(0.14, accent),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=accent, size=24),
                ),
                ft.Column(
                    expand=True,
                    spacing=3,
                    controls=[
                        ft.Text(
                            title,
                            size=17,
                            weight=ft.FontWeight.W_700,
                            color=c["on_surface"],
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        ft.Text(
                            subtitle,
                            size=12.5,
                            weight=ft.FontWeight.W_400,
                            color=c["on_surface_variant"],
                            max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                ),
                ft.Icon(
                    ft.Icons.CHEVRON_RIGHT_ROUNDED,
                    size=20,
                    color=ft.Colors.with_opacity(0.45, c["on_surface_variant"]),
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
            padding=ft.Padding.only(left=0, right=0, top=4, bottom=0),
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
                                    spacing=12,
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
                                            c["primary"],
                                            lambda e: on_open_calculator(),
                                        ),
                                        _build_home_card(
                                            page,
                                            colors_fn,
                                            ft.Icons.CALENDAR_MONTH_ROUNDED,
                                            "Detalle Balances",
                                            "Cantidad neta, sostenimiento y 21% por mes",
                                            c["secondary"],
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
