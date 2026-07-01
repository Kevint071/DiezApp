import os
import calendar
import flet as ft
from datetime import datetime, date

from utils.theme import (
    ON_SURFACE_LIGHT,
    ON_SURFACE_DARK,
    FOCUS_LIGHT,
    FOCUS_DARK,
    OUTLINE_LIGHT_INPUT,
)
from utils.storage import load_calculations, update_calculation, delete_calculation


def build_date_range_picker_view(page: ft.Page, colors_fn):
    c = colors_fn(page)
    light = page.theme_mode == ft.ThemeMode.LIGHT
    today = datetime.today().date()

    MONTH_NAMES = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    DAY_NAMES = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
    CELL = 42

    state = {"start": None, "end": None, "month": today.replace(day=1)}

    def _get_range():
        s, e = state["start"], state["end"]
        return (e, s) if s and e and s > e else (s, e)

    def _pos(d):
        s, e = _get_range()
        if d == s and e and s != e:
            return "start"
        if d == s:
            return "solo"
        if e and d == e:
            return "end"
        if s and e and s < d < e:
            return "range"
        if d == today:
            return "today"
        return "normal"

    def _on_tap(d):
        s, e = state["start"], state["end"]
        if s is None or e is not None:
            state["start"], state["end"] = d, None
        elif d == s:
            state["start"] = None
        elif d < s:
            state["start"], state["end"] = d, s
        else:
            state["end"] = d
        _refresh()

    def _cell(d):
        if d is None:
            return ft.Container(width=CELL, height=CELL)
        p = _pos(d)
        _, e = _get_range()
        half = CELL // 2
        layers = []
        # ── Range band ────────────────────────────────────
        if p == "range":
            layers.append(ft.Container(
                width=CELL, height=CELL,
                bgcolor=ft.Colors.with_opacity(0.14, c["primary"]),
            ))
        elif p == "start" and e:
            layers.append(ft.Row(spacing=0, controls=[
                ft.Container(width=half, height=CELL),
                ft.Container(width=CELL - half, height=CELL,
                             bgcolor=ft.Colors.with_opacity(0.14, c["primary"])),
            ]))
        elif p == "end":
            layers.append(ft.Row(spacing=0, controls=[
                ft.Container(width=half, height=CELL,
                             bgcolor=ft.Colors.with_opacity(0.14, c["primary"])),
                ft.Container(width=CELL - half, height=CELL),
            ]))
        # ── Circle ───────────────────────────────────────
        if p in ("start", "end", "solo"):
            layers.append(ft.Container(
                width=CELL, height=CELL,
                border_radius=CELL // 2,
                bgcolor=c["primary"],
            ))
        elif p == "today":
            layers.append(ft.Container(
                width=CELL, height=CELL,
                border_radius=CELL // 2,
                border=ft.Border.all(1.5, c["primary"]),
            ))
        # ── Day number ───────────────────────────────────
        if p in ("start", "end", "solo"):
            txt_color = "#FFFFFF" if light else "#064E3B"
            weight = ft.FontWeight.W_700
        elif p in ("range", "today"):
            txt_color = c["primary"]
            weight = ft.FontWeight.W_500
        else:
            txt_color = c["on_surface"]
            weight = ft.FontWeight.W_400
        layers.append(ft.Container(
            width=CELL, height=CELL, alignment=ft.Alignment.CENTER,
            content=ft.Text(
                str(d.day), size=13, color=txt_color, weight=weight,
                text_align=ft.TextAlign.CENTER,
            ),
        ))
        return ft.Container(
            width=CELL, height=CELL,
            content=ft.Stack(width=CELL, height=CELL, controls=layers),
            on_click=lambda e, day=d: _on_tap(day),
        )

    def _grid():
        m = state["month"]
        first_wd = m.weekday()
        days_in = calendar.monthrange(m.year, m.month)[1]
        raw = [None] * first_wd + [date(m.year, m.month, n) for n in range(1, days_in + 1)]
        while len(raw) % 7:
            raw.append(None)
        header = ft.Row(
            spacing=0, alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=CELL, height=28, alignment=ft.Alignment.CENTER,
                    content=ft.Text(
                        name, size=11, weight=ft.FontWeight.W_600,
                        color=c["on_surface_variant"], text_align=ft.TextAlign.CENTER,
                    ),
                )
                for name in DAY_NAMES
            ],
        )
        rows = [header]
        for i in range(0, len(raw), 7):
            rows.append(ft.Row(
                spacing=0, alignment=ft.MainAxisAlignment.CENTER,
                controls=[_cell(d) for d in raw[i:i + 7]],
            ))
        return ft.Column(spacing=2, controls=rows)

    # ── Static controls ───────────────────────────────────
    m0 = state["month"]
    month_lbl = ft.Text(
        f"{MONTH_NAMES[m0.month - 1]} {m0.year}",
        size=15, weight=ft.FontWeight.W_700, color=c["on_surface"],
    )
    start_val = ft.Text(
        "Seleccionar", size=14,
        color=c["on_surface_variant"], weight=ft.FontWeight.W_400,
    )
    end_val = ft.Text(
        "Seleccionar", size=14,
        color=c["on_surface_variant"], weight=ft.FontWeight.W_400,
    )
    grid_box = ft.Container(content=_grid())
    err_txt = ft.Text(
        "", size=12, color="#DC2626", visible=False,
        text_align=ft.TextAlign.CENTER,
    )
    export_btn = ft.FilledButton(
        "Exportar PDF",
        icon=ft.Icons.PICTURE_AS_PDF_OUTLINED,
        disabled=True,
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.Padding.symmetric(vertical=14, horizontal=20),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
        ),
        width=float("inf"),
    )

    def _refresh():
        m = state["month"]
        month_lbl.value = f"{MONTH_NAMES[m.month - 1]} {m.year}"
        grid_box.content = _grid()
        s, e = state["start"], state["end"]
        if s:
            start_val.value = s.strftime("%d/%m/%Y")
            start_val.color = c["on_surface"]
            start_val.weight = ft.FontWeight.W_600
        else:
            start_val.value = "Seleccionar"
            start_val.color = c["on_surface_variant"]
            start_val.weight = ft.FontWeight.W_400
        if e:
            end_val.value = e.strftime("%d/%m/%Y")
            end_val.color = c["on_surface"]
            end_val.weight = ft.FontWeight.W_600
        else:
            end_val.value = "Seleccionar"
            end_val.color = c["on_surface_variant"]
            end_val.weight = ft.FontWeight.W_400
        export_btn.disabled = not (s and e)
        err_txt.visible = False
        page.update()

    def _prev(e):
        m = state["month"]
        state["month"] = m.replace(month=m.month - 1) if m.month > 1 else m.replace(year=m.year - 1, month=12)
        _refresh()

    def _next(e):
        m = state["month"]
        state["month"] = m.replace(month=m.month + 1) if m.month < 12 else m.replace(year=m.year + 1, month=1)
        _refresh()

    async def _export(e):
        s, en = _get_range()
        if not s or not en:
            return
        calculations = load_calculations()
        filtered = []
        for calc in calculations:
            try:
                cd = datetime.fromisoformat(calc.get("created_at", "")).date()
                if s <= cd <= en:
                    filtered.append(calc)
            except (ValueError, TypeError):
                continue
        if not filtered:
            err_txt.value = "No hay cálculos en el rango seleccionado"
            err_txt.visible = True
            page.update()
            return
        from utils.pdf_export import generate_pdf
        pdf_path = generate_pdf(filtered)
        share = ft.Share()
        await share.share_files(
            [ft.ShareFile.from_path(pdf_path, name=pdf_path.split(os.sep)[-1])],
            title="Exportar cálculos",
        )

    export_btn.on_click = _export

    def _chip(icon, label: str, val_ctrl: ft.Text):
        return ft.Container(
            expand=True,
            bgcolor=c["card_bg"],
            border_radius=14,
            padding=ft.Padding.only(left=14, right=14, top=12, bottom=12),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(icon, color=c["primary"], size=15),
                            ft.Text(label, size=11, color=c["on_surface_variant"],
                                    weight=ft.FontWeight.W_500),
                        ],
                    ),
                    val_ctrl,
                ],
            ),
        )

    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(left=24, right=24, top=8, bottom=24),
            content=ft.Column(
                expand=True,
                spacing=16,
                controls=[
                    # ── Date range chips ────────────────────────
                    ft.Row(
                        spacing=12,
                        controls=[
                            _chip(ft.Icons.CALENDAR_TODAY_OUTLINED, "Desde", start_val),
                            _chip(ft.Icons.EVENT_OUTLINED, "Hasta", end_val),
                        ],
                    ),
                    # ── Calendar card ───────────────────────────
                    ft.Container(
                        bgcolor=c["card_bg"],
                        border_radius=16,
                        padding=ft.Padding.only(top=12, bottom=16, left=4, right=4),
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.IconButton(
                                            icon=ft.Icons.CHEVRON_LEFT_ROUNDED,
                                            icon_color=c["on_surface"],
                                            icon_size=22,
                                            on_click=_prev,
                                            style=ft.ButtonStyle(padding=ft.Padding.all(8)),
                                        ),
                                        month_lbl,
                                        ft.IconButton(
                                            icon=ft.Icons.CHEVRON_RIGHT_ROUNDED,
                                            icon_color=c["on_surface"],
                                            icon_size=22,
                                            on_click=_next,
                                            style=ft.ButtonStyle(padding=ft.Padding.all(8)),
                                        ),
                                    ],
                                ),
                                grid_box,
                            ],
                        ),
                    ),
                    err_txt,
                    ft.Container(expand=True),
                    export_btn,
                ],
            ),
        ),
    )


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
