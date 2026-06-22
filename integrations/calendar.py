import os
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def get_google_service(service_name: str, version: str):
    creds = None
    token_path = "token.json"
    creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build(service_name, version, credentials=creds)


def get_upcoming_events(days: int = 7) -> list[dict]:
    service = get_google_service("calendar", "v3")
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

    result = service.events().list(
        calendarId="primary",
        timeMin=now,
        timeMax=end,
        maxResults=20,
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for e in result.get("items", []):
        start = e["start"].get("dateTime", e["start"].get("date"))
        events.append({
            "id": e["id"],
            "title": e.get("summary", "Kein Titel"),
            "start": start,
            "description": e.get("description", ""),
            "location": e.get("location", ""),
        })
    return events


def create_event(title: str, start: str, end: str, description: str = "", location: str = "") -> dict:
    service = get_google_service("calendar", "v3")
    event = {
        "summary": title,
        "location": location,
        "description": description,
        "start": {"dateTime": start, "timeZone": "Europe/Zurich"},
        "end": {"dateTime": end, "timeZone": "Europe/Zurich"},
    }
    result = service.events().insert(calendarId="primary", body=event).execute()
    return {"id": result["id"], "link": result.get("htmlLink", "")}
