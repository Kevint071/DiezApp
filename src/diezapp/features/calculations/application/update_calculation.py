from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.domain.repositories import CalculationRepository
from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)
from diezapp.shared.datetime_utils import local_now, to_local_iso


class UpdateCalculation:
    def __init__(
        self,
        repository: CalculationRepository,
        calculate_distribution: CalculateDistribution | None = None,
    ):
        self.repository = repository
        self.calculate_distribution = calculate_distribution or CalculateDistribution()

    def execute(self, calculation_id: str, new_amount: float) -> Calculation | None:
        calculations = self.repository.list()
        for calculation in calculations:
            if calculation["id"] != calculation_id:
                continue
            distribution = self.calculate_distribution.execute(
                new_amount, calculation["fund_percentage"]
            )
            calculation.update(
                {
                    "amount": distribution.amount,
                    "envio_21": distribution.envio_21,
                    "restante": distribution.restante,
                    "fondo_local": distribution.fondo_local,
                    "sostenimiento": distribution.sostenimiento,
                    "updated_at": to_local_iso(local_now()),
                }
            )
            self.repository.replace_all(calculations)
            return calculation
        return None
