from diezapp.infrastructure.pdf.pdf_generator import PdfGenerator


class PdfExportService:
    def __init__(self, generator: PdfGenerator):
        self.generator = generator

    def export_calculations(self, calculations: list) -> str:
        return self.generator.generate_calculations_pdf(calculations)
