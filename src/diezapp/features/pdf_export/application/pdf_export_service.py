from typing import Protocol


class PdfGeneratorPort(Protocol):
    def generate_calculations_pdf(self, calculations: list) -> str: ...


class PdfExportService:
    def __init__(self, generator: PdfGeneratorPort):
        self.generator = generator

    def export_calculations(self, calculations: list) -> str:
        return self.generator.generate_calculations_pdf(calculations)
