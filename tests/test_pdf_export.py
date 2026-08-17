from pathlib import Path

from diezapp.features.pdf_export.application.pdf_export_service import (
    PdfExportService,
)
from diezapp.infrastructure.pdf.pdf_generator import PdfGenerator


def test_pdf_export_generates_file_with_minimal_calculation(tmp_path, monkeypatch):
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(tmp_path))
    calculations = [
        {
            "amount": 100,
            "envio_21": 21,
            "restante": 79,
            "fondo_local": 1,
            "sostenimiento": 2,
            "fund_percentage": 1,
            "created_at": "2026-08-17T10:00:00+00:00",
        }
    ]

    output_path = PdfExportService(PdfGenerator()).export_calculations(calculations)

    assert Path(output_path).exists()
    assert Path(output_path).stat().st_size > 0
