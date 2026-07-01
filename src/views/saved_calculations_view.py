import os
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


def _show_date_range_modal(page: ft.Page, colors_fn):
    """Show a modal to select date range and export filtered calculations as PDF."""
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT
    focus_color = FOCUS_LIGHT if light else FOCUS_DARK
    input_border = OUTLINE_LIGHT_INPUT if light else c["outline"]

    state = {"start_date": None, "end_date": None}

    start_field = ft.TextField(
        label="Fecha inicial",
        hint_text="DD/MM/AAAA",
        read_only=True,
        border_radius=10,
        content_padding=ft.Padding.symmetric(vertical=10, horizontal=12),
        text_size=14,
        border_color=input_border,
        focused_border_color=focus_color,
        expand=True,
    )

    end_field = ft.TextField(
        label="Fecha final",
        hint_text="DD/MM/AAAA",
        read_only=True,
        border_radius=10,
        content_padding=ft.Padding.symmetric(vertical=10, horizontal=12),
        text_size=14,
        border_color=input_border,
        focused_border_color=focus_color,
        expand=True,
    )

    error_text = ft.Text("", size=12, color=c.get("error", "#DC2626"), visible=False)

    def _on_start_date_picked(e):
        if e.control.value:
            state["start_date"] = e.control.value
            start_field.value = e.control.value.strftime("%d/%m/%Y")
            error_text.visible = False
            page.update()

    def _on_end_date_picked(e):
        if e.control.value:
            state["end_date"] = e.control.value
            end_field.value = e.control.value.strftime("%d/%m/%Y")
            error_text.visible = False
            page.update()

    start_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=_on_start_date_picked,
        locale=ft.Locale("es"),
        help_text="Fecha inicial",
        cancel_text="Cancelar",
        confirm_text="Aceptar",
        error_format_text="Formato inválido",
        error_invalid_text="Fecha inválida",
        field_hint_text="dd/mm/aaaa",
        field_label_text="Fecha",
        entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY,
    )

    end_picker = ft.DatePicker(
        first_date=datetime(2020, 1, 1),
        last_date=datetime(2030, 12, 31),
        on_change=_on_end_date_picked,
        locale=ft.Locale("es"),
        help_text="Fecha final",
        cancel_text="Cancelar",
        confirm_text="Aceptar",
        error_format_text="Formato inválido",
        error_invalid_text="Fecha inválida",
        field_hint_text="dd/mm/aaaa",
        field_label_text="Fecha",
        entry_mode=ft.DatePickerEntryMode.CALENDAR_ONLY,
    )

    page.overlay.append(start_picker)
    page.overlay.append(end_picker)

    def _open_start_picker(e):
        start_picker.open = True
        page.update()

    def _open_end_picker(e):
        end_picker.open = True
        page.update()

    async def _on_export_filtered(e):
        if not state["start_date"] or not state["end_date"]:
            error_text.value = "Selecciona ambas fechas"
            error_text.visible = True
            page.update()
            return

        sd = state["start_date"].date() if hasattr(state["start_date"], "date") else state["start_date"]
        ed = state["end_date"].date() if hasattr(state["end_date"], "date") else state["end_date"]
        if sd > ed:
            error_text.value = "La fecha inicial no puede ser mayor a la final"
            error_text.visible = True
            page.update()
            return

        calculations = load_calculations()
        start_d = state["start_date"].date() if hasattr(state["start_date"], "date") else state["start_date"]
        end_d = state["end_date"].date() if hasattr(state["end_date"], "date") else state["end_date"]

        filtered = []
        for calc in calculations:
            try:
                calc_date = datetime.fromisoformat(calc.get("created_at", "")).date()
                if start_d <= calc_date <= end_d:
                    filtered.append(calc)
            except (ValueError, TypeError):
                continue

        if not filtered:
            error_text.value = "No hay cálculos en el rango seleccionado"
            error_text.visible = True
            page.update()
            return

        page.pop_dialog()
        # Remove pickers from overlay
        if start_picker in page.overlay:
            page.overlay.remove(start_picker)
        if end_picker in page.overlay:
            page.overlay.remove(end_picker)

        from utils.pdf_export import generate_pdf
        pdf_path = generate_pdf(filtered)
        share = ft.Share()
        await share.share_files(
            [ft.ShareFile.from_path(pdf_path, name=pdf_path.split(os.sep)[-1])],
            title="Exportar cálculos",
        )

    def _on_cancel(e):
        page.pop_dialog()
        if start_picker in page.overlay:
            page.overlay.remove(start_picker)
        if end_picker in page.overlay:
            page.overlay.remove(end_picker)
        page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Text(
            "Exportar PDF",
            size=17,
            weight=ft.FontWeight.W_600,
            color=c["on_surface"],
        ),
        content=ft.Container(
            width=300,
            content=ft.Column(
                tight=True,
                spacing=16,
                controls=[
                    ft.Text(
                        "Selecciona el rango de fechas",
                        size=14,
                        color=c["on_surface_variant"],
                    ),
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            start_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_TODAY,
                                icon_color=c["primary"],
                                icon_size=22,
                                tooltip="Seleccionar fecha",
                                on_click=_open_start_picker,
                            ),
                        ],
                    ),
                    ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            end_field,
                            ft.IconButton(
                                icon=ft.Icons.CALENDAR_TODAY,
                                icon_color=c["primary"],
                                icon_size=22,
                                tooltip="Seleccionar fecha",
                                on_click=_open_end_picker,
                            ),
                        ],
                    ),
                    error_text,
                ],
            ),
        ),
        actions=[
            ft.TextButton("Cancelar", on_click=_on_cancel),
            ft.FilledTonalButton("Exportar", on_click=_on_export_filtered),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )
    page.show_dialog(dlg)


def apply_saved_calculations_appbar(page: ft.Page, on_navigate_back, colors_fn, has_calculations: bool):
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
            size=17,
        ),
        center_title=False,
        leading_width=40,
        title_spacing=0,
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
            return d.strftime("%d/%m/%Y %I:%M %p")
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
            icon_color="#1976D2",
            icon_size=20,
            tooltip="Editar",
            style=ft.ButtonStyle(padding=ft.Padding.all(0)),
            width=28,
            height=28,
        )
        delete_btn = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_color="#D32F2F",
            icon_size=20,
            tooltip="Eliminar",
            style=ft.ButtonStyle(padding=ft.Padding.all(0)),
            width=28,
            height=28,
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
            padding=ft.Padding.symmetric(vertical=10, horizontal=16),
            margin=ft.Margin.only(bottom=12),
            content=ft.Column(
                spacing=8,
                controls=[
                    # Header: date + action buttons
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text(
                                _format_date(calc.get("created_at", "")),
                                size=14,
                                weight=ft.FontWeight.W_700,
                                color=c["on_surface"],
                            ),
                            ft.Row(
                                spacing=0,
                                tight=True,
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
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=8, left=24, right=24, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=0,
                scroll=ft.ScrollMode.AUTO,
                controls=cards,
            ),
        ),
    )
