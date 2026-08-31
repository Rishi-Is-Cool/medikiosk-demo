"""Intake submodule for MediKiosk AI."""

from ai.intake.schemas import (
    Allergy,
    ChiefComplaint,
    IntakeMetadata,
    IntakeResponse,
    MedicalCondition,
    Medication,
    Symptom,
)
from ai.intake.provider import ClinicalExtractionProvider, ExtractionResult

__all__ = [
    "ChiefComplaint",
    "Symptom",
    "MedicalCondition",
    "Medication",
    "Allergy",
    "IntakeMetadata",
    "IntakeResponse",
    "ClinicalExtractionProvider",
    "ExtractionResult",
]

from ai.intake.gemini_provider import GeminiClinicalExtractionProvider
__all__.append('GeminiClinicalExtractionProvider')
