import pytest


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    """Point the singleton DB connection at a throwaway file for each test."""
    from utils import db

    db.DB_PATH = str(tmp_path / "app.db")
    db._conn = None
    yield
    if db._conn is not None:
        db._conn.close()
    db._conn = None
