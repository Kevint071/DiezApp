import json
import os

CONFLICTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pending_conflicts.json")


def load_conflicts() -> dict:
    """Load pending conflicts. Returns {"conflicts": [...], "pending_add": [...]}"""
    try:
        with open(CONFLICTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"conflicts": [], "pending_add": []}


def save_conflicts(conflicts: list, pending_add: list):
    data = {"conflicts": conflicts, "pending_add": pending_add}
    with open(CONFLICTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def clear_conflicts():
    if os.path.exists(CONFLICTS_FILE):
        os.remove(CONFLICTS_FILE)


def conflict_count() -> int:
    data = load_conflicts()
    return len(data.get("conflicts", []))
