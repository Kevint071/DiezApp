import flet as ft
from datetime import datetime

from utils.theme import (
    ON_SURFACE_LIGHT,
    ON_SURFACE_DARK,
    FOCUS_LIGHT,
    FOCUS_DARK,
    OUTLINE_LIGHT_INPUT,
)
from utils.storage import load_calculations, update_calculation, delete_calculation


def apply_saved_calculations_appbar(page: ft.Page, on_navigate_back, colors_fn):
    light = page.theme_mode == ft.ThemeMode.LIGHT
    fg = ON_SURFACE_LIGHT if light else ON_SURFACE_DARK
    page.appbar = ft.AppBar(
        leading=ft.Container(
            width=40,
            height=40,
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: on_navigate_back(),
            content=ft.Image(
                src="chevron-left.svg",
                width=24,
                height=24,
                color=fg,
            ),
        ),
        title=ft.Text(
            "Cálculos guardados",
            color=fg,
            weight=ft.FontWeight.W_700,
            size=18,
            style=ft.TextStyle(height=1),
        ),
        center_title=False,
        leading_width=40,
        bgcolor=ft.Colors.TRANSPARENT,
        elevation=0,
    )


def build_saved_calculations_view(page: ft.Page, colors_fn, on_refresh):
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT
    calculations = load_calculations()

    if not calculations:
        return ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.only(top=80, left=24, right=24, bottom=24),
                alignment=ft.Alignment.TOP_CENTER,
                content=ft.Column(
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Icon(ft.Icons.CALCULATE_OUTLINED, size=48, color=c["on_surface_variant"]),
                        ft.Container(height=12),
                        ft.Text(
                            "No hay cálculos guardados",
                            size=16,
                            weight=ft.FontWeight.W_500,
                            color=c["on_surface_variant"],
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                ),
            ),
        )

    def _format_currency(value: float) -> str:
        return f"${value:,.0f}".replace(",", ".")

    def _format_date(date_str: str) -> str:
        try:
            d = datetime.fromisoformat(date_str)
            return d.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return date_str

    def _build_card(calc: dict):
        calc_id = calc["id"]
        fund_pct = calc.get("fund_percentage", 1)

        # Edit state
        editing = {"active": False, "original_amount": calc["amount"]}

        # Value displays
        txt_amount = ft.Text(
            _format_currency(calc["amount"]),
            size=14, weight=ft.FontWeight.W_600, color=c["primary"],
        )
        txt_envio = ft.Text(
            _format_currency(calc["envio_21"]),
            size=14, weight=ft.FontWeight.W_600, color=c["primary"],
        )
        txt_restante = ft.Text(
            _format_currency(calc["restante"]),
            size=14, weight=ft.FontWeight.W_600, color=c["primary"],
        )
        txt_fondo = ft.Text(
            _format_currency(calc["fondo_local"]),
            size=14, weight=ft.FontWeight.W_600, color=c["primary"],
        )
        txt_sost = ft.Text(
            _format_currency(calc["sostenimiento"]),
            size=14, weight=ft.FontWeight.W_600, color=c["primary"],
        )

        # Edit field
        focus_color = FOCUS_LIGHT if light else FOCUS_DARK
        input_border = OUTLINE_LIGHT_INPUT if light else c["outline"]
        edit_field = ft.TextField(
            value=str(int(calc["amount"])) if calc["amount"] == int(calc["amount"]) else str(calc["amount"]),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=10,
            content_padding=ft.Padding.symmetric(vertical=10, horizontal=12),
            text_size=14,
            border_color=input_border,
            focused_border_color=focus_color,
            visible=False,
            expand=True,
        )

        # Buttons
        save_edit_btn = ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE_OUTLINED,
            icon_color=c["primary"],
            icon_size=22,
            tooltip="Guardar",
            visible=False,
        )
        cancel_edit_btn = ft.IconButton(
            icon=ft.Icons.CANCEL_OUTLINED,
            icon_color=c["on_surface_variant"],
            icon_size=22,
            tooltip="Cancelar",
            visible=False,
        )
        edit_btn = ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED,
            icon_color=c["on_surface_variant"],
            icon_size=20,
            tooltip="Editar",
        )
        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color=c["on_surface_variant"],
            icon_size=20,
            tooltip="Eliminar",
        )

        # Amount row: shows either text or edit field
        amount_text_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Text("Cantidad neta", size=13, weight=ft.FontWeight.W_500, color=c["on_surface_variant"]),
                txt_amount,
            ],
        )
        amount_edit_row = ft.Row(
            visible=False,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text("Cantidad neta", size=13, weight=ft.FontWeight.W_500, color=c["on_surface_variant"]),
                ft.Container(width=120, content=edit_field),
            ],
        )

        def _recalculate_display(amount: float):
            val_21 = amount * 0.21
            val_79 = amount * 0.79
            val_fondo = val_79 * (fund_pct / 100)
            val_sost = amount - val_21 - val_fondo
            txt_envio.value = _format_currency(val_21)
            txt_restante.value = _format_currency(val_79)
            txt_fondo.value = _format_currency(val_fondo)
            txt_sost.value = _format_currency(val_sost)

        def _on_edit_field_change(e):
            try:
                amount = float(edit_field.value.replace(",", "."))
                _recalculate_display(amount)
            except (ValueError, AttributeError):
                pass
            page.update()

        edit_field.on_change = _on_edit_field_change

        def _enter_edit(e):
            editing["active"] = True
            editing["original_amount"] = calc["amount"]
            edit_field.value = str(int(calc["amount"])) if calc["amount"] == int(calc["amount"]) else str(calc["amount"])
            edit_field.visible = True
            amount_text_row.visible = False
            amount_edit_row.visible = True
            edit_btn.visible = False
            delete_btn.visible = False
            save_edit_btn.visible = True
            cancel_edit_btn.visible = True
            page.update()

        def _cancel_edit(e):
            editing["active"] = False
            edit_field.visible = False
            amount_text_row.visible = True
            amount_edit_row.visible = False
            edit_btn.visible = True
            delete_btn.visible = True
            save_edit_btn.visible = False
            cancel_edit_btn.visible = False
            # Restore original values
            txt_amount.value = _format_currency(editing["original_amount"])
            _recalculate_display(editing["original_amount"])
            page.update()

        def _save_edit(e):
            try:
                new_amount = float(edit_field.value.replace(",", "."))
            except (ValueError, AttributeError):
                return
            update_calculation(calc_id, new_amount)
            # Update local display
            calc["amount"] = new_amount
            txt_amount.value = _format_currency(new_amount)
            _recalculate_display(new_amount)
            # Exit edit mode
            editing["active"] = False
            edit_field.visible = False
            amount_text_row.visible = True
            amount_edit_row.visible = False
            edit_btn.visible = True
            delete_btn.visible = True
            save_edit_btn.visible = False
            cancel_edit_btn.visible = False
            page.update()

        def _confirm_delete(e):
            def _do_delete(e):
                delete_calculation(calc_id)
                page.pop_dialog()
                on_refresh()

            def _cancel_delete(e):
                page.pop_dialog()

            dlg = ft.AlertDialog(
                modal=True,
                title=ft.Text("Eliminar cálculo", size=17, weight=ft.FontWeight.W_600),
                content=ft.Text("¿Estás seguro de que deseas eliminar este cálculo?"),
                actions=[
                    ft.TextButton("Cancelar", on_click=_cancel_delete),
                    ft.FilledTonalButton("Eliminar", on_click=_do_delete),
                ],
                actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
            page.show_dialog(dlg)

        edit_btn.on_click = _enter_edit
        cancel_edit_btn.on_click = _cancel_edit
        save_edit_btn.on_click = _save_edit
        delete_btn.on_click = _confirm_delete

        def _value_row(label: str, value_ctrl: ft.Text):
            return ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(label, size=13, weight=ft.FontWeight.W_500, color=c["on_surface_variant"]),
                    value_ctrl,
                ],
            )

        return ft.Container(
            bgcolor=c["card_bg"],
            border_radius=14,
            padding=ft.Padding.symmetric(vertical=14, horizontal=16),
            margin=ft.Margin.only(bottom=12),
            content=ft.Column(
                spacing=8,
                controls=[
                    # Header: date + action buttons
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                _format_date(calc.get("created_at", "")),
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=c["on_surface"],
                            ),
                            ft.Row(
                                spacing=0,
                                controls=[save_edit_btn, cancel_edit_btn, edit_btn, delete_btn],
                            ),
                        ],
                    ),
                    ft.Divider(height=1, color=c["divider"]),
                    # Amount (text or edit)
                    amount_text_row,
                    amount_edit_row,
                    # Other values
                    _value_row("Envío (21%)", txt_envio),
                    _value_row("Restante", txt_restante),
                    _value_row(f"Fondo local ({fund_pct}%)", txt_fondo),
                    _value_row("Sostenimiento", txt_sost),
                ],
            ),
        )

    cards = [_build_card(calc) for calc in calculations]

    return ft.SafeArea(
        content=ft.Container(
            padding=ft.Padding.only(top=8, left=24, right=24, bottom=24),
            content=ft.Column(
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                controls=cards,
            ),
        ),
    )
