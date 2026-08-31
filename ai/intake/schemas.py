"""AI clinical intake data schema and contract for MediKiosk.

Defines structured Pydantic models for capturing patient-reported chief complaints,
symptoms (SOCRATES format), medical history, medications, allergies, and metadata.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChiefComplaint(BaseModel):
    """Primary reason for the patient's visit or clinical encounter."""

    name: str = Field(..., description="Name or phrase describing the chief complaint.")
    normalized_name: Optional[str] = Field(
        default=None, description="Standardized or normalized clinical term if available."
    )
    duration: Optional[str] = Field(
        default=None, description="Human-readable duration (e.g., '3 days', 'since yesterday')."
    )
    severity: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Patient-reported severity on a scale from 0 to 10.",
    )
    source: Optional[str] = Field(
        default=None, description="Source of extraction (e.g., 'transcript', 'user_input')."
    )


class Symptom(BaseModel):
    """Structured symptom details supporting SOCRATES clinical exploration."""

    name: str = Field(..., description="Name or description of the symptom.")
    normalized_name: Optional[str] = Field(
        default=None, description="Standardized or normalized clinical term if available."
    )
    site: Optional[str] = Field(
        default=None, description="Anatomical location or site of the symptom."
    )
    onset: Optional[str] = Field(
        default=None, description="Manner or timing of onset (e.g., sudden, gradual)."
    )
    duration: Optional[str] = Field(
        default=None, description="Human-readable duration (e.g., '2 weeks', '3 hours')."
    )
    character: Optional[str] = Field(
        default=None, description="Nature/character of the symptom (e.g., throbbing, sharp, dull)."
    )
    radiation: Optional[str] = Field(
        default=None, description="Radiation or spread to other anatomical areas."
    )
    associations: List[str] = Field(
        default_factory=list,
        description="Associated symptoms or physiological signs reported alongside.",
    )
    timing: Optional[str] = Field(
        default=None, description="Pattern or timing course (e.g., constant, intermittent, worse at night)."
    )
    aggravating_factors: List[str] = Field(
        default_factory=list,
        description="Factors, triggers, or activities that worsen the symptom.",
    )
    relieving_factors: List[str] = Field(
        default_factory=list,
        description="Factors, remedies, or positions that alleviate the symptom.",
    )
    severity: Optional[int] = Field(
        default=None,
        ge=0,
        le=10,
        description="Symptom severity on a scale from 0 to 10.",
    )
    negated: bool = Field(
        default=False,
        description="True if the patient explicitly denied or negated experiencing this symptom.",
    )
    source: Optional[str] = Field(
        default=None, description="Source snippet or extraction origin."
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score between 0.0 and 1.0.",
    )


class MedicalCondition(BaseModel):
    """Past or current medical condition reported by the patient."""

    name: str = Field(..., description="Name of the medical condition or diagnosis.")
    normalized_name: Optional[str] = Field(
        default=None, description="Standardized or normalized clinical term if available."
    )
    status: Optional[str] = Field(
        default=None, description="Current status of the condition (e.g., active, resolved, chronic)."
    )
    source: Optional[str] = Field(
        default=None, description="Source snippet or extraction origin."
    )


class Medication(BaseModel):
    """Current or recent medication reported by the patient."""

    name: str = Field(..., description="Name of the medication.")
    dose: Optional[str] = Field(
        default=None, description="Dosage information (e.g., '500mg', '1 tablet')."
    )
    frequency: Optional[str] = Field(
        default=None, description="Frequency of intake (e.g., 'twice daily', 'PRN as needed')."
    )
    source: Optional[str] = Field(
        default=None, description="Source snippet or extraction origin."
    )


class Allergy(BaseModel):
    """Reported allergy or adverse substance reaction."""

    substance: str = Field(..., description="Allergen or substance causing reaction (e.g., 'Penicillin', 'Peanuts').")
    reaction: Optional[str] = Field(
        default=None, description="Description of the allergic reaction (e.g., 'hives', 'rash', 'swelling')."
    )
    severity: Optional[str] = Field(
        default=None, description="Qualitative severity of reaction (e.g., 'mild', 'moderate', 'severe', 'anaphylaxis')."
    )
    source: Optional[str] = Field(
        default=None, description="Source snippet or extraction origin."
    )


class IntakeMetadata(BaseModel):
    """Contextual metadata regarding the clinical intake session."""

    patient_id: Optional[str] = Field(
        default=None, description="Optional patient identifier if known at intake time."
    )
    language: str = Field(
        ..., description="Language used during the intake session (e.g., 'en', 'es', 'hi')."
    )
    intake_mode: str = Field(
        ..., description="Intake interaction modality (e.g., 'audio', 'text', 'kiosk_voice')."
    )
    timestamp: datetime = Field(
        ..., description="Timestamp marking when the intake session took place."
    )


class IntakeResponse(BaseModel):
    """Main structured clinical intake data contract produced by the AI layer."""

    patient_id: Optional[str] = Field(
        default=None, description="Optional patient identifier."
    )
    language: str = Field(
        ..., description="Primary language of the intake conversation."
    )
    chief_complaint: Optional[ChiefComplaint] = Field(
        default=None, description="Primary chief complaint reported by the patient."
    )
    symptoms: List[Symptom] = Field(
        default_factory=list, description="List of structured symptoms captured."
    )
    medical_history: List[MedicalCondition] = Field(
        default_factory=list, description="List of past or chronic medical conditions."
    )
    medications: List[Medication] = Field(
        default_factory=list, description="List of current medications reported."
    )
    allergies: List[Allergy] = Field(
        default_factory=list, description="List of known allergies reported."
    )
    metadata: IntakeMetadata = Field(
        ..., description="Intake session metadata and provenance details."
    )
