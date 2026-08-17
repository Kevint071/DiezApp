from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)


class InMemoryCalculationRepository:
    def __init__(self):
        self.calculations = []

    def list(self):
        return list(self.calculations)

    def add(self, calculation):
        self.calculations.insert(0, calculation)

    def replace_all(self, calculations):
        self.calculations = list(calculations)


def test_calculation_service_adds_calculated_distribution():
    repository = InMemoryCalculationRepository()
    calculation = CalculationService(repository).add(1000, 10)

    assert calculation["amount"] == 1000
    assert calculation["envio_21"] == 210
    assert calculation["fondo_local"] == 79
    assert calculation["sostenimiento"] == 711
    assert repository.list() == [calculation]
