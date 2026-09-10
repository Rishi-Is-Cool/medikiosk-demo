"""
MediKiosk Backend — Medicine catalog and prescription templates.
Both are specialty-scoped: a general-medicine doctor never sees Ayurvedic
formulation names or another doctor's templates, and vice versa.
"""
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.schemas import DoctorProfile, Medicine, PrescriptionTemplate
from app.models.pydantic_models import TemplateRequest
from app.utils.security import decode_token

router = APIRouter(prefix="/api", tags=["Prescribing"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def _doctor(payload: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    data = decode_token(payload)
    if data.get("role") not in {"doctor", "admin"}:
        raise HTTPException(403, "Doctor access required")
    return data


def _specialty(db: Session, username: str) -> str:
    profile = db.query(DoctorProfile).filter(DoctorProfile.username == username).first()
    if not profile:
        raise HTTPException(404, "No profile on file for this account")
    return profile.practitioner_type


def _medicine_payload(m: Medicine) -> Dict[str, Any]:
    return {"id": m.medicine_id, "name": m.name, "form": m.form, "strength": m.strength, "used_count": m.used_count}


def _template_payload(t: PrescriptionTemplate) -> Dict[str, Any]:
    return {"id": t.template_id, "name": t.name, "diagnosis_label": t.diagnosis_label,
            "medicines": t.medicines or [], "advice_ids": t.advice_ids or []}


@router.get("/medicines")
def list_medicines(q: Optional[str] = None, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    specialty = _specialty(db, clinician.get("sub"))
    query = db.query(Medicine).filter(Medicine.practitioner_type == specialty)
    if q:
        query = query.filter(Medicine.name.ilike(f"%{q}%"))
    medicines = query.order_by(Medicine.used_count.desc(), Medicine.name).all()
    return [_medicine_payload(m) for m in medicines]


@router.get("/templates")
def list_templates(clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    templates = (db.query(PrescriptionTemplate)
                 .filter(PrescriptionTemplate.owner_username == clinician.get("sub"))
                 .order_by(PrescriptionTemplate.name).all())
    return [_template_payload(t) for t in templates]


@router.post("/templates", status_code=201)
def create_template(payload: TemplateRequest, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    template = PrescriptionTemplate(template_id=f"tpl_{uuid.uuid4().hex[:16]}", owner_username=clinician.get("sub"),
                                    name=payload.name, diagnosis_label=payload.diagnosis_label,
                                    medicines=payload.medicines, advice_ids=payload.advice_ids)
    db.add(template)
    db.commit()
    db.refresh(template)
    return _template_payload(template)


def _own_template(db: Session, template_id: str, clinician: Dict[str, Any]) -> PrescriptionTemplate:
    template = db.query(PrescriptionTemplate).filter(PrescriptionTemplate.template_id == template_id).first()
    if not template:
        raise HTTPException(404, "Template not found")
    if template.owner_username != clinician.get("sub"):
        raise HTTPException(403, "This template belongs to a different doctor")
    return template


@router.put("/templates/{template_id}")
def update_template(template_id: str, payload: TemplateRequest, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    template = _own_template(db, template_id, clinician)
    template.name = payload.name
    template.diagnosis_label = payload.diagnosis_label
    template.medicines = payload.medicines
    template.advice_ids = payload.advice_ids
    db.commit()
    db.refresh(template)
    return _template_payload(template)


@router.delete("/templates/{template_id}", status_code=204)
def delete_template(template_id: str, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    template = _own_template(db, template_id, clinician)
    db.delete(template)
    db.commit()
