import json
import os

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFLICTS_FILE = os.path.join(_BASE_DIR, "pending_conflicts.json")


def _conflicts_file(kind: str = "calculations") -> str:
    """Resolve the conflicts file path for a given data kind.

    Defaults to "calculations" and returns the original CONFLICTS_FILE path
    so existing behavior (and file location) is unchanged. Other kinds
    (e.g. "notes") get their own dedicated file.
    """
    if kind == "calculations":
        return CONFLICTS_FILE
    return os.path.join(_BASE_DIR, f"pending_conflicts_{kind}.json")


def load_conflicts(kind: str = "calculations") -> dict:
    """Load pending conflicts. Returns {"conflicts": [...], "pending_add": [...]}"""
    try:
        with open(_conflicts_file(kind), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"conflicts": [], "pending_add": []}


def save_conflicts(conflicts: list, pending_add: list, kind: str = "calculations"):
    data = {"conflicts": conflicts, "pending_add": pending_add}
    with open(_conflicts_file(kind), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clear_conflicts(kind: str = "calculations"):
    path = _conflicts_file(kind)
    if os.path.exists(path):
        os.remove(path)


def conflict_count(kind: str = "calculations") -> int:
    data = load_conflicts(kind)
    return len(data.get("conflicts", []))

