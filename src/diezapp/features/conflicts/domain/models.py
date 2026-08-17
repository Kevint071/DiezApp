from typing import TypedDict


class Conflict(TypedDict):
    existing: dict
    imported: dict


class ConflictSet(TypedDict):
    conflicts: list[Conflict]
    pending_add: list[dict]