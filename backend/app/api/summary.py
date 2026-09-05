"""
MediKiosk Backend — Structured History Summary Generator API
POST /api/summary/generate/{patient_id}  — AI generates physician-ready clinical summary
GET  /api/summary/{patient_id}           — Fetch the latest stored summary for a patient
PUT  /api/summary/confirm/{history_id}  — Physician confirms / edits the summary
"""
import uuid
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import Patient, ClinicalHistory, LabResult
from app.models.pydantic_models import ClinicalSummaryResponse, SummaryUpdateRequest
from app.ai.history_extractor import history_extractor
from app.ai.red_flag_detector import red_flag_detector
from app.ai.summary_generator import summary_generator

router = APIRouter(prefix="/api/summary", tags=["Structured History Summary Generator"])


@router.post("/generate/{patient_id}", response_model=ClinicalSummaryResponse)
def generate_summary(
    patient_id: str,
    department_mode: str = "Allopathy",
    answers: Dict[str, Any] = Body(default={}),
    db: Session = Depends(get_db)
):
    """
    AI-powered clinical summary generation from interview answers.
    Combines conversational history, red-flag detection, OCR lab data,
    and AYUSH Dashavidha Pariksha (if AYUSH mode) into a single structured document.
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # ── Step 1: Extract structured clinical history domains from interview answers ──
    extracted_history = history_extractor.extract_history(answers, department_mode=department_mode)

    # ── Step 2: Fetch all stored lab results for this patient (from prior OCR docs) ─
    labs_db = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    lab_list = [
        {
            "test_name": l.test_name,
            "value": l.value,
            "unit": l.unit,
            "reference_range": l.reference_range,
            "abnormal": l.abnormal
        } for l in labs_db
    ]

    # ── Step 3: Evaluate for emergency red flags ─────────────────────────────────
    text_corpus = f"{extracted_history['chief_complaint']} {extracted_history['hpi']}"
    red_flags = red_flag_detector.check_red_flags(text_corpus, answers=answers)

    patient_dict = {
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "abha_id": patient.abha_id,
        "language": patient.language
    }

    # ── Step 4: Generate final physician-facing summary markdown ─────────────────
    summary_output = summary_generator.generate_physician_summary(
        patient_info=patient_dict,
        history_data=extracted_history,
        lab_results=lab_list,
        red_flags=red_flags,
        department_mode=department_mode
    )

    history_uuid = f"HIST-{uuid.uuid4().hex[:8].upper()}"

    # ── Step 5: Persist clinical history record ───────────────────────────────────
    db_history = ClinicalHistory(
        history_id=history_uuid,
        patient_id=patient_id,
        department_mode=department_mode,
        chief_complaint=extracted_history["chief_complaint"],
        hpi=extracted_history["hpi"],
        past_history=extracted_history["past_history"],
        surgical_history=extracted_history["surgical_history"],
        allergies=extracted_history["allergies"],
        medications=extracted_history["medications"],
        family_history=extracted_history["family_history"],
        personal_history=extracted_history["personal_history"],
        ros=extracted_history["ros"],
        ayush_data=extracted_history["ayush_data"],
        red_flags=json.dumps(red_flags),
        summary=summary_output["formatted_summary_markdown"],
        status="draft"
    )

    db.add(db_history)
    db.commit()
    db.refresh(db_history)

    return {
        "patient_id": patient_id,
        "history_id": db_history.history_id,
        "patient_name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "department_mode": department_mode,
        "chief_complaint": extracted_history["chief_complaint"],
        "hpi": extracted_history["hpi"],
        "past_history": extracted_history["past_history"],
        "surgical_history": extracted_history["surgical_history"],
        "allergies": extracted_history["allergies"],
        "medications": extracted_history["medications"],
        "family_history": extracted_history["family_history"],
        "personal_history": extracted_history["personal_history"],
        "review_of_systems": extracted_history["ros"],
        "ayush_dashavidha_summary": summary_output["ayush_dashavidha_summary"],
        "lab_timeline_summary": lab_list,
        "red_flags": red_flags,
        "formatted_summary_markdown": summary_output["formatted_summary_markdown"],
        "audio_summary_text": summary_output["audio_summary_text"],
        "status": db_history.status
    }


@router.get("/{patient_id}", response_model=ClinicalSummaryResponse)
def get_patient_summary(patient_id: str, db: Session = Depends(get_db)):
    """
    Retrieve the most recent confirmed or draft clinical summary for a patient.
    Used by the physician's consultation screen to display the pre-generated history.
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
    if not history:
        raise HTTPException(status_code=404, detail="No clinical summary found for this patient. Generate one first via POST /api/summary/generate/{patient_id}")

    labs_db = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    lab_list = [
        {
            "test_name": l.test_name,
            "value": l.value,
            "unit": l.unit,
            "reference_range": l.reference_range,
            "abnormal": l.abnormal
        } for l in labs_db
    ]

    red_flags = json.loads(history.red_flags) if history.red_flags else []
    ayush_data = json.loads(history.ayush_data) if history.ayush_data else None

    return {
        "patient_id": patient_id,
        "history_id": history.history_id,
        "patient_name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "department_mode": history.department_mode,
        "chief_complaint": history.chief_complaint or "",
        "hpi": history.hpi or "",
        "past_history": history.past_history or "",
        "surgical_history": history.surgical_history or "",
        "allergies": history.allergies or "",
        "medications": history.medications or "",
        "family_history": history.family_history or "",
        "personal_history": history.personal_history or "",
        "review_of_systems": history.ros or "",
        "ayush_dashavidha_summary": ayush_data,
        "lab_timeline_summary": lab_list,
        "red_flags": red_flags,
        "formatted_summary_markdown": history.summary or "",
        "audio_summary_text": f"Clinical summary for {patient.name} is ready for physician review.",
        "status": history.status
    }


@router.put("/confirm/{history_id}")
def confirm_or_update_summary(
    history_id: str,
    update_in: SummaryUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Physician edits and confirms the AI-generated clinical intake summary.
    The AI-generated summary is always a draft — physician has full editorial control.
    """
    history = db.query(ClinicalHistory).filter(ClinicalHistory.history_id == history_id).first()
    if not history:
        raise HTTPException(status_code=404, detail="Clinical history record not found")

    if update_in.chief_complaint is not None:
        history.chief_complaint = update_in.chief_complaint
    if update_in.hpi is not None:
        history.hpi = update_in.hpi
    if update_in.past_history is not None:
        history.past_history = update_in.past_history
    if update_in.medications is not None:
        history.medications = update_in.medications
    if update_in.allergies is not None:
        history.allergies = update_in.allergies
    if update_in.status is not None:
        history.status = update_in.status

    db.commit()
    return {
        "success": True,
        "history_id": history_id,
        "status": history.status,
        "message": "Physician confirmed and updated clinical intake summary."
    }
