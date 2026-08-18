import os
import sqlite3

from diezapp.infrastructure.files.sqlite_snapshot_adapter import SqliteSnapshotAdapter
from utils.db import get_connection


def test_snapshot_contains_current_database_data():
    connection = get_connection()
    connection.execute("CREATE TABLE snapshot_probe (value TEXT)")
    connection.execute("INSERT INTO snapshot_probe VALUES (?)", ("present",))
    connection.commit()

    path = SqliteSnapshotAdapter().create_snapshot()
    try:
        snapshot = sqlite3.connect(path)
        try:
            row = snapshot.execute("SELECT value FROM snapshot_probe").fetchone()
        finally:
            snapshot.close()
        assert row == ("present",)
    finally:
        os.unlink(path)
