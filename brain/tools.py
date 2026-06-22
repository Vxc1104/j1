import json
from datetime import datetime

try:
    from integrations import calendar
    HAS_GOOGLE = True
except Exception:
    HAS_GOOGLE = False

try:
    from integrations import gmail
    HAS_GMAIL = True
except Exception:
    HAS_GMAIL = False

try:
    from integrations import notion
    HAS_NOTION = True
except Exception:
    HAS_NOTION = False

from integrations import n8n
from integrations import news
from integrations import files
from integrations import weather
from integrations import reminders
from integrations import search
from brain.memory import save_memory, forget_memory, get_memory_summary

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Gibt aktuelle Uhrzeit, Datum und Wochentag zurück",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Liest bevorstehende Kalendertermine aus Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Wie viele Tage in die Zukunft (Standard: 7)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Erstellt einen neuen Termin im Google Calendar",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start": {"type": "string", "description": "ISO 8601, z.B. 2024-12-01T10:00:00"},
                    "end": {"type": "string", "description": "ISO 8601"},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["title", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_emails",
            "description": "Liest E-Mails aus Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer"},
                    "query": {"type": "string", "description": "Gmail Suchfilter, Standard: is:unread"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Holt aktuelle Nachrichten. Themen: welt, spiegel, tagesschau, business, tech, finanzen",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Nachrichtenquelle/Thema (Standard: tagesschau)"},
                    "max_results": {"type": "integer", "description": "Anzahl Artikel (Standard: 5)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_notion",
            "description": "Durchsucht Notion nach Seiten und Datenbanken",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_notion_page",
            "description": "Liest den Inhalt einer Notion-Seite",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string"}
                },
                "required": ["page_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_update",
            "description": "Ruft Business-Updates über n8n Webhook ab",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_business_file",
            "description": "Liest eine Business-Datei aus dem data/ Ordner (Berichte, KPIs, Notizen)",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Dateiname im data/ Ordner"}
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_business_files",
            "description": "Listet alle verfügbaren Business-Dateien im data/ Ordner auf",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Speichert eine Notiz oder Information im data/ Ordner",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "trigger_n8n_workflow",
            "description": "Startet einen n8n Workflow über Webhook",
            "parameters": {
                "type": "object",
                "properties": {
                    "webhook_name": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["webhook_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Holt das aktuelle Wetter für eine Stadt (kostenlos)",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Stadtname (Standard: Zurich)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_reminder",
            "description": "Setzt eine Erinnerung für einen bestimmten Zeitpunkt",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Was soll erinnert werden"},
                    "datetime": {"type": "string", "description": "ISO 8601 Datum/Zeit, z.B. 2024-12-01T10:00:00"},
                },
                "required": ["text", "datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reminders",
            "description": "Zeigt alle ausstehenden Erinnerungen",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember",
            "description": "Speichert eine wichtige Information dauerhaft im Gedächtnis von J1",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Bezeichnung/Schlüssel der Information"},
                    "value": {"type": "string", "description": "Der zu merkende Inhalt"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget",
            "description": "Löscht eine gespeicherte Information aus dem Gedächtnis",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"}
                },
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Zeigt alles was J1 sich gemerkt hat",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Sucht aktuelle Informationen im Internet. Nutze dieses Tool immer wenn der Nutzer nach aktuellen Fakten, Preisen, Personen, Ereignissen oder allem fragt was du nicht sicher weißt.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Die Suchanfrage auf Deutsch oder Englisch"},
                    "max_results": {"type": "integer", "description": "Anzahl Ergebnisse (Standard: 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Sucht aktuelle Nachrichten zu einem bestimmten Thema im Internet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Thema oder Suchbegriff"},
                    "max_results": {"type": "integer", "description": "Anzahl Ergebnisse (Standard: 5)"},
                },
                "required": ["query"],
            },
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "get_current_time":
            now = datetime.now()
            return json.dumps({
                "datetime": now.isoformat(),
                "date": now.strftime("%d.%m.%Y"),
                "time": now.strftime("%H:%M"),
                "weekday": now.strftime("%A"),
            }, ensure_ascii=False)

        elif name == "get_calendar_events":
            if not HAS_GOOGLE:
                return json.dumps({"error": "Google Calendar nicht eingerichtet. credentials.json fehlt."})
            events = calendar.get_upcoming_events(days=args.get("days", 7))
            return json.dumps(events, ensure_ascii=False)

        elif name == "create_calendar_event":
            if not HAS_GOOGLE:
                return json.dumps({"error": "Google Calendar nicht eingerichtet."})
            result = calendar.create_event(
                title=args["title"],
                start=args["start"],
                end=args["end"],
                description=args.get("description", ""),
                location=args.get("location", ""),
            )
            return json.dumps(result, ensure_ascii=False)

        elif name == "get_emails":
            if not HAS_GMAIL:
                return json.dumps({"error": "Gmail nicht eingerichtet. credentials.json fehlt."})
            emails = gmail.get_recent_emails(
                max_results=args.get("max_results", 5),
                query=args.get("query", "is:unread"),
            )
            return json.dumps(emails, ensure_ascii=False)

        elif name == "get_news":
            articles = news.get_news(
                topic=args.get("topic", "tagesschau"),
                max_results=args.get("max_results", 5),
            )
            return json.dumps(articles, ensure_ascii=False)

        elif name == "search_notion":
            if not HAS_NOTION:
                return json.dumps({"error": "Notion nicht eingerichtet. NOTION_API_KEY fehlt."})
            results = notion.search_notion(args["query"])
            return json.dumps(results, ensure_ascii=False)

        elif name == "get_notion_page":
            if not HAS_NOTION:
                return json.dumps({"error": "Notion nicht eingerichtet."})
            return notion.get_page_content(args["page_id"])

        elif name == "get_business_update":
            result = n8n.get_business_update()
            return json.dumps(result, ensure_ascii=False)

        elif name == "read_business_file":
            return files.read_business_data(args["filename"])

        elif name == "list_business_files":
            result = files.list_data_files()
            return json.dumps(result, ensure_ascii=False)

        elif name == "save_note":
            return files.save_note(args["title"], args["content"])

        elif name == "trigger_n8n_workflow":
            result = n8n.trigger_webhook(args["webhook_name"], args.get("payload", {}))
            return json.dumps(result, ensure_ascii=False)

        elif name == "get_weather":
            result = weather.get_weather(args.get("city", "Zurich"))
            return json.dumps(result, ensure_ascii=False)

        elif name == "set_reminder":
            return reminders.add_reminder(args["text"], args["datetime"])

        elif name == "get_reminders":
            result = reminders.get_upcoming_reminders()
            return json.dumps(result, ensure_ascii=False)

        elif name == "remember":
            return save_memory(args["key"], args["value"])

        elif name == "forget":
            return forget_memory(args["key"])

        elif name == "recall_memory":
            return get_memory_summary()

        elif name == "web_search":
            results = search.web_search(args["query"], args.get("max_results", 5))
            return json.dumps(results, ensure_ascii=False)

        elif name == "search_news":
            results = search.search_news(args["query"], args.get("max_results", 5))
            return json.dumps(results, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unbekanntes Tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
