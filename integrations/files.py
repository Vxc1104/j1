import os
import json


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def read_business_data(filename: str) -> str:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return f"Datei '{filename}' nicht gefunden im data/ Ordner."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def list_data_files() -> list[str]:
    if not os.path.exists(DATA_DIR):
        return []
    return [f for f in os.listdir(DATA_DIR) if not f.startswith(".")]


def save_note(title: str, content: str) -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    safe = "".join(c for c in title if c.isalnum() or c in " -_").strip().replace(" ", "_")
    path = os.path.join(DATA_DIR, f"{safe}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{content}")
    return f"Notiz gespeichert: {path}"
