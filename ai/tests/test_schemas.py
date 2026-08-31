"""Unit tests for AI clinical intake schemas."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from ai.intake.schemas import (
    Allergy,
    ChiefComplaint,
    IntakeMetadata,
    IntakeResponse,
    MedicalCondition,
    Medication,
    Symptom,
)


def test_complete_valid_intake_response():
    """Test 1: Creating a complete valid IntakeResponse with all fields populated."""
    now = datetime.now(timezone.utc)
    chief_complaint = ChiefComplaint(
        name="Chest discomfort and shortness of breath",
        normalized_name="Chest pain",
        duration="3 days",
        severity=7,
        source="transcript_001",
    )
    symptom = Symptom(
        name="Sharp chest pain",
        normalized_name="Precordial pain",
        site="Substernal",
        onset="Sudden",
        duration="3 days",
        character="Sharp, stabbing",
        radiation="Left arm and jaw",
        associations=["Nausea", "Diaphoresis"],
        timing="Constant, worse on exertion",
        aggravating_factors=["Walking uphill", "Deep inspiration"],
        relieving_factors=["Rest"],
        severity=8,
        negated=False,
        source="transcript_001",
        confidence=0.95,
    )
    condition = MedicalCondition(
        name="Hypertension",
        normalized_name="Essential hypertension",
        status="chronic",
        source="transcript_001",
    )
    medication = Medication(
        name="Amlodipine",
        dose="5mg",
        frequency="once daily",
        source="transcript_001",
    )
    allergy = Allergy(
        substance="Penicillin",
        reaction="Urticaria and facial swelling",
        severity="moderate",
        source="transcript_001",
    )
    metadata = IntakeMetadata(
        patient_id="PT-98765",
        language="en",
        intake_mode="kiosk_voice",
        timestamp=now,
    )

    intake = IntakeResponse(
        patient_id="PT-98765",
        language="en",
        chief_complaint=chief_complaint,
        symptoms=[symptom],
        medical_history=[condition],
        medications=[medication],
        allergies=[allergy],
        metadata=metadata,
    )

    assert intake.patient_id == "PT-98765"
    assert intake.language == "en"
    assert intake.chief_complaint is not None
    assert intake.chief_complaint.name == "Chest discomfort and shortness of breath"
    assert intake.chief_complaint.severity == 7
    assert len(intake.symptoms) == 1
    assert intake.symptoms[0].character == "Sharp, stabbing"
    assert intake.symptoms[0].confidence == 0.95
    assert len(intake.medical_history) == 1
    assert len(intake.medications) == 1
    assert len(intake.allergies) == 1
    assert intake.metadata.intake_mode == "kiosk_voice"


def test_missing_optional_fields():
    """Test 2: Creating an intake object with missing optional fields."""
    now = datetime.now(timezone.utc)
    metadata = IntakeMetadata(
        language="en",
        intake_mode="text",
        timestamp=now,
    )

    # Chief complaint with only required field
    cc = ChiefComplaint(name="Headache")
    assert cc.name == "Headache"
    assert cc.normalized_name is None
    assert cc.duration is None
    assert cc.severity is None
    assert cc.source is None

    # Symptom with only required field
    sym = Symptom(name="Throbbing pain")
    assert sym.name == "Throbbing pain"
    assert sym.site is None
    assert sym.associations == []
    assert sym.aggravating_factors == []
    assert sym.relieving_factors == []
    assert sym.negated is False
    assert sym.confidence is None

    # Minimal intake response without optional top-level fields
    intake = IntakeResponse(
        language="en",
        metadata=metadata,
    )
    assert intake.patient_id is None
    assert intake.chief_complaint is None
    assert intake.symptoms == []
    assert intake.medical_history == []
    assert intake.medications == []
    assert intake.allergies == []
    assert intake.metadata.patient_id is None


def test_empty_lists_default():
    """Test 3: Empty symptoms, medications, and allergies lists default safely."""
    now = datetime.now(timezone.utc)
    metadata = IntakeMetadata(
        language="es",
        intake_mode="audio",
        timestamp=now,
    )

    intake = IntakeResponse(
        language="es",
        metadata=metadata,
    )

    assert isinstance(intake.symptoms, list)
    assert len(intake.symptoms) == 0
    assert isinstance(intake.medical_history, list)
    assert len(intake.medical_history) == 0
    assert isinstance(intake.medications, list)
    assert len(intake.medications) == 0
    assert isinstance(intake.allergies, list)
    assert len(intake.allergies) == 0

    # Also check symptom-level list defaults
    symptom = Symptom(name="Cough")
    assert symptom.associations == []
    assert symptom.aggravating_factors == []
    assert symptom.relieving_factors == []


def test_invalid_severity_values():
    """Test 4: Invalid severity values below 0 and above 10 are rejected."""
    # ChiefComplaint severity validation
    with pytest.raises(ValidationError):
        ChiefComplaint(name="Fever", severity=-1)

    with pytest.raises(ValidationError):
        ChiefComplaint(name="Fever", severity=11)

    # Valid boundary cases for ChiefComplaint
    cc_0 = ChiefComplaint(name="Fever", severity=0)
    assert cc_0.severity == 0
    cc_10 = ChiefComplaint(name="Fever", severity=10)
    assert cc_10.severity == 10

    # Symptom severity validation
    with pytest.raises(ValidationError):
        Symptom(name="Back pain", severity=-5)

    with pytest.raises(ValidationError):
        Symptom(name="Back pain", severity=15)

    # Valid boundary cases for Symptom
    sym_0 = Symptom(name="Back pain", severity=0)
    assert sym_0.severity == 0
    sym_10 = Symptom(name="Back pain", severity=10)
    assert sym_10.severity == 10


def test_invalid_confidence_values():
    """Test 5: Invalid confidence values below 0.0 and above 1.0 are rejected."""
    with pytest.raises(ValidationError):
        Symptom(name="Dizziness", confidence=-0.1)

    with pytest.raises(ValidationError):
        Symptom(name="Dizziness", confidence=1.05)

    # Valid boundary cases
    sym_0 = Symptom(name="Dizziness", confidence=0.0)
    assert sym_0.confidence == 0.0

    sym_1 = Symptom(name="Dizziness", confidence=1.0)
    assert sym_1.confidence == 1.0


def test_medical_condition_and_medication_and_allergy():
    """Test models for conditions, medications, and allergies with various field configurations."""
    cond = MedicalCondition(name="Type 2 Diabetes")
    assert cond.name == "Type 2 Diabetes"
    assert cond.status is None

    med = Medication(name="Metformin", dose="500mg")
    assert med.name == "Metformin"
    assert med.dose == "500mg"
    assert med.frequency is None

    allergy = Allergy(substance="Sulfa drugs")
    assert allergy.substance == "Sulfa drugs"
    assert allergy.reaction is None
    assert allergy.severity is None
