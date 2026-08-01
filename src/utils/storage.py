import uuid
from datetime import datetime

from utils.db import get_connection


_COLUMNS = [
    "id",
    "created_at",
    "amount",
    "envio_21",
    "restante",
    "fondo_local",
    "sostenimiento",
    "fund_percentage",
]


def load_calculations() -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, created_at, amount, envio_21, restante, fondo_local, "
        "sostenimiento, fund_percentage FROM calculations ORDER BY sort_index ASC"
    ).fetchall()
    return [dict(zip(_COLUMNS, row)) for row in rows]


def save_calculations(calculations: list):
    conn = get_connection()
    conn.execute("DELETE FROM calculations")
    for i, calc in enumerate(calculations):
        conn.execute(
            "INSERT INTO calculations (id, created_at, amount, envio_21, restante, "
            "fondo_local, sostenimiento, fund_percentage, sort_index) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                calc.get("id"),
                calc.get("created_at"),
                calc.get("amount"),
                calc.get("envio_21"),
                calc.get("restante"),
                calc.get("fondo_local"),
                calc.get("sostenimiento"),
                calc.get("fund_percentage"),
                i,
            ),
        )
    conn.commit()


def add_calculation(amount: float, envio_21: float, restante: float, fondo_local: float, sostenimiento: float, fund_percentage: int) -> dict:
    calc = {
        "id": str(uuid.uuid4()),
        "created_at": datetime.now().isoformat(),
        "amount": amount,
        "envio_21": envio_21,
        "restante": restante,
        "fondo_local": fondo_local,
        "sostenimiento": sostenimiento,
        "fund_percentage": fund_percentage,
    }
    calculations = load_calculations()
    calculations.insert(0, calc)
    save_calculations(calculations)
    return calc


def update_calculation(calc_id: str, new_amount: float) -> dict | None:
    calculations = load_calculations()
    for calc in calculations:
        if calc["id"] == calc_id:
            calc["amount"] = new_amount
            calc["envio_21"] = new_amount * 0.21
            calc["restante"] = new_amount * 0.79
            calc["fondo_local"] = calc["restante"] * (calc["fund_percentage"] / 100)
            calc["sostenimiento"] = new_amount - calc["envio_21"] - calc["fondo_local"]
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
