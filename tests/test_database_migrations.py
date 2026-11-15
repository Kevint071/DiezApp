import sqlite3

import pytest

from diezapp.infrastructure.database.migrations import run_migrations


@pytest.mark.parametrize("version", [1, 2, 3, 4])
def test_migrations_upgrade_supported_schema_versions(version):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    connection.execute("CREATE TABLE notes (id TEXT PRIMARY KEY)")
    connection.execute("CREATE TABLE calculations (id TEXT PRIMARY KEY)")
    if version >= 2:
        connection.execute("ALTER TABLE notes ADD COLUMN updated_at TEXT")
    if version >= 3:
        connection.execute("ALTER TABLE calculations ADD COLUMN updated_at TEXT")

    run_migrations(connection)
    run_migrations(connection)

    current_version = connection.execute(
        "SELECT version FROM schema_version"
    ).fetchone()[0]
    note_columns = {row[1] for row in connection.execute("PRAGMA table_info(notes)")}
    calculation_columns = {
        row[1] for row in connection.execute("PRAGMA table_info(calculations)")
    }

    assert current_version == 6
    assert "updated_at" in note_columns
    assert "format" in note_columns
    assert "color" in note_columns
    assert "updated_at" in calculation_columns


def test_migration_6_keeps_the_notes_in_the_order_they_were_shown():
    # Before v6 the list was sorted by last edit; the stored order now rules.
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_version (version) VALUES (5)")
    connection.execute("CREATE TABLE calculations (id TEXT PRIMARY KEY)")
    connection.execute(
        "CREATE TABLE notes (id TEXT PRIMARY KEY, created_at TEXT, "
        "updated_at TEXT, sort_index INTEGER, format TEXT)"
    )
    connection.executemany(
        "INSERT INTO notes VALUES (?, ?, ?, ?, NULL)",
        [
            ("old", "2026-01-01", None, 0),
            ("edited", "2026-01-02", "2026-01-20", 1),
            ("new", "2026-01-10", None, 2),
        ],
    )

    run_migrations(connection)

    order = [
        row[0] for row in connection.execute("SELECT id FROM notes ORDER BY sort_index")
    ]
    assert order == ["edited", "new", "old"]
