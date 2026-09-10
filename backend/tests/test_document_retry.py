"""Prescription reading retries while the vision model is briefly overloaded."""
from app.api import integration


def test_busy_model_is_retried_then_succeeds(monkeypatch):
    calls = []

    def flaky(path, document_type, patient_id, document_id):
        calls.append(document_id)
        if len(calls) == 1:
            return {"success": False, "error": "Vision LLM Perception Error: 503 UNAVAILABLE. high demand"}
        return {"success": True, "error": None, "diagnoses": ["Hypertension"]}

    monkeypatch.setattr(integration, "extract_and_normalize", flaky)
    monkeypatch.setattr(integration, "_OCR_RETRY_DELAYS", (0, 0))
    result = integration._read_document("x.jpg", "prescription", "pat_1", "doc_1")
    assert result["success"] is True and len(calls) == 2


def test_permanent_failure_is_not_retried(monkeypatch):
    calls = []

    def broken(path, document_type, patient_id, document_id):
        calls.append(document_id)
        return {"success": False, "error": "Schema validation failed: not a document"}

    monkeypatch.setattr(integration, "extract_and_normalize", broken)
    monkeypatch.setattr(integration, "_OCR_RETRY_DELAYS", (0, 0))
    assert integration._read_document("x.jpg", "prescription", "pat_1", "doc_1")["success"] is False
    assert len(calls) == 1
