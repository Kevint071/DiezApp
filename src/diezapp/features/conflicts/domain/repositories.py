from typing import Protocol

from diezapp.features.conflicts.domain.models import ConflictSet


class ConflictRepository(Protocol):
    def load(self, kind: str = "calculations") -> ConflictSet: ...

    def save(
        self,
        conflicts: list[dict],
        pending_add: list[dict],
        kind: str = "calculations",
    ) -> None: ...

    def clear(self, kind: str = "calculations") -> None: ...
