from typing import List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ml_backend.schemas.document import LabResultItem, ExtractedDocument
from ml_backend.schemas.medical_fact import PatientFact
from ml_backend.schemas.snapshot import CurrentIntakeHistory, SnapshotAlert
from ml_backend.services.lab_validator import lab_validator_service
from ml_backend.services.conflict_detector import conflict_detector_service

router = APIRouter(tags=["Clinical Validation & Safety"])


class LabBatchRequest(BaseModel):
    labs: List[LabResultItem] = Field(..., description="List of unvalidated or unclassified lab result items")


class ConflictCheckRequest(BaseModel):
    current_history: CurrentIntakeHistory = Field(..., description="Current kiosk intake session information")
    historical_facts: List[PatientFact] = Field(default_factory=list, description="Historical patient facts extracted from documents")
    historical_documents: List[ExtractedDocument] = Field(default_factory=list, description="Extracted medical documents")


class ConflictCheckResponse(BaseModel):
    conflicts_detected: int
    alerts: List[SnapshotAlert]


@router.post("/validate/labs", response_model=List[LabResultItem])
def validate_labs(batch: LabBatchRequest):
    """
    Deterministically validate a batch of lab results against standardized physiological reference ranges.
    """
    return lab_validator_service.validate_lab_results(batch.labs)


@router.post("/validate/conflicts", response_model=ConflictCheckResponse)
def check_clinical_conflicts(req: ConflictCheckRequest):
    """
    Detect clinical contradictions between current patient self-report at the kiosk and historical medical documents.
    """
    alerts = conflict_detector_service.detect_conflicts(
        current_history=req.current_history,
        historical_facts=req.historical_facts,
        historical_documents=req.historical_documents
    )
    return ConflictCheckResponse(
        conflicts_detected=len(alerts),
        alerts=alerts
    )
