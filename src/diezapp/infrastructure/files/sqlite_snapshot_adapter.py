import os
import sqlite3
import tempfile

from diezapp.infrastructure.database.connection import get_connection
from diezapp.shared.datetime_utils import local_now


class SqliteSnapshotAdapter:
    def create_snapshot(self) -> str:
        file_name = local_now().strftime("backup_%Y%m%d_%H%M%S.db")
        destination = os.path.join(tempfile.gettempdir(), file_name)
        source = get_connection()
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
        return destination
