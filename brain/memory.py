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
    with open(HISTORY_FILE, "w") as f:
        json.dump(history[-40:], f, ensure_ascii=False, indent=2)


def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r") as f:
        return json.load(f)
