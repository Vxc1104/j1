import os
import tempfile
import numpy as np
import scipy.io.wavfile as wav
import sounddevice as sd
from groq import Groq

SAMPLE_RATE      = 16000
CHANNELS         = 1
CHUNK_SECS       = 0.25          # 250ms chunks — schnellere Reaktion
SILENCE_THRESH   = 0.018         # RMS-Schwelle: unter diesem Wert = Stille
MIN_SPEECH_CHUNKS = 3            # mind. 750ms echtes Sprechen
MAX_SILENT_CHUNKS = 2            # 500ms Stille → fertig (war 2000ms)
MIN_ENERGY       = 0.006         # Gesamtenergie: darunter = nicht gesprochen

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


def record_until_silence(max_duration: int = 25) -> np.ndarray | None:
    """
    Nimmt auf bis Stille erkannt wird.
    Gibt None zurück wenn kein echtes Sprechen erkannt wurde.
    """
    chunk_size   = int(SAMPLE_RATE * CHUNK_SECS)
    max_chunks   = int(max_duration / CHUNK_SECS)
    audio_chunks = []
    silent_count = 0
    speech_count = 0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16") as stream:
        while len(audio_chunks) < max_chunks:
            chunk, _ = stream.read(chunk_size)
            chunk = chunk.copy()
            audio_chunks.append(chunk)

            rms = np.sqrt(np.mean(chunk.astype(np.float32) ** 2)) / 32768.0

            if rms >= SILENCE_THRESH:
                speech_count += 1
                silent_count  = 0
            else:
                # Nur zählen wenn schon Sprache erkannt
                if speech_count >= MIN_SPEECH_CHUNKS:
                    silent_count += 1
                    if silent_count >= MAX_SILENT_CHUNKS:
                        break

    audio = np.concatenate(audio_chunks)

    # Gesamtenergie prüfen — bei zu wenig Energie gar nicht transkribieren
    total_rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2)) / 32768.0
    if total_rms < MIN_ENERGY or speech_count < MIN_SPEECH_CHUNKS:
        return None

    return audio


def transcribe(audio: np.ndarray) -> str:
    """Whisper-Transkription via Groq."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav.write(f.name, SAMPLE_RATE, audio)
        tmp = f.name

    with open(tmp, "rb") as f:
        result = _get_client().audio.transcriptions.create(
            file=("audio.wav", f, "audio/wav"),
            model=os.getenv("STT_MODEL", "whisper-large-v3-turbo"),
            language="de",
        )

    os.unlink(tmp)
    text = result.text.strip()

    # Whisper-Halluzinationen filtern (kurze Einzelwörter ohne Inhalt)
    if len(text) < 3 or text.lower() in {
        ".", "..", "...", "äh", "öh", "hmm", "hm", "ähm",
        "okay", "ok", "ja", "nein", "danke", "tschüss",
        "you", "thank you", "thanks",  # englische Halluzinationen
    }:
        return ""

    return text
