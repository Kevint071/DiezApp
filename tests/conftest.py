import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Point the singleton DB connection at a throwaway file for each test."""
    from diezapp.infrastructure.database import connection

    connection.DB_PATH = str(tmp_path / "app.db")
    connection._conn = None
    yield
    if connection._conn is not None:
        connection._conn.close()
    connection._conn = None
