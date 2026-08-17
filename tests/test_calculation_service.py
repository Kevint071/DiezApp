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


def test_calculation_service_updates_distribution():
    repository = InMemoryCalculationRepository()
    service = CalculationService(repository)
    calculation = service.add(1000, 10)

    updated = service.update(calculation["id"], 2000)

    assert updated["amount"] == 2000
    assert updated["envio_21"] == 420
    assert updated["fondo_local"] == 158
    assert updated["sostenimiento"] == 1422


def test_calculation_service_deletes_existing_calculation():
    repository = InMemoryCalculationRepository()
    service = CalculationService(repository)
    calculation = service.add(1000, 10)

    assert service.delete(calculation["id"]) is True
    assert repository.list() == []
    assert service.delete(calculation["id"]) is False
