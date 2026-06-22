import threading
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
CHUNK = 1024
KEYWORDS = ["hey j1", "hey jay one", "j1", "jarvis"]


def _normalize(text: str) -> str:
    return text.lower().strip()


def listen_for_wakeword(callback, stop_event: threading.Event):
    """
    Simple energy-based wake trigger + Whisper keyword check.
    Listens continuously and calls callback() when wake word detected.
    """
    from groq import Groq
    import os, tempfile
    import scipy.io.wavfile as wav

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    SILENCE_THRESHOLD = 0.015
    PRE_RECORD = int(SAMPLE_RATE * 1.5)

    buffer = []
    triggered = False

    def audio_callback(indata, frames, time, status):
        nonlocal triggered
        if stop_event.is_set():
            return
        chunk = indata[:, 0].copy()
        buffer.extend(chunk.tolist())

        if len(buffer) > PRE_RECORD:
            del buffer[:-PRE_RECORD]

        rms = np.sqrt(np.mean(chunk ** 2))
        if rms > SILENCE_THRESHOLD and not triggered:
            triggered = True
            audio_snap = np.array(buffer, dtype=np.float32)
            threading.Thread(
                target=_check_keyword,
                args=(audio_snap, client, callback),
                daemon=True
            ).start()
            buffer.clear()

        if rms < SILENCE_THRESHOLD * 0.5:
            triggered = False

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=CHUNK,
        callback=audio_callback,
    ):
        stop_event.wait()


def _check_keyword(audio: np.ndarray, client, callback):
    import os, tempfile
    import scipy.io.wavfile as wav

    try:
        pcm = (audio * 32767).astype(np.int16)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav.write(f.name, SAMPLE_RATE, pcm)
            tmp = f.name

        with open(tmp, "rb") as f:
            result = client.audio.transcriptions.create(
                file=("audio.wav", f, "audio/wav"),
                model=os.getenv("STT_MODEL", "whisper-large-v3-turbo"),
                language="de",
            )
        os.unlink(tmp)
        text = result.text.lower().strip()
        if any(kw in text for kw in KEYWORDS):
            callback()
    except Exception:
        pass
