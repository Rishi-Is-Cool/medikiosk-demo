"""
MediKiosk Backend — FHIR R4 & ABDM Interoperability API
FHIR export and ABDM integration endpoints for HIS push and consent management.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import Patient, ClinicalHistory, LabResult
from app.integrations.fhir import fhir_converter
from app.integrations.abdm import abdm_service

router = APIRouter(prefix="/api/fhir", tags=["FHIR R4 & ABDM Interoperability"])


@router.get(
    "/export/{patient_id}",
    summary="Export complete patient clinical record as FHIR R4 Bundle JSON"
)
def export_fhir_bundle(patient_id: str, db: Session = Depends(get_db)):
    """
    Generates a valid HL7 FHIR R4 Bundle containing:
    - Patient resource (with ABHA identifier)
    - Condition resource (Chief complaint)
    - Observation resources (Lab results from OCR)
    - Composition resource (Clinical summary)
    Compatible with ABDM Health Information Exchange (HIE-CM) standards.
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    history = (
        db.query(ClinicalHistory)
        .filter(ClinicalHistory.patient_id == patient_id)
        .order_by(ClinicalHistory.created_at.desc())
        .first()
    )
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()

    patient_dict = {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "abha_id": patient.abha_id,
        "phone": patient.phone
    }

    history_dict = {
        "chief_complaint": history.chief_complaint if history else "General Clinical Consultation",
        "hpi": history.hpi if history else "",
        "summary": history.summary if history else ""
    }

    lab_list = [
        {
            "test_name": l.test_name,
            "value": l.value,
            "unit": l.unit,
            "reference_range": l.reference_range,
            "abnormal": l.abnormal
        } for l in labs
    ]

    bundle = fhir_converter.build_fhir_bundle(patient_dict, history_dict, lab_list)
    return bundle


@router.post(
    "/push-to-his/{patient_id}",
    summary="Push FHIR bundle to Hospital Information System (HIS / EMR)"
)
def push_to_his(patient_id: str, db: Session = Depends(get_db)):
    """
    Pushes the patient's structured FHIR clinical record to the hospital HIS/EMR.
    This simulates the ABDM Health Information Provider (HIP) gateway push.
    In production, this connects to the hospital's FHIR-enabled HIS via ABDM APIs.
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    bundle = export_fhir_bundle(patient_id, db=db)
    result = abdm_service.push_to_hospital_his(patient_id, bundle)
    return result


@router.post(
    "/consent/{patient_id}",
    summary="Generate ABDM-compliant Digital Health Consent Artefact for patient"
)
def generate_consent(patient_id: str, db: Session = Depends(get_db)):
    """
    Creates a DPDPA 2023 and ABDM Consent Framework compliant consent record.
    Consent is required before any clinical data is linked to ABHA and shared.
    In production, this integrates with the ABDM Consent Manager (HIE-CM).
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not patient.consent_granted:
        raise HTTPException(
            status_code=403,
            detail="Patient has not granted consent. Cannot generate consent artefact."
        )

    consent_artefact = abdm_service.generate_consent_artefact(
        patient_id=patient_id,
        abha_id=patient.abha_id or f"TEMP-{patient_id}"
    )
    return consent_artefact
