"""
MediKiosk Backend — Admin & System Dashboard API
Provides system-wide statistics, patient queue management, and OPD dashboard endpoints.
Used by hospital administration and OPD supervisor screens.
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.connection import get_db
from app.database.schemas import Patient, ClinicalHistory, Document, LabResult
from app.utils.security import decode_token

router = APIRouter(prefix="/api/admin", tags=["Admin & OPD Dashboard"])
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def _require_admin(payload: str = Depends(_oauth2_scheme)) -> None:
    """These endpoints list every patient in the hospital by name — the same
    kind of hospital-wide access the /admin/overview endpoints in
    integration.py are scoped to, so they get the same gate."""
    if decode_token(payload).get("role") != "admin":
        raise HTTPException(403, "Admin access required")


@router.get(
    "/stats",
    summary="System-wide statistics dashboard for hospital administration"
)
def get_system_stats(db: Session = Depends(get_db), _: None = Depends(_require_admin)):
    """
    Returns aggregate statistics for the OPD administration dashboard:
    - Total patients registered today and all-time
    - Summaries generated (draft vs confirmed)
    - Documents digitized
    - Red flag / emergency patients today
    - Allopathy vs AYUSH breakdown
    """
    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime(today.year, today.month, today.day)

    total_patients = db.query(func.count(Patient.id)).scalar()
    patients_today = db.query(func.count(Patient.id)).filter(
        Patient.created_at >= today_start
    ).scalar()

    total_histories = db.query(func.count(ClinicalHistory.id)).scalar()
    draft_histories = db.query(func.count(ClinicalHistory.id)).filter(
        ClinicalHistory.status == "draft"
    ).scalar()
    confirmed_histories = db.query(func.count(ClinicalHistory.id)).filter(
        ClinicalHistory.status == "confirmed"
    ).scalar()
    histories_today = db.query(func.count(ClinicalHistory.id)).filter(
        ClinicalHistory.created_at >= today_start
    ).scalar()

    ayush_count = db.query(func.count(ClinicalHistory.id)).filter(
        ClinicalHistory.department_mode == "AYUSH"
    ).scalar()
    allopathy_count = total_histories - ayush_count

    total_documents = db.query(func.count(Document.id)).scalar()
    docs_today = db.query(func.count(Document.id)).filter(
        Document.created_at >= today_start
    ).scalar()

    total_labs = db.query(func.count(LabResult.id)).scalar()
    abnormal_labs = db.query(func.count(LabResult.id)).filter(
        LabResult.abnormal == True
    ).scalar()

    return {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "patients": {
            "total": total_patients,
            "registered_today": patients_today
        },
        "clinical_summaries": {
            "total": total_histories,
            "today": histories_today,
            "draft": draft_histories,
            "confirmed": confirmed_histories,
            "allopathy_mode": allopathy_count,
            "ayush_mode": ayush_count
        },
        "documents_digitized": {
            "total": total_documents,
            "today": docs_today
        },
        "lab_results": {
            "total_extracted": total_labs,
            "abnormal_flagged": abnormal_labs
        },
        "system_health": "operational"
    }


@router.get(
    "/patients",
    summary="List all registered patients (paginated)"
)
def list_all_patients(
    skip: int = 0,
    limit: int = 50,
    q: str | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """
    Returns paginated list of all registered patients, optionally filtered
    by name or ABHA number (q). Used by the hospital-wide patient directory,
    OPD token queue, and physician dashboard.
    """
    query = db.query(Patient)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter((Patient.name.ilike(like)) | (Patient.abha_id.ilike(like)))
    total = query.with_entities(func.count(Patient.id)).scalar()
    patients = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "patients": [
            {
                "patient_id": p.patient_id,
                "name": p.name,
                "age": p.age,
                "gender": p.gender,
                "language": p.language,
                "abha_id": p.abha_id,
                "consent_granted": p.consent_granted,
                "registered_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in patients
        ]
    }


@router.get(
    "/queue/today",
    summary="Today's OPD patient queue with intake completion status"
)
def get_today_queue(db: Session = Depends(get_db), _: None = Depends(_require_admin)):
    """
    Returns the list of patients registered today and whether their
    clinical history intake is complete (has a summary generated).
    Used by OPD triage desk and physician queue screens.
    """
    today = datetime.datetime.utcnow().date()
    today_start = datetime.datetime(today.year, today.month, today.day)

    patients_today = db.query(Patient).filter(
        Patient.created_at >= today_start
    ).order_by(Patient.created_at).all()

    queue = []
    for idx, p in enumerate(patients_today, start=1):
        latest_history = (
            db.query(ClinicalHistory)
            .filter(ClinicalHistory.patient_id == p.patient_id)
            .order_by(ClinicalHistory.created_at.desc())
            .first()
        )
        import json
        red_flags = []
        if latest_history and latest_history.red_flags:
            try:
                red_flags = json.loads(latest_history.red_flags)
            except Exception:
                pass

        queue.append({
            "token": idx,
            "patient_id": p.patient_id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender,
            "language": p.language,
            "intake_status": latest_history.status if latest_history else "not_started",
            "department_mode": latest_history.department_mode if latest_history else "—",
            "chief_complaint": latest_history.chief_complaint if latest_history else "—",
            "is_emergency": any(rf.get("priority") == "P1_CRITICAL" for rf in red_flags),
            "red_flags_count": len(red_flags),
            "registered_at": p.created_at.isoformat() if p.created_at else None
        })

    # Sort: emergencies first, then by token number
    queue.sort(key=lambda x: (not x["is_emergency"], x["token"]))

    return {
        "date": today.isoformat(),
        "total_in_queue": len(queue),
        "emergencies": sum(1 for q in queue if q["is_emergency"]),
        "queue": queue
    }
