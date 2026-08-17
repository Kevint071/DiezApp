from diezapp.features.pdf_export.application.pdf_export_service import PdfExportService
from diezapp.infrastructure.pdf.pdf_generator import PdfGenerator

_service = PdfExportService(PdfGenerator())


def generate_pdf(calculations: list) -> str:
    return _service.export_calculations(calculations)
