from typing import Protocol

from diezapp.features.calculations.domain.models import Calculation


class CalculationRepository(Protocol):
    def list(self) -> list[Calculation]: ...

    def add(self, calculation: Calculation) -> None: ...

    def replace_all(self, calculations: list[Calculation]) -> None: ...
