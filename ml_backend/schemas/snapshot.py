from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ml_backend.schemas.medical_fact import PatientFact
from ml_backend.schemas.timeline import TimelineEvent
from ml_backend.schemas.document import ExtractedDocument, LabResultItem


class CurrentIntakeHistory(BaseModel):
    chief_complaint: str = Field(..., description="Primary reason for current encounter")
    duration: Optional[str] = Field(None, description="Duration of symptoms")
    symptoms: List[str] = Field(default_factory=list)
    hpi: Optional[str] = Field(None, description="History of present illness narrative")
    past_history: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    family_history: List[str] = Field(default_factory=list)
    personal_history: List[str] = Field(default_factory=list)
    ros: List[str] = Field(default_factory=list)


class SnapshotAlert(BaseModel):
    type: str = Field(..., description="Alert category: data_inconsistency, abnormal_lab, allergy_warning, etc.")
    message: str = Field(..., description="Clinical alert description")
    severity: str = Field("medium", description="high, medium, low")
    source_document_ids: List[str] = Field(default_factory=list)


class SnapshotRequest(BaseModel):
    patient_id: Optional[str] = "P_DEMO_001"
    current_history: Optional[CurrentIntakeHistory] = None
    facts: List[PatientFact] = Field(default_factory=list)
    timeline: List[TimelineEvent] = Field(default_factory=list)
    documents: List[ExtractedDocument] = Field(default_factory=list)
    lab_results: List[LabResultItem] = Field(default_factory=list)


class PhysicianSnapshot(BaseModel):
    patient_id: Optional[str] = "P_DEMO_001"
    generated_at: Optional[str] = None
    chief_complaint: str
    hpi: str
    past_medical_history: List[Dict[str, Any]] = Field(default_factory=list)
    past_surgical_history: List[Dict[str, Any]] = Field(default_factory=list)
    medications: List[Dict[str, Any]] = Field(default_factory=list)
    allergies: List[Dict[str, Any]] = Field(default_factory=list)
    family_history: List[Dict[str, Any]] = Field(default_factory=list)
    personal_history: List[Dict[str, Any]] = Field(default_factory=list)
    review_of_systems: List[Dict[str, Any]] = Field(default_factory=list)
    previous_investigations: List[Dict[str, Any]] = Field(default_factory=list)
    timeline_summary: List[Dict[str, Any]] = Field(default_factory=list)
    alerts: List[SnapshotAlert] = Field(default_factory=list)
    clinical_disclaimer: str = (
        "Draft intake synthesis prepared by AI for attending physician review. "
        "Not a diagnostic claim or prescription. Attending physician is the sole clinical decision-maker."
    )
