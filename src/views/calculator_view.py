"""Calculator ("Distribución") screen.

Holds its own controls/state in a class (rather than a plain builder
function) because `main.py` keeps a single instance alive for the whole
session and resets it whenever the view is opened.
"""

import flet as ft

from diezapp.features.calculations.application.create_calculation import (
    CreateCalculation,
)
from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from utils.scroll_divider import build_scroll_divider, make_scroll_divider_handler


class CalculatorView:
    def __init__(
        self,
        page: ft.Page,
        state: dict,
        colors_fn,
        create_calculation: CreateCalculation,
        conflicts: ConflictService,
    ):
        self.page = page
        self.state = state
        self.colors_fn = colors_fn
        self.create_calculation = create_calculation
        self.conflicts = conflicts

        self.txt_21 = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)
        self.txt_79 = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)
        self.txt_1_of_79 = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)
        self.txt_rest = ft.Text(value="", size=15, weight=ft.FontWeight.W_600)

        self.lbl_21 = ft.Text("Envío (21%)", size=13, weight=ft.FontWeight.W_500)
        self.lbl_79 = ft.Text("Restante", size=13, weight=ft.FontWeight.W_500)
        self.lbl_1_of_79 = ft.Text(
            self._fund_label(), size=13, weight=ft.FontWeight.W_500
        )
        self.lbl_rest = ft.Text("Sostenimiento", size=13, weight=ft.FontWeight.W_500)

        self.results_container = ft.Container(visible=False)

        self.save_btn = ft.OutlinedButton(
            "Guardar",
            visible=False,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=14, horizontal=20),
                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
            ),
            width=float("inf"),
            on_click=self._save_calculation,
        )

        self.input_amount = ft.TextField(
            label="Cantidad neta ($)",
            label_style=ft.TextStyle(weight=ft.FontWeight.W_400),
            keyboard_type=ft.KeyboardType.NUMBER,
            border_radius=12,
            content_padding=ft.Padding.symmetric(vertical=14, horizontal=14),
            text_size=15,
            expand=True,
            on_submit=self.calculate,
            on_change=self._format_input_number,
        )

        self.calc_btn = ft.FilledButton(
            "Calcular",
            on_click=self.calculate,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(vertical=14, horizontal=20),
                text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_600),
            ),
            width=float("inf"),
        )

    def _fund_label(self) -> str:
        return f"Fondo local ({self.state['fund_percentage']}%)"

    def _format_input_number(self, e):
        """Format the input with dots as thousand separators while typing."""
        raw = self.input_amount.value.replace(".", "").replace(",", "")
        if not raw:
            return
        digits = "".join(ch for ch in raw if ch.isdigit())
        if not digits:
            self.input_amount.value = ""
            self.page.update()
            return
        formatted = ""
        for i, d in enumerate(reversed(digits)):
            if i > 0 and i % 3 == 0:
                formatted = "." + formatted
            formatted = d + formatted
        self.input_amount.value = formatted
        self.page.update()

    def apply_input_colors(self):
        c = self.colors_fn(self.page)
        self.input_amount.border_color = c["input_border"]
        self.input_amount.focused_border_color = c["input_focused"]

    @staticmethod
    def format_currency(value: float) -> str:
        return f"${value:,.0f}".replace(",", ".")

    def _build_results(self):
        c = self.colors_fn(self.page)

        def _result_tile(label_ctrl: ft.Text, value_ctrl: ft.Text):
            label_ctrl.color = c["on_surface_variant"]
            value_ctrl.color = c["primary"]
            return ft.Container(
                bgcolor=c["card_bg"],
                border_radius=14,
                padding=ft.Padding.symmetric(vertical=12, horizontal=16),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[label_ctrl, value_ctrl],
                ),
            )

        self.results_container.content = ft.Column(
            spacing=10,
            controls=[
                ft.Container(height=8),
                ft.Text(
                    "Distribución",
                    size=14,
                    weight=ft.FontWeight.W_600,
                    color=c["on_surface_variant"],
                ),
                _result_tile(self.lbl_21, self.txt_21),
                _result_tile(self.lbl_79, self.txt_79),
                _result_tile(self.lbl_1_of_79, self.txt_1_of_79),
                _result_tile(self.lbl_rest, self.txt_rest),
            ],
        )

    def calculate(self, e):
        try:
            amount = float(self.input_amount.value.replace(".", "").replace(",", "."))
        except ValueError, AttributeError:
            self.input_amount.error = "Ingresa un número válido"
            self.page.update()
            return

        self.input_amount.error = None
        distribution = calculate_distribution(amount, self.state["fund_percentage"])

        self.txt_21.value = self.format_currency(distribution.envio_21)
        self.txt_79.value = self.format_currency(distribution.restante)
        self.txt_1_of_79.value = self.format_currency(distribution.fondo_local)
        self.txt_rest.value = self.format_currency(distribution.sostenimiento)

        self._build_results()
        self.results_container.visible = True
        self.save_btn.visible = True
        self.page.update()

    def _save_calculation(self, e):
        if self.conflicts.count() > 0:
            snack = ft.SnackBar(
                content=ft.Text("Resuelve los conflictos antes de guardar"), open=True
            )
            self.page.overlay.append(snack)
            self.page.update()
            return
        try:
            amount = float(self.input_amount.value.replace(".", "").replace(",", "."))
        except ValueError, AttributeError:
            return
        self.create_calculation.execute(amount, self.state["fund_percentage"])
        self.save_btn.visible = False
        self.page.update()

    def reset(self):
        """Clear the input and hide results before opening the view again."""
        self.input_amount.value = ""
        self.input_amount.error = None
        self.results_container.visible = False
        self.save_btn.visible = False

    def prepare_for_show(self):
        """Refresh label/colors right before `build_content()` is added to the page."""
        self.lbl_1_of_79.value = self._fund_label()
        self.apply_input_colors()

    def build_content(self):
        c = self.colors_fn(self.page)
        divider = build_scroll_divider()
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                expand=True,
                padding=ft.Padding.only(left=0, right=0, top=8, bottom=24),
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
                                    margin=ft.Margin.symmetric(horizontal=24),
                                    content=ft.Column(
                                        expand=True,
                                        spacing=20,
                                        controls=[
                                            self.input_amount,
                                            self.calc_btn,
                                            self.results_container,
                                            self.save_btn,
                                        ],
                                    ),
                                ),
                            ],
                        ),
                    ],
                ),
            ),
        )
