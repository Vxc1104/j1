import os
import re
import subprocess
import threading
import asyncio
import tempfile

VOICE = os.getenv("TTS_VOICE", "de-DE-FlorianMultilingualNeural")
RATE  = os.getenv("TTS_RATE",  "-5%")
PITCH = os.getenv("TTS_PITCH", "-4Hz")


def clean_text(text: str) -> str:
    """Bereinigt Text für natürliche Sprachausgabe."""
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'^\s*[-•*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[^\w\s.,!?;:\-äöüÄÖÜß\'\"()\n]', '', text)
    text = re.sub(r'\n+', '. ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def to_ssml(text: str) -> str:
    """Wandelt Text in SSML um für natürliche Intonation."""
    text = clean_text(text)
    if not text:
        return ""

    # Sätze aufteilen und mit natürlichen Pausen versehen
    sentences = re.split(r'(?<=[.!?])\s+', text)
    ssml_parts = []

    for sentence in sentences:
        s = sentence.strip()
        if not s:
            continue

        # Fragen: Tonhöhe am Ende leicht anheben
        if s.endswith('?'):
            ssml_parts.append(
                f'<prosody pitch="+8Hz" rate="-3%">{s}</prosody>'
                f'<break time="400ms"/>'
            )
        # Ausrufe: etwas schneller und höher
        elif s.endswith('!'):
            ssml_parts.append(
                f'<prosody pitch="+4Hz" rate="+5%">{s}</prosody>'
                f'<break time="350ms"/>'
            )
        # Normale Sätze: natürliche Pause
        else:
            ssml_parts.append(
                f'<prosody>{s}</prosody>'
                f'<break time="300ms"/>'
            )

    inner = ' '.join(ssml_parts)
    return (
        f'<speak xmlns="http://www.w3.org/2001/10/synthesis" '
        f'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="de-DE">'
        f'<voice name="{VOICE}">'
        f'<prosody rate="{RATE}" pitch="{PITCH}">'
        f'{inner}'
        f'</prosody></voice></speak>'
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
        _speak_edge_ssml(text)


def _speak_edge_ssml(text: str):
    """Edge TTS mit SSML für natürliche Intonation."""
    import edge_tts

    ssml = to_ssml(text)
    if not ssml:
        return

    async def _run():
        communicate = edge_tts.Communicate(ssml, VOICE)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        await communicate.save(tmp_path)
        subprocess.run(["afplay", tmp_path], check=False)
        os.unlink(tmp_path)

    asyncio.run(_run())


def _speak_macos(text: str):
    clean = text.replace('"', "'")
    subprocess.run(["say", "-v", "Anna", "-r", "165", clean], check=False)


def _speak_elevenlabs(text: str):
    import requests

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.55, "similarity_boost": 0.8},
        },
    )
    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(response.content)
            tmp_path = f.name
        subprocess.run(["afplay", tmp_path], check=False)
        os.unlink(tmp_path)
    else:
        _speak_edge_ssml(text)


def speak_async(text: str):
    threading.Thread(target=speak, args=(text,), daemon=True).start()
