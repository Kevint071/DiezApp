import flet as ft
from datetime import datetime

from utils.storage import load_calculations


MONTHS = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _get_month_calculations(year: int, month: int) -> list:
    calculations = load_calculations()
    filtered = []
    for calc in calculations:
        try:
            calc_date = datetime.fromisoformat(calc.get("created_at", ""))
            if calc_date.year == year and calc_date.month == month:
                filtered.append(calc)
        except (ValueError, TypeError):
            continue
    # Oldest first for progressive sum
    filtered.reverse()
    return filtered


def _build_breakdown_view(page: ft.Page, colors_fn, month_idx: int, year: int, on_back):
    c = colors_fn(page)
    calcs = _get_month_calculations(year, month_idx + 1)

    rows = []
    running_total = 0.0

    for calc in calcs:
        envio = calc.get("envio_21", 0.0)
        running_total += envio
        try:
            d = datetime.fromisoformat(calc.get("created_at", ""))
            date_str = d.strftime("%d/%m")
        except (ValueError, TypeError):
            date_str = "—"

        rows.append(
            ft.Container(
                padding=ft.Padding.symmetric(vertical=10, horizontal=16),
                border=ft.Border(bottom=ft.BorderSide(1, c["divider"])),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.Text(date_str, size=12, color=c["on_surface_variant"], width=40),
                                ft.Text(_format_currency(envio), size=13, weight=ft.FontWeight.W_500, color=c["on_surface"]),
                            ],
                        ),
                        ft.Text(_format_currency(running_total), size=13, weight=ft.FontWeight.W_600, color=c["primary"]),
                    ],
                ),
            )
        )

    # Header row
    header = ft.Container(
        padding=ft.Padding.symmetric(vertical=8, horizontal=16),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Row(
                    spacing=12,
                    controls=[
                        ft.Text("Fecha", size=11, weight=ft.FontWeight.W_600, color=c["on_surface_variant"], width=40),
                        ft.Text("21%", size=11, weight=ft.FontWeight.W_600, color=c["on_surface_variant"]),
                    ],
                ),
                ft.Text("Acumulado", size=11, weight=ft.FontWeight.W_600, color=c["on_surface_variant"]),
            ],
        ),
    )

    # Total footer
    footer = ft.Container(
        bgcolor=c["hero_bg"],
        border_radius=12,
        padding=ft.Padding.symmetric(vertical=14, horizontal=20),
        margin=ft.Margin.only(top=12),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Total", size=14, weight=ft.FontWeight.W_600, color=c["hero_fg"]),
                ft.Text(_format_currency(running_total), size=16, weight=ft.FontWeight.W_700, color=c["hero_fg"]),
            ],
        ),
    )

    content_controls = [header] + rows + [footer] if rows else [
        ft.Container(
            padding=ft.Padding.only(top=40),
            alignment=ft.Alignment.CENTER,
            content=ft.Text("Sin cálculos en este mes", size=14, color=c["on_surface_variant"]),
        )
    ]

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text(
                        f"{MONTHS[month_idx]} {year}",
                        size=15,
                        weight=ft.FontWeight.W_600,
                        color=c["on_surface"],
                    ),
                    ft.Container(height=16),
                ] + content_controls,
            ),
        ),
    )


