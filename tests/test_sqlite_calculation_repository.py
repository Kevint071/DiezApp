from diezapp.infrastructure.persistence.sqlite_calculation_repository import (
    SqliteCalculationRepository,
)


def calculation(calculation_id: str, amount: float) -> dict:
    return {
        "id": calculation_id,
        "created_at": f"2026-08-17T10:00:0{calculation_id}Z",
        "amount": amount,
        "envio_21": amount * 0.21,
        "restante": amount * 0.79,
        "fondo_local": amount * 0.1,
        "sostenimiento": amount * 0.69,
        "fund_percentage": 10,
        "updated_at": None,
    }


def test_sqlite_calculation_repository_round_trips_and_preserves_order():
    repository = SqliteCalculationRepository()
    first = calculation("1", 1000)
    second = calculation("2", 2000)

    repository.replace_all([first, second])

    assert repository.list() == [first, second]

    repository.add(calculation("3", 3000))

    assert [item["id"] for item in repository.list()] == ["3", "1", "2"]
