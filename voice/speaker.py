import os
import re
import subprocess
import threading
import asyncio
import tempfile

VOICE = os.getenv("TTS_VOICE", "de-DE-KillianNeural")
BASE_RATE  = os.getenv("TTS_RATE",  "-4%")
BASE_PITCH = os.getenv("TTS_PITCH", "-6Hz")


def clean_text(text: str) -> str:
    """Bereinigt Text — entfernt Markdown und Sonderzeichen."""
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'^\s*[-•*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[<>&]', '', text)
    text = re.sub(r'[^\w\s.,!?;:\-äöüÄÖÜß\'\"()\n]', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\.\.+', '.', text)
    return text.strip()


def text_to_ssml(text: str) -> str:
    """
    Wandelt Text in SSML um — natürliche Pausen, Betonung,
    Fragen gehen hoch, Satzenden gehen runter.
    """
    text = clean_text(text)
    if not text:
        return ""

    # Gedankenpausen bei Gedankenstrichen
    text = re.sub(r'\s*—\s*', ' <break time="250ms"/> ', text)
    text = re.sub(r'\s*\.\.\.\s*', '<break time="400ms"/> ', text)

    # Sätze aufsplitten
    chunks = re.split(r'(?<=[.!?])\s+', text)
    parts = []

    for chunk in chunks:
        c = chunk.strip()
        if not c:
            continue

        if c.endswith('?'):
            # Fragen: leicht höher und langsamer am Ende
            parts.append(
                f'<prosody pitch="+6Hz" rate="-2%">{c}</prosody>'
                f'<break time="450ms"/>'
            )
        elif c.endswith('!'):
            # Ausrufe: etwas lebhafter
            parts.append(
                f'<prosody pitch="+3Hz" rate="+3%">{c}</prosody>'
                f'<break time="380ms"/>'
            )
        else:
            # Normale Sätze: natürliche Komma-Pausen einbauen
            c_with_breaks = re.sub(r',\s+', ', <break time="180ms"/> ', c)
            c_with_breaks = re.sub(r';\s+', '; <break time="220ms"/> ', c_with_breaks)
            parts.append(
                f'<prosody>{c_with_breaks}</prosody>'
                f'<break time="350ms"/>'
            )

    inner = ' '.join(parts)

    return (
        f'<speak version="1.0" '
        f'xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xml:lang="de-DE">'
        f'<voice name="{VOICE}">'
        f'<prosody rate="{BASE_RATE}" pitch="{BASE_PITCH}">'
        f'{inner}'
        f'</prosody>'
        f'</voice>'
        f'</speak>'
    )


def speak(text: str):
    provider = os.getenv("TTS_PROVIDER", "edge")
    if not text or not text.strip():
        return
    if provider == "elevenlabs":
        _speak_elevenlabs(clean_text(text))
    elif provider == "macos":
        _speak_macos(clean_text(text))
    else:
        _speak_edge(text)


def _speak_edge(text: str):
    """Edge TTS mit SSML — natürliche Intonation, Jarvis-Stimme."""
    import edge_tts

    ssml = text_to_ssml(text)
    if not ssml:
        return

    async def _run():
        # Kein voice/rate/pitch Parameter — alles im SSML
        communicate = edge_tts.Communicate(ssml)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        await communicate.save(tmp_path)
        subprocess.run(["afplay", tmp_path], check=False)
        os.unlink(tmp_path)

    asyncio.run(_run())


def _speak_macos(text: str):
    clean = text.replace('"', "'")
    subprocess.run(["say", "-v", "Anna", "-r", "160", clean], check=False)


def _speak_elevenlabs(text: str):
    import requests
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_turbo_v2",
              "voice_settings": {"stability": 0.55, "similarity_boost": 0.8}},
    )
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(response.content)
            tmp_path = f.name
        subprocess.run(["afplay", tmp_path], check=False)
        os.unlink(tmp_path)
    else:
        _speak_edge(text)


def speak_async(text: str):
    threading.Thread(target=speak, args=(text,), daemon=True).start()
