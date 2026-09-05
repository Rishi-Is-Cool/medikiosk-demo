import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float
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
