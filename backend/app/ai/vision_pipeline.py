"""
MediKiosk Backend — Document Vision Intelligence Adapter
Bridges the FastAPI backend to the ml_backend/ document intelligence service
(Vision LLM extraction, terminology normalization, deterministic lab validation)
built for MediKiosk's Module B, so the backend no longer relies on the
regex-only OCR/extraction stubs.
"""
import logging
import mimetypes
import os
from typing import Any, Dict

from ml_backend.services.vision_extract import vision_extraction_service
from ml_backend.services.llm_client import get_llm_client
from ml_backend.config import settings

logger = logging.getLogger(__name__)

_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
    ".tiff": "image/tiff",
    ".webp": "image/webp",
}


def _guess_mime(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return _MIME_MAP.get(ext) or mimetypes.guess_type(file_path)[0] or "image/jpeg"


def extract_and_normalize(
    file_path: str,
    document_type: str,
    patient_id: str,
    document_id: str,
) -> Dict[str, Any]:
    """
    Run the full vision intelligence pipeline (perception, terminology
    normalization, deterministic lab validation) on a saved document file and
    return a flat dict compatible with the backend's document/lab DB models.
    """
    with open(file_path, "rb") as f:
        image_bytes = f.read()

    # The document_type hint from the kiosk upload form isn't consumed by the
    # vision model directly, but folding it into the id keeps the built-in
    # MockLLMClient's demo fixtures on-topic when no live provider key is set.
    biased_id = f"{document_id}_{document_type}"

    result = vision_extraction_service.extract_document(
        image_bytes=image_bytes,
        mime_type=_guess_mime(file_path),
        document_id=biased_id,
        patient_id=patient_id,
    )
    extraction = result.extraction

    ocr_text_parts = list(extraction.clinical_notes)
    for collection in (
        extraction.diagnoses,
        extraction.medications,
        extraction.allergies,
        extraction.procedures,
        extraction.surgeries,
        extraction.lab_results,
    ):
        for item in collection:
            if getattr(item, "raw_text", None):
                ocr_text_parts.append(item.raw_text)

    engine_used = (
        f"Vision Intelligence Pipeline ({settings.VISION_LLM_PROVIDER}/{settings.VISION_LLM_MODEL})"
        if settings.VISION_LLM_API_KEY
        else "Vision Intelligence Pipeline (demo mode — set GEMINI_API_KEY for live extraction)"
    )

    return {
        "success": result.success,
        "ocr_text": "\n".join(ocr_text_parts),
        "extracted_date": extraction.document_date,
        "document_type": extraction.document_type.value,
        "engine_used": engine_used,
        "error": result.errors[0] if result.errors else None,
        "diagnoses": [d.condition for d in extraction.diagnoses],
        "medications": [
            {
                "name": m.name,
                "dosage": m.dosage or "Standard",
                "frequency": m.frequency or "As directed",
            }
            for m in extraction.medications
        ],
        "lab_results": [
            {
                "test_name": l.test_name,
                "value": l.value,
                "unit": l.unit,
                "reference_range": l.reference_range,
                "abnormal": l.abnormal,
                "interpretation": l.interpretation,
                "category": "Blood Test",
            }
            for l in extraction.lab_results
        ],
        "normalized_facts": result.normalized_facts,
    }


def extract_identity(image_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    """Best-effort OCR of an ABHA/Aadhaar card photo — name + ID number only.

    Never used to verify identity against anything (the kiosk build spec is
    explicit about this); it just fills a form field the patient can correct.
    Reuses the same vision LLM client as document extraction with a distinct
    prompt. Degrades cleanly with no result when no live provider is
    configured — the mock client below has no notion of an identity card.
    """
    prompt = (
        "This is a photo of an Indian patient identity card (ABHA health ID "
        "or Aadhaar). Extract the printed full name and the ID number exactly "
        "as printed (digits only for the number, no spaces or dashes). "
        'Respond as JSON: {"name": string or null, "identifier": string or null}.'
    )
    client = get_llm_client()
    try:
        raw = client.extract_document_vision(
            image_bytes=image_bytes, mime_type=mime_type, prompt=prompt, document_id="identity_scan"
        )
    except Exception as exc:
        logger.warning("Identity scan failed: %s", exc)
        return {"name": None, "identifier": None}
    return {"name": raw.get("name"), "identifier": raw.get("identifier")}
