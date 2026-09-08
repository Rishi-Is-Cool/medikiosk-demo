import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.database.connection import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    language = Column(String, default="en")
    abha_id = Column(String, unique=True, nullable=True, index=True)
    phone = Column(String, nullable=True)
    consent_granted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    histories = relationship("ClinicalHistory", back_populates="patient", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="patient", cascade="all, delete-orphan")
    lab_results = relationship("LabResult", back_populates="patient", cascade="all, delete-orphan")
    encounters = relationship("Encounter", back_populates="patient", cascade="all, delete-orphan")
    consents = relationship("ConsentRecord", back_populates="patient", cascade="all, delete-orphan")


class ClinicalHistory(Base):
    __tablename__ = "clinical_histories"

    id = Column(Integer, primary_key=True, index=True)
    history_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False)
    department_mode = Column(String, default="Allopathy")  # Allopathy or AYUSH
    chief_complaint = Column(Text, nullable=True)
    hpi = Column(Text, nullable=True)
    past_history = Column(Text, nullable=True)
    surgical_history = Column(Text, nullable=True)
    allergies = Column(Text, nullable=True)
    medications = Column(Text, nullable=True)
    family_history = Column(Text, nullable=True)
    personal_history = Column(Text, nullable=True)
    ros = Column(Text, nullable=True)
    ayush_data = Column(Text, nullable=True)  # JSON string of Dashavidha Pariksha
    red_flags = Column(Text, nullable=True)   # JSON array string
    summary = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft / confirmed / rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="histories")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    document_type = Column(String, default="prescription")  # prescription, lab_report, discharge_summary
    document_date = Column(String, nullable=True)
    ocr_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="documents")
    lab_results = relationship("LabResult", back_populates="document", cascade="all, delete-orphan")


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True, index=True)
    result_id = Column(String, unique=True, index=True, nullable=False)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=True)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False)
    test_name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    abnormal = Column(Boolean, default=False)
    category = Column(String, default="general")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    patient = relationship("Patient", back_populates="lab_results")
    document = relationship("Document", back_populates="lab_results")


# The tables below are intentionally additive.  ClinicalHistory and the early
# Document/LabResult tables remain supported for the original API while the
# integration API records a longitudinal, source-linked record.
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False, default="doctor")
    display_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class Encounter(Base):
    __tablename__ = "encounters"
    id = Column(Integer, primary_key=True)
    encounter_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    intake_framework = Column(String, default="allopathic", nullable=False)
    status = Column(String, default="intake_in_progress", nullable=False, index=True)
    priority = Column(String, default="normal", nullable=False)
    chief_complaint = Column(Text, nullable=True)
    language = Column(String, default="en", nullable=False)
    assigned_doctor_username = Column(String, nullable=True, index=True)
    started_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    finalized_at = Column(DateTime, nullable=True)
    finalized_by = Column(String, nullable=True)
    patient = relationship("Patient", back_populates="encounters")
    sessions = relationship("KioskSession", back_populates="encounter", cascade="all, delete-orphan")
    answers = relationship("IntakeAnswer", back_populates="encounter", cascade="all, delete-orphan")
    facts = relationship("ClinicalFact", back_populates="encounter", cascade="all, delete-orphan")
    alerts = relationship("ClinicalAlert", back_populates="encounter", cascade="all, delete-orphan")
    ledger_entries = relationship("LedgerEntry", back_populates="encounter", cascade="all, delete-orphan")


