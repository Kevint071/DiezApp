from typing import ClassVar

from diezapp.features.calculations.domain.models import Calculation
from diezapp.infrastructure.database.connection import get_connection


class SqliteCalculationRepository:
    _columns: ClassVar[list[str]] = [
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

    def list(self) -> list[Calculation]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT id, created_at, amount, envio_21, restante, fondo_local, "
            "sostenimiento, fund_percentage, updated_at "
            "FROM calculations ORDER BY sort_index ASC"
        ).fetchall()
        return [dict(zip(self._columns, row, strict=True)) for row in rows]

    def add(self, calculation: Calculation) -> None:
        calculations = self.list()
        calculations.insert(0, calculation)
        self.replace_all(calculations)

    def replace_all(self, calculations: list[Calculation]) -> None:
        conn = get_connection()
        conn.execute("DELETE FROM calculations")
        for index, calculation in enumerate(calculations):
            conn.execute(
                "INSERT INTO calculations (id, created_at, amount, envio_21, "
                "restante, fondo_local, sostenimiento, fund_percentage, "
                "updated_at, sort_index) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    calculation.get("id"),
                    calculation.get("created_at"),
                    calculation.get("amount"),
                    calculation.get("envio_21"),
                    calculation.get("restante"),
                    calculation.get("fondo_local"),
                    calculation.get("sostenimiento"),
                    calculation.get("fund_percentage"),
                    calculation.get("updated_at"),
                    index,
                ),
            )
        conn.commit()
