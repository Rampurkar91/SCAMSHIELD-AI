"""Cheap installation checks, explicitly not a successful OCR/transcription probe."""

import importlib.util
import os
import shutil
import subprocess
from pathlib import Path


def speech_model_ready():
    directory = Path(os.getenv("WHISPER_MODEL_PATH") or "/nonexistent-speech-model")
    return bool(importlib.util.find_spec("faster_whisper")) and all(
        (directory / name).is_file() and (directory / name).stat().st_size > 0
        for name in ("model.bin", "config.json", "tokenizer.json")
    )


def tool_status():
    command = shutil.which(os.getenv("TESSERACT_CMD") or "tesseract")
    languages = []
    if command:
        try:
            output = subprocess.run(
                [command, "--list-langs"],
                capture_output=True,
                text=True,
                timeout=3,
                check=True,
            )
            languages = output.stdout.splitlines()[1:]
        except (OSError, subprocess.SubprocessError):
            pass
    requested = (os.getenv("OCR_LANG") or "eng").split("+")
    return {
        "ocr_installed": bool(command and set(requested) <= set(languages)),
        "ocr_languages": [name for name in languages if name in ("eng", "hin", "mar")],
        "voice_model_installed": speech_model_ready(),
        "check_kind": "Installation checks only; no inference probe has run.",
    }
