import logging
from typing import List, Dict, Any, Optional
from ml_backend.schemas.snapshot import CurrentIntakeHistory, SnapshotAlert
from ml_backend.schemas.document import ExtractedDocument
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum

logger = logging.getLogger(__name__)


class ConflictDetectorService:
    @staticmethod
    def _is_negation(text: Optional[str]) -> bool:
        if not text:
            return False
        cleaned = text.strip().lower()
        negations = [
            "no known",
            "nkda",
            "none",
            "nil",
            "no allergies",
            "no allergy",
            "no past history",
            "no past medical history",
            "no chronic illness",
            "no medical history",
            "denies",
            "not present"
        ]
        return any(neg in cleaned for neg in negations)

    def detect_conflicts(
        self,
        current_history: Optional[CurrentIntakeHistory] = None,
        extracted_documents: Optional[List[ExtractedDocument]] = None,
        patient_facts: Optional[List[PatientFact]] = None,
        historical_documents: Optional[List[ExtractedDocument]] = None,
        historical_facts: Optional[List[PatientFact]] = None
    ) -> List[SnapshotAlert]:
        """
        Analyze current clinical intake vs documented historical records to find contradictions.
        Flexible interface supporting both extracted_documents and historical_documents.
        """
        docs = extracted_documents or historical_documents or []
        facts = patient_facts or historical_facts or []

        alerts: List[SnapshotAlert] = []
        if not current_history:
            return alerts

        # 1. Check Allergy Inconsistencies
        historical_allergies = []
        for doc in docs:
            for allergy in doc.allergies:
                if allergy.substance:
                    historical_allergies.append((allergy.substance, doc.document_id))

        for fact in facts:
            if fact.type == FactTypeEnum.ALLERGY:
                historical_allergies.append((fact.normalized_value or fact.raw_value, fact.source_document_id))

        # Compare with current reported allergies
        curr_allergies_str = " ".join(current_history.allergies).lower() if current_history.allergies else ""
        if self._is_negation(curr_allergies_str) and historical_allergies:
            for sub, src_id in historical_allergies:
                alerts.append(
                    SnapshotAlert(
                        type="data_inconsistency",
                        severity="high",
                        message=f"Conflict: Patient denies allergies on kiosk intake ('{curr_allergies_str}'), but document {src_id} records allergy to '{sub}'.",
                        source_document_ids=[src_id]
                    )
                )

        # 2. Check Past Medical History Inconsistencies
        historical_conditions = []
        for doc in docs:
            for diag in doc.diagnoses:
                if diag.condition:
                    historical_conditions.append((diag.condition, doc.document_id))

        for fact in facts:
            if fact.type == FactTypeEnum.CONDITION:
                historical_conditions.append((fact.normalized_value or fact.raw_value, fact.source_document_id))

        curr_past_hx_str = " ".join(current_history.past_history).lower() if current_history.past_history else ""
        if self._is_negation(curr_past_hx_str) and historical_conditions:
            for cond, src_id in historical_conditions:
                alerts.append(
                    SnapshotAlert(
                        type="data_inconsistency",
                        severity="high",
                        message=f"Conflict: Patient reports no past medical history on intake, but past record {src_id} documents '{cond}'.",
                        source_document_ids=[src_id]
                    )
                )

        # 3. Check Chief Complaint vs Past Hospitalization
        for doc in docs:
            if doc.document_type and "discharge" in doc.document_type.value:
                for diag in doc.diagnoses:
                    if current_history.chief_complaint and diag.condition.lower() in current_history.chief_complaint.lower():
                        alerts.append(
                            SnapshotAlert(
                                type="recurrent_symptom",
                                severity="low",
                                message=f"Note: Current chief complaint '{current_history.chief_complaint}' matches prior hospitalization discharge diagnosis '{diag.condition}' in {doc.document_id}.",
                                source_document_ids=[doc.document_id]
                            )
                        )

        return alerts


conflict_detector_service = ConflictDetectorService()
