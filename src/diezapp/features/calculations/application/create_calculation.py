import uuid
from datetime import date, datetime

from diezapp.features.calculations.domain.models import Calculation
from diezapp.features.calculations.domain.repositories import CalculationRepository
from diezapp.features.calculator.application.calculate_distribution import (
    CalculateDistribution,
)
from diezapp.shared.datetime_utils import local_now, to_local_datetime, to_local_iso


class CreateCalculation:
    def __init__(
        self,
        repository: CalculationRepository,
        calculate_distribution: CalculateDistribution | None = None,
    ):
        self.repository = repository
        self.calculate_distribution = calculate_distribution or CalculateDistribution()

    def execute(
        self,
        amount: float,
        fund_percentage: int,
        calculation_date: date | None = None,
    ) -> Calculation:
        distribution = self.calculate_distribution.execute(amount, fund_percentage)
        created_at = self._created_at(calculation_date)
        calculation: Calculation = {
            "id": str(uuid.uuid4()),
            "created_at": to_local_iso(created_at),
            "amount": distribution.amount,
            "envio_21": distribution.envio_21,
            "restante": distribution.restante,
            "fondo_local": distribution.fondo_local,
            "sostenimiento": distribution.sostenimiento,
            "fund_percentage": fund_percentage,
            "updated_at": None,
        }
        calculations = self.repository.list()
        calculations.insert(self._insert_index(calculations, created_at), calculation)
        self.repository.replace_all(calculations)
        return calculation

    @staticmethod
    def _created_at(calculation_date: date | None) -> datetime:
        # The picked day keeps the current time so same-day entries stay ordered.
        now = local_now()
        if calculation_date is None:
            return now
        return now.replace(
            year=calculation_date.year,
            month=calculation_date.month,
            day=calculation_date.day,
        )

    @staticmethod
    def _insert_index(calculations: list[Calculation], created_at: datetime) -> int:
        """Keep the list newest-first when a back-dated calculation is saved."""
        for index, existing in enumerate(calculations):
            try:
                if to_local_datetime(existing.get("created_at", "")) <= created_at:
                    return index
            except ValueError, TypeError:
                continue
        return len(calculations)
