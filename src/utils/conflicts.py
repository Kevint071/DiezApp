import json

from utils.db import get_connection

CALC_DIFF_FIELDS = ["amount", "envio_21", "restante", "fondo_local", "sostenimiento", "fund_percentage"]
NOTE_DIFF_FIELDS = ["title", "content"]


def calcs_differ(a: dict, b: dict) -> bool:
    return any(a.get(k) != b.get(k) for k in CALC_DIFF_FIELDS)


def notes_differ(a: dict, b: dict) -> bool:
    return any(a.get(k) != b.get(k) for k in NOTE_DIFF_FIELDS)


def load_conflicts(kind: str = "calculations") -> dict:
    """Load pending conflicts. Returns {"conflicts": [...], "pending_add": [...]}"""
    conn = get_connection()
    row = conn.execute(
        "SELECT payload FROM pending_conflicts WHERE kind = ?", (kind,)
    ).fetchone()
    if row is None:
        return {"conflicts": [], "pending_add": []}
    try:
        return json.loads(row[0])
    except (json.JSONDecodeError, TypeError):
        return {"conflicts": [], "pending_add": []}


def save_conflicts(conflicts: list, pending_add: list, kind: str = "calculations"):
    conn = get_connection()
    payload = json.dumps({"conflicts": conflicts, "pending_add": pending_add}, ensure_ascii=False)
    conn.execute(
        "INSERT INTO pending_conflicts (kind, payload) VALUES (?, ?) "
        "ON CONFLICT(kind) DO UPDATE SET payload = excluded.payload",
        (kind, payload),
    )
    conn.commit()


def clear_conflicts(kind: str = "calculations"):
    conn = get_connection()
    conn.execute("DELETE FROM pending_conflicts WHERE kind = ?", (kind,))
    conn.commit()


def conflict_count(kind: str = "calculations") -> int:
    data = load_conflicts(kind)
    return len(data.get("conflicts", []))

