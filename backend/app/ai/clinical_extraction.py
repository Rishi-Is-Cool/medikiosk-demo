"""
MediKiosk Backend — Structured Clinical Extraction Adapter
Bridges the FastAPI backend to the ai/intake/ Gemini extraction provider
(Module A), turning a raw voice transcript into structured chief complaint,
symptoms, history, medications and allergies. Optional: only runs when
GEMINI_API_KEY is configured, and never raises — callers get None on failure
so the deterministic SOCRATES/AYUSH interview flow is unaffected.
"""
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_provider = None
_provider_load_attempted = False


def _get_provider():
    """Lazily construct the Gemini extraction provider (no-op without a key)."""
    global _provider, _provider_load_attempted
    if _provider_load_attempted:
        return _provider
    _provider_load_attempted = True
    if not os.getenv("GEMINI_API_KEY"):
        logger.info("Clinical extraction: GEMINI_API_KEY not set, structured extraction disabled.")
        return None
    try:
        from ai.intake.gemini_provider import GeminiClinicalExtractionProvider
        _provider = GeminiClinicalExtractionProvider()
    except Exception as exc:
        logger.warning("Clinical extraction provider unavailable: %s", exc)
        _provider = None
    return _provider


def extract_from_transcript(
    text: str,
    language: Optional[str] = None,
    patient_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run Gemini structured clinical extraction on free-text (a voice transcript).
    Returns a JSON-serialisable dict on success, or None when no provider is
    configured or extraction failed — callers should treat this as optional
    enrichment, not a required step.
    """
    provider = _get_provider()
    if provider is None or not text or not text.strip():
        return None

    result = provider.extract(text=text, language=language, patient_id=patient_id)
    if not result.success or result.data is None:
        logger.info("Clinical extraction did not produce structured data: %s", result.error)
        return None

    return result.data.model_dump(mode="json")
