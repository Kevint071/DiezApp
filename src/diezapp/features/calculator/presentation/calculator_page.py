"""Calculator ("Distribución") screen.

Holds its own controls/state in a class (rather than a plain builder
function) because `main.py` keeps a single instance alive for the whole
session and resets it whenever the view is opened.
"""

from datetime import date, timedelta

import flet as ft

from diezapp.features.calculations.application.create_calculation import (
    CreateCalculation,
)
from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)
from diezapp.features.calculator.presentation.date_sheet import show_date_sheet
from diezapp.features.calculator.presentation.distribution_breakdown import (
    build_breakdown_bar,
    build_distribution_breakdown,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.shared.datetime_utils import local_now
from diezapp.shared.presentation.date_labels import MONTHS_SHORT, WEEKDAYS_SHORT
from diezapp.shared.presentation.scroll_divider import (
    build_scroll_divider,
    make_scroll_divider_handler,
)


def date_row_label(value: date, today: date) -> str:
    """e.g. ``Hoy, 8 oct 2026`` · ``Ayer, 7 oct 2026`` · ``Vie, 15 mar 2024``."""
    if value == today:
        prefix = "Hoy"
    elif value == today - timedelta(days=1):
        prefix = "Ayer"
    else:
        prefix = WEEKDAYS_SHORT[value.weekday()].capitalize()
    return f"{prefix}, {value.day} {MONTHS_SHORT[value.month - 1]} {value.year}"


CALC_BTN_SIZE = 48
SAVE_BTN_HEIGHT = 48
SAVE_BTN_WIDTH = 150
RESULTS_HIDDEN_OFFSET = ft.Offset(0, 0.04)
ACTION_BAR_HIDDEN_OFFSET = ft.Offset(0, 0.15)

# Type scale: section titles carry the main text colour; labels and helper
# notes step down in size/weight and use the variant colour.
TITLE_SIZE = 16


class CalculatorView:
    def __init__(
        self,
        page: ft.Page,
        state: dict,
        colors_fn,
        create_calculation: CreateCalculation,
        calculate_distribution: CalculateDistribution,
        conflicts: ConflictService,
    ):
        self.page = page
        self.state = state
        self.colors_fn = colors_fn
        self.create_calculation = create_calculation
        self.calculate_distribution = calculate_distribution
        self.conflicts = conflicts

        self.calculation_date: date = local_now().date()
        self.saved = False

        # ── Amount input ──
        self.input_amount = ft.TextField(
            hint_text="0",
            keyboard_type=ft.KeyboardType.NUMBER,
            border=ft.NoInputBorder(),
            content_padding=ft.Padding.all(0),
            text_size=32,
            text_style=ft.TextStyle(weight=ft.FontWeight.W_700),
            hint_style=ft.TextStyle(size=32, weight=ft.FontWeight.W_700),
            dense=True,
            expand=True,
            on_submit=self.calculate,
            on_change=self._format_input_number,
            on_focus=lambda e: self._set_input_focus(True),
            on_blur=lambda e: self._set_input_focus(False),
        )
        self.input_focused = False
        self.currency_prefix = ft.Text("$", size=32, weight=ft.FontWeight.W_700)
        self.calc_btn = ft.IconButton(
            icon=ft.Icons.ARROW_FORWARD_ROUNDED,
            icon_size=22,
            tooltip="Calcular",
            width=CALC_BTN_SIZE,
            height=CALC_BTN_SIZE,
            disabled=True,
            # Hidden until there is an amount, then pops in.
            opacity=0,
            scale=ft.Scale(0.6),
            animate_opacity=ft.Animation(180, ft.AnimationCurve.EASE_OUT),
            animate_scale=ft.Animation(260, ft.AnimationCurve.EASE_OUT_BACK),
            on_click=self.calculate,
        )
        self.input_label = ft.Text(
            "Cantidad neta", size=TITLE_SIZE, weight=ft.FontWeight.W_700
        )
        # Without a box, this line is the only cue that the amount is editable.
        self.input_underline = ft.Container(
            height=1,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
        )
        self.fund_icon = ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=14)
        self.fund_caption = ft.Text("", size=12, weight=ft.FontWeight.W_400)
        self.input_block = ft.Column(
            spacing=0,
            tight=True,
            controls=[
                self.input_label,
                ft.Container(height=10),
                ft.Row(
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[self.currency_prefix, self.input_amount, self.calc_btn],
                ),
                ft.Container(height=8),
                self.input_underline,
                ft.Container(height=10),
                ft.Row(spacing=6, controls=[self.fund_icon, self.fund_caption]),
            ],
        )

        # ── Results ──
        # Fades and slides up into place the first time results are shown.
        self.results_container = ft.Container(
            visible=False,
            opacity=0,
            offset=RESULTS_HIDDEN_OFFSET,
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(320, ft.AnimationCurve.EASE_OUT_CUBIC),
        )
        # The bar grows from the left on every calculation.
        self.bar = build_breakdown_bar(
            scale=ft.Scale(scale_x=0, scale_y=1, alignment=ft.Alignment.CENTER_LEFT),
            animate_scale=ft.Animation(650, ft.AnimationCurve.EASE_OUT_CUBIC),
        )

        self.bar_bracket = ft.Container(
            opacity=0,
            animate_opacity=ft.Animation(500, ft.AnimationCurve.EASE_OUT),
        )

        # ── Bottom action bar: the date only matters when saving, so it sits
        # next to "Guardar" instead of among the results. ──
        self.date_switcher = ft.AnimatedSwitcher(
            content=ft.Container(),
            duration=240,
            reverse_duration=140,
            transition=ft.AnimatedSwitcherTransition.FADE,
        )
        self.date_label = ft.Text(
            "Fecha del cálculo", size=12, weight=ft.FontWeight.W_500
        )
        self.date_icon = ft.Icon(ft.Icons.EXPAND_MORE_ROUNDED, size=18)
        self.date_card = ft.Container(
            border_radius=12,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            ink=True,
            tooltip="Cambiar fecha",
            on_click=self._open_date_picker,
            on_hover=self._on_date_hover,
            # Padding lives on an inner container: on an ink + animate container
            # Flet applies it twice while enabled but once when disabled, so the
            # card shrank on save and dragged the "Guardar" button with it.
            content=ft.Container(
                # Horizontal padding gives the hover/ripple room around the text.
                padding=ft.Padding.symmetric(vertical=8, horizontal=12),
                content=ft.Column(
                    spacing=2,
                    tight=True,
                    controls=[
                        self.date_label,
                        ft.Row(
                            spacing=2,
                            tight=True,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[self.date_switcher, self.date_icon],
                        ),
                    ],
                ),
            ),
        )

        # Fixed width: "Guardar" and "✓ Guardado" differ in content width, and
        # a content-sized button would shift (and drag the date) on save.
        self.save_btn = ft.FilledButton(
            width=SAVE_BTN_WIDTH,
            height=SAVE_BTN_HEIGHT,
            on_click=self._save_calculation,
        )
        self.action_bar = ft.Container(
            visible=False,
            opacity=0,
            offset=ACTION_BAR_HIDDEN_OFFSET,
            animate_opacity=ft.Animation(220, ft.AnimationCurve.EASE_OUT),
            animate_offset=ft.Animation(320, ft.AnimationCurve.EASE_OUT_CUBIC),
            # Lives outside the 24px content margin: left padding is 12 because
            # the date row adds its own 12, so its text lines up with the rest.
            padding=ft.Padding.only(left=12, right=24, top=0, bottom=24),
            content=ft.Column(
                spacing=12,
                tight=True,
                controls=[
                    ft.Container(
                        height=1, margin=ft.Margin.only(left=12), content=None
                    ),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[self.date_card, self.save_btn],
                    ),
                ],
            ),
        )
        self._paint_input()
        self._paint_save_btn()

    # ── Helpers ──

    @staticmethod
    def format_currency(value: float) -> str:
        return f"${value:,.0f}".replace(",", ".")

    def _parse_amount(self) -> float:
        return float(self.input_amount.value.replace(".", "").replace(",", "."))

    def _format_input_number(self, e):
        """Format the input with dots as thousand separators while typing."""
        raw = self.input_amount.value.replace(".", "").replace(",", "")
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            self.input_amount.value = ""
            self._paint_input()
            self.page.update()
            return
        formatted = ""
        for i, d in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                formatted = "." + formatted
            formatted = d + formatted
        self.input_amount.value = formatted
        self.input_amount.error = None
        self._paint_input()
        self.page.update()

    def _set_input_focus(self, focused: bool):
        self.input_focused = focused
        self._paint_input()
        self.page.update()

    def _show_input_error(self, message: str):
        self.input_amount.error = message
        self._paint_input()
        self.page.update()

    # ── Painting ──

    def apply_input_colors(self):
        self._paint_input()

    def _paint_input(self):
        c = self.colors_fn(self.page)
        focused = self.input_focused
        if self.input_amount.error:
            line_color = c["error"]
        elif focused:
            line_color = c["primary"]
        else:
            line_color = c["outline"]
        self.input_underline.bgcolor = line_color
        self.input_underline.height = 2 if focused or self.input_amount.error else 1
        self.input_amount.color = c["on_surface"]
        self.input_amount.cursor_color = c["primary"]
        self.input_amount.hint_style.color = ft.Colors.with_opacity(
            0.35, c["on_surface_variant"]
        )
        has_value = bool(self.input_amount.value)
        self.currency_prefix.color = (
            c["primary"] if has_value else c["on_surface_variant"]
        )
        self.calc_btn.disabled = not has_value
        self.calc_btn.opacity = 1 if has_value else 0
        self.calc_btn.scale.scale = 1 if has_value else 0.6
        self.calc_btn.style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            bgcolor={
                ft.ControlState.DEFAULT: c["button"],
                ft.ControlState.DISABLED: c["outline"],
            },
            icon_color={
                ft.ControlState.DEFAULT: c["on_button"],
                ft.ControlState.DISABLED: c["on_surface_variant"],
            },
            overlay_color=ft.Colors.with_opacity(0.12, c["on_button"]),
            animation_duration=200,
        )
        self.fund_caption.value = (
            f"Fondo local configurado al {self.state['fund_percentage']}%"
        )
        self.fund_caption.color = c["on_surface_variant"]
        self.fund_icon.color = c["on_surface_variant"]
        self.input_label.color = c["on_surface"]

    def _paint_save_btn(self):
        c = self.colors_fn(self.page)
        if self.saved:
            bg, fg = c["navigation_indicator"], c["primary"]
            controls = [
                ft.Icon(ft.Icons.CHECK_ROUNDED, size=18, color=fg),
                ft.Text("Guardado", size=15, weight=ft.FontWeight.W_600, color=fg),
            ]
        else:
            bg, fg = c["button"], c["on_button"]
            controls = [
                ft.Text("Guardar", size=15, weight=ft.FontWeight.W_700, color=fg)
            ]
        self.save_btn.content = ft.Row(
            tight=True,
            spacing=6,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=controls,
        )
        self.save_btn.style = ft.ButtonStyle(
            shape=ft.RoundedRectangleBorder(radius=14),
            padding=ft.Padding.symmetric(horizontal=16),
            bgcolor={
                ft.ControlState.DEFAULT: bg,
                ft.ControlState.DISABLED: bg,
            },
            overlay_color=ft.Colors.with_opacity(0.08, fg),
            elevation=0,
            animation_duration=220,
        )
        self.save_btn.disabled = self.saved
        self.date_card.disabled = self.saved
        self.date_card.opacity = 0.6 if self.saved else 1

    def _build_results(self, distribution):
        c = self.colors_fn(self.page)
        breakdown = build_distribution_breakdown(
            c,
            distribution,
            self.state["fund_percentage"],
            bar=self.bar,
            bar_bracket=self.bar_bracket,
        )
        self._refresh_date_card()
        self.results_container.content = ft.Column(
            spacing=0,
            controls=[
                ft.Container(height=12),
                # The app bar already says "Distribución".
                ft.Text(
                    "Desglose",
                    size=TITLE_SIZE,
                    weight=ft.FontWeight.W_700,
                    color=c["on_surface"],
                ),
                ft.Container(height=16),
                *breakdown,
            ],
        )

    # ── Date ──

    def _refresh_date_card(self):
        """Paint the date row for `self.calculation_date` (switcher fades the swap)."""
        c = self.colors_fn(self.page)
        self.date_switcher.content = ft.Text(
            date_row_label(self.calculation_date, local_now().date()),
            key=self.calculation_date.isoformat(),
            size=15,
            weight=ft.FontWeight.W_600,
            color=c["on_surface"],
        )
        self.date_card.ink_color = ft.Colors.with_opacity(0.08, c["primary"])
        self.date_label.color = c["on_surface_variant"]
        self.date_icon.color = c["on_surface_variant"]
        self.action_bar.content.controls[0].bgcolor = c["outline"]

    def _on_date_hover(self, e):
        c = self.colors_fn(self.page)
        self.date_card.bgcolor = (
            ft.Colors.with_opacity(0.06, c["primary"]) if e.data else None
        )
        self.date_card.update()

    def _set_calculation_date(self, value: date):
        if value == self.calculation_date:
            return
        self.calculation_date = value
        self._refresh_date_card()
        self.page.update()

    async def _open_date_picker(self, e):
        # The amount field keeps focus (and its numeric keyboard) while the sheet
        # is open, because tapping a day never takes focus. Flet has no blur(), so
        # park focus on the save button, which hides the keyboard.
        await self.save_btn.focus()
        show_date_sheet(
            self.page, self.colors_fn, self.calculation_date, self._set_calculation_date
        )

    # ── Actions ──

    async def calculate(self, e):
        try:
            amount = self._parse_amount()
        except ValueError, AttributeError:
            self._show_input_error("Ingresa un número válido")
            return
        try:
            distribution = self.calculate_distribution.execute(
                amount, self.state["fund_percentage"]
            )
        except ValueError:
            self._show_input_error("Ingresa un importe válido")
            return

        self.input_amount.error = None
        self._paint_input()
        self.saved = False
        self._build_results(distribution)
        self._paint_save_btn()

        # Mount at the start state first so the entrance and bar growth play.
        first_show = not self.results_container.visible
        self.results_container.visible = True
        self.action_bar.visible = True
        self.bar.scale.scale_x = 0
        self.bar_bracket.opacity = 0
        self.page.update()
        if first_show:
            self.results_container.opacity = 1
            self.results_container.offset = ft.Offset(0, 0)
            self.action_bar.opacity = 1
            self.action_bar.offset = ft.Offset(0, 0)
        self.bar.scale.scale_x = 1
        self.bar_bracket.opacity = 1
        self.page.update()
        # Flet has no blur(): parking focus on the save button drops the amount
        # field's focus and hides the keyboard so the results are fully visible.
        await self.save_btn.focus()

    def _save_calculation(self, e):
        if self.conflicts.count() > 0:
            snack = ft.SnackBar(
                content=ft.Text("Resuelve los conflictos antes de guardar"), open=True
            )
            self.page.overlay.append(snack)
            self.page.update()
            return
        try:
            amount = self._parse_amount()
        except ValueError, AttributeError:
            return
        self.create_calculation.execute(
            amount, self.state["fund_percentage"], self.calculation_date
        )
        self.saved = True
        self._paint_save_btn()
        self.page.update()

    def reset(self):
        """Clear the input and hide results before opening the view again."""
        self.input_amount.value = ""
        self.input_amount.error = None
        self.results_container.visible = False
        self.results_container.opacity = 0
        self.results_container.offset = RESULTS_HIDDEN_OFFSET
        self.bar.scale.scale_x = 0
        self.bar_bracket.opacity = 0
        self.action_bar.visible = False
        self.action_bar.opacity = 0
        self.action_bar.offset = ACTION_BAR_HIDDEN_OFFSET
        self.saved = False
        self.calculation_date = local_now().date()

    def prepare_for_show(self):
        """Refresh label/colors right before `build_content()` is added to the page."""
        self._paint_input()

    def build_content(self):
        c = self.colors_fn(self.page)
        divider = build_scroll_divider()
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=0, right=0, top=8, bottom=0),
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
                                    expand=True,
                                    margin=ft.Margin.only(left=24, right=24, bottom=16),
                                    content=ft.Column(
                                        expand=True,
                                        spacing=16,
                                        controls=[
                                            self.input_block,
                                            self.results_container,
                                        ],
                                    ),
                                ),
                                self.action_bar,
                            ],
                        ),
                    ],
                ),
            ),
        )
