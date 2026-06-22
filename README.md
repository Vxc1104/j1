# J1 — Persönlicher Sprachassistent

> Jarvis-style KI-Assistent mit Sprachsteuerung, Kalender, Gmail, Notion & n8n

## Features
- Spracheingabe via Groq Whisper (lokal, gratis)
- KI-Gehirn: Groq Llama 3.3 70B (gratis) oder Claude API
- Sprachausgabe: macOS TTS oder ElevenLabs
- Google Calendar lesen & Termine erstellen
- Gmail ungelesene E-Mails zusammenfassen
- Notion Seiten durchsuchen & lesen
- n8n Webhook Integration für Business-Workflows
- Modernes Dark-Mode Desktop UI

## Setup

### 1. Python Umgebung
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. API Keys konfigurieren
```bash
cp .env.example .env
# .env öffnen und Keys eintragen
```

### 3. Groq API Key holen (kostenlos)
- Gehe zu https://console.groq.com
- Account erstellen → API Keys → Create API Key
- Key in `.env` eintragen: `GROQ_API_KEY=...`

### 4. Google Calendar & Gmail einrichten
- Gehe zu https://console.cloud.google.com
- Neues Projekt erstellen
- APIs aktivieren: Google Calendar API + Gmail API
- OAuth 2.0 Credentials erstellen → `credentials.json` im Projektordner speichern

### 5. Notion einrichten
- Gehe zu https://www.notion.so/my-integrations
- Neue Integration erstellen → API Key kopieren
- Integration zu deinen Notion-Seiten hinzufügen

### 6. Starten
```bash
python main.py
```

## Nutzung
- **Mikrofon-Button** drücken → sprechen → J1 antwortet
- **Textfeld** für Texteingabe
- Beispiele:
  - "Was habe ich heute für Termine?"
  - "Erstelle einen Termin morgen um 10 Uhr: Team Meeting"
  - "Zeig mir meine ungelesenen E-Mails"
  - "Suche in Notion nach unserem Business Plan"
  - "Gib mir ein Business Update"

## Architektur
```
Mikrofon → Groq Whisper (STT) → Groq Llama / Claude (Gehirn) → macOS say / ElevenLabs (TTS)
                                          ↕
              Google Calendar / Gmail / Notion / n8n Webhooks
```

## Kosten
| Service | Kosten |
|---|---|
| Groq API (STT + LLM) | Gratis (Free Tier) |
| macOS TTS | Gratis |
| Google APIs | Gratis |
| Notion API | Gratis |
| Claude API (optional) | ~$5-10/Monat |
| ElevenLabs (optional) | Ab $5/Monat |
