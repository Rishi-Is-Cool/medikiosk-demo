from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from ml_backend.schemas.medical_fact import PatientFact
from ml_backend.schemas.timeline import TimelineEvent
from ml_backend.schemas.document import ExtractedDocument, LabResultItem
from ml_backend.schemas.snapshot import CurrentIntakeHistory


class QueryPatternEnum(str, Enum):
    LAST_VISIT = "last_visit"
    DIABETES_HISTORY = "diabetes_history"
    MEDICATION_CHANGE = "medication_change"
    HOSPITALIZATION = "hospitalization"
    ALLERGIES = "allergies"
    GENERAL = "general"


class SourceReference(BaseModel):
    document_id: str
    document_type: Optional[str] = None
    date: Optional[str] = None
    excerpt: Optional[str] = None


class DoctorQARequest(BaseModel):
    patient_id: Optional[str] = "P_DEMO_001"
    question: str = Field(..., description="Doctor's clinical question")
    query_type: Optional[QueryPatternEnum] = None
    context_facts: List[PatientFact] = Field(default_factory=list)
    context_timeline: List[TimelineEvent] = Field(default_factory=list)
    context_labs: List[LabResultItem] = Field(default_factory=list)
    context_documents: List[ExtractedDocument] = Field(default_factory=list)
    current_history: Optional[CurrentIntakeHistory] = None


class DoctorQAResponse(BaseModel):
    question: str
    interpreted_pattern: QueryPatternEnum
    answer: str
    source_references: List[SourceReference] = Field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    data_available: bool = True
    confidence: float = 1.0
