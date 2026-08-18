from diezapp.features.calculations.application.create_calculation import (
    CreateCalculation,
)
from diezapp.features.calculations.application.delete_calculation import (
    DeleteCalculation,
)
from diezapp.features.calculations.application.update_calculation import (
    UpdateCalculation,
)


class InMemoryCalculationRepository:
    def __init__(self, calculations=None):
        self.calculations = list(calculations or [])

    def list(self):
        return list(self.calculations)

    def add(self, calculation):
        self.calculations.insert(0, calculation)

    def replace_all(self, calculations):
        self.calculations = list(calculations)


def test_create_calculation_persists_distribution_at_the_front():
    repository = InMemoryCalculationRepository()
    use_case = CreateCalculation(repository)

    calculation = use_case.execute(1000, 10)

    assert calculation["amount"] == 1000
    assert calculation["envio_21"] == 210
    assert calculation["fondo_local"] == 79
    assert calculation["sostenimiento"] == 711
    assert calculation["fund_percentage"] == 10
    assert calculation["updated_at"] is None
    assert repository.list() == [calculation]


def test_update_calculation_recalculates_using_existing_percentage():
    repository = InMemoryCalculationRepository()
    calculation = CreateCalculation(repository).execute(1000, 10)

    updated = UpdateCalculation(repository).execute(calculation["id"], 2000)

    assert updated["amount"] == 2000
    assert updated["envio_21"] == 420
    assert updated["fondo_local"] == 158
    assert updated["sostenimiento"] == 1422
    assert updated["fund_percentage"] == 10
    assert updated["updated_at"] is not None


def test_update_calculation_returns_none_for_unknown_id():
    repository = InMemoryCalculationRepository()

    assert UpdateCalculation(repository).execute("missing", 2000) is None


def test_delete_calculation_removes_existing_calculation():
    repository = InMemoryCalculationRepository()
    calculation = CreateCalculation(repository).execute(1000, 10)

    assert DeleteCalculation(repository).execute(calculation["id"]) is True
    assert repository.list() == []


def test_delete_calculation_returns_false_for_unknown_id():
    repository = InMemoryCalculationRepository()

    assert DeleteCalculation(repository).execute("missing") is False
