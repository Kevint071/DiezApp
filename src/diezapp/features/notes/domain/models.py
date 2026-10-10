from typing import NotRequired, TypedDict


class Note(TypedDict):
    id: str
    title: str
    content: str
    created_at: str
    updated_at: str | None
    # Rich body as a Quill Delta in JSON (see note_document); None when plain.
    format: NotRequired[str | None]
