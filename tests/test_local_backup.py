import sqlite3

import pytest
from diezapp.features.local_backup.application.local_backup_service import (
    LocalBackupService,
)
from diezapp.infrastructure.files.sqlite_backup_adapter import SqliteBackupAdapter


def test_local_backup_round_trip(tmp_path):
    path = str(tmp_path / "backup.db")
    calculations = [
        {
            "id": "calc-1",
            "created_at": "2026-08-17T10:00:00+00:00",
            "amount": 100,
            "envio_21": 21,
            "restante": 79,
            "fondo_local": 1,
            "sostenimiento": 2,
            "fund_percentage": 1,
            "updated_at": None,
        }
    ]
    notes = [
        {
            "id": "note-1",
            "title": "Lista",
            "content": "Pan",
            "created_at": "2026-08-17T10:00:00+00:00",
            "updated_at": None,
        }
    ]
    service = LocalBackupService(SqliteBackupAdapter())

    service.export_calculations(path, calculations)
    service.export_notes(path, notes)

    assert service.read_calculations(path) == calculations
    assert service.read_notes(path) == notes


def test_local_backup_rejects_invalid_file(tmp_path):
    path = tmp_path / "invalid.db"
    path.write_text("not a sqlite backup", encoding="utf-8")

    with pytest.raises(ValueError, match="Archivo de respaldo inválido"):
        SqliteBackupAdapter().read_notes(str(path))


def test_local_backup_accepts_old_schema_without_updated_at(tmp_path):
    path = str(tmp_path / "old.db")
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE notes (id TEXT PRIMARY KEY, title TEXT, content TEXT, "
            "created_at TEXT)"
        )
        conn.execute(
            "INSERT INTO notes VALUES (?, ?, ?, ?)",
            ("note-1", "Antigua", "Contenido", "2025-01-01"),
        )

    notes = SqliteBackupAdapter().read_notes(path)

    assert notes == [
        {
            "id": "note-1",
            "title": "Antigua",
            "content": "Contenido",
            "created_at": "2025-01-01",
            "updated_at": None,
        }
    ]
