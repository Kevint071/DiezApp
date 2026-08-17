from typing import Protocol


class CalculationRepository(Protocol):
    def list(self) -> list[dict]: ...

    def replace_all(self, calculations: list[dict]) -> None: ...
