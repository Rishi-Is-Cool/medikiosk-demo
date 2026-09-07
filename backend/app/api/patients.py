import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.database.connection import get_db
from app.database.schemas import ClinicalFact, Encounter, Patient, TimelineEvent
from app.models.pydantic_models import PatientCreate, PatientResponse
from app.integrations.abdm import abdm_service

router = APIRouter(prefix="/api/patients", tags=["Patients & ABHA Registration"])


def _patient_summary(db: Session, patient: Patient) -> Dict[str, Any]:
    encounters = db.query(Encounter).filter(Encounter.patient_id == patient.patient_id).order_by(Encounter.started_at.desc()).all()
    facts = db.query(ClinicalFact).filter(ClinicalFact.patient_id == patient.patient_id).all()
    conditions = sorted({f.normalized_value or f.raw_value for f in facts if f.fact_type == "condition"})
    allergies = sorted({f.raw_value for f in facts if f.fact_type == "allergy"})
    finalized = [e for e in encounters if e.finalized_at]
    last_visit = max((e.finalized_at for e in finalized), default=None)
    open_encounter = next((e for e in encounters if e.status != "finalized"), None)
    department = "Ayurveda" if any(e.intake_framework == "ayush" for e in encounters) else "General med"
    return {
        "patient_id": patient.patient_id, "name": patient.name, "age_years": patient.age, "sex": patient.gender.lower(),
        "abha_id": patient.abha_id, "department": department,
        "last_visit": last_visit.strftime("%Y-%m-%d") if last_visit else None,
        "next_appointment": None,
        "visits": len(encounters), "conditions": conditions, "allergies": allergies,
        "encounter_id": open_encounter.encounter_id if open_encounter else None,
    }

@router.post("/register", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(patient_in: PatientCreate, db: Session = Depends(get_db)):
    # Check if ABHA ID is provided and verify
    if patient_in.abha_id:
        verification = abdm_service.verify_abha_number(patient_in.abha_id)
        if not verification["verified"]:
            raise HTTPException(status_code=400, detail="Invalid ABHA ID provided")

    new_patient_id = f"PAT-{uuid.uuid4().hex[:8].upper()}"

    db_patient = Patient(
        patient_id=new_patient_id,
        name=patient_in.name,
        age=patient_in.age,
        gender=patient_in.gender,
        language=patient_in.language or "hi",
        abha_id=patient_in.abha_id,
        phone=patient_in.phone,
        consent_granted=patient_in.consent_granted
    )

    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient


@router.get("")
def list_patients(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Every patient on file, not just today's queue — the doctor console's patient directory."""
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    return [_patient_summary(db, p) for p in patients]


@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    summary = _patient_summary(db, patient)
    events = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient_id).order_by(TimelineEvent.event_date.desc()).all()
    summary["timeline"] = [{"date": e.event_date.strftime("%Y-%m-%d") if e.event_date else None, "type": e.event_type,
                             "title": e.summary, "detail": None, "by": None} for e in events]
    summary["appointments"] = []  # no scheduling system exists in this backend yet
    summary["language"] = patient.language
    summary["phone"] = patient.phone
    summary["consent_granted"] = patient.consent_granted
    return summary


@router.get("/verify-abha/{abha_id}")
def verify_abha(abha_id: str):
    return abdm_service.verify_abha_number(abha_id)
