import os
import sqlite3
import threading

from diezapp.infrastructure.database.schema import initialize_schema

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.getenv("FLET_APP_STORAGE_DATA", _BASE_DIR)
os.makedirs(_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, "app.db")

_conn = None
_lock = threading.RLock()


def get_connection():
    """Return the process-wide singleton connection to the local database."""
    global _conn
    with _lock:
        if _conn is None:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _apply_pragmas(conn)
            initialize_schema(conn)
            _conn = conn
        return _conn


def _apply_pragmas(conn):
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -20000")
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA foreign_keys = ON")


def get_setting(key: str, default: str | None = None) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row is not None else default


def set_setting(key: str, value: str) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
