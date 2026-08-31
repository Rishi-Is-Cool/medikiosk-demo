"""Clinical Intake Pipeline for MediKiosk.

This module orchestrates the end-to-end flow from audio transcription
to clinical information extraction.
"""

from typing import Optional

from pydantic import BaseModel

from ai.intake.provider import ClinicalExtractionProvider
from ai.intake.schemas import IntakeResponse
from ai.speech.provider import TranscriptionProvider


class PipelineResult(BaseModel):
    """Result of the complete end-to-end pipeline."""

    success: bool
    error: Optional[str] = None
    transcript: Optional[str] = None
    data: Optional[IntakeResponse] = None


class ClinicalIntakePipeline:
    """Orchestrates audio transcription and clinical extraction."""

    def __init__(
        self,
        transcription_provider: TranscriptionProvider,
        extraction_provider: ClinicalExtractionProvider,
    ):
        """Initialise the pipeline with generic providers.

        Args:
            transcription_provider: Engine-agnostic speech-to-text provider.
            extraction_provider: LLM-agnostic clinical extraction provider.
        """
        self.transcriber = transcription_provider
        self.extractor = extraction_provider

    def process_audio(
        self,
        audio_path: str,
        patient_id: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> PipelineResult:
        """Process an audio file end-to-end.

        Args:
            audio_path: Absolute path to the audio file.
            patient_id: Optional patient identifier.
            language_hint: Optional language code hint.

        Returns:
            A PipelineResult containing the final transcript and structured data.
        """
        # 1. Transcription Phase
        try:
            transcription = self.transcriber.transcribe(
                audio_path=audio_path, language=language_hint
            )
        except Exception as e:
            return PipelineResult(
                success=False,
                error=f"Transcription failed: {str(e)}",
            )

        if not transcription.success:
            return PipelineResult(
                success=False,
                error=f"Transcription failed: {transcription.error}",
            )

        transcript_text = transcription.text.strip() if transcription.text else ""
        if not transcript_text:
            return PipelineResult(
                success=False,
                error="Transcription succeeded but yielded an empty transcript.",
                transcript="",
            )

        # 2. Language Routing
        # Detected language from the speech model takes priority over the hint.
        extraction_language = transcription.language or language_hint

        # 3. Extraction Phase
        try:
            extraction = self.extractor.extract(
                text=transcript_text,
                language=extraction_language,
                patient_id=patient_id,
            )
        except Exception as e:
            return PipelineResult(
                success=False,
                error=f"Extraction failed: {str(e)}",
                transcript=transcript_text,
            )

        if not extraction.success:
            return PipelineResult(
                success=False,
                error=f"Extraction failed: {extraction.error}",
                transcript=transcript_text,
            )

        return PipelineResult(
            success=True,
            data=extraction.data,
            transcript=transcript_text,
        )
