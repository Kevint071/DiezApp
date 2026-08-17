from datetime import datetime

from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.domain.repositories import CalculationRepository

INDICATOR_KEYS = ("amount", "sostenimiento", "envio_21", "fondo_local")


class MonthlySummaryService:
    def __init__(self, calculations: CalculationRepository):
        self.calculations = calculations

    def month_calculations(self, year: int, month: int) -> list[Calculation]:
        filtered = []
        for calculation in self.calculations.list():
            try:
                calculation_date = datetime.fromisoformat(
                    calculation.get("created_at", "")
                )
                if calculation_date.year == year and calculation_date.month == month:
                    filtered.append(calculation)
            except ValueError, TypeError:
                continue
        filtered.reverse()
        return filtered

    def month_totals(self, year: int, month: int) -> dict[str, float]:
        calculations = self.month_calculations(year, month)
        return {
            key: sum(calculation.get(key, 0.0) for calculation in calculations)
            for key in INDICATOR_KEYS
        }

    def sum_month_totals(self, months: list[tuple[int, int]]) -> dict[str, float]:
        totals = {key: 0.0 for key in INDICATOR_KEYS}
        for year, month in months:
            month_totals = self.month_totals(year, month)
            for key in totals:
                totals[key] += month_totals[key]
        return totals

    def average_totals(self, months: list[tuple[int, int]]) -> dict[str, float]:
        if not months:
            return {key: 0.0 for key in INDICATOR_KEYS}
        totals = self.sum_month_totals(months)
        return {key: value / len(months) for key, value in totals.items()}

    def general_totals(self, months: list[tuple[int, int]]) -> dict[str, float]:
        if not months:
            return {key: 0.0 for key in INDICATOR_KEYS}
        totals = self.sum_month_totals(months)
        return {
            key: value if key == "fondo_local" else value / len(months)
            for key, value in totals.items()
        }
