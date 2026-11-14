"""Optional local Whisper. Only validated PCM WAV; no automatic calls or recording."""

import os, io, wave, tempfile
from pathlib import Path
from functools import lru_cache
from fastapi import HTTPException
from .analysis import enrich


@lru_cache(maxsize=1)
def whisper_model(path):
    from faster_whisper import WhisperModel

    return WhisperModel(
        path, device="cpu", compute_type="int8", local_files_only=True, cpu_threads=2
    )


def analyze_voice(raw):
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(413, "Audio exceeds 8 MiB.")
    try:
        with wave.open(io.BytesIO(raw), "rb") as audio:
            duration = audio.getnframes() / audio.getframerate()
            if (
                not 1 <= duration <= 120
                or audio.getnchannels() > 2
                or audio.getsampwidth() not in (1, 2, 3, 4)
            ):
                raise ValueError()
    except (wave.Error, ValueError, EOFError, ZeroDivisionError):
        raise HTTPException(422, "Use PCM WAV audio, 1–120 seconds, mono or stereo.")
    path = os.getenv("WHISPER_MODEL_PATH", "")
    if not path or not Path(path).is_dir():
        raise HTTPException(
            503,
            "Local speech transcription is not configured. Set WHISPER_MODEL_PATH to an installed faster-whisper model directory.",
        )
    try:
        model = whisper_model(path)
    except (ImportError, ValueError, RuntimeError, OSError):
        raise HTTPException(
            503,
            "Speech model unavailable. Install optional voice requirements and model files.",
        )
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            f.write(raw)
            f.flush()
            segments, _ = model.transcribe(f.name, beam_size=1)
            text = " ".join(s.text for s in segments)[:12000]
    except Exception:
        raise HTTPException(
            503, "Transcription failed. Please try a clearer supported recording."
        )
    if len(text.strip()) < 3:
        raise HTTPException(422, "No intelligible speech was found.")
    result = enrich("message", text)
    result["details"].update(
        transcript=text,
        duration_seconds=round(duration, 1),
        deepfake_detection="Not performed. A transcript cannot establish voice authenticity.",
    )
    return text, result
