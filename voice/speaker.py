import os
import subprocess
import threading
import asyncio
import tempfile


VOICE = os.getenv("TTS_VOICE", "de-DE-FlorianMultilingualNeural")
RATE  = os.getenv("TTS_RATE",  "-3%")   # leicht langsamer = klarer
PITCH = os.getenv("TTS_PITCH", "-6Hz")  # etwas tiefer = Jarvis-Feeling


def speak(text: str):
    provider = os.getenv("TTS_PROVIDER", "edge")
    if provider == "elevenlabs":
        _speak_elevenlabs(text)
    elif provider == "macos":
        _speak_macos(text)
    else:
        _speak_edge(text)


def _speak_edge(text: str):
    """Microsoft Edge TTS — natürliche, menschliche Stimme (kostenlos)."""
    import edge_tts

    async def _run():
        communicate = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp_path = f.name
        await communicate.save(tmp_path)
        subprocess.run(["afplay", tmp_path], check=False)
        os.unlink(tmp_path)

    asyncio.run(_run())


def _speak_macos(text: str):
    clean = text.replace('"', "'")
    subprocess.run(["say", "-v", "Daniel", "-r", "185", clean], check=False)


def _speak_elevenlabs(text: str):
    import requests
    import sounddevice as sd
    import soundfile as sf

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "onwK4e9ZLuTAKqWW03F9")

    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={"text": text, "model_id": "eleven_turbo_v2", "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
    )

    if response.status_code == 200:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(response.content)
            tmp_path = f.name
        data, samplerate = sf.read(tmp_path)
        sd.play(data, samplerate)
        sd.wait()
        os.unlink(tmp_path)
    else:
        _speak_edge(text)


def speak_async(text: str):
    threading.Thread(target=speak, args=(text,), daemon=True).start()
