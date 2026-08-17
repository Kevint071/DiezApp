from diezapp.features.conflicts.application.conflict_service import (
    ConflictService,
    calcs_differ,
    notes_differ,
)
from diezapp.infrastructure.persistence.sqlite_conflict_repository import (
    SqliteConflictRepository,
)

__all__ = [
    "calcs_differ",
    "clear_conflicts",
    "conflict_count",
    "load_conflicts",
    "notes_differ",
    "save_conflicts",
]

_service = ConflictService(SqliteConflictRepository())


def load_conflicts(kind: str = "calculations") -> dict:
    """Load pending conflicts. Returns {"conflicts": [...], "pending_add": [...]}"""
    return _service.load(kind)


def save_conflicts(conflicts: list, pending_add: list, kind: str = "calculations"):
    _service.save(conflicts, pending_add, kind)


def clear_conflicts(kind: str = "calculations"):
    _service.clear(kind)


def conflict_count(kind: str = "calculations") -> int:
    return _service.count(kind)
