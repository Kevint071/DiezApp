import uuid
from datetime import UTC, datetime

from diezapp.features.calculations.domain.repositories import CalculationRepository
from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)


class CalculationService:
    def __init__(self, repository: CalculationRepository):
        self.repository = repository

    def add(self, amount: float, fund_percentage: int) -> dict:
        distribution = calculate_distribution(amount, fund_percentage)
        calculation = {
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

    def list(self) -> list[dict]:
        return self.repository.list()

    def update(self, calculation_id: str, new_amount: float) -> dict | None:
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

    def delete(self, calculation_id: str) -> bool:
        calculations = self.repository.list()
        remaining = [
            calculation
            for calculation in calculations
            if calculation["id"] != calculation_id
        ]
        if len(remaining) == len(calculations):
            return False
        self.repository.replace_all(remaining)
        return True
