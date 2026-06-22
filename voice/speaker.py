import os
import re
import subprocess
import threading
import tempfile

VOICE = os.getenv("TTS_VOICE", "de-DE-FlorianMultilingualNeural")
RATE  = os.getenv("TTS_RATE",  "-3%")
PITCH = os.getenv("TTS_PITCH", "+0Hz")

# Thread-safe speaking flag — mic loop waits until False
_speaking = threading.Event()


def is_speaking() -> bool:
    return _speaking.is_set()


def clean_text(text: str) -> str:
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


def speak(text: str):
    text = clean_text(text)
    if not text:
        return
    # Limit length — never speak prompts or code
    text = text[:600]
    _speaking.set()
    try:
        _speak_edge(text)
    finally:
        import time
        time.sleep(0.5)
        _speaking.clear()


def _speak_edge(text: str):
    """Edge TTS — plain text, explicit male voice, new event loop per call."""
    import asyncio
    import edge_tts

    async def _run():
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        await communicate.save(tmp)
        subprocess.run(["afplay", tmp], check=False)
        os.unlink(tmp)

    # Always use a fresh event loop — avoids conflicts in threads
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


def _speak_macos(text: str):
    subprocess.run(["say", "-v", "Daniel", "-r", "170", text.replace('"', "'")], check=False)


def speak_async(text: str):
    threading.Thread(target=speak, args=(text,), daemon=True).start()
