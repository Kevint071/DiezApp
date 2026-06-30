from __future__ import annotations

import os
import tempfile
from datetime import date, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fpdf import FPDF


def _format_currency(value: float) -> str:
    return f"${value:,.0f}".replace(",", ".")


def _format_date(date_str: str) -> str:
    try:
        d = datetime.fromisoformat(date_str)
        return d.strftime("%d/%m/%Y %I:%M %p")
    except (ValueError, TypeError):
        try:
            parts = date_str.split("-")
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except (IndexError, AttributeError):
            return date_str


def generate_pdf(calculations: list) -> str:
    """Generate a PDF with all calculations in 2-column layout, oldest first.

    Returns the path to the generated temporary PDF file.
    """
    from fpdf import FPDF

    # Order oldest first (they're stored newest first)
    calcs = list(reversed(calculations))

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)

    # Page dimensions
    page_w = 210
    margin = 12
    col_gap = 8
    col_w = (page_w - 2 * margin - col_gap) / 2
    top_margin = 12
    card_h = 38
    card_spacing = 4
    title_h = 14

    # Calculate how many cards fit per column
    usable_h = 297 - top_margin - margin - title_h
    cards_per_col = int(usable_h / (card_h + card_spacing))

    cards_per_page = cards_per_col * 2
    total_pages = max(1, (len(calcs) + cards_per_page - 1) // cards_per_page)

    card_idx = 0
    for _ in range(total_pages):
        pdf.add_page()

        # Title
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_xy(margin, top_margin)
        pdf.cell(page_w - 2 * margin, 8, "Calculos Porcentuales de Diezmo", align="C")

        content_top = top_margin + title_h

        for col in range(2):
            x = margin if col == 0 else margin + col_w + col_gap

            for row in range(cards_per_col):
                if card_idx >= len(calcs):
                    break

                calc = calcs[card_idx]
                card_idx += 1

                y = content_top + row * (card_h + card_spacing)
                _draw_card(pdf, x, y, col_w, card_h, calc)

            if card_idx >= len(calcs):
                break

    # Write to temp file
    file_name = f"diezmos_{date.today().isoformat()}.pdf"
    tmp_dir = tempfile.gettempdir()
    output_path = os.path.join(tmp_dir, file_name)
    pdf.output(output_path)
    return output_path


def _draw_card(pdf: FPDF, x: float, y: float, w: float, h: float, calc: dict):
    """Draw a single calculation card at the given position."""
    fund_pct = calc.get("fund_percentage", 1)

    # Card background
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(x, y, w, h, "F")

    # Date header
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_xy(x + 3, y + 2)
    pdf.cell(w - 6, 4, _format_date(calc.get("created_at", "")))

    # Separator line
    pdf.set_draw_color(200, 200, 200)
    pdf.line(x + 3, y + 7, x + w - 3, y + 7)

    # Values
    rows = [
        ("Cantidad neta:", _format_currency(calc["amount"])),
        ("Envio (21%):", _format_currency(calc["envio_21"])),
        ("Restante:", _format_currency(calc["restante"])),
        (f"Fondo local ({fund_pct}%):", _format_currency(calc["fondo_local"])),
        ("Sostenimiento:", _format_currency(calc["sostenimiento"])),
    ]

    row_y = y + 9
    row_h = 5.4
    for label, value in rows:
        pdf.set_font("Helvetica", "", 7)
        pdf.set_xy(x + 3, row_y)
        pdf.cell(w * 0.55 - 3, row_h, label)

        pdf.set_font("Helvetica", "B", 7)
        pdf.set_xy(x + w * 0.55, row_y)
        pdf.cell(w * 0.45 - 3, row_h, value, align="R")

        row_y += row_h
