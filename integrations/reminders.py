import os
import json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")


def _load() -> list:
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, "r") as f:
        return json.load(f)


def _save(reminders: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


def add_reminder(text: str, datetime_str: str) -> str:
    reminders = _load()
    reminders.append({
        "id": len(reminders) + 1,
        "text": text,
        "datetime": datetime_str,
        "done": False,
        "created": datetime.now().isoformat(),
    })
    _save(reminders)
    return f"Erinnerung gesetzt: '{text}' am {datetime_str}"


def get_due_reminders() -> list:
    reminders = _load()
    now = datetime.now()
    due = []
    updated = []
    for r in reminders:
        if r["done"]:
            updated.append(r)
            continue
        try:
            dt = datetime.fromisoformat(r["datetime"])
            if dt <= now:
                r["done"] = True
                due.append(r)
        except Exception:
            pass
        updated.append(r)
    _save(updated)
    return due


def get_upcoming_reminders() -> list:
    reminders = _load()
    return [r for r in reminders if not r["done"]]


def delete_reminder(reminder_id: int) -> str:
    reminders = _load()
    reminders = [r for r in reminders if r["id"] != reminder_id]
    _save(reminders)
    return f"Erinnerung {reminder_id} gelöscht."
