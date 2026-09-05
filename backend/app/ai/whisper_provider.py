"""Optional local Faster-Whisper provider used by the kiosk speech boundary."""
from __future__ import annotations

import os
from typing import Optional


class SpeechUnavailable(RuntimeError):
    """Raised when local speech processing is not installed/configured."""


class FasterWhisperProvider:
    def __init__(self) -> None:
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SpeechUnavailable("Local Whisper is not installed; configure a speech provider or install faster-whisper.") from exc
        try:
            self._model = WhisperModel(os.getenv("WHISPER_MODEL", "base"), device=os.getenv("WHISPER_DEVICE", "cpu"),
                                       compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"))
        except Exception as exc:
            raise SpeechUnavailable(f"Local Whisper could not be initialized: {exc}") from exc
        return self._model

    def transcribe(self, path: str, language: Optional[str] = None) -> dict:
        model = self._load()
        try:
            segments, info = model.transcribe(path, language=language, beam_size=5, vad_filter=True,
                                              initial_prompt=os.getenv("WHISPER_INITIAL_PROMPT") or None)
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return {"transcript": text, "language": info.language or language or "en", "confidence": None,
                    "duration_ms": int((info.duration or 0) * 1000), "provider": "faster-whisper"}
        except Exception as exc:
            raise SpeechUnavailable(f"Transcription failed: {exc}") from exc


whisper_provider = FasterWhisperProvider()
