from diezapp.infrastructure.database.migrations import run_migrations


def initialize_schema(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
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
            updated_at TEXT,
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
            updated_at TEXT,
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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS gdrive_accounts (
            id TEXT PRIMARY KEY,
            google_account_email TEXT,
            display_label TEXT,
            folder_id TEXT,
            folder_name TEXT,
            access_token TEXT,
            refresh_token TEXT,
            token_expiry_at TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS backup_history (
            id TEXT PRIMARY KEY,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            details TEXT
        )
        """
    )
    conn.commit()
    run_migrations(conn)
