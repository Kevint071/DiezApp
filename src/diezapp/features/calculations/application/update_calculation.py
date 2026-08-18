from datetime import UTC, datetime

from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.domain.repositories import CalculationRepository
from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)


class UpdateCalculation:
    def __init__(self, repository: CalculationRepository):
        self.repository = repository

    def execute(self, calculation_id: str, new_amount: float) -> Calculation | None:
        calculations = self.repository.list()
        for calculation in calculations:
            if calculation["id"] != calculation_id:
                continue
            distribution = calculate_distribution(
                new_amount, calculation["fund_percentage"]
            )
            calculation.update(
                {
                    "amount": distribution.amount,
                    "envio_21": distribution.envio_21,
                    "restante": distribution.restante,
                    "fondo_local": distribution.fondo_local,
                    "sostenimiento": distribution.sostenimiento,
                    "updated_at": datetime.now(UTC).astimezone().isoformat(),
                }
            )
            self.repository.replace_all(calculations)
            return calculation
        return None
