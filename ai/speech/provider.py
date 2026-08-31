"""Transcription data contract and provider abstraction for MediKiosk.

This module defines the structured result returned by any transcription provider,
and the abstract base class that all providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field


class TranscriptionResult(BaseModel):
    """Structured result from a speech-to-text transcription."""

    text: str = Field(
        ..., description="The transcribed text from the audio input."
    )
    language: Optional[str] = Field(
        default=None,
        description="Detected or requested language code (e.g., 'en', 'hi', 'es').",
    )
    success: bool = Field(
        ..., description="Whether the transcription completed successfully."
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the transcription failed.",
    )
    duration_seconds: Optional[float] = Field(
        default=None,
        description="Duration of the audio in seconds, if available.",
    )


class TranscriptionProvider(ABC):
    """Abstract base for speech-to-text providers.

    All transcription providers must implement this interface so the rest of
    the application never depends on a specific STT engine directly.
    """

    @abstractmethod
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe an audio file and return a structured result.

        Args:
            audio_path: Absolute path to the audio file.
            language: Optional BCP-47 language code. If None, the provider
                      should attempt automatic language detection.

        Returns:
            A TranscriptionResult with the transcript text and metadata.
        """
        ...
