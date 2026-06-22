import os
import json
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MEMORY_FILE = os.path.join(DATA_DIR, "memory.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def load_memory() -> dict:
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


def save_memory(key: str, value: str) -> str:
    mem = load_memory()
    mem[key] = {"value": value, "saved": datetime.now().isoformat()}
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, ensure_ascii=False, indent=2)
    return f"Gespeichert: {key} = {value}"


def forget_memory(key: str) -> str:
    mem = load_memory()
    if key in mem:
        del mem[key]
        with open(MEMORY_FILE, "w") as f:
            json.dump(mem, f, ensure_ascii=False, indent=2)
        return f"Vergessen: {key}"
    return f"'{key}' war nicht im Gedächtnis."


def get_memory_summary() -> str:
    mem = load_memory()
    if not mem:
        return "Kein gespeichertes Wissen vorhanden."
    lines = [f"{k}: {v['value']}" for k, v in mem.items()]
    return "\n".join(lines)


def save_history(history: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    # Nur user/assistant Text-Messages speichern — keine Tool-Calls
    clean = [
        m for m in history[-40:]
        if m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
        and m.get("content", "").strip()
    ]
    with open(HISTORY_FILE, "w") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)


def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            data = json.load(f)
        # Nur valide user/assistant Messages laden
        return [
            m for m in data
            if m.get("role") in ("user", "assistant")
            and isinstance(m.get("content"), str)
            and m.get("content", "").strip()
        ]
    except Exception:
        return []
