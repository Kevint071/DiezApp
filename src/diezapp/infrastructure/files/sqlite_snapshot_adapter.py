import os
import sqlite3
import tempfile
from datetime import UTC, datetime

from utils.db import get_connection


class SqliteSnapshotAdapter:
    def create_snapshot(self) -> str:
        file_name = datetime.now(UTC).strftime("backup_%Y%m%d_%H%M%S.db")
        destination = os.path.join(tempfile.gettempdir(), file_name)
        source = get_connection()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
        return destination
