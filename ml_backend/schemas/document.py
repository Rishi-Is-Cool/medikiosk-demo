from enum import Enum
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field


class DocumentTypeEnum(str, Enum):
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    DISCHARGE_SUMMARY = "discharge_summary"
    UNKNOWN = "unknown"


class SourceProvenance(BaseModel):
    document_id: str
    document_type: Optional[str] = None
    page_number: Optional[int] = None
    section: Optional[str] = None


class MedicationItem(BaseModel):
    name: str = Field(..., description="Medication or brand name")
    dosage: Optional[str] = Field(None, description="Strength / dosage (e.g. 500 mg)")
    frequency: Optional[str] = Field(None, description="Frequency (e.g. BD, OD, TDS)")
    duration: Optional[str] = Field(None, description="Duration (e.g. 5 days, 1 month)")
    route: Optional[str] = Field(None, description="Route (e.g. Oral, IV)")
    raw_text: Optional[str] = Field(None, description="Raw text from document")
    source: Optional[SourceProvenance] = None


class LabResultItem(BaseModel):
    test_name: str = Field(..., description="Name of laboratory test")
    value: Optional[Any] = Field(None, description="Numeric or string value")
    unit: Optional[str] = Field(None, description="Measurement unit (e.g. %, mg/dL)")
    reference_range: Optional[str] = Field(None, description="Reference / biological interval")
    abnormal: Optional[bool] = Field(None, description="True if abnormal, False if normal, null if indeterminate")
    interpretation: Optional[str] = Field(None, description="High / Low / Normal / Indeterminate")
    raw_text: Optional[str] = Field(None, description="Raw text as appeared in document")
    source: Optional[SourceProvenance] = None


class DiagnosisItem(BaseModel):
    condition: str
    code: Optional[str] = None
    status: Optional[str] = None  # e.g., active, chronic, resolved, provisional
    raw_text: Optional[str] = None
    source: Optional[SourceProvenance] = None


class AllergyItem(BaseModel):
    substance: str
    reaction: Optional[str] = None
    severity: Optional[str] = None
    source_document_id: Optional[str] = None
    source: Optional[SourceProvenance] = None


class ProcedureItem(BaseModel):
    name: str
    date: Optional[str] = None
    indication: Optional[str] = None
    source: Optional[SourceProvenance] = None


class FollowUpItem(BaseModel):
    instructions: str
    date: Optional[str] = None
    doctor_or_dept: Optional[str] = None
    source: Optional[SourceProvenance] = None


class ExtractedDocument(BaseModel):
    document_id: str
    document_type: DocumentTypeEnum = DocumentTypeEnum.UNKNOWN
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    document_date: Optional[str] = Field(None, description="Date in YYYY-MM-DD or raw format if year/month only")
    patient_name: Optional[str] = None
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None

    diagnoses: List[DiagnosisItem] = Field(default_factory=list)
    medications: List[MedicationItem] = Field(default_factory=list)
    allergies: List[AllergyItem] = Field(default_factory=list)
    procedures: List[ProcedureItem] = Field(default_factory=list)
    surgeries: List[ProcedureItem] = Field(default_factory=list)
    lab_results: List[LabResultItem] = Field(default_factory=list)
    clinical_notes: List[str] = Field(default_factory=list)
    follow_up: List[FollowUpItem] = Field(default_factory=list)
    raw_entities: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentExtractionRequest(BaseModel):
    document_id: str
    patient_id: Optional[str] = "P_DEMO_001"
    session_id: Optional[str] = "SESS_001"
    image_base64: Optional[str] = None
    image_url: Optional[str] = None
    file_path: Optional[str] = None
    mime_type: Optional[str] = "image/jpeg"


class DocumentExtractionResponse(BaseModel):
    success: bool = True
    document_id: str
    document_type: DocumentTypeEnum
    confidence: float
    extraction: ExtractedDocument
    normalized_facts: List[Any] = Field(default_factory=list)
    timeline_events: List[Any] = Field(default_factory=list)
    errors: Optional[List[str]] = None
