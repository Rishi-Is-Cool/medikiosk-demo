"""Speech submodule for MediKiosk AI."""

from ai.speech.provider import TranscriptionProvider, TranscriptionResult
from ai.speech.transcription import FasterWhisperProvider

__all__ = [
    "TranscriptionProvider",
    "TranscriptionResult",
    "FasterWhisperProvider",
]
