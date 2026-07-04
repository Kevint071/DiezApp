import json
import os
import uuid
import tempfile
from datetime import datetime


NOTES_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "notes.json")


def load_notes() -> list:
    try:
        with open(NOTES_FILE, "r") as f:
            data = json.load(f)
            return data.get("notes", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_notes(notes: list):
    data = {"notes": notes}
    dir_name = os.path.dirname(NOTES_FILE)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, NOTES_FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def add_note(content: str) -> dict:
    note = {
        "id": str(uuid.uuid4()),
        "content": content,
        "created_at": datetime.now().isoformat(),
    }
    notes = load_notes()
    notes.insert(0, note)
    save_notes(notes)
    return note


def update_note(note_id: str, new_content: str) -> dict | None:
    notes = load_notes()
    for note in notes:
        if note["id"] == note_id:
            note["content"] = new_content
            save_notes(notes)
            return note
    return None


def delete_note(note_id: str) -> bool:
    notes = load_notes()
    original_len = len(notes)
    notes = [n for n in notes if n["id"] != note_id]
    if len(notes) < original_len:
        save_notes(notes)
        return True
    return False