class KioskSession(Base):
    __tablename__ = "kiosk_sessions"
    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    encounter_id = Column(String, ForeignKey("encounters.encounter_id"), nullable=True, index=True)
    status = Column(String, default="active", nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    patient = relationship("Patient")
    encounter = relationship("Encounter", back_populates="sessions")


class ConsentRecord(Base):
    __tablename__ = "consent_records"
    id = Column(Integer, primary_key=True)
    consent_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    granted = Column(JSON, default=list, nullable=False)
    declined = Column(JSON, default=list, nullable=False)
    language = Column(String, default="en", nullable=False)
    audio_explanation_played = Column(Boolean, default=False, nullable=False)
    accepted_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    patient = relationship("Patient", back_populates="consents")


class UploadSession(Base):
    __tablename__ = "upload_sessions"
    id = Column(Integer, primary_key=True)
    token = Column(String, unique=True, index=True, nullable=False)
    session_id = Column(String, ForeignKey("kiosk_sessions.session_id"), nullable=False, index=True)
    status = Column(String, default="waiting", nullable=False)
    expires_at = Column(DateTime, nullable=False)
    document_ids = Column(JSON, default=list, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class IntakeAnswer(Base):
    __tablename__ = "intake_answers"
    id = Column(Integer, primary_key=True)
    answer_id = Column(String, unique=True, index=True, nullable=False)
    encounter_id = Column(String, ForeignKey("encounters.encounter_id"), nullable=False, index=True)
    question_id = Column(String, nullable=False)
    answer_text = Column(Text, nullable=True)
    values = Column(JSON, default=list, nullable=False)
    source = Column(String, nullable=False)
    language = Column(String, default="en", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    encounter = relationship("Encounter", back_populates="answers")
    transcripts = relationship("Transcript", back_populates="answer", cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"
    id = Column(Integer, primary_key=True)
    transcript_id = Column(String, unique=True, index=True, nullable=False)
    answer_id = Column(String, ForeignKey("intake_answers.answer_id"), nullable=True, index=True)
    text = Column(Text, nullable=False)
    language = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    provider = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    answer = relationship("IntakeAnswer", back_populates="transcripts")


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"
    id = Column(Integer, primary_key=True)
    extraction_id = Column(String, unique=True, index=True, nullable=False)
    document_id = Column(String, ForeignKey("documents.document_id"), nullable=False, index=True)
    provider = Column(String, nullable=False)
    status = Column(String, default="completed", nullable=False)
    payload = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class ClinicalFact(Base):
    __tablename__ = "clinical_facts"
    id = Column(Integer, primary_key=True)
    fact_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    encounter_id = Column(String, ForeignKey("encounters.encounter_id"), nullable=True, index=True)
    fact_type = Column(String, nullable=False, index=True)
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=True)
    details = Column(JSON, default=dict, nullable=False)
    status = Column(String, default="ai_extracted", nullable=False)
    confidence = Column(Float, nullable=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    supersedes_fact_id = Column(String, nullable=True)
    encounter = relationship("Encounter", back_populates="facts")
    provenance = relationship("FactProvenance", back_populates="fact", cascade="all, delete-orphan")


class FactProvenance(Base):
    __tablename__ = "fact_provenance"
    id = Column(Integer, primary_key=True)
    provenance_id = Column(String, unique=True, index=True, nullable=False)
    fact_id = Column(String, ForeignKey("clinical_facts.fact_id"), nullable=False, index=True)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    locator = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    fact = relationship("ClinicalFact", back_populates="provenance")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id = Column(Integer, primary_key=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    encounter_id = Column(String, nullable=True, index=True)
    event_date = Column(DateTime, nullable=True)
    event_type = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    source_type = Column(String, nullable=False)
    source_id = Column(String, nullable=False)
    details = Column(JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class ClinicalAlert(Base):
    __tablename__ = "clinical_alerts"
    id = Column(Integer, primary_key=True)
    alert_id = Column(String, unique=True, index=True, nullable=False)
    patient_id = Column(String, ForeignKey("patients.patient_id"), nullable=False, index=True)
    encounter_id = Column(String, ForeignKey("encounters.encounter_id"), nullable=True, index=True)
    severity = Column(String, nullable=False)
    rule = Column(String, nullable=False)
    headline = Column(Text, nullable=False)
    detail = Column(Text, nullable=True)
    sources = Column(JSON, default=list, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    encounter = relationship("Encounter", back_populates="alerts")


class PhysicianSnapshot(Base):
    __tablename__ = "physician_snapshots"
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String, unique=True, index=True, nullable=False)
    encounter_id = Column(String, ForeignKey("encounters.encounter_id"), nullable=False, index=True)
    payload = Column(JSON, default=dict, nullable=False)
    generated_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    initials = Column(String, nullable=True)
    qualifications = Column(String, nullable=True)
    title = Column(String, nullable=True)
    registration = Column(String, nullable=True)
    practitioner_type = Column(String, default="allopathy", nullable=False)
    clinic_name = Column(String, nullable=True)
    tagline = Column(String, nullable=True)
    slogan = Column(String, nullable=True)
    address = Column(String, nullable=True)
    department = Column(String, nullable=True)
    languages = Column(JSON, default=list, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)


class AdviceLibraryEntry(Base):
    __tablename__ = "advice_library_entries"
    id = Column(Integer, primary_key=True)
    advice_id = Column(String, unique=True, index=True, nullable=False)
    kind = Column(String, nullable=False)  # pathya / apathya
    text = Column(String, nullable=False)
    text_hi = Column(String, nullable=True)
    used_count = Column(Integer, default=0, nullable=False)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    ledger_id = Column(String, unique=True, index=True, nullable=False)
    encounter_id = Column(String, ForeignKey("encounters.encounter_id"), nullable=False, index=True)
    clinician_id = Column(String, nullable=False)
    treatment_change = Column(Boolean, default=False, nullable=False)
    previous_treatment = Column(Text, nullable=True)
    new_treatment = Column(Text, nullable=True)
    deviation_reason = Column(String, nullable=True)
    doctor_rationale = Column(Text, nullable=True)
    advice = Column(JSON, default=list, nullable=False)
    follow_up_required = Column(Boolean, default=False, nullable=False)
    follow_up_timeframe = Column(String, nullable=True)
    amendment_of = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    encounter = relationship("Encounter", back_populates="ledger_entries")
