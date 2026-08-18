SCHEMA_VERSION = 4


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

    if row is None:
        conn.execute("INSERT INTO schema_version (version) VALUES (?)", (current,))
    else:
        conn.execute("UPDATE schema_version SET version = ?", (current,))
    conn.commit()
