from collections.abc import Sequence
from typing import Protocol

from diezapp.features.calculations.domain.models import Calculation


class PdfGeneratorPort(Protocol):
    def generate_calculations_pdf(self, calculations: Sequence[Calculation]) -> str: ...


class PdfExportService:
    def __init__(self, generator: PdfGeneratorPort):
        self.generator = generator

    def export_calculations(self, calculations: Sequence[Calculation]) -> str:
        return self.generator.generate_calculations_pdf(calculations)
