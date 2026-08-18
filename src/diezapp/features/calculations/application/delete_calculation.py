from diezapp.features.calculations.domain.repositories import CalculationRepository


class DeleteCalculation:
    def __init__(self, repository: CalculationRepository):
        self.repository = repository

    def execute(self, calculation_id: str) -> bool:
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
