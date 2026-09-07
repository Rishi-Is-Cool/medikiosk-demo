import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from ml_backend.config import settings
from ml_backend.schemas.snapshot import (
    CurrentIntakeHistory,
    SnapshotRequest,
    PhysicianSnapshot,
    SnapshotAlert
)
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum
from ml_backend.schemas.timeline import TimelineEvent
from ml_backend.schemas.document import ExtractedDocument, LabResultItem
from ml_backend.services.llm_client import get_llm_client
from ml_backend.services.conflict_detector import conflict_detector_service

logger = logging.getLogger(__name__)


class SnapshotGeneratorService:
    def __init__(self, prompt_path: Optional[str] = None):
        self.prompt_path = prompt_path or str(settings.PROMPTS_DIR / "snapshot_generation.txt")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load prompt from {self.prompt_path}: {e}")
            return "Synthesize the patient intake and medical documents into a structured clinical snapshot."

    def generate_snapshot(
        self,
        request: SnapshotRequest,
        provider: Optional[str] = None
    ) -> PhysicianSnapshot:
        """
        Synthesize current clinical intake, historical facts, labs, timeline, and conflict alerts.
        """
        # Step 1: Detect deterministic conflicts and alerts
        detected_alerts: List[SnapshotAlert] = conflict_detector_service.detect_conflicts(
            current_history=request.current_history,
            extracted_documents=request.documents,
            patient_facts=request.facts
        )

        # Step 2: Format structured payload for LLM synthesis
        user_payload = {
            "patient_id": request.patient_id or "P_DEMO_001",
            "current_history": request.current_history.model_dump() if request.current_history else None,
            "patient_facts": [f.model_dump() for f in request.facts],
            "timeline": [t.model_dump() for t in request.timeline],
            "documents_summary": [
                {
                    "document_id": d.document_id,
                    "document_type": d.document_type.value,
                    "date": d.document_date,
                    "hospital": d.hospital_name,
                    "doctor": d.doctor_name,
                    "diagnoses": [diag.condition for diag in d.diagnoses],
                    "medications": [m.name for m in d.medications],
                    "allergies": [a.substance for a in d.allergies]
                }
                for d in request.documents
            ],
            "lab_results": [l.model_dump() for l in request.lab_results],
            "detected_alerts": [a.model_dump() for a in detected_alerts]
        }

        user_content_str = json.dumps(user_payload, indent=2, default=str)

        # Step 3: Invoke synthesis LLM
        llm_client = get_llm_client(provider)
        try:
            raw_result = llm_client.generate_text_synthesis(
                system_prompt=self.prompt_template,
                user_content=user_content_str
            )
            snapshot = PhysicianSnapshot.model_validate(raw_result)
        except Exception as e:
            logger.warning(f"LLM Snapshot generation failed or returned invalid schema: {e}. Building deterministic fallback.", exc_info=True)
            snapshot = self._build_deterministic_snapshot(request, detected_alerts)

        # Ensure all detected alerts are included in snapshot.alerts
        existing_alert_msgs = {a.message for a in snapshot.alerts}
        for da in detected_alerts:
            if da.message not in existing_alert_msgs:
                snapshot.alerts.append(da)

        snapshot.generated_at = datetime.now(timezone.utc).isoformat()
        return snapshot

    def _build_deterministic_snapshot(
        self,
        request: SnapshotRequest,
        alerts: List[SnapshotAlert]
    ) -> PhysicianSnapshot:
        """Deterministic rule-based fallback snapshot ensuring 100% reliability."""
        curr = request.current_history
        chief_complaint = curr.chief_complaint if curr else "Not documented"
        if curr and curr.duration:
            chief_complaint += f" for {curr.duration}"

        hpi = curr.hpi if curr and curr.hpi else (
            f"Patient presents with {chief_complaint}. Associated symptoms: {', '.join(curr.symptoms) if curr and curr.symptoms else 'None reported'}."
        )

        pmh = []
        for f in request.facts:
            if f.type == FactTypeEnum.CONDITION:
                pmh.append({
                    "condition": f.normalized_value or f.raw_value,
                    "raw_term": f.raw_value,
                    "date_recorded": f.date_recorded,
                    "source_document_ids": [f.source_document_id]
                })

        meds = []
        for f in request.facts:
            if f.type == FactTypeEnum.MEDICATION:
                meds.append({
                    "name": f.normalized_value or f.raw_value,
                    "dosage": f.details.get("dosage"),
                    "frequency": f.details.get("normalized_frequency") or f.details.get("raw_frequency"),
                    "source_document_ids": [f.source_document_id]
                })

        allergies = []
        for f in request.facts:
            if f.type == FactTypeEnum.ALLERGY:
                allergies.append({
                    "substance": f.normalized_value or f.raw_value,
                    "reaction": f.details.get("reaction"),
                    "source_document_ids": [f.source_document_id]
                })

        labs = []
        for l in request.lab_results:
            labs.append({
                "test_name": l.test_name,
                "value": l.value,
                "unit": l.unit,
                "reference_range": l.reference_range,
                "abnormal": l.abnormal,
                "interpretation": l.interpretation,
                "source_document_ids": [l.source.document_id] if l.source else []
            })

        timeline_summary = []
        for ev in request.timeline:
            timeline_summary.append({
                "date": ev.event_date or "Not documented",
                "event": ev.summary,
                "source_document_id": ev.source_document_id
            })

        return PhysicianSnapshot(
            patient_id=request.patient_id or "P_DEMO_001",
            chief_complaint=chief_complaint,
            hpi=hpi,
            past_medical_history=pmh,
            past_surgical_history=[],
            medications=meds,
            allergies=allergies,
            family_history=[],
            personal_history=[],
            review_of_systems=[{"symptoms": curr.symptoms, "source": "current_intake"}] if curr and curr.symptoms else [],
            previous_investigations=labs,
            timeline_summary=timeline_summary,
            alerts=alerts
        )


snapshot_generator_service = SnapshotGeneratorService()
