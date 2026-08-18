from diezapp.features.calculations.application.calculation_service import (
    CalculationService,
)
from diezapp.features.conflicts.application.conflict_service import ConflictService
from diezapp.features.notes.application.note_service import NoteService


class BackupImportService:
    def __init__(
        self,
        calculations_service: CalculationService,
        notes_service: NoteService,
        conflicts_service: ConflictService,
    ):
        self._calculations = calculations_service
        self._notes = notes_service
        self._conflicts = conflicts_service

    def import_data(
        self,
        calculations: list,
        notes: list,
        mode: str,
    ) -> dict[str, int]:
        result = {
            "calculations": 0,
            "notes": 0,
            "calculation_conflicts": 0,
            "note_conflicts": 0,
        }
        if calculations:
            result.update(self._import_calculations(calculations, mode))
        if notes:
            result.update(self._import_notes(notes, mode))
        return result

    def _import_calculations(self, imported: list, mode: str) -> dict[str, int]:
        if mode == "replace":
            self._calculations.replace_all(imported)
            return {"calculations": len(imported), "calculation_conflicts": 0}
        existing = self._calculations.list()
        existing_map = {item["id"]: item for item in existing if "id" in item}
        conflicts, to_add = [], []
        for item in imported:
            item_id = item.get("id")
            if item_id and item_id in existing_map:
                if self._conflicts.calculations_differ(existing_map[item_id], item):
                    conflicts.append(
                        {"existing": existing_map[item_id], "imported": item}
                    )
            else:
                to_add.append(item)
        if conflicts:
            self._conflicts.save(conflicts, to_add, kind="calculations")
        else:
            self._calculations.replace_all(existing + to_add)
        return {"calculations": len(to_add), "calculation_conflicts": len(conflicts)}

    def _import_notes(self, imported: list, mode: str) -> dict[str, int]:
        if mode == "replace":
            self._notes.replace_all(imported)
            return {"notes": len(imported), "note_conflicts": 0}
        existing = self._notes.list()
        existing_map = {item["id"]: item for item in existing if "id" in item}
        conflicts, to_add = [], []
        for item in imported:
            item_id = item.get("id")
            if item_id and item_id in existing_map:
                if self._conflicts.notes_differ(existing_map[item_id], item):
                    conflicts.append(
                        {"existing": existing_map[item_id], "imported": item}
                    )
            else:
                to_add.append(item)
        if conflicts:
            self._conflicts.save(conflicts, to_add, kind="notes")
        else:
            self._notes.replace_all(existing + to_add)
        return {"notes": len(to_add), "note_conflicts": len(conflicts)}
