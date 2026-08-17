from dataclasses import dataclass

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.notes.application.note_service import NoteService
from diezapp.features.settings.application.settings_service import SettingsService
from diezapp.infrastructure.persistence.sqlite_calculation_repository import (
    SqliteCalculationRepository,
)
from diezapp.infrastructure.persistence.sqlite_conflict_repository import (
    SqliteConflictRepository,
)
from diezapp.infrastructure.persistence.sqlite_note_repository import (
    SqliteNoteRepository,
)
from diezapp.infrastructure.persistence.sqlite_settings_repository import (
    SqliteSettingsRepository,
)


@dataclass(frozen=True)
class AppDependencies:
    calculations: CalculationService
    conflicts: ConflictService
    notes: NoteService
    settings: SettingsService


def create_dependencies() -> AppDependencies:
    calculation_repository = SqliteCalculationRepository()
    conflict_repository = SqliteConflictRepository()
    note_repository = SqliteNoteRepository()
    settings_repository = SqliteSettingsRepository()
    return AppDependencies(
        calculations=CalculationService(calculation_repository),
        conflicts=ConflictService(conflict_repository),
        notes=NoteService(note_repository),
        settings=SettingsService(settings_repository),
    )
