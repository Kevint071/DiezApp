from typing import TypedDict


class Note(TypedDict):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str | None
