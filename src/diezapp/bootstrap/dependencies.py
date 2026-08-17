from dataclasses import dataclass

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.infrastructure.persistence.sqlite_calculation_repository import (
    SqliteCalculationRepository,
)


@dataclass(frozen=True)
class AppDependencies:
    calculations: CalculationService


def create_dependencies() -> AppDependencies:
    calculation_repository = SqliteCalculationRepository()
    return AppDependencies(
        calculations=CalculationService(calculation_repository),
    )
