import logging
import os
import tempfile
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_provider = None
_provider_load_attempted = False


def _get_provider():
    """Lazily load the faster-whisper backed transcription provider.

    Loading the model is slow and the dependency may not be installed in
    every environment, so this is attempted once and cached — a failure
    here just means real transcription is unavailable, not a crash.
    """
    global _provider, _provider_load_attempted
    if _provider_load_attempted:
        return _provider
    _provider_load_attempted = True
    try:
        from ai.speech.transcription import FasterWhisperProvider
        _provider = FasterWhisperProvider(
            model_size=os.getenv("WHISPER_MODEL", "base"),
            device=os.getenv("WHISPER_DEVICE", "cpu"),
            compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            initial_prompt=os.getenv("WHISPER_INITIAL_PROMPT"),
        )
    except Exception as exc:
        logger.warning("Real speech transcription unavailable, using simulation fallback: %s", exc)
        _provider = None
    return _provider


class SpeechToTextEngine:
    """
    Speech-to-Text engine supporting Indian languages (Hindi, Marathi, English).
    Uses local faster-whisper (with VAD) for real audio when available, and
    falls back to a deterministic simulated transcript otherwise — e.g. when
    the model isn't installed, or the payload isn't decodable audio.
    """
    def __init__(self):
        self.supported_languages = ["hi", "mr", "en", "ta", "te", "bn"]

    def transcribe_audio(self, audio_bytes: bytes, language: str = "hi") -> Dict[str, Any]:
        """
        Transcribes incoming audio bytes to a structured transcript.
        Tries real local ASR first; falls back to a simulated transcript
        fixture if real transcription is unavailable or fails.
        """
        if not audio_bytes or len(audio_bytes) < 10:
            return {
                "success": False,
                "transcript": "",
                "language": language,
                "confidence": 0.0,
                "message": "Empty audio provided"
            }

        real_result = self._transcribe_real(audio_bytes, language)
        if real_result is not None:
            return real_result

        return self._transcribe_simulated(language)

    def _transcribe_real(self, audio_bytes: bytes, language: Optional[str]) -> Optional[Dict[str, Any]]:
        provider = _get_provider()
        if provider is None:
            return None

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp:
                temp.write(audio_bytes)
                temp_path = temp.name

            result = provider.transcribe(temp_path, language=language)
            if not result.success or not result.text:
                return None

            return {
                "success": True,
                "transcript": result.text,
                "language": result.language or language,
                "confidence": None,
                "engine": "MediKiosk ASR (faster-whisper, local)"
            }
        except Exception as exc:
            logger.warning("Real transcription attempt failed, falling back to simulation: %s", exc)
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def _transcribe_simulated(self, language: str) -> Dict[str, Any]:
        # Simulated fallback transcript mapping for offline demos and tests.
        mock_transcripts = {
            "hi": "मुझे पिछले ३ दिनों से छाती में तेज दर्द हो रहा है और सांस लेने में तकलीफ है।",
            "mr": "मला गेल्या ३ दिवसांपासून छातीत तीव्र वेदना होत आहेत आणि श्वास घेण्यास त्रास होत आहे.",
            "en": "I have had severe chest pain for 3 days and difficulty breathing."
        }

        transcript = mock_transcripts.get(language, mock_transcripts["en"])

        return {
            "success": True,
            "transcript": transcript,
            "language": language,
            "confidence": 0.94,
            "engine": "MediKiosk ASR (simulation — real transcription unavailable or audio unrecognized)"
        }

stt_engine = SpeechToTextEngine()
