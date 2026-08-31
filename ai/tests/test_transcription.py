"""Unit tests for the speech-to-text module.

All tests mock the faster-whisper model — no model download, GPU, or
real audio transcription is required.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ai.speech.provider import TranscriptionProvider, TranscriptionResult
from ai.speech.transcription import FasterWhisperProvider

# Patch target — WhisperModel as imported in the transcription module.
WHISPER_MODEL_PATCH = "ai.speech.transcription.WhisperModel"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_segment(text: str):
    """Return a mock segment object with a ``.text`` attribute."""
    return SimpleNamespace(text=text)


def _make_info(language: str = "en", duration: float = 5.0):
    """Return a mock transcription info object."""
    return SimpleNamespace(language=language, duration=duration)


def _build_provider(mock_model_cls):
    """Construct a FasterWhisperProvider with a mocked WhisperModel."""
    mock_model_cls.return_value = MagicMock()
    return FasterWhisperProvider(model_size="tiny", device="cpu")


# ---------------------------------------------------------------------------
# TranscriptionResult model tests
# ---------------------------------------------------------------------------

class TestTranscriptionResult:
    """Verify the data contract itself."""

    def test_success_result(self):
        result = TranscriptionResult(
            text="I have a headache",
            language="en",
            success=True,
            duration_seconds=3.5,
        )
        assert result.text == "I have a headache"
        assert result.language == "en"
        assert result.success is True
        assert result.error is None
        assert result.duration_seconds == 3.5

    def test_failure_result(self):
        result = TranscriptionResult(
            text="",
            success=False,
            error="Model not loaded",
        )
        assert result.text == ""
        assert result.success is False
        assert result.error == "Model not loaded"
        assert result.language is None
        assert result.duration_seconds is None


# ---------------------------------------------------------------------------
# Provider interface contract
# ---------------------------------------------------------------------------

class TestProviderInterface:
    """Ensure FasterWhisperProvider satisfies the abstract interface."""

    @patch(WHISPER_MODEL_PATCH)
    def test_is_subclass(self, mock_cls):
        provider = _build_provider(mock_cls)
        assert isinstance(provider, TranscriptionProvider)


# ---------------------------------------------------------------------------
# Successful transcription
# ---------------------------------------------------------------------------

class TestSuccessfulTranscription:
    """Test 1 & 2: Successful transcription with and without explicit language."""

    @patch(WHISPER_MODEL_PATCH)
    def test_successful_transcription(self, mock_cls, tmp_path):
        """Test 1: audio file → correct TranscriptionResult."""
        provider = _build_provider(mock_cls)

        audio_file = tmp_path / "sample.wav"
        audio_file.write_bytes(b"fake audio data")

        segments = [_make_segment("I have been having"), _make_segment("chest pain")]
        info = _make_info(language="en", duration=4.2)
        provider._model.transcribe.return_value = (iter(segments), info)

        result = provider.transcribe(str(audio_file))

        assert result.success is True
        assert result.text == "I have been having chest pain"
        assert result.language == "en"
        assert result.duration_seconds == 4.2
        assert result.error is None

    @patch(WHISPER_MODEL_PATCH)
    def test_explicit_language_parameter(self, mock_cls, tmp_path):
        """Test 2: Language param is forwarded to the model."""
        provider = _build_provider(mock_cls)

        audio_file = tmp_path / "hindi.wav"
        audio_file.write_bytes(b"fake hindi audio")

        segments = [_make_segment("मुझे सिर दर्द है")]
        info = _make_info(language="hi", duration=2.0)
        provider._model.transcribe.return_value = (iter(segments), info)

        result = provider.transcribe(str(audio_file), language="hi")

        assert result.success is True
        assert result.language == "hi"
        # Verify language was actually forwarded to the model
        provider._model.transcribe.assert_called_once_with(
            str(audio_file), language="hi", beam_size=5,
        )


# ---------------------------------------------------------------------------
# Auto-detection (no language parameter)
# ---------------------------------------------------------------------------

class TestAutoDetection:
    """Test 3: No language parameter → auto-detection."""

    @patch(WHISPER_MODEL_PATCH)
    def test_no_language_auto_detects(self, mock_cls, tmp_path):
        provider = _build_provider(mock_cls)

        audio_file = tmp_path / "spanish.wav"
        audio_file.write_bytes(b"fake spanish audio")

        segments = [_make_segment("Tengo dolor de cabeza")]
        info = _make_info(language="es", duration=3.0)
        provider._model.transcribe.return_value = (iter(segments), info)

        result = provider.transcribe(str(audio_file))

        assert result.success is True
        assert result.language == "es"
        # language=None should be passed through
        provider._model.transcribe.assert_called_once_with(
            str(audio_file), language=None, beam_size=5,
        )


# ---------------------------------------------------------------------------
# Provider / model failure
# ---------------------------------------------------------------------------

class TestProviderFailure:
    """Test 4: Model raises an exception during transcription."""

    @patch(WHISPER_MODEL_PATCH)
    def test_transcription_runtime_error(self, mock_cls, tmp_path):
        provider = _build_provider(mock_cls)

        audio_file = tmp_path / "corrupt.wav"
        audio_file.write_bytes(b"corrupt data")

        provider._model.transcribe.side_effect = RuntimeError("Decoding failed")

        result = provider.transcribe(str(audio_file))

        assert result.success is False
        assert result.text == ""
        assert "Decoding failed" in result.error

    def test_model_load_failure(self):
        """The provider should raise RuntimeError if the model can't load."""
        with patch(
            WHISPER_MODEL_PATCH,
            side_effect=Exception("CUDA not available"),
        ):
            with pytest.raises(RuntimeError, match="Failed to load"):
                FasterWhisperProvider(model_size="large-v3", device="cuda")


# ---------------------------------------------------------------------------
# Invalid / missing audio path
# ---------------------------------------------------------------------------

class TestInvalidAudioPath:
    """Test 5: Missing or invalid audio file path."""

    @patch(WHISPER_MODEL_PATCH)
    def test_nonexistent_file(self, mock_cls):
        provider = _build_provider(mock_cls)

        result = provider.transcribe("/nonexistent/path/audio.wav")

        assert result.success is False
        assert result.text == ""
        assert "not found" in result.error

    @patch(WHISPER_MODEL_PATCH)
    def test_empty_path(self, mock_cls):
        provider = _build_provider(mock_cls)

        result = provider.transcribe("")

        assert result.success is False
        assert result.text == ""

    @patch(WHISPER_MODEL_PATCH)
    def test_none_path(self, mock_cls):
        provider = _build_provider(mock_cls)

        result = provider.transcribe(None)

        assert result.success is False
        assert result.text == ""
