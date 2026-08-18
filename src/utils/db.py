from diezapp.infrastructure.database import connection


def get_connection():
    return connection.get_connection()


def get_setting(key: str, default: str | None = None) -> str | None:
    return connection.get_setting(key, default)


def set_setting(key: str, value: str) -> None:
    connection.set_setting(key, value)
