from dataclasses import dataclass

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.notes.application.note_service import NoteService
from diezapp.infrastructure.persistence.sqlite_calculation_repository import (
    SqliteCalculationRepository,
)
from diezapp.infrastructure.persistence.sqlite_note_repository import (
    SqliteNoteRepository,
)


@dataclass(frozen=True)
class AppDependencies:
    calculations: CalculationService
    notes: NoteService


def create_dependencies() -> AppDependencies:
    calculation_repository = SqliteCalculationRepository()
    note_repository = SqliteNoteRepository()
    return AppDependencies(
        calculations=CalculationService(calculation_repository),
        notes=NoteService(note_repository),
    )
