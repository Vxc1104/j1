from integrations import calendar, gmail, notion, n8n
import json
from datetime import datetime

TOOLS = [
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
                    "title": {"type": "string", "description": "Titel des Termins"},
                    "start": {"type": "string", "description": "Startzeit ISO 8601 (z.B. 2024-12-01T10:00:00)"},
                    "end": {"type": "string", "description": "Endzeit ISO 8601"},
                    "description": {"type": "string", "description": "Beschreibung (optional)"},
                    "location": {"type": "string", "description": "Ort (optional)"},
                },
                "required": ["title", "start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_emails",
            "description": "Liest ungelesene E-Mails aus Gmail",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Maximale Anzahl E-Mails (Standard: 5)"},
                    "query": {"type": "string", "description": "Gmail Suchfilter (Standard: is:unread)"},
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
                    "query": {"type": "string", "description": "Suchbegriff"}
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
                    "page_id": {"type": "string", "description": "Notion Page ID"}
                },
                "required": ["page_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_business_update",
            "description": "Ruft Business-Updates über n8n ab",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Gibt aktuelle Uhrzeit und Datum zurück",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    try:
        if name == "get_calendar_events":
            events = calendar.get_upcoming_events(days=args.get("days", 7))
            return json.dumps(events, ensure_ascii=False)

        elif name == "create_calendar_event":
            result = calendar.create_event(
                title=args["title"],
                start=args["start"],
                end=args["end"],
                description=args.get("description", ""),
                location=args.get("location", ""),
            )
            return json.dumps(result, ensure_ascii=False)

        elif name == "get_emails":
            emails = gmail.get_recent_emails(
                max_results=args.get("max_results", 5),
                query=args.get("query", "is:unread"),
            )
            return json.dumps(emails, ensure_ascii=False)

        elif name == "search_notion":
            results = notion.search_notion(args["query"])
            return json.dumps(results, ensure_ascii=False)

        elif name == "get_notion_page":
            content = notion.get_page_content(args["page_id"])
            return content

        elif name == "get_business_update":
            result = n8n.get_business_update()
            return json.dumps(result, ensure_ascii=False)

        elif name == "get_current_time":
            now = datetime.now()
            return json.dumps({
                "datetime": now.isoformat(),
                "date": now.strftime("%d.%m.%Y"),
                "time": now.strftime("%H:%M"),
                "weekday": now.strftime("%A"),
            }, ensure_ascii=False)

        else:
            return json.dumps({"error": f"Unbekanntes Tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})
