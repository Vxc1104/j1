import os
import json
from datetime import datetime
from brain.claude import chat
from integrations import weather, news
from brain.memory import load_memory

try:
    from integrations import calendar as cal
    HAS_CAL = True
except Exception:
    HAS_CAL = False

try:
    from integrations import gmail
    HAS_GMAIL = True
except Exception:
    HAS_GMAIL = False


def build_morning_briefing() -> str:
    city = os.getenv("WEATHER_CITY", "Zurich")
    now = datetime.now()
    parts = [f"Datum: {now.strftime('%A, %d. %B %Y')}, {now.strftime('%H:%M')} Uhr"]

    # Wetter
    w = weather.get_weather(city)
    if "error" not in w:
        parts.append(f"Wetter in {city}: {w['description']}, {w['temp_c']}°C (max {w['max_temp']}°C, min {w['min_temp']}°C)")

    # Kalender
    if HAS_CAL:
        try:
            events = cal.get_upcoming_events(days=1)
            if events:
                event_str = ", ".join([f"{e['title']} um {e['start'][11:16]}" for e in events[:5]])
                parts.append(f"Heutige Termine: {event_str}")
            else:
                parts.append("Heute keine Termine.")
        except Exception:
            pass

    # E-Mails
    if HAS_GMAIL:
        try:
            emails = gmail.get_recent_emails(max_results=3)
            if emails:
                email_str = ", ".join([f"'{e['subject']}' von {e['from'].split('<')[0].strip()}" for e in emails[:3]])
                parts.append(f"Ungelesene E-Mails: {email_str}")
        except Exception:
            pass

    # Nachrichten
    try:
        articles = news.get_top_news(max_results=3)
        if articles and "error" not in articles[0]:
            headlines = ", ".join([a["title"] for a in articles[:3]])
            parts.append(f"Top-Nachrichten: {headlines}")
    except Exception:
        pass

    # Gedächtnis
    mem = load_memory()
    if mem:
        mem_str = "; ".join([f"{k}: {v['value']}" for k, v in list(mem.items())[:3]])
        parts.append(f"Kontext: {mem_str}")

    context = "\n".join(parts)
    prompt = f"""Erstelle ein kurzes, gesprochenes Morgen-Briefing auf Deutsch basierend auf diesen Daten.
Klinge wie Jarvis — präzise, warm, motivierend. Maximal 4-5 Sätze.

{context}"""

    answer, _ = chat(prompt, [])
    return answer
