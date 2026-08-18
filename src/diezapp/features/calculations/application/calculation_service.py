from diezapp.features.calculations.application.create_calculation import (
    CreateCalculation,
)
from diezapp.features.calculations.application.delete_calculation import (
    DeleteCalculation,
)
from diezapp.features.calculations.application.update_calculation import (
    UpdateCalculation,
)
from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.domain.repositories import CalculationRepository


class CalculationService:
    def __init__(self, repository: CalculationRepository):
        self.repository = repository
        self.create = CreateCalculation(repository)
        self.update_calculation = UpdateCalculation(repository)
        self.delete_calculation = DeleteCalculation(repository)

    def add(self, amount: float, fund_percentage: int) -> Calculation:
        return self.create.execute(amount, fund_percentage)

    def list(self) -> list[Calculation]:
        return self.repository.list()

    def replace_all(self, calculations: list[Calculation]) -> None:
        self.repository.replace_all(calculations)

    def update(self, calculation_id: str, new_amount: float) -> Calculation | None:
        return self.update_calculation.execute(calculation_id, new_amount)

    def delete(self, calculation_id: str) -> bool:
        return self.delete_calculation.execute(calculation_id)