def build_monthly_summary_view(page: ft.Page, colors_fn, on_back=None):
    c = colors_fn(page)
    now = datetime.now()
    state = {"year": now.year}

    year_text = ft.Text(
        str(state["year"]),
        size=16,
        weight=ft.FontWeight.W_600,
        color=c["on_surface"],
    )

    result_container = ft.Container(visible=False)

    def _get_monthly_total(month: int) -> float:
        calcs = _get_month_calculations(state["year"], month)
        return sum(calc.get("envio_21", 0.0) for calc in calcs)

    def _on_result_tap(month_idx):
        def handler(e):
            from views.monthly_summary_view import _build_breakdown_view
            light = page.theme_mode == ft.ThemeMode.LIGHT
            from utils.theme import ON_SURFACE_LIGHT, ON_SURFACE_DARK
            fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
            page.appbar = ft.AppBar(
                leading=ft.Container(
                    width=40,
                    height=40,
                    alignment=ft.Alignment.CENTER,
                    on_click=lambda e: _back_to_summary(),
                    content=ft.Image(
                        src="chevron-left.svg",
                        width=24,
                        height=24,
                        color=fg,
                    ),
                ),
                leading_width=40,
                title=ft.Text("Desglose", color=fg, weight=ft.FontWeight.W_600, size=18),
                center_title=False,
                bgcolor=ft.Colors.TRANSPARENT,
                elevation=0,
            )
            page.controls.clear()
            page.add(_build_breakdown_view(page, colors_fn, month_idx, state["year"], _back_to_summary))
            page.update()
        return handler

    def _back_to_summary():
        light = page.theme_mode == ft.ThemeMode.LIGHT
        from utils.theme import ON_SURFACE_LIGHT, ON_SURFACE_DARK
        fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
        page.appbar = ft.AppBar(
            leading=ft.Container(
                width=40,
                height=40,
                alignment=ft.Alignment.CENTER,
                on_click=lambda e: on_back() if on_back else None,
                content=ft.Image(
                    src="chevron-left.svg",
                    width=24,
                    height=24,
                    color=fg,
                ),
            ),
            leading_width=40,
            title=ft.Text("Resumen mensual", color=fg, weight=ft.FontWeight.W_600, size=18),
            center_title=False,
            bgcolor=ft.Colors.TRANSPARENT,
            elevation=0,
        )
        page.controls.clear()
        page.add(build_monthly_summary_view(page, colors_fn, on_back))
        page.update()

    def _on_month_tap(month_idx):
        def handler(e):
            total = _get_monthly_total(month_idx + 1)
            state["selected_month"] = month_idx
            result_container.content = ft.Container(
                bgcolor=c["surface_variant"],
                border_radius=14,
                padding=ft.Padding.symmetric(vertical=20, horizontal=24),
                on_click=_on_result_tap(month_idx),
                ink=True,
                border=ft.Border.all(1, c["outline"]),
                content=ft.Column(
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            MONTHS[month_idx],
                            size=13,
                            weight=ft.FontWeight.W_500,
                            color=c["on_surface_variant"],
                        ),
                        ft.Text(
                            _format_currency(total),
                            size=24,
                            weight=ft.FontWeight.W_700,
                            color=c["primary"],
                        ),
                        ft.Icon(
                            ft.Icons.EXPAND_MORE_ROUNDED,
                            size=18,
                            color=c["on_surface_variant"],
                        ),
                    ],
                ),
            )
            result_container.visible = True
            page.update()
        return handler

    def _prev_year(e):
        state["year"] -= 1
        year_text.value = str(state["year"])
        result_container.visible = False
        page.update()

    def _next_year(e):
        state["year"] += 1
        year_text.value = str(state["year"])
        result_container.visible = False
        page.update()

    def _build_month_chip(idx):
        return ft.Container(
            bgcolor=c["card_bg"],
            border_radius=10,
            alignment=ft.Alignment.CENTER,
            padding=ft.Padding.symmetric(vertical=10, horizontal=4),
            on_click=_on_month_tap(idx),
            ink=True,
            content=ft.Text(
                MONTHS[idx][:3],
                size=13,
                weight=ft.FontWeight.W_500,
                color=c["on_surface"],
                text_align=ft.TextAlign.CENTER,
            ),
        )

    months_grid = ft.Container(
        width=360,
        content=ft.GridView(
            runs_count=4,
            spacing=10,
            run_spacing=10,
            child_aspect_ratio=1.8,
            controls=[_build_month_chip(i) for i in range(12)],
        ),
    )

    year_selector = ft.Row(
        alignment=ft.MainAxisAlignment.CENTER,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
        controls=[
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
                icon_size=20,
                icon_color=c["on_surface_variant"],
                on_click=_prev_year,
            ),
            year_text,
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
                icon_size=20,
                icon_color=c["on_surface_variant"],
                on_click=_next_year,
            ),
        ],
    )

    return ft.SafeArea(
        content=ft.Container(
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                spacing=20,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    year_selector,
                    ft.Text(
                        "Selecciona un mes",
                        size=13,
                        weight=ft.FontWeight.W_400,
                        color=c["on_surface_variant"],
                    ),
                    months_grid,
                    result_container,
                ],
            ),
        ),
    )
