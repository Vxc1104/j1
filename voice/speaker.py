import os
import re
import subprocess
import threading
import tempfile

_speaking = threading.Event()


def is_speaking() -> bool:
    return _speaking.is_set()


def clean_text(text: str) -> str:
    # Markdown entfernen
    text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
    text = re.sub(r'#{1,6}\s*', '', text)
    text = re.sub(r'`{1,3}.*?`{1,3}', '', text, flags=re.DOTALL)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'^\s*[-•*]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[<>&]', '', text)
    # Gedankenstriche und Doppelstriche → Komma (fließender Übergang)
    text = re.sub(r'\s*—\s*', ', ', text)
    text = re.sub(r'\s*-{2,}\s*', ', ', text)
    # Klammern → Einschub mit Komma
    text = re.sub(r'\(([^)]+)\)', r', \1,', text)
    # Doppelpunkte → Komma
    text = re.sub(r':\s+', ', ', text)
    # Semikolon → Komma
    text = re.sub(r';\s*', ', ', text)
    # Doppelte Kommas bereinigen
    text = re.sub(r',\s*,+', ',', text)
    # Zeilenumbrüche → Leerzeichen
    text = re.sub(r'\n+', ' ', text)
    # Mehrfach-Leerzeichen
    text = re.sub(r'\s+', ' ', text)
    # Mehrfachpunkte
    text = re.sub(r'\.\.+', '.', text)
    # Komma direkt vor Punkt entfernen
    text = re.sub(r',\s*\.', '.', text)
    return text.strip()


def speak(text: str):
    text = clean_text(text)
    if not text:
        return
    text = text[:700]
    _speaking.set()
    try:
        provider = os.getenv("TTS_PROVIDER", "edge").lower()
        if provider == "elevenlabs":
            _speak_elevenlabs(text)
        elif provider == "macos":
            _speak_macos(text)
        else:
            _speak_edge(text)
    except Exception:
        try:
            _speak_edge(text)
        except Exception:
            _speak_macos(text)
    finally:
        import time
        time.sleep(0.4)
        _speaking.clear()


def _speak_edge(text: str):
    import asyncio
    import edge_tts

    voice = os.getenv("TTS_VOICE", "de-DE-FlorianMultilingualNeural")
    rate  = os.getenv("TTS_RATE", "+8%")
    pitch = os.getenv("TTS_PITCH", "-2Hz")

    async def _run():
        c = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        await c.save(tmp)
        subprocess.run(["afplay", tmp], check=False)
        os.unlink(tmp)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


def _speak_macos(text: str):
    voice = os.getenv("TTS_MACOS_VOICE", "Eddy (Deutsch (Deutschland))")
    rate  = os.getenv("TTS_MACOS_RATE", "160")
    clean = text.replace('"', "'").replace("’", "'")
    subprocess.run(["say", "-v", voice, "-r", rate, clean], check=False)


def _speak_elevenlabs(text: str):
    import requests
    key      = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
    if not key or not voice_id:
        raise RuntimeError("ElevenLabs nicht konfiguriert")
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.45, "similarity_boost": 0.80,
                               "style": 0.35, "use_speaker_boost": True},
        },
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(r.content)
        tmp = f.name
    subprocess.run(["afplay", tmp], check=False)
    os.unlink(tmp)


def speak_async(text: str):
    threading.Thread(target=speak, args=(text,), daemon=True).start()
