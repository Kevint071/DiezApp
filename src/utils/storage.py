import json
import os
import uuid
import tempfile
from datetime import datetime


CALCULATIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_calculations.json")


def load_calculations() -> list:
    try:
        with open(CALCULATIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("calculations", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_calculations(calculations: list):
    data = {"calculations": calculations}
    dir_name = os.path.dirname(CALCULATIONS_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, CALCULATIONS_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


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
