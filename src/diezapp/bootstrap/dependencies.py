from dataclasses import dataclass

from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.calculations.application.create_calculation import (
    CreateCalculation,
)
from diezapp.features.calculations.application.delete_calculation import (
    DeleteCalculation,
)
from diezapp.features.calculations.application.update_calculation import (
    UpdateCalculation,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.google_drive.application.backup_scheduler import BackupScheduler
from diezapp.features.google_drive.application.link_account import LinkAccountService
from diezapp.features.google_drive.application.url_opener import UrlOpener
from diezapp.features.google_drive.domain.repositories import BackupHistoryRepository
from diezapp.features.local_backup.application.local_backup_service import (
    LocalBackupService,
)
from diezapp.features.monthly_summary.domain.monthly_summary_service import (
    MonthlySummaryService,
)
from diezapp.features.notes.application.note_service import NoteService
from diezapp.features.pdf_export.application.pdf_export_service import PdfExportService
from diezapp.features.settings.application.settings_service import SettingsService
from diezapp.infrastructure.files.sqlite_backup_adapter import SqliteBackupAdapter
from diezapp.infrastructure.google.flet_url_opener import FletUrlOpener
from diezapp.infrastructure.pdf.pdf_generator import PdfGenerator
from diezapp.infrastructure.persistence.sqlite_backup_history_repository import (
    SqliteBackupHistoryRepository,
)
from diezapp.infrastructure.persistence.sqlite_calculation_repository import (
    SqliteCalculationRepository,
)
from diezapp.infrastructure.persistence.sqlite_conflict_repository import (
    SqliteConflictRepository,
)
from diezapp.infrastructure.persistence.sqlite_drive_account_repository import (
    SqliteDriveAccountRepository,
)
from diezapp.infrastructure.persistence.sqlite_note_repository import (
    SqliteNoteRepository,
)
from diezapp.infrastructure.persistence.sqlite_settings_repository import (
    SqliteSettingsRepository,
)
from utils.gdrive_backup import get_interval_seconds, get_last_backup_at


@dataclass(frozen=True)
class AppDependencies:
    calculations: CalculationService
    create_calculation: CreateCalculation
    delete_calculation: DeleteCalculation
    update_calculation: UpdateCalculation
    conflicts: ConflictService
    google_drive_history: BackupHistoryRepository
    google_drive_link: LinkAccountService
    google_drive_scheduler: BackupScheduler
    google_drive_url_opener: UrlOpener
    local_backup: LocalBackupService
    monthly_summary: MonthlySummaryService
    notes: NoteService
    pdf_export: PdfExportService
    settings: SettingsService


def create_dependencies() -> AppDependencies:
    calculation_repository = SqliteCalculationRepository()
    conflict_repository = SqliteConflictRepository()
    drive_account_repository = SqliteDriveAccountRepository()
    backup_history_repository = SqliteBackupHistoryRepository()
    backup_adapter = SqliteBackupAdapter()
    note_repository = SqliteNoteRepository()
    settings_repository = SqliteSettingsRepository()
    pdf_generator = PdfGenerator()
    monthly_summary = MonthlySummaryService(calculation_repository)
    calculations = CalculationService(calculation_repository)
    return AppDependencies(
        calculations=calculations,
        create_calculation=calculations.create,
        delete_calculation=calculations.delete_calculation,
        update_calculation=calculations.update_calculation,
        conflicts=ConflictService(conflict_repository),
        google_drive_history=backup_history_repository,
        google_drive_link=LinkAccountService(drive_account_repository),
        google_drive_scheduler=BackupScheduler(
            get_interval_seconds,
            get_last_backup_at,
        ),
        google_drive_url_opener=FletUrlOpener(),
        local_backup=LocalBackupService(backup_adapter),
        monthly_summary=monthly_summary,
        notes=NoteService(note_repository),
        pdf_export=PdfExportService(pdf_generator),
        settings=SettingsService(settings_repository),
    )
