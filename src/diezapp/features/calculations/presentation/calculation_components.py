import flet as ft

from diezapp.shared.datetime_utils import to_local_datetime


def format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def format_date(value: str) -> str:
    try:
        parsed = to_local_datetime(value)
        return parsed.strftime("%d/%m/%Y %I:%M %p")
    except ValueError, TypeError:
        return value


def build_data_row(
    label: str,
    value_control: ft.Control,
    on_surface_color: str,
    divider_color: str,
    is_amount: bool = False,
    amount_control: ft.Control | None = None,
    last: bool = False,
) -> ft.Container:
    right_control = (
        ft.Row(spacing=0, tight=True, controls=[amount_control, value_control])
        if is_amount and amount_control is not None
        else value_control
    )
    return ft.Container(
        padding=ft.Padding.symmetric(vertical=12, horizontal=16),
        border=None
        if last
        else ft.Border.only(bottom=ft.BorderSide(0.5, divider_color)),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    label,
                    size=13,
                    weight=ft.FontWeight.W_400,
                    color=on_surface_color,
                ),
                right_control,
            ],
        ),
    )
