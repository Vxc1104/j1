import os
import io
import tempfile
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from groq import Groq

SAMPLE_RATE = 16000
CHANNELS = 1

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def record_audio(duration: int = 5) -> np.ndarray:
    """Record audio from microphone."""
    print(f"[J1] Höre zu... ({duration}s)")
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    sd.wait()
    return audio


def record_until_silence(silence_threshold: float = 0.01, max_duration: int = 30) -> np.ndarray:
    """Record until silence is detected."""
    chunk_size = int(SAMPLE_RATE * 0.5)
    audio_chunks = []
    silent_chunks = 0
    max_silent_chunks = 4  # 2 seconds of silence

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16") as stream:
        print("[J1] Spreche...")
        while len(audio_chunks) * chunk_size < SAMPLE_RATE * max_duration:
            chunk, _ = stream.read(chunk_size)
            audio_chunks.append(chunk.copy())
            rms = np.sqrt(np.mean(chunk.astype(float) ** 2))
            normalized = rms / 32768.0

            if normalized < silence_threshold and len(audio_chunks) > 4:
                silent_chunks += 1
                if silent_chunks >= max_silent_chunks:
                    break
            else:
                silent_chunks = 0

    return np.concatenate(audio_chunks)


def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio using Groq Whisper."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav.write(f.name, SAMPLE_RATE, audio)
        tmp_path = f.name

    with open(tmp_path, "rb") as f:
        result = client.audio.transcriptions.create(
            file=("audio.wav", f, "audio/wav"),
            model=os.getenv("STT_MODEL", "whisper-large-v3-turbo"),
            language="de",
        )

    os.unlink(tmp_path)
    return result.text.strip()
