"""Central local database module (single SQLite file via the stdlib ``sqlite3``).

All local app data (calculations, notes, settings and pending import
conflicts) lives in ONE local file: ``src/app.db``. Every other module must
go through the connection returned by ``get_connection()`` — no module
should open its own local ``.db`` file.

The database starts empty on first launch. Legacy ``saved_calculations.json``,
``notes.json`` and ``settings.json`` files are intentionally NOT read, imported,
renamed or deleted.

Uses the Python standard library ``sqlite3`` module — no external dependency.
Everything is 100% local — there is no cloud sync layer. PRAGMAs are tuned
for a local-only, single-process desktop/mobile app (WAL journaling,
NORMAL synchronous durability, and a larger page cache).

Only ONE connection to ``app.db`` ever exists for the life of the process
(this module's singleton).
"""

import os
import sqlite3
import threading

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # src/
DB_PATH = os.path.join(_BASE_DIR, "app.db")

# Bump when the schema changes and add a migration branch in run_migrations().
SCHEMA_VERSION = 1

_conn = None
_lock = threading.RLock()


def get_connection():
    """Return the process-wide singleton connection to the local database."""
    global _conn
    with _lock:
        if _conn is None:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _apply_pragmas(conn)
            _init_schema(conn)
            _conn = conn
        return _conn


def _apply_pragmas(conn):
    """Tune SQLite for a local-only, single-process app."""
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -20000")  # ~20 MB page cache
    conn.execute("PRAGMA temp_store = MEMORY")
    conn.execute("PRAGMA foreign_keys = ON")


def _init_schema(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS calculations (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            amount REAL,
            envio_21 REAL,
            restante REAL,
            fondo_local REAL,
            sostenimiento REAL,
            fund_percentage INTEGER,
            sort_index INTEGER
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS notes (
            id TEXT PRIMARY KEY,
            title TEXT,
            content TEXT,
            created_at TEXT,
            sort_index INTEGER
        )
        """
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS pending_conflicts (kind TEXT PRIMARY KEY, payload TEXT)"
    )
    conn.commit()
    run_migrations(conn)


def run_migrations(conn):
    """Apply pending schema migrations in order, tracking ``schema_version``."""
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    current = row[0] if row is not None else 0

    current = max(current, 1)

    # Future migrations go here:
    #   if current < 2: ...; current = 2

    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (current,))
    else:
        conn.execute("UPDATE schema_version SET version = ?", (current,))
    conn.commit()


# ── Simple key/value settings helpers ──────────────────────────────

def get_setting(key: str, default: str | None = None) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row is not None else default


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
    conn.commit()
