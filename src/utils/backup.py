"""Read/write helpers for backup files exchanged via export/import.

These are standalone, one-off SQLite (`.db`) files generated on demand for
sharing or importing. They are SEPARATE from the app's single local database
(`app.db`) and are never opened through ``utils.db``.
"""

import sqlite3

CALC_COLUMNS = [
    "id",
    "created_at",
    "amount",
    "envio_21",
    "restante",
    "fondo_local",
    "sostenimiento",
    "fund_percentage",
]

NOTE_COLUMNS = ["id", "title", "content", "created_at"]


def export_calculations(path: str, calculations: list):
    conn = sqlite3.connect(path)
    conn.execute("DROP TABLE IF EXISTS calculations")
    conn.execute(
        "CREATE TABLE calculations ("
        "id TEXT PRIMARY KEY, created_at TEXT, amount REAL, envio_21 REAL, "
        "restante REAL, fondo_local REAL, sostenimiento REAL, fund_percentage INTEGER)"
    )
    for calc in calculations:
        conn.execute(
            "INSERT INTO calculations (id, created_at, amount, envio_21, restante, "
            "fondo_local, sostenimiento, fund_percentage) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            tuple(calc.get(col) for col in CALC_COLUMNS),
        )
    conn.commit()


def export_notes(path: str, notes: list):
    conn = sqlite3.connect(path)
    conn.execute("DROP TABLE IF EXISTS notes")
    conn.execute(
        "CREATE TABLE notes (id TEXT PRIMARY KEY, title TEXT, content TEXT, created_at TEXT)"
    )
    for note in notes:
        conn.execute(
            "INSERT INTO notes (id, title, content, created_at) VALUES (?, ?, ?, ?)",
            (
                note.get("id"),
                note.get("title", ""),
                note.get("content"),
                note.get("created_at"),
            ),
        )
    conn.commit()


def read_calculations(path: str) -> list:
    """Read calculations from a backup `.db`. Raises ValueError if invalid."""
    try:
        conn = sqlite3.connect(path)
        rows = conn.execute(
            "SELECT id, created_at, amount, envio_21, restante, fondo_local, "
            "sostenimiento, fund_percentage FROM calculations"
        ).fetchall()
    except Exception as exc:
        raise ValueError("Archivo de respaldo inválido") from exc
    return [dict(zip(CALC_COLUMNS, row)) for row in rows]


def read_notes(path: str) -> list:
    """Read notes from a backup `.db`. Raises ValueError if invalid."""
    try:
        conn = sqlite3.connect(path)
        rows = conn.execute(
            "SELECT id, title, content, created_at FROM notes"
        ).fetchall()
    except Exception as exc:
        raise ValueError("Archivo de respaldo inválido") from exc
    return [dict(zip(NOTE_COLUMNS, row)) for row in rows]
