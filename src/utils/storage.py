import uuid
from datetime import UTC, datetime

from diezapp.features.calculator.domain.calculator_service import (
    calculate_distribution,
)
from diezapp.infrastructure.persistence.sqlite_calculation_repository import (
    SqliteCalculationRepository,
)

_repository = SqliteCalculationRepository()


def load_calculations() -> list:
    return _repository.list()


def save_calculations(calculations: list):
    _repository.replace_all(calculations)


def add_calculation(
    amount: float,
    envio_21: float,
    restante: float,
    fondo_local: float,
    sostenimiento: float,
    fund_percentage: int,
) -> dict:
    calc = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now(UTC).astimezone().isoformat(),
        "amount": amount,
        "envio_21": envio_21,
        "restante": restante,
        "fondo_local": fondo_local,
        "sostenimiento": sostenimiento,
        "fund_percentage": fund_percentage,
        "updated_at": None,
    }
    calculations = load_calculations()
    calculations.insert(0, calc)
    save_calculations(calculations)
    return calc


def update_calculation(calc_id: str, new_amount: float) -> dict | None:
    calculations = load_calculations()
    for calc in calculations:
        if calc["id"] == calc_id:
            distribution = calculate_distribution(new_amount, calc["fund_percentage"])
            calc["amount"] = distribution.amount
            calc["envio_21"] = distribution.envio_21
            calc["restante"] = distribution.restante
            calc["fondo_local"] = distribution.fondo_local
            calc["sostenimiento"] = distribution.sostenimiento
            calc["updated_at"] = datetime.now(UTC).astimezone().isoformat()
            save_calculations(calculations)
            return calc
    return None


def delete_calculation(calc_id: str) -> bool:
    calculations = load_calculations()
    original_len = len(calculations)
    calculations = [c for c in calculations if c["id"] != calc_id]
    if len(calculations) < original_len:
        save_calculations(calculations)
        return True
    return False
