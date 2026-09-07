import os
import json
import logging
from typing import Optional, Dict, Any, List
from ml_backend.config import settings
from ml_backend.schemas.document import (
    ExtractedDocument,
    DocumentExtractionResponse,
    DocumentTypeEnum,
    SourceProvenance,
    LabResultItem
)
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum
from ml_backend.services.llm_client import get_llm_client
from ml_backend.services.normalization import normalization_service
from ml_backend.services.lab_validator import lab_validator_service
from ml_backend.services.timeline import timeline_service

logger = logging.getLogger(__name__)


class DocumentExtractionError(Exception):
    """Raised when document extraction or schema validation fails explicitly."""
    pass


class VisionExtractionService:
    def __init__(self, prompt_path: Optional[str] = None):
        self.prompt_path = prompt_path or str(settings.PROMPTS_DIR / "document_extraction.txt")
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        try:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"Could not load prompt from {self.prompt_path}: {e}")
            return "Extract all medical entities from document into structured JSON."

    def extract_document(
        self,
        image_bytes: bytes,
        mime_type: str,
        document_id: str,
        patient_id: Optional[str] = "P_DEMO_001",
        provider: Optional[str] = None
    ) -> DocumentExtractionResponse:
        """
        Orchestrate complete document perception, validation, normalization, and fact extraction.
        Guarantees strict schema validation with explicit error reporting on malformed output.
        """
        if not image_bytes:
            raise DocumentExtractionError("Cannot extract from empty document payload.")

        llm_client = get_llm_client(provider)

        try:
            raw_dict = llm_client.extract_document_vision(
                image_bytes=image_bytes,
                mime_type=mime_type,
                prompt=self.prompt_template,
                document_id=document_id
            )
        except Exception as e:
            logger.error(f"Vision LLM extraction failed for document {document_id}: {e}", exc_info=True)
            return DocumentExtractionResponse(
                success=False,
                document_id=document_id,
                document_type=DocumentTypeEnum.UNKNOWN,
                confidence=0.0,
                extraction=ExtractedDocument(
                    document_id=document_id,
                    document_type=DocumentTypeEnum.UNKNOWN,
                    confidence=0.0
                ),
                errors=[f"Vision LLM Perception Error: {str(e)}"]
            )

        # Ensure document_id is matched
        raw_dict["document_id"] = document_id
        if "document_type" not in raw_dict:
            raw_dict["document_type"] = "unknown"

        # Strict Pydantic Schema Validation (P1 Fix: No silent swallowing into UNKNOWN)
        try:
            extracted_doc = ExtractedDocument.model_validate(raw_dict)
        except Exception as e:
            logger.error(f"Pydantic schema validation failure for document {document_id}: {e}")
            return DocumentExtractionResponse(
                success=False,
                document_id=document_id,
                document_type=DocumentTypeEnum.UNKNOWN,
                confidence=0.0,
                extraction=ExtractedDocument(
                    document_id=document_id,
                    document_type=DocumentTypeEnum.UNKNOWN,
                    confidence=0.0
                ),
                errors=[f"Schema validation failed: LLM output violates ExtractedDocument contract: {str(e)}"]
            )

        # 1. Deterministic Lab Validation on lab_results
        validated_labs: List[LabResultItem] = []
        for lab in extracted_doc.lab_results:
            validated_lab = lab_validator_service.validate_lab_item(lab)
            validated_lab.source = SourceProvenance(
                document_id=document_id,
                document_type=extracted_doc.document_type.value
            )
            validated_labs.append(validated_lab)
        extracted_doc.lab_results = validated_labs

        # 2. Enrich Source Provenance on all entities
        doc_prov = SourceProvenance(
            document_id=document_id,
            document_type=extracted_doc.document_type.value
        )
        for d in extracted_doc.diagnoses:
            d.source = doc_prov
        for m in extracted_doc.medications:
            m.source = doc_prov
        for a in extracted_doc.allergies:
            a.source = doc_prov
            a.source_document_id = document_id
        for p in extracted_doc.procedures:
            p.source = doc_prov
        for s in extracted_doc.surgeries:
            s.source = doc_prov
        for fu in extracted_doc.follow_up:
            fu.source = doc_prov

        # 3. Generate Normalized Patient Facts
        facts: List[PatientFact] = []

        # Diagnoses / Conditions
        for d in extracted_doc.diagnoses:
            fact = normalization_service.create_patient_fact(
                fact_type=FactTypeEnum.CONDITION,
                raw_val=d.condition,
                source_doc_id=document_id,
                date_recorded=extracted_doc.document_date,
                confidence=extracted_doc.confidence,
                details={"status": d.status, "code": d.code}
            )
            facts.append(fact)

        # Medications
        for m in extracted_doc.medications:
            norm_freq = normalization_service.normalize_frequency(m.frequency or "")
            norm_route = normalization_service.normalize_route(m.route or "")
            fact = normalization_service.create_patient_fact(
                fact_type=FactTypeEnum.MEDICATION,
                raw_val=m.name,
                source_doc_id=document_id,
                date_recorded=extracted_doc.document_date,
                confidence=extracted_doc.confidence,
                details={
                    "dosage": m.dosage,
                    "frequency": norm_freq.normalized_value or m.frequency,
                    "raw_frequency": m.frequency,
                    "duration": m.duration,
                    "route": norm_route.normalized_value or m.route
                }
            )
            facts.append(fact)

        # Allergies
        for a in extracted_doc.allergies:
            fact = normalization_service.create_patient_fact(
                fact_type=FactTypeEnum.ALLERGY,
                raw_val=a.substance,
                source_doc_id=document_id,
                date_recorded=extracted_doc.document_date,
                confidence=extracted_doc.confidence,
                details={"reaction": a.reaction, "severity": a.severity}
            )
            facts.append(fact)

        # Procedures
        for p in extracted_doc.procedures:
            fact = normalization_service.create_patient_fact(
                fact_type=FactTypeEnum.PROCEDURE,
                raw_val=p.name,
                source_doc_id=document_id,
                date_recorded=p.date or extracted_doc.document_date,
                confidence=extracted_doc.confidence,
                details={"indication": p.indication}
            )
            facts.append(fact)

        # Surgeries
        for s in extracted_doc.surgeries:
            fact = normalization_service.create_patient_fact(
                fact_type=FactTypeEnum.SURGERY,
                raw_val=s.procedure_name,
                source_doc_id=document_id,
                date_recorded=s.date or extracted_doc.document_date,
                confidence=extracted_doc.confidence,
                details={"implants": s.implants, "outcome": s.outcome}
            )
            facts.append(fact)

        # Lab Investigations
        for l in extracted_doc.lab_results:
            fact = normalization_service.create_patient_fact(
                fact_type=FactTypeEnum.INVESTIGATION,
                raw_val=l.test_name,
                source_doc_id=document_id,
                date_recorded=extracted_doc.document_date,
                confidence=extracted_doc.confidence,
                details={
                    "value": l.value,
                    "unit": l.unit,
                    "reference_range": l.reference_range,
                    "abnormal": l.abnormal,
                    "interpretation": l.interpretation
                }
            )
            facts.append(fact)

        # 4. Generate Timeline Events
        timeline_res = timeline_service.build_chronological_timeline([extracted_doc])

        return DocumentExtractionResponse(
            success=True,
            document_id=document_id,
            document_type=extracted_doc.document_type,
            confidence=extracted_doc.confidence,
            extraction=extracted_doc,
            normalized_facts=facts,
            timeline_events=timeline_res.events,
            errors=[]
        )


vision_extraction_service = VisionExtractionService()
