import pytest
from unittest.mock import MagicMock
from ai.pipeline import ClinicalIntakePipeline
from ai.speech.provider import TranscriptionResult
from ai.intake.provider import ExtractionResult
from ai.intake.schemas import IntakeResponse, ChiefComplaint

def _get_mock_intake():
    return IntakeResponse(
        language="en",
        metadata={"intake_mode": "test", "language": "en", "timestamp": "2023-01-01T00:00:00Z"},
        chief_complaint=ChiefComplaint(name="Headache")
    )

def test_pipeline_complete_success():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="I have a headache.",
        language="en",
        success=True
    )
    
    mock_extractor.extract.return_value = ExtractionResult(
        success=True,
        data=_get_mock_intake()
    )
    
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    result = pipeline.process_audio("fake_audio.wav", patient_id="pt-123", language_hint="es")
    
    mock_transcriber.transcribe.assert_called_once_with(audio_path="fake_audio.wav", language="es")
    mock_extractor.extract.assert_called_once_with(text="I have a headache.", language="en", patient_id="pt-123")
    
    assert result.success is True
    assert result.transcript == "I have a headache."
    assert result.data is not None
    assert result.data.chief_complaint.name == "Headache"

def test_pipeline_language_routing():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    
    mock_extractor.extract.return_value = ExtractionResult(success=True, data=_get_mock_intake())
    
    # 1. Transcription provides language (takes priority)
    mock_transcriber.transcribe.return_value = TranscriptionResult(text="text", language="en", success=True)
    pipeline.process_audio("audio.wav", language_hint="es")
    mock_extractor.extract.assert_called_with(text="text", language="en", patient_id=None)
    
    # 2. Transcription missing language, fallback to hint
    mock_transcriber.transcribe.return_value = TranscriptionResult(text="text", language=None, success=True)
    pipeline.process_audio("audio.wav", language_hint="es")
    mock_extractor.extract.assert_called_with(text="text", language="es", patient_id=None)
    
    # 3. Both missing
    mock_transcriber.transcribe.return_value = TranscriptionResult(text="text", language=None, success=True)
    pipeline.process_audio("audio.wav", language_hint=None)
    mock_extractor.extract.assert_called_with(text="text", language=None, patient_id=None)

def test_pipeline_transcription_failure():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="", success=False, error="File corrupted"
    )
    
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    result = pipeline.process_audio("audio.wav")
    
    assert result.success is False
    assert "Transcription failed" in result.error
    mock_extractor.extract.assert_not_called()

def test_pipeline_extraction_failure():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="I have a headache", success=True, language="en"
    )
    mock_extractor.extract.return_value = ExtractionResult(
        success=False, error="LLM error"
    )
    
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    result = pipeline.process_audio("audio.wav")
    
    assert result.success is False
    assert "Extraction failed" in result.error
    assert result.transcript == "I have a headache"

def test_pipeline_empty_transcript():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="   ", success=True, language="en"
    )
    
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    result = pipeline.process_audio("audio.wav")
    
    assert result.success is False
    assert "empty transcript" in result.error
    mock_extractor.extract.assert_not_called()

def test_pipeline_transcription_exception():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    
    mock_transcriber.transcribe.side_effect = Exception("System error in STT")
    
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    result = pipeline.process_audio("audio.wav")
    
    assert result.success is False
    assert "Transcription failed: System error in STT" in result.error
    mock_extractor.extract.assert_not_called()

def test_pipeline_extraction_exception():
    mock_transcriber = MagicMock()
    mock_extractor = MagicMock()
    
    mock_transcriber.transcribe.return_value = TranscriptionResult(
        text="I have a headache", success=True, language="en"
    )
    mock_extractor.extract.side_effect = Exception("System error in LLM")
    
    pipeline = ClinicalIntakePipeline(mock_transcriber, mock_extractor)
    result = pipeline.process_audio("audio.wav")
    
    assert result.success is False
    assert "Extraction failed: System error in LLM" in result.error
    assert result.transcript == "I have a headache"
