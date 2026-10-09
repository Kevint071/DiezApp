"""The "Desglose" block: proportional bar plus the Envío / Restante tree.

Shared by the calculator results and the saved-calculation detail so a stored
calculation reads exactly like the one that was saved.
"""

import flet as ft

from diezapp.features.calculations.presentation.calculation_components import (
    format_currency,
)
from diezapp.features.calculator.domain.models import Distribution

TREE_ROW_HEIGHT = 48


def build_breakdown_bar(**kwargs) -> ft.Container:
    return ft.Container(
        height=10,
        border_radius=999,
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        **kwargs,
    )


def build_distribution_breakdown(
    c: dict,
    distribution: Distribution,
    fund_percentage: int,
    bar: ft.Container | None = None,
    bar_bracket: ft.Container | None = None,
) -> list[ft.Control]:
    """Paint ``bar``/``bar_bracket`` and return the block's controls in order.

    Callers that animate the bar pass their own containers; otherwise static
    ones are created.
    """
    bar = bar if bar is not None else build_breakdown_bar()
    bar_bracket = bar_bracket if bar_bracket is not None else ft.Container()
    pct = fund_percentage
    amount = distribution.amount or 1

    def _segment(value: float, color: str) -> ft.Container:
        # `expand` takes ints, so shares are spread over 1000 parts.
        return ft.Container(
            expand=max(1, round(value / amount * 1000)),
            bgcolor=color,
        )

    bar.bgcolor = c["outline"]
    bar.content = ft.Row(
        spacing=3,
        controls=[
            _segment(distribution.envio_21, c["chart_envio"]),
            _segment(distribution.fondo_local, c["chart_fondo"]),
            _segment(distribution.sostenimiento, c["primary"]),
        ],
    )

    restante_share = max(1, round(distribution.restante / amount * 1000))
    envio_share = max(1, round(distribution.envio_21 / amount * 1000))
    # A bracket under the fondo + sostenimiento segments labels them as
    # "Restante", so the bar shows the same two-level split as the list.
    bar_bracket.content = ft.Row(
        spacing=3,
        controls=[
            ft.Container(expand=envio_share),
            ft.Column(
                expand=restante_share,
                spacing=4,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        height=6,
                        border=ft.Border.only(
                            left=ft.BorderSide(1.5, c["outline"]),
                            right=ft.BorderSide(1.5, c["outline"]),
                            bottom=ft.BorderSide(1.5, c["outline"]),
                        ),
                        border_radius=ft.BorderRadius.only(
                            bottom_left=4, bottom_right=4
                        ),
                    ),
                    ft.Text(
                        "Restante 79%",
                        size=11,
                        weight=ft.FontWeight.W_500,
                        color=c["on_surface_variant"],
                    ),
                ],
            ),
        ],
    )

    def _pill(text: str, color: str) -> ft.Container:
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=1, horizontal=7),
            border_radius=999,
            bgcolor=ft.Colors.with_opacity(0.14, color),
            content=ft.Text(text, size=11, weight=ft.FontWeight.W_600, color=color),
        )

    def _dot(color: str) -> ft.Container:
        return ft.Container(width=10, height=10, border_radius=999, bgcolor=color)

    def _row(leading, label, pill, value, caption=None, value_size=15):
        title = ft.Row(
            spacing=8,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    label,
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=c["on_surface"],
                ),
                pill,
            ],
        )
        return ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(width=16, alignment=ft.Alignment.CENTER, content=leading),
                ft.Column(
                    expand=True,
                    spacing=2,
                    tight=True,
                    controls=[title]
                    + (
                        [ft.Text(caption, size=12, color=c["on_surface_variant"])]
                        if caption
                        else []
                    ),
                ),
                ft.Text(
                    format_currency(value),
                    size=value_size,
                    weight=ft.FontWeight.W_700,
                    color=c["on_surface"],
                ),
            ],
        )

    def _connector(last: bool) -> ft.Stack:
        """├ / └ elbow joining a child row to the "Restante" trunk."""
        mid = TREE_ROW_HEIGHT / 2
        return ft.Stack(
            width=22,
            height=TREE_ROW_HEIGHT,
            controls=[
                ft.Container(
                    left=7.25,
                    top=0,
                    width=1.5,
                    height=mid if last else TREE_ROW_HEIGHT,
                    bgcolor=c["outline"],
                ),
                ft.Container(
                    left=8,
                    top=mid - 0.75,
                    width=14,
                    height=1.5,
                    bgcolor=c["outline"],
                ),
            ],
        )

    def _child(label, pct_value, value, color, last=False):
        return ft.Container(
            height=TREE_ROW_HEIGHT,
            content=ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    _connector(last),
                    ft.Container(
                        expand=True,
                        content=_row(
                            _dot(color), label, _pill(f"{pct_value}%", color), value
                        ),
                    ),
                ],
            ),
        )

    restante_group = ft.Column(
        spacing=0,
        controls=[
            _row(
                # Hollow ring: a subtotal, not a segment, and not tappable.
                ft.Container(
                    width=12,
                    height=12,
                    border_radius=999,
                    border=ft.Border.all(2, c["on_surface_variant"]),
                ),
                "Restante",
                _pill("79%", c["on_surface_variant"]),
                distribution.restante,
                caption="Se reparte en",
            ),
            ft.Container(height=6),
            _child("Fondo local", pct, distribution.fondo_local, c["chart_fondo"]),
            _child(
                "Sostenimiento",
                100 - pct,
                distribution.sostenimiento,
                c["primary"],
                last=True,
            ),
        ],
    )

    return [
        bar,
        ft.Container(height=4),
        bar_bracket,
        ft.Container(height=20),
        _row(
            _dot(c["chart_envio"]),
            "Envío",
            _pill("21%", c["chart_envio"]),
            distribution.envio_21,
        ),
        ft.Container(
            height=1,
            bgcolor=c["outline"],
            margin=ft.Margin.symmetric(vertical=16),
        ),
        restante_group,
    ]
