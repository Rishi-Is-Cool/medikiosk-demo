import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database.schemas import Patient
from app.models.pydantic_models import PatientCreate, PatientResponse
from app.integrations.abdm import abdm_service

router = APIRouter(prefix="/api/patients", tags=["Patients & ABHA Registration"])

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


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/verify-abha/{abha_id}")
def verify_abha(abha_id: str):
    return abdm_service.verify_abha_number(abha_id)
