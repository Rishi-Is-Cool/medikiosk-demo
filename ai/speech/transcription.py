"""Faster-Whisper transcription provider for MediKiosk.

Wraps the faster-whisper library behind the TranscriptionProvider interface
so the rest of the application remains engine-agnostic.
"""

import os
from typing import Optional

from faster_whisper import WhisperModel

from ai.speech.provider import TranscriptionProvider, TranscriptionResult

# Default model size — small enough for dev, good enough for demos.
# Configurable per-instance: "tiny", "base", "small", "medium", "large-v3", etc.
DEFAULT_MODEL_SIZE = "base"


class FasterWhisperProvider(TranscriptionProvider):
    """Speech-to-text provider backed by faster-whisper (CTranslate2).

    The Whisper model is loaded once at construction time and reused for
    every subsequent ``transcribe()`` call.

    Args:
        model_size: Whisper model identifier (e.g. "tiny", "base", "small").
        device: Compute device — "cpu" or "cuda".
        compute_type: CTranslate2 quantisation type (e.g. "int8", "float16").
    """

    def __init__(
        self,
        model_size: str = DEFAULT_MODEL_SIZE,
        device: str = "cpu",
        compute_type: str = "int8",
        initial_prompt: Optional[str] = None,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._initial_prompt = initial_prompt
        self._model = self._load_model()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_model(self):
        """Load the faster-whisper model once and return it."""
        try:
            return WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to load faster-whisper model '{self._model_size}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file using the loaded Whisper model.

        Args:
            audio_path: Absolute path to a supported audio file
                        (wav, mp3, flac, ogg, m4a, etc.).
            language: Optional BCP-47 language hint. When ``None``,
                      Whisper auto-detects the language.

        Returns:
            A ``TranscriptionResult`` with the full transcript and metadata.
        """
        # --- Validate input path ---
        if not audio_path or not os.path.isfile(audio_path):
            return TranscriptionResult(
                text="",
                success=False,
                error=f"Audio file not found: {audio_path}",
            )

        # --- Run transcription ---
        try:
            segments, info = self._model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                initial_prompt=self._initial_prompt,
                vad_filter=True,
            )

            # Materialise the lazy segment generator into full text.
            full_text = " ".join(segment.text.strip() for segment in segments)
            full_text = full_text.strip()

            return TranscriptionResult(
                text=full_text,
                language=info.language,
                success=True,
                duration_seconds=round(info.duration, 2) if info.duration else None,
            )

        except Exception as exc:
            return TranscriptionResult(
                text="",
                success=False,
                error=f"Transcription failed: {exc}",
            )
