from datetime import datetime


def local_now() -> datetime:
    return datetime.now().astimezone()


def to_local_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return value.astimezone().isoformat()


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


def to_local_datetime(value: str) -> datetime:
    return parse_datetime(value).astimezone()
