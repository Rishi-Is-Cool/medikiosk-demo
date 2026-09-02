from typing import Optional, Any
from dataclasses import dataclass
from ai.speech.provider import TranscriptionProvider, TranscriptionResult
from ai.intake.provider import ClinicalExtractionProvider, ExtractionResult

@dataclass
class PipelineResult:
    success: bool
    transcript: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None

class ClinicalIntakePipeline:
    def __init__(self, transcriber: TranscriptionProvider, extractor: ClinicalExtractionProvider):
        self.transcriber = transcriber
        self.extractor = extractor
        
    def process_audio(
        self,
        audio_path: str,
        patient_id: Optional[str] = None,
        language_hint: Optional[str] = None,
    ) -> PipelineResult:
        try:
            # 1. Transcribe audio
            try:
                transcription = self.transcriber.transcribe(audio_path=audio_path, language=language_hint)
            except Exception as e:
                return PipelineResult(success=False, error=f"Transcription failed: {str(e)}")

            if not transcription or not transcription.success:
                error_msg = transcription.error if transcription and transcription.error else "No text returned."
                return PipelineResult(
                    success=False, 
                    error=f"Transcription failed: {error_msg}"
                )
            
            transcript_text = transcription.text.strip() if transcription.text else ""
            if not transcript_text:
                return PipelineResult(
                    success=False,
                    transcript="",
                    error="Transcription succeeded but yielded an empty transcript."
                )
            
            # 2. Extract clinical data
            extraction_language = transcription.language or language_hint
            try:
                extraction = self.extractor.extract(
                    text=transcript_text,
                    language=extraction_language,
                    patient_id=patient_id,
                )
            except Exception as e:
                return PipelineResult(
                    success=False, 
                    transcript=transcript_text,
                    error=f"Extraction failed: {str(e)}"
                )
            
            if not extraction.success:
                return PipelineResult(
                    success=False,
                    transcript=transcript_text,
                    error=f"Extraction failed: {extraction.error}"
                )
            
            extracted_data = extraction.data
            
            # Populate language if it was detected by STT but missing in extraction
            if transcription.language and extracted_data and getattr(extracted_data, 'language', None) is None:
                extracted_data.language = transcription.language

            return PipelineResult(
                success=True,
                transcript=transcript_text,
                data=extracted_data
            )
            
        except Exception as e:
            return PipelineResult(success=False, error=str(e))
