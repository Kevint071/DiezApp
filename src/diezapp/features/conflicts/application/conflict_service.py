from diezapp.features.conflicts.domain.models import ConflictSet
from diezapp.features.conflicts.domain.repositories import ConflictRepository

CALC_DIFF_FIELDS = [
    "amount",
    "envio_21",
    "restante",
    "fondo_local",
    "sostenimiento",
    "fund_percentage",
]
NOTE_DIFF_FIELDS = ["title", "content"]


def calcs_differ(first: dict, second: dict) -> bool:
    return any(first.get(key) != second.get(key) for key in CALC_DIFF_FIELDS)


def notes_differ(first: dict, second: dict) -> bool:
    return any(first.get(key) != second.get(key) for key in NOTE_DIFF_FIELDS)


class ConflictService:
    def __init__(self, repository: ConflictRepository):
        self.repository = repository

    def load(self, kind: str = "calculations") -> ConflictSet:
        return self.repository.load(kind)

    def save(
        self,
        conflicts: list[dict],
        pending_add: list[dict],
        kind: str = "calculations",
    ) -> None:
        self.repository.save(conflicts, pending_add, kind)

    def clear(self, kind: str = "calculations") -> None:
        self.repository.clear(kind)

    def count(self, kind: str = "calculations") -> int:
        return len(self.load(kind)["conflicts"])