import uuid
from datetime import UTC, datetime

from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.domain.repositories import CalculationRepository
from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)


class CreateCalculation:
    def __init__(
        self,
        repository: CalculationRepository,
        calculate_distribution: CalculateDistribution | None = None,
    ):
        self.repository = repository
        self.calculate_distribution = calculate_distribution or CalculateDistribution()

    def execute(self, amount: float, fund_percentage: int) -> Calculation:
        distribution = self.calculate_distribution.execute(amount, fund_percentage)
        calculation: Calculation = {
            "id": str(uuid.uuid4()),
            "created_at": datetime.now(UTC).astimezone().isoformat(),
            "amount": distribution.amount,
            "envio_21": distribution.envio_21,
            "restante": distribution.restante,
            "fondo_local": distribution.fondo_local,
            "sostenimiento": distribution.sostenimiento,
            "fund_percentage": fund_percentage,
            "updated_at": None,
        }
        calculations = self.repository.list()
        calculations.insert(0, calculation)
        self.repository.replace_all(calculations)
        return calculation
