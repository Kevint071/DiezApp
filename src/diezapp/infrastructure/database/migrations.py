SCHEMA_VERSION = 6


def run_migrations(conn):
    """Apply pending schema migrations in order, tracking the schema version."""
    row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    current = max(row[0] if row is not None else 0, 1)

    if current < 2:
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()
        }
        if "updated_at" not in existing_cols:
            conn.execute("ALTER TABLE notes ADD COLUMN updated_at TEXT")
        current = 2

    if current < 3:
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(calculations)").fetchall()
        }
        if "updated_at" not in existing_cols:
            conn.execute("ALTER TABLE calculations ADD COLUMN updated_at TEXT")
        current = 3

    if current < 4:
        current = max(current, 4)

    if current < 5:
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()
        }
        if "format" not in existing_cols:
            conn.execute("ALTER TABLE notes ADD COLUMN format TEXT")
        current = 5

    if current < 6:
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(notes)").fetchall()
        }
        if "color" not in existing_cols:
            conn.execute("ALTER TABLE notes ADD COLUMN color TEXT")
        if "sort_index" in existing_cols:
            _order_notes_by_recency(conn, existing_cols)
        current = 6

    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (current,))
    else:
        conn.execute("UPDATE schema_version SET version = ?", (current,))
    conn.commit()


def _order_notes_by_recency(conn, columns: set[str]) -> None:
    """Notes used to be listed by last edit; now the stored order is the
    order shown (and the user can change it). Start from what they saw."""
    dates = [name for name in ("updated_at", "created_at") if name in columns]
    recency = f"COALESCE({', '.join(dates)}, '')" if dates else "''"
    rows = conn.execute(
        f"SELECT id FROM notes ORDER BY {recency} DESC, sort_index ASC"
    ).fetchall()
    for index, (note_id,) in enumerate(rows):
        conn.execute("UPDATE notes SET sort_index = ? WHERE id = ?", (index, note_id))
