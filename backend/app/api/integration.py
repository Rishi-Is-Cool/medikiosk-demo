"""Kiosk and doctor-console integration API for the MVP."""
from __future__ import annotations

import os
import shutil
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, joinedload

from app.ai.vision_pipeline import extract_and_normalize
from app.database.connection import get_db
from app.database.schemas import (ClinicalAlert, ClinicalFact, ConsentRecord, Document, DocumentExtraction,
    Encounter, FactProvenance, KioskSession, LedgerEntry, Patient, PhysicianSnapshot, TimelineEvent, Transcript, UploadSession)
from app.models.pydantic_models import (ConsentSubmission, DoctorQuestionRequest, LedgerRequest, RegistrationRequest,
    StartIntakeRequestV2, SubmitIntakeAnswerRequest)
from app.services.integration import (add_timeline_event, create_fact, kiosk_question, now, persist_answer,
    persist_red_flags, priority_state, ref, require_session, source_for_fact)
from app.utils.security import decode_token
from app.ai.whisper_provider import SpeechUnavailable, whisper_provider

kiosk_router = APIRouter(tags=["Kiosk Integration"])
doctor_router = APIRouter(prefix="/api", tags=["Doctor Integration"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}


def _session_payload(session: KioskSession, patient: Patient) -> Dict[str, Any]:
    return {"session_id": session.session_id, "patient_ref": patient.patient_id, "display_name": patient.name,
            "identity_method": "abha" if patient.abha_id else "new", "masked_id": ("****" + patient.abha_id[-4:]) if patient.abha_id else None,
            "age": patient.age, "sex": patient.gender.lower()}


@kiosk_router.post("/patient/register")
def kiosk_register(request: RegistrationRequest, db: Session = Depends(get_db)):
    data = request.new_patient or {}
    name = data.get("name") or request.identifier or "Patient"
    try:
        age = int(data.get("age", 0))
    except ValueError:
        age = 0
    if not name.strip() or age < 0:
        raise HTTPException(422, "A valid patient name and age are required")
    patient = Patient(patient_id=ref("pat"), name=name.strip(), age=age, gender=data.get("sex", "unknown"),
                      language=request.language, phone=data.get("phone"), abha_id=request.identifier if request.identity_method == "abha" else None,
                      consent_granted=False)
    db.add(patient); db.flush()
    session = KioskSession(session_id=ref("ks"), patient_id=patient.patient_id, expires_at=now() + timedelta(minutes=30))
    db.add(session); db.commit(); db.refresh(session)
    return _session_payload(session, patient)


@kiosk_router.get("/patient/session")
def kiosk_session(session_id: str, db: Session = Depends(get_db)):
    try: session = require_session(db, session_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    return _session_payload(session, session.patient)


@kiosk_router.post("/patient/consent")
def record_consent(request: ConsentSubmission, db: Session = Depends(get_db)):
    try: session = require_session(db, request.session_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    consent = ConsentRecord(consent_id=ref("consent"), patient_id=session.patient_id, session_id=session.session_id,
                            granted=request.granted, declined=request.declined, language=request.language,
                            audio_explanation_played=request.audio_explanation_played)
    db.add(consent); session.patient.consent_granted = bool(request.granted); db.commit()
    return {"consent_id": consent.consent_id, "accepted_at": consent.accepted_at.isoformat() + "Z"}


@kiosk_router.get("/intake/complaints")
def complaints(language: str = "en"):
    # The fixed taxonomy is deliberately server-owned; labels are fallback English where not translated.
    return [{"id": x, "label": label, "icon": "medical"} for x, label in [("chest_pain", "Chest pain"), ("fever_cough", "Fever and cough"), ("abdominal_pain", "Abdominal pain"), ("joint_pain", "Joint pain"), ("headache", "Headache"), ("breathlessness", "Difficulty breathing"), ("other", "Other")]]


@kiosk_router.post("/intake/match-complaint")
def match_complaint(body: Dict[str, str]):
    text = (body.get("transcript") or "").strip(); lower = text.lower()
    matches = [("chest_pain", "Chest pain", ("chest", "chati", "सीने")), ("fever_cough", "Fever and cough", ("fever", "cough", "bukhar", "बुखार")),
               ("breathlessness", "Difficulty breathing", ("breath", "shortness", "सांस"))]
    found = next(({"id": code, "label": label, "icon": "medical"} for code, label, words in matches if any(w in lower for w in words)), None)
    return {"complaint": found, "transcript": text}


@kiosk_router.post("/intake/start")
def start_intake(request: StartIntakeRequestV2, db: Session = Depends(get_db)):
    try: session = require_session(db, request.session_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    if not session.patient.consent_granted:
        raise HTTPException(409, "Consent is required before clinical intake")
    if session.encounter_id:
        encounter = db.query(Encounter).filter(Encounter.encounter_id == session.encounter_id).first()
        if encounter and encounter.status != "finalized": return kiosk_question(encounter, request.language)
    encounter = Encounter(encounter_id=ref("enc"), patient_id=session.patient_id, intake_framework=request.history_mode,
                          chief_complaint=request.chief_complaint_text or request.chief_complaint, language=request.language)
    db.add(encounter); db.flush(); session.encounter_id = encounter.encounter_id
    persist_answer(db, encounter, "q1_chief_complaint", "patient_touch", [], request.chief_complaint_text or request.chief_complaint, request.language)
    add_timeline_event(db, encounter.patient_id, encounter.encounter_id, "consultation", f"New encounter: {encounter.chief_complaint}", "encounter", encounter.encounter_id)
    db.commit(); db.refresh(encounter)
    return kiosk_question(encounter, request.language)


@kiosk_router.get("/intake/question")
def current_question(session_id: str, language: str = "en", db: Session = Depends(get_db)):
    try: session = require_session(db, session_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    encounter = db.query(Encounter).options(joinedload(Encounter.answers)).filter(Encounter.encounter_id == session.encounter_id).first()
    if not encounter: raise HTTPException(409, "Intake has not started")
    return kiosk_question(encounter, language)


@kiosk_router.post("/intake/answer")
def submit_intake_answer(request: SubmitIntakeAnswerRequest, db: Session = Depends(get_db)):
    try: session = require_session(db, request.session_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    encounter = db.query(Encounter).options(joinedload(Encounter.answers)).filter(Encounter.encounter_id == session.encounter_id).first()
    if not encounter: raise HTTPException(409, "Intake has not started")
    if encounter.status == "finalized": raise HTTPException(409, "Encounter is finalized")
    raw = request.answer.text or ", ".join(request.answer.values)
    if request.mode == "extract":
        return {"question_id": request.question_id, "summary": raw, "fields": [{"label": "Patient response", "value": raw}] if raw else [], "source": request.answer.source}
    answer = persist_answer(db, encounter, request.question_id, request.answer.source, request.answer.values, request.answer.text, request.language)
    flags = persist_red_flags(db, encounter, raw)
    db.commit(); db.refresh(encounter)
    result = kiosk_question(encounter, request.language)
    result["priority"] = priority_state(flags)
    if result["complete"]:
        encounter.status = "ready"; db.commit()
    return result


@kiosk_router.post("/speech/transcribe")
async def transcribe_speech(session_id: str = Form(...), question_id: str = Form(...), language: str = Form("en"),
                            audio: UploadFile = File(...), duration_ms: int = Form(None), db: Session = Depends(get_db)):
    """Transcribe a kiosk recording with local Whisper; no patient audio is retained."""
    try: session = require_session(db, session_id)
    except ValueError as exc: raise HTTPException(404, str(exc))
    if audio.content_type and not (audio.content_type.startswith("audio/") or audio.content_type == "video/webm"):
        raise HTTPException(415, "An audio recording is required")
    content = await audio.read()
    if len(content) < 700: raise HTTPException(422, "Recording is too short to transcribe")
    suffix = Path(audio.filename or "answer.webm").suffix or ".webm"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(content); temp_path = temp.name
        result = whisper_provider.transcribe(temp_path, language)
    except SpeechUnavailable as exc:
        raise HTTPException(503, str(exc))
    finally:
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
    encounter = db.query(Encounter).options(joinedload(Encounter.answers)).filter(
        Encounter.encounter_id == session.encounter_id
    ).first()
    if not encounter:
        raise HTTPException(409, "Intake has not started")
    if encounter.status == "finalized":
        raise HTTPException(409, "Encounter is finalized")

    # A transcript is clinical source material, not a standalone artefact.  Persist
    # it as the answer for the question that was recorded and retain both links in
    # provenance so the evidence panel can trace a fact back to the audio result.
    answer = persist_answer(db, encounter, question_id, "patient_voice", [], result["transcript"], result["language"])
    transcript = Transcript(transcript_id=ref("tr"), answer_id=answer.answer_id, text=result["transcript"],
                            language=result["language"], confidence=result.get("confidence"),
                            duration_ms=duration_ms or result.get("duration_ms"), provider=result["provider"])
    db.add(transcript); db.flush()
    for provenance in db.query(FactProvenance).join(ClinicalFact).filter(
        ClinicalFact.encounter_id == encounter.encounter_id,
        ClinicalFact.fact_type == "intake_answer",
        FactProvenance.source_id == answer.answer_id,
    ):
        provenance.source_type = "transcript"
        provenance.source_id = transcript.transcript_id
        provenance.locator = {"answer_id": answer.answer_id, "question_id": question_id}
    flags = persist_red_flags(db, encounter, transcript.text)
    db.commit()
    return {"transcript_id": transcript.transcript_id, "answer_id": answer.answer_id, "transcript": transcript.text,
            "language": transcript.language, "confidence": transcript.confidence or 0.0,
            "duration_ms": transcript.duration_ms or 0, "priority": priority_state(flags)}


@kiosk_router.post("/documents/upload-session")
def create_upload_session(body: Dict[str, Any], db: Session = Depends(get_db)):
    try: session = require_session(db, body["session_id"])
    except (KeyError, ValueError) as exc: raise HTTPException(404, "Kiosk session is unknown or expired") from exc
    upload = UploadSession(token=ref("upload"), session_id=session.session_id, expires_at=now() + timedelta(minutes=15))
    db.add(upload); db.commit()
    return {"token": upload.token, "upload_url": f"/upload/{upload.token}", "status": upload.status, "documents": [], "expires_at": upload.expires_at.isoformat() + "Z"}


@kiosk_router.get("/documents/upload-session/{token}")
def upload_session_status(token: str, db: Session = Depends(get_db)):
    upload = db.query(UploadSession).filter(UploadSession.token == token).first()
    if not upload or upload.expires_at < now(): raise HTTPException(410, "Upload session expired")
    docs = db.query(Document).filter(Document.document_id.in_(upload.document_ids or [])).all()
    return {"token": token, "upload_url": f"/upload/{token}", "status": upload.status,
            "documents": [{"document_id": d.document_id, "file_name": d.file_name, "size_bytes": os.path.getsize(d.file_path) if os.path.exists(d.file_path) else 0,
                           "status": "processed", "doc_type": d.document_type, "received_at": d.created_at.isoformat() + "Z"} for d in docs],
            "expires_at": upload.expires_at.isoformat() + "Z"}


@kiosk_router.post("/documents/upload-session/{token}/documents")
async def upload_from_phone(token: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    upload = db.query(UploadSession).filter(UploadSession.token == token).first()
    if not upload or upload.expires_at < now(): raise HTTPException(410, "Upload session expired")
    if file.content_type not in ALLOWED_TYPES: raise HTTPException(415, "Only JPEG, PNG, and PDF documents are accepted")
    content = await file.read()
    if not content or len(content) > MAX_UPLOAD_BYTES: raise HTTPException(413, "Document is empty or exceeds the upload limit")
    session = db.query(KioskSession).filter(KioskSession.session_id == upload.session_id).first()
    encounter = db.query(Encounter).filter(Encounter.encounter_id == session.encounter_id).first() if session else None
    if not session: raise HTTPException(404, "Kiosk session is unavailable")
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "document").suffix.lower() or ".bin"; document_id = ref("doc")
    safe_path = UPLOAD_ROOT / f"{document_id}{suffix}"; safe_path.write_bytes(content)
    kind = "lab_report" if "lab" in (file.filename or "").lower() else "prescription"
    ocr = extract_and_normalize(str(safe_path), document_type=kind, patient_id=session.patient_id, document_id=document_id)
    extracted = {"diagnoses": ocr["diagnoses"], "medications": ocr["medications"], "lab_results": ocr["lab_results"]} if ocr.get("success") else {"diagnoses": [], "medications": [], "lab_results": []}
    document = Document(document_id=document_id, patient_id=session.patient_id, file_name=Path(file.filename or "document").name,
                        file_path=str(safe_path), document_type=kind, document_date=ocr.get("extracted_date"), ocr_text=ocr["ocr_text"])
    db.add(document); db.flush()
    extraction_status = "completed" if ocr.get("success") else "unavailable"
    db.add(DocumentExtraction(extraction_id=ref("extract"), document_id=document_id, provider=ocr.get("engine_used", "local"), status=extraction_status,
                              payload={"diagnoses": extracted["diagnoses"], "medications": extracted["medications"], "labs": extracted["lab_results"], "error": ocr.get("error")}))
    for diagnosis in extracted["diagnoses"]: create_fact(db, patient_id=session.patient_id, encounter_id=encounter.encounter_id if encounter else None, fact_type="condition", raw_value=diagnosis, source_type="document", source_id=document_id)
    for medication in extracted["medications"]: create_fact(db, patient_id=session.patient_id, encounter_id=encounter.encounter_id if encounter else None, fact_type="medication", raw_value=medication.get("name", "Medication"), source_type="document", source_id=document_id, details=medication)
    add_timeline_event(db, session.patient_id, encounter.encounter_id if encounter else None, "document", f"Uploaded {kind.replace('_', ' ')}", "document", document_id)
    upload.document_ids = [*(upload.document_ids or []), document_id]; upload.status = "complete"; db.commit()
    return {"document_id": document_id, "file_name": document.file_name, "size_bytes": len(content), "status": extraction_status, "doc_type": kind, "received_at": document.created_at.isoformat() + "Z"}


def _doctor(payload: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    data = decode_token(payload)
    if data.get("role") not in {"doctor", "admin"}: raise HTTPException(403, "Doctor access required")
    return data


def _snapshot(db: Session, encounter: Encounter) -> Dict[str, Any]:
    patient = encounter.patient; facts = db.query(ClinicalFact).options(joinedload(ClinicalFact.provenance)).filter(ClinicalFact.patient_id == patient.patient_id).all()
    by_type = lambda typ: [f for f in facts if f.fact_type == typ]
    src = lambda f: source_for_fact(f)
    alerts = db.query(ClinicalAlert).filter(ClinicalAlert.encounter_id == encounter.encounter_id).all()
    events = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient.patient_id).order_by(TimelineEvent.event_date).all()
    docs = db.query(Document).filter(Document.patient_id == patient.patient_id).all()
    answer_facts = by_type("intake_answer")
    hpi_items = [{"key": f.details.get("question_id", f.fact_id), "label": f.details.get("question_id", "Intake response"), "value": f.raw_value, "source": src(f), "status": f.status} for f in answer_facts]
    snap = {"encounter_id": encounter.encounter_id, "generated_at": now().isoformat() + "Z", "status": encounter.status,
            "intake_framework": encounter.intake_framework, "patient": {"patient_id": patient.patient_id, "name": patient.name, "age_years": patient.age, "sex": patient.gender.lower(), "abha_id": patient.abha_id, "preferred_language": patient.language, "department": "OPD"},
            "alerts": [{"alert_id": a.alert_id, "severity": a.severity, "rule": a.rule, "headline": a.headline, "detail": a.detail, "conflicting_sources": a.sources} for a in alerts],
            "sections": {"chief_complaint": {"label": "Chief complaint", "text": {"value": encounter.chief_complaint or "Not recorded", "duration": "", "source": {"type": "encounter", "id": encounter.encounter_id}, "status": "patient_reported"}},
                         "hpi": {"label": "History of present illness", "framework": "SOCRATES", "items": hpi_items},
                         "past_medical_surgical": {"label": "Past medical and surgical", "items": [{"fact_id": f.fact_id, "value": f.normalized_value or f.raw_value, "normalized": None, "source": src(f), "status": f.status} for f in by_type("condition")]},
                         "drug_and_allergy": {"label": "Drug and allergy", "medications": [{"fact_id": f.fact_id, "value": f.raw_value, "source": src(f), "status": f.status} for f in by_type("medication")], "allergies": [{"fact_id": f.fact_id, "value": f.raw_value, "reaction": f.details.get("reaction"), "source": src(f), "status": f.status, "alert_ids": []} for f in by_type("allergy")]},
                         "family_history": {"label": "Family history", "collapsed_by_default": True, "count": 0, "items": []}, "personal_history": {"label": "Personal history", "collapsed_by_default": True, "count": 0, "items": []}, "review_of_systems": {"label": "Review of systems", "collapsed_by_default": True, "systems_reviewed": 0, "positive_count": 0, "items": []}},
            "trend": {"label": "Timeline", "dates": [e.event_date.strftime("%d %b") for e in events if e.event_date], "groups": [{"label": "Clinical events", "rows": [{"key": e.event_id, "label": e.event_type, "values": [e.summary], "flags": [None], "ref": "—", "source": {"type": e.source_type, "id": e.source_id}} for e in events]}]},
            "ayush": None, "ayush_status": "not_captured", "last_visit": None, "documents": [{"document_id": d.document_id, "doc_type": d.document_type, "dated": d.document_date, "title": d.file_name, "page_count": 1} for d in docs]}
    db.add(PhysicianSnapshot(snapshot_id=ref("snap"), encounter_id=encounter.encounter_id, payload=snap)); db.commit()
    return snap


@doctor_router.get("/queue")
def doctor_queue(_: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounters = db.query(Encounter).options(joinedload(Encounter.patient)).filter(Encounter.status != "finalized").order_by(Encounter.started_at).all()
    return {"department": "MediKiosk OPD", "doctor": {"name": "Authenticated clinician"}, "stats": {"in_queue": len(encounters)},
            "patients": [{"encounter_id": e.encounter_id, "token": str(i + 1), "name": e.patient.name, "age_years": e.patient.age, "sex": e.patient.gender.lower(), "complaint": e.chief_complaint, "department": "OPD", "intake_framework": e.intake_framework, "intake_state": e.status, "wait_min": None, "priority": e.priority in {"urgent", "priority"}} for i, e in enumerate(encounters)]}


@doctor_router.get("/encounters/{encounter_id}/snapshot")
def doctor_snapshot(encounter_id: str, _: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).options(joinedload(Encounter.patient)).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    return _snapshot(db, encounter)


@doctor_router.get("/documents/{document_id}")
def doctor_document(document_id: str, _: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc: raise HTTPException(404, "Document not found")
    return {"document_id": doc.document_id, "dated": doc.document_date, "lines": [{"text": line} for line in (doc.ocr_text or "").splitlines()]}


@doctor_router.post("/encounters/{encounter_id}/qa")
def doctor_qa(encounter_id: str, request: DoctorQuestionRequest, _: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    terms = [word.lower() for word in request.question.split() if len(word) > 3]
    facts = db.query(ClinicalFact).options(joinedload(ClinicalFact.provenance)).filter(ClinicalFact.patient_id == encounter.patient_id).all()
    found = [f for f in facts if any(term in (f.raw_value + " " + (f.normalized_value or "")).lower() for term in terms)]
    if not found: return {"question": request.question, "answer": "The requested information was not found in this patient's records.", "sources": [], "data_available": False}
    return {"question": request.question, "answer": "; ".join(f.normalized_value or f.raw_value for f in found), "sources": [source_for_fact(f) for f in found], "data_available": True}


@doctor_router.post("/encounters/{encounter_id}/ledger")
def save_ledger(encounter_id: str, request: LedgerRequest, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    if encounter.status == "finalized": raise HTTPException(409, "Finalized encounters require an explicit amendment")
    if request.treatment_change and (not request.deviation_reason or not request.doctor_rationale): raise HTTPException(422, "A reason and doctor-authored rationale are required for treatment changes")
    if not request.doctor_confirmed: raise HTTPException(422, "Doctor confirmation is required")
    entry = LedgerEntry(ledger_id=ref("ledger"), encounter_id=encounter_id, clinician_id=clinician.get("sub", "doctor"), treatment_change=request.treatment_change,
                        previous_treatment=request.previous_treatment, new_treatment=request.new_treatment, deviation_reason=request.deviation_reason,
                        doctor_rationale=request.doctor_rationale, advice=request.advice, follow_up_required=request.follow_up_required,
                        follow_up_timeframe=request.follow_up_timeframe)
    db.add(entry); db.flush(); add_timeline_event(db, encounter.patient_id, encounter_id, "clinical_decision", "Doctor-authored ledger entry", "clinician", entry.ledger_id)
    db.commit(); return {"ok": True, "encounter_id": encounter_id, "ledger_id": entry.ledger_id}


@doctor_router.post("/encounters/{encounter_id}/finalize")
def finalize_encounter(encounter_id: str, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    if not db.query(LedgerEntry).filter(LedgerEntry.encounter_id == encounter_id).first(): raise HTTPException(409, "A ledger entry is required before finalization")
    encounter.status = "finalized"; encounter.finalized_at = now(); encounter.finalized_by = clinician.get("sub", "doctor")
    add_timeline_event(db, encounter.patient_id, encounter_id, "finalization", "Encounter finalized", "encounter", encounter_id); db.commit()
    return {"ok": True, "encounter_id": encounter_id, "status": encounter.status}
