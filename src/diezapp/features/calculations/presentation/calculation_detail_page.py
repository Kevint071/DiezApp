"""Detail of one saved calculation: full breakdown, edit and delete.

Reads like the calculator results (same "Desglose" block) so a stored
calculation looks exactly as it did when it was saved. Editing only changes
the net amount; the fund percentage stays the one the calculation was saved
with, not the current setting.
"""

from collections.abc import Callable

import flet as ft

from diezapp.features.calculations.application.delete_calculation import (
    DeleteCalculation,
)
from diezapp.features.calculations.application.update_calculation import (
    UpdateCalculation,
)
from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.presentation.calculation_components import (
    format_currency,
)
from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)
from diezapp.features.calculator.domain.models import Distribution
from diezapp.features.calculator.presentation.distribution_breakdown import (
    build_distribution_breakdown,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.shared.datetime_utils import to_local_datetime
from diezapp.shared.presentation.date_labels import (
    MONTHS_SHORT,
    WEEKDAYS_SHORT,
    clock,
    full_date,
)
from diezapp.shared.presentation.dialogs import (
    build_dialog,
    dialog_cancel_button,
    dialog_primary_button,
)
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)

AMOUNT_SIZE = 34
SAVE_BTN_HEIGHT = 48


def created_label(value: str) -> str:
    """e.g. ``Mié, 8 de octubre de 2026 · 10:32``."""
    try:
        moment = to_local_datetime(value)
    except ValueError, TypeError:
        return "Sin fecha"
    weekday = WEEKDAYS_SHORT[moment.weekday()].capitalize()
    return f"{weekday}, {full_date(moment)} · {clock(moment)}"


def edited_label(value: str | None) -> str | None:
    """e.g. ``Editado el 9 oct 2026 · 08:10``; ``None`` if never edited."""
    if not value:
        return None
    try:
        moment = to_local_datetime(value)
    except ValueError, TypeError:
        return None
    return (
        f"Editado el {moment.day} {MONTHS_SHORT[moment.month - 1]} "
        f"{moment.year} · {clock(moment)}"
    )


def format_thousands(value: float) -> str:
    return f"{int(value):,}".replace(",", ".")


def parse_amount(text: str | None) -> float | None:
    digits = "".join(ch for ch in (text or "") if ch.isdigit())
    return float(digits) if digits else None


def stored_distribution(calc: Calculation) -> Distribution:
    return Distribution(
        amount=calc["amount"],
        envio_21=calc["envio_21"],
        restante=calc["restante"],
        fondo_local=calc["fondo_local"],
        sostenimiento=calc["sostenimiento"],
    )


