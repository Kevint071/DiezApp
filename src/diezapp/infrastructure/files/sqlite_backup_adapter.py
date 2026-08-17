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
    "updated_at",
]
NOTE_COLUMNS = ["id", "title", "content", "created_at", "updated_at"]


class SqliteBackupAdapter:
    def export_calculations(self, path: str, calculations: list) -> None:
        with sqlite3.connect(path) as conn:
            conn.execute("DROP TABLE IF EXISTS calculations")
            conn.execute(
                "CREATE TABLE calculations ("
                "id TEXT PRIMARY KEY, created_at TEXT, amount REAL, envio_21 REAL, "
                "restante REAL, fondo_local REAL, sostenimiento REAL, "
                "fund_percentage INTEGER, updated_at TEXT)"
            )
            for calculation in calculations:
                conn.execute(
                    "INSERT INTO calculations (id, created_at, amount, envio_21, "
                    "restante, fondo_local, sostenimiento, fund_percentage, "
                    "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    tuple(calculation.get(column) for column in CALC_COLUMNS),
                )

    def export_notes(self, path: str, notes: list) -> None:
        with sqlite3.connect(path) as conn:
            conn.execute("DROP TABLE IF EXISTS notes")
            conn.execute(
                "CREATE TABLE notes (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
                "created_at TEXT, updated_at TEXT)"
            )
            for note in notes:
                conn.execute(
                    "INSERT INTO notes (id, title, content, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        note.get("id"),
                        note.get("title", ""),
                        note.get("content"),
                        note.get("created_at"),
                        note.get("updated_at"),
                    ),
                )

    def read_calculations(self, path: str) -> list:
        try:
            with sqlite3.connect(path) as conn:
                columns = {
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(calculations)"
                    ).fetchall()
                }
                updated_at = "updated_at" if "updated_at" in columns else "NULL"
                rows = conn.execute(
                    "SELECT id, created_at, amount, envio_21, restante, fondo_local, "
                    f"sostenimiento, fund_percentage, {updated_at} FROM calculations"
                ).fetchall()
        except Exception as exc:
            raise ValueError("Archivo de respaldo inválido") from exc
        return [dict(zip(CALC_COLUMNS, row, strict=True)) for row in rows]

    def read_notes(self, path: str) -> list:
        try:
            with sqlite3.connect(path) as conn:
                columns = {
                    row[1]
                    for row in conn.execute("PRAGMA table_info(notes)").fetchall()
                }
                updated_at = "updated_at" if "updated_at" in columns else "NULL"
                rows = conn.execute(
                    f"SELECT id, title, content, created_at, {updated_at} FROM notes"
                ).fetchall()
        except Exception as exc:
            raise ValueError("Archivo de respaldo inválido") from exc
        return [dict(zip(NOTE_COLUMNS, row, strict=True)) for row in rows]
