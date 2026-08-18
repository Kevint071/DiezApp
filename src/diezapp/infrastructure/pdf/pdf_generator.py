import os
import tempfile
from collections.abc import Sequence

from diezapp.features.calculations.domain.models import Calculation
from diezapp.shared.datetime_utils import local_now, to_local_datetime


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _format_date(date_str: str) -> str:
    try:
        parsed = to_local_datetime(date_str)
        return parsed.strftime("%d/%m/%Y %I:%M %p")
    except ValueError, TypeError:
        try:
            parts = date_str.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except IndexError, AttributeError:
            return date_str


class PdfGenerator:
    def generate_calculations_pdf(self, calculations: Sequence[Calculation]) -> str:
        from fpdf import FPDF

        ordered_calculations = list(reversed(calculations))
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False)

        page_width = 210
        margin = 12
        column_gap = 8
        column_width = (page_width - 2 * margin - column_gap) / 2
        top_margin = 12
        card_height = 38
        card_spacing = 4
        title_height = 14
        usable_height = 297 - top_margin - margin - title_height
        cards_per_column = int(usable_height / (card_height + card_spacing))
        cards_per_page = cards_per_column * 2
        total_pages = max(
            1,
            (len(ordered_calculations) + cards_per_page - 1) // cards_per_page,
        )

        calculation_index = 0
        for _ in range(total_pages):
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_xy(margin, top_margin)
            pdf.cell(
                page_width - 2 * margin,
                8,
                "Calculos Porcentuales de Diezmo",
                align="C",
            )
            content_top = top_margin + title_height
            for column in range(2):
                x = margin if column == 0 else margin + column_width + column_gap
                for row in range(cards_per_column):
                    if calculation_index >= len(ordered_calculations):
                        break
                    y = content_top + row * (card_height + card_spacing)
                    self._draw_card(
                        pdf,
                        x,
                        y,
                        column_width,
                        card_height,
                        ordered_calculations[calculation_index],
                    )
                    calculation_index += 1
                if calculation_index >= len(ordered_calculations):
                    break

        output_path = os.path.join(
            tempfile.gettempdir(),
            f"diezmos_{local_now().date().isoformat()}.pdf",
        )
        pdf.output(output_path)
        return output_path

    def _draw_card(
        self,
        pdf,
        x: float,
        y: float,
        width: float,
        height: float,
        calc: Calculation,
    ):
        fund_percentage = calc.get("fund_percentage", 1)
        pdf.set_fill_color(245, 245, 245)
        pdf.rect(x, y, width, height, "F")
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_xy(x + 3, y + 2)
        pdf.cell(width - 6, 4, _format_date(calc.get("created_at", "")))
        pdf.set_draw_color(200, 200, 200)
        pdf.line(x + 3, y + 7, x + width - 3, y + 7)
        rows = [
            ("Cantidad neta:", _format_currency(calc["amount"])),
            ("Envio (21%):", _format_currency(calc["envio_21"])),
            ("Restante:", _format_currency(calc["restante"])),
            (
                f"Fondo local ({fund_percentage}%):",
                _format_currency(calc["fondo_local"]),
            ),
            ("Sostenimiento:", _format_currency(calc["sostenimiento"])),
        ]
        row_y = y + 9
        for label, value in rows:
            pdf.set_font("Helvetica", "", 7)
            pdf.set_xy(x + 3, row_y)
            pdf.cell(width * 0.55 - 3, 5.4, label)
            pdf.set_font("Helvetica", "B", 7)
            pdf.set_xy(x + width * 0.55, row_y)
            pdf.cell(width * 0.45 - 3, 5.4, value, align="R")
            row_y += 5.4