def build_calculation_detail_view(
    page: ft.Page,
    colors_fn,
    calculation: Calculation,
    calculate_distribution: CalculateDistribution,
    update_calculation: UpdateCalculation,
    delete_calculation: DeleteCalculation,
    conflicts_service: ConflictService,
    on_deleted: Callable[[], None],
    set_header_actions: Callable[[list[ft.Control]], None],
    register_leave_guard=None,
):
    c = colors_fn(page)
    calc = calculation
    fund_pct = calc.get("fund_percentage", 1)
    state = {"editing": False}

    def _snack(message: str):
        page.overlay.append(ft.SnackBar(content=ft.Text(message), open=True))
        page.update()

    # ── Hero: the net amount, read-only or as an input ────
    amount_text = ft.Text(
        format_currency(calc["amount"]),
        size=AMOUNT_SIZE,
        weight=ft.FontWeight.W_700,
        color=c["on_surface"],
    )
    amount_field = ft.TextField(
        keyboard_type=ft.KeyboardType.NUMBER,
        border=ft.InputBorder.NONE,
        content_padding=ft.Padding.all(0),
        text_size=AMOUNT_SIZE,
        text_style=ft.TextStyle(weight=ft.FontWeight.W_700),
        hint_text="0",
        hint_style=ft.TextStyle(
            size=AMOUNT_SIZE,
            weight=ft.FontWeight.W_700,
            color=ft.Colors.with_opacity(0.35, c["on_surface_variant"]),
        ),
        color=c["on_surface"],
        cursor_color=c["primary"],
        dense=True,
        expand=True,
    )
    # Without a box, this line is the only cue that the amount is editable.
    underline = ft.Container(height=2, bgcolor=c["primary"])
    edit_block = ft.Column(
        spacing=8,
        tight=True,
        visible=False,
        controls=[
            ft.Row(
                spacing=6,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Text(
                        "$",
                        size=AMOUNT_SIZE,
                        weight=ft.FontWeight.W_700,
                        color=c["primary"],
                    ),
                    amount_field,
                ],
            ),
            underline,
        ],
    )
    edited_text = ft.Text("", size=12, italic=True, color=c["on_surface_variant"])

    def _paint_edited():
        label = edited_label(calc.get("updated_at"))
        edited_text.value = label or ""
        edited_text.visible = label is not None

    _paint_edited()

    hero = ft.Column(
        spacing=0,
        controls=[
            ft.Text(
                "Cantidad neta",
                size=13,
                weight=ft.FontWeight.W_500,
                color=c["on_surface_variant"],
            ),
            ft.Container(height=6),
            amount_text,
            edit_block,
            ft.Container(height=8),
            ft.Row(
                spacing=6,
                controls=[
                    ft.Icon(
                        ft.Icons.EVENT_OUTLINED, size=14, color=c["on_surface_variant"]
                    ),
                    ft.Text(
                        created_label(calc.get("created_at", "")),
                        size=13,
                        color=c["on_surface_variant"],
                    ),
                ],
            ),
            ft.Container(height=4),
            edited_text,
        ],
    )

    # ── Breakdown ─────────────────────────────────────────
    breakdown = ft.Column(spacing=0)

    def _paint_breakdown(distribution: Distribution):
        breakdown.controls = build_distribution_breakdown(c, distribution, fund_pct)

    _paint_breakdown(stored_distribution(calc))

    # ── Bottom bar (edit mode only) ───────────────────────
    save_btn = ft.FilledButton(
        height=SAVE_BTN_HEIGHT,
        expand=True,
        content=ft.Text("Guardar", size=15, weight=ft.FontWeight.W_700),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            bgcolor={
                ft.ControlState.DEFAULT: c["button"],
                ft.ControlState.DISABLED: c["outline"],
            },
            color={
                ft.ControlState.DEFAULT: c["on_button"],
                ft.ControlState.DISABLED: c["on_surface_variant"],
            },
            elevation=0,
        ),
    )
    cancel_btn = ft.OutlinedButton(
        height=SAVE_BTN_HEIGHT,
        expand=True,
        content=ft.Text("Cancelar", size=15, weight=ft.FontWeight.W_600),
        style=ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            color=c["on_surface"],
            side=ft.BorderSide(1, c["outline"]),
        ),
    )
    action_bar = ft.Container(
        visible=False,
        bgcolor=c["surface"],
        border=ft.Border.only(top=ft.BorderSide(1, c["outline"])),
        padding=ft.Padding.only(left=24, right=24, top=12, bottom=20),
        content=ft.Row(spacing=12, controls=[cancel_btn, save_btn]),
    )

    # ── Editing ───────────────────────────────────────────
    def _is_dirty() -> bool:
        if not state["editing"]:
            return False
        return parse_amount(amount_field.value) != calc["amount"]

    def _paint_save_btn():
        amount = parse_amount(amount_field.value)
        save_btn.disabled = amount is None or amount == calc["amount"]

    def _on_amount_change(e):
        amount = parse_amount(amount_field.value)
        amount_field.value = "" if amount is None else format_thousands(amount)
        _paint_breakdown(
            stored_distribution(calc)
            if amount is None
            else calculate_distribution.execute(amount, fund_pct)
        )
        _paint_save_btn()
        page.update()

    amount_field.on_change = _on_amount_change

    def _set_editing(editing: bool):
        state["editing"] = editing
        amount_text.visible = not editing
        edit_block.visible = editing
        action_bar.visible = editing
        if editing:
            amount_field.value = format_thousands(calc["amount"])
            _paint_save_btn()
        else:
            amount_text.value = format_currency(calc["amount"])
            _paint_breakdown(stored_distribution(calc))
        set_header_actions(_build_actions())

    def _start_edit(e):
        if conflicts_service.count() > 0:
            _snack("Resuelve los conflictos antes de editar")
            return
        _set_editing(True)
        page.update()
        page.run_task(amount_field.focus)

    def _cancel_edit(e=None):
        _set_editing(False)
        page.update()

    def _perform_save() -> bool:
        if conflicts_service.count() > 0:
            _snack("Resuelve los conflictos antes de editar")
            return False
        amount = parse_amount(amount_field.value)
        if amount is None:
            return False
        updated = update_calculation.execute(calc["id"], amount)
        if updated is None:
            return False
        calc.update(updated)
        _paint_edited()
        _set_editing(False)
        return True

    def _save_edit(e):
        if _perform_save():
            _snack("Cálculo actualizado")

    cancel_btn.on_click = _cancel_edit
    save_btn.on_click = _save_edit

    # ── Deleting ──────────────────────────────────────────
    def _confirm_delete(e):
        if conflicts_service.count() > 0:
            _snack("Resuelve los conflictos antes de eliminar")
            return

        def _do_delete(ev):
            page.pop_dialog()
            if delete_calculation.execute(calc["id"]):
                on_deleted()

        page.show_dialog(
            build_dialog(
                c,
                modal=True,
                title="Eliminar cálculo",
                content=(
                    f"Se eliminará el cálculo de {format_currency(calc['amount'])}. "
                    "Esta acción no se puede deshacer."
                ),
                actions=[
                    dialog_cancel_button("Cancelar", lambda ev: page.pop_dialog(), c),
                    dialog_primary_button("Eliminar", _do_delete, c, destructive=True),
                ],
            )
        )

    # ── App-bar actions: edit up front, the destructive one tucked away ──
    def _build_actions() -> list[ft.Control]:
        if state["editing"]:
            return []
        return [
            ft.IconButton(
                ft.Icons.EDIT_OUTLINED,
                icon_size=20,
                icon_color=c["on_surface_variant"],
                tooltip="Editar",
                on_click=_start_edit,
            ),
            ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_color=c["on_surface_variant"],
                icon_size=20,
                tooltip="Más opciones",
                items=[
                    ft.PopupMenuItem(
                        content=ft.Row(
                            spacing=10,
                            controls=[
                                ft.Icon(
                                    ft.Icons.DELETE_OUTLINE,
                                    size=18,
                                    color=c["error"],
                                ),
                                ft.Text("Eliminar", color=c["error"]),
                            ],
                        ),
                        on_click=_confirm_delete,
                    )
                ],
            ),
            ft.Container(width=4),
        ]

    # ── Leave guard: never drop an edited amount silently ─
    def _leave_guard(proceed, cancel):
        if not _is_dirty():
            proceed()
            return

        resolved = {"value": False}

        def _handle_save(ev):
            resolved["value"] = True
            page.pop_dialog()
            if _perform_save():
                proceed()
            else:
                cancel()

        def _handle_discard(ev):
            resolved["value"] = True
            page.pop_dialog()
            _set_editing(False)
            proceed()

        def _handle_dismiss(ev):
            if not resolved["value"]:
                cancel()

        page.show_dialog(
            build_dialog(
                c,
                title="Cambios sin guardar",
                content=(
                    "Cambiaste la cantidad neta de este cálculo. "
                    "¿Deseas guardarla o descartarla?"
                ),
                actions=[
                    dialog_cancel_button("Descartar", _handle_discard, c),
                    dialog_primary_button("Guardar", _handle_save, c),
                ],
                on_dismiss=_handle_dismiss,
            )
        )

    if register_leave_guard is not None:
        register_leave_guard(_leave_guard)

    set_header_actions(_build_actions())

    divider = build_scroll_divider()
    return ft.SafeArea(
        expand=True,
        content=ft.Container(
            expand=True,
            padding=ft.Padding.only(top=4),
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    divider,
                    ft.Column(
                        expand=True,
                        spacing=0,
                        scroll=ft.Scrollbar(thickness=6, radius=4),
                        on_scroll=make_scroll_divider_handler(divider, c),
                        controls=[
                            ft.Container(
                                margin=ft.Margin.only(
                                    left=24, right=24, top=8, bottom=24
                                ),
                                content=ft.Column(
                                    spacing=0,
                                    controls=[
                                        hero,
                                        ft.Container(height=28),
                                        ft.Text(
                                            "Desglose",
                                            size=16,
                                            weight=ft.FontWeight.W_700,
                                            color=c["on_surface"],
                                        ),
                                        ft.Container(height=16),
                                        breakdown,
                                    ],
                                ),
                            )
                        ],
                    ),
                    action_bar,
                ],
            ),
        ),
    )
