import os
import subprocess
import threading


def speak(text: str):
    """Speak text using configured TTS provider."""
    provider = os.getenv("TTS_PROVIDER", "macos")
    if provider == "elevenlabs":
        _speak_elevenlabs(text)
    else:
        _speak_macos(text)


def _speak_macos(text: str):
    """Use macOS built-in TTS."""
    clean = text.replace('"', "'")
    subprocess.run(["say", "-v", "Daniel", "-r", "185", clean], check=False)


def _speak_elevenlabs(text: str):
    """Use ElevenLabs TTS."""
    import requests
    import tempfile
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
        _speak_macos(text)


def speak_async(text: str):
    """Speak in background thread."""
    threading.Thread(target=speak, args=(text,), daemon=True).start()
