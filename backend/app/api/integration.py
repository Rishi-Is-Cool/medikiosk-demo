"""Kiosk and doctor-console integration API for the MVP."""
from __future__ import annotations

import logging
import os
import secrets
import statistics
import tempfile
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, sessionmaker

from app.ai import adaptive_engine as engine
from app.ai.vision_pipeline import extract_and_normalize, extract_identity
from app.ai.clinical_extraction import extract_from_transcript
from app.services.ayush_snapshot import build_ayush_block
from app.database.connection import get_db
from app.database.schemas import (AdviceLibraryEntry, ClinicalAlert, ClinicalFact, ConsentRecord, Document,
    DocumentExtraction, DoctorProfile, Encounter, FactProvenance, KioskSession, LedgerEntry, Patient,
    PhysicianSnapshot, TimelineEvent, Transcript, UploadSession)
from app.models.pydantic_models import (AutofillRequest, ConsentSubmission, DoctorQuestionRequest, LedgerRequest,
    LookupRequest, RegistrationRequest, StartIntakeRequestV2, SubmitIntakeAnswerRequest)
from app.services.integration import (add_timeline_event, assign_doctor, canonical_gender, canonical_specialty,
    contract_source, create_fact, encounter_context, issue_queue_token, kiosk_question, NoDoctorAvailable, now,
    parse_follow_up_days, persist_answer, queue_status, reconcile_red_flags, ref, require_session, source_for_fact)
from app.utils.identity import aadhaar_hash, mask_aadhaar, mask_abha, normalize_aadhaar, normalize_abha
from app.utils.security import decode_token
from app.ai.whisper_provider import SpeechUnavailable, whisper_provider

logger = logging.getLogger(__name__)

kiosk_router = APIRouter(tags=["Kiosk Integration"])
doctor_router = APIRouter(prefix="/api", tags=["Doctor Integration"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
UPLOAD_ROOT = Path(os.getenv("UPLOAD_DIR", "./data/uploads"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
# Every still-image format the Gemini vision pipeline accepts natively, not
# just the two a desktop scanner produces — a phone camera hands back HEIC on
# iOS and WEBP on plenty of Android camera apps by default.
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif", "application/pdf"}
# Phones sometimes send an empty or generic content type (iOS HEIC in
# particular). Fall back to the file extension rather than rejecting the
# patient over a MIME-sniffing quirk.
_EXTENSION_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
                    ".heic": "image/heic", ".heif": "image/heif", ".pdf": "application/pdf"}
UPLOAD_SESSION_TTL = timedelta(minutes=int(os.getenv("UPLOAD_SESSION_MINUTES", "30")))
_KNOWN_DOCUMENT_TYPES = {"prescription", "lab_report", "discharge_summary", "imaging_report", "referral_letter"}

_UNDERSTOOD = {"en": "Understood as", "hi": "हमने समझा", "mr": "आम्ही समजलो"}
_YOUR_ANSWER = {"en": "Your answer", "hi": "आपका जवाब", "mr": "तुमचे उत्तर"}


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _bg_session(bind: Engine) -> Session:
    """A fresh session on the same database as the request — background tasks
    outlive the request's session, and must never fall back to another DB."""
    return sessionmaker(bind=bind, autocommit=False, autoflush=False)()


def _session_or_404(db: Session, session_id: str) -> KioskSession:
    try:
        return require_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


def _load_encounter(db: Session, encounter_id: Optional[str]) -> Optional[Encounter]:
    if not encounter_id:
        return None
    return (db.query(Encounter).options(joinedload(Encounter.answers))
            .filter(Encounter.encounter_id == encounter_id).first())


def _active_encounter(db: Session, session: KioskSession) -> Encounter:
    encounter = _load_encounter(db, session.encounter_id)
    if not encounter:
        raise HTTPException(409, "Intake has not started")
    if encounter.status == "finalized":
        raise HTTPException(409, "Encounter is finalized")
    return encounter


def _masked_id(patient: Patient, identity_method: str) -> Optional[str]:
    if identity_method == "aadhaar":
        return mask_aadhaar(patient.aadhaar_last4)
    if identity_method == "abha":
        return mask_abha(patient.abha_id)
    return mask_abha(patient.abha_id) or mask_aadhaar(patient.aadhaar_last4)


def _session_payload(session: KioskSession, patient: Patient, *, identity_method: str,
                     returning: bool = False, last_visit: Optional[str] = None) -> Dict[str, Any]:
    return {"session_id": session.session_id, "patient_ref": patient.patient_id, "display_name": patient.name,
            "identity_method": identity_method, "masked_id": _masked_id(patient, identity_method),
            "age": patient.age, "sex": (patient.gender or "").lower(), "returning": returning, "last_visit": last_visit}


def _open_session(db: Session, patient: Patient) -> KioskSession:
    session = KioskSession(session_id=ref("ks"), patient_id=patient.patient_id, expires_at=now() + timedelta(minutes=30))
    db.add(session)
    return session


def _normalize_identity(method: str, identifier: Optional[str]) -> str:
    if method == "abha":
        value = normalize_abha(identifier)
        if not value:
            raise HTTPException(422, "An ABHA number has 14 digits, e.g. 91-7267-4417-6579")
        return value
    if method == "aadhaar":
        value = normalize_aadhaar(identifier)
        if not value:
            raise HTTPException(422, "An Aadhaar number has 12 digits")
        return value
    raise HTTPException(422, "identity_method must be 'abha' or 'aadhaar'")


def _find_patient(db: Session, method: str, value: str) -> Optional[Patient]:
    if method == "abha":
        return db.query(Patient).filter(Patient.abha_id == value).first()
    return db.query(Patient).filter(Patient.aadhaar_hash == aadhaar_hash(value)).first()


def _consented(db: Session, session: KioskSession) -> bool:
    """Consent is per visit: this kiosk session must carry its own record."""
    record = (db.query(ConsentRecord).filter(ConsentRecord.session_id == session.session_id)
              .order_by(ConsentRecord.accepted_at.desc()).first())
    return bool(record and record.granted)


# ─── Identity ─────────────────────────────────────────────────────────────────


def _lookup(db: Session, method: str, identifier: Optional[str], language: str) -> Dict[str, Any]:
    value = _normalize_identity(method, identifier)
    patient = _find_patient(db, method, value)
    if not patient:
        raise HTTPException(404, "No patient is registered with this ID")
    if language:
        patient.language = language
    last = (db.query(Encounter.started_at).filter(Encounter.patient_id == patient.patient_id)
            .order_by(Encounter.started_at.desc()).first())
    session = _open_session(db, patient)
    db.commit()
    return _session_payload(session, patient, identity_method=method, returning=True,
                            last_visit=last[0].strftime("%Y-%m-%d") if last and last[0] else None)


@kiosk_router.post("/patient/register")
def kiosk_register(request: RegistrationRequest, db: Session = Depends(get_db)):
    """Register a first-time patient, optionally attaching their ABHA/Aadhaar."""
    if request.identity_method in {"abha", "aadhaar"} and request.identifier and not request.new_patient:
        # Older clients sent a returning patient's ID to this endpoint.
        return _lookup(db, request.identity_method, request.identifier, request.language)

    data = request.new_patient or {}
    name = str(data.get("name") or "").strip()
    try:
        age = int(str(data.get("age", "")).strip())
    except (TypeError, ValueError):
        age = -1
    if len(name) < 2 or not 0 <= age <= 120:
        raise HTTPException(422, "A valid patient name and age (0–120) are required")

    abha = _normalize_identity("abha", request.abha_number) if request.abha_number else None
    aadhaar = _normalize_identity("aadhaar", request.aadhaar_number) if request.aadhaar_number else None
    if (abha and _find_patient(db, "abha", abha)) or (aadhaar and _find_patient(db, "aadhaar", aadhaar)):
        raise HTTPException(409, "This ID is already registered — continue as a returning patient")

    patient = Patient(patient_id=ref("pat"), name=name, age=age, gender=canonical_gender(data.get("sex")),
                      language=request.language, phone=(str(data.get("phone") or "").strip() or None),
                      abha_id=abha, aadhaar_hash=aadhaar_hash(aadhaar) if aadhaar else None,
                      aadhaar_last4=aadhaar[-4:] if aadhaar else None, consent_granted=False)
    db.add(patient)
    db.flush()
    session = _open_session(db, patient)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This ID is already registered — continue as a returning patient") from exc
    method = "abha" if abha else "aadhaar" if aadhaar else "new"
    return _session_payload(session, patient, identity_method=method)


@kiosk_router.post("/patient/lookup")
def kiosk_lookup(request: LookupRequest, db: Session = Depends(get_db)):
    """Find a returning patient by ABHA number or Aadhaar and open a kiosk session."""
    return _lookup(db, request.identity_method, request.identifier, request.language)


@kiosk_router.get("/patient/session")
def kiosk_session(session_id: str, db: Session = Depends(get_db)):
    session = _session_or_404(db, session_id)
    patient = session.patient
    method = "abha" if patient.abha_id else "aadhaar" if patient.aadhaar_hash else "new"
    return _session_payload(session, patient, identity_method=method)


@kiosk_router.post("/patient/consent")
def record_consent(request: ConsentSubmission, db: Session = Depends(get_db)):
    session = _session_or_404(db, request.session_id)
    consent = ConsentRecord(consent_id=ref("consent"), patient_id=session.patient_id, session_id=session.session_id,
                            granted=request.granted, declined=request.declined, language=request.language,
                            audio_explanation_played=request.audio_explanation_played)
    db.add(consent)
    session.patient.consent_granted = bool(request.granted)
    db.commit()
    return {"consent_id": consent.consent_id, "accepted_at": consent.accepted_at.isoformat() + "Z"}


@kiosk_router.post("/patient/scan-identity")
async def scan_identity(identity_method: str = Form(...), image: UploadFile = File(...)):
    """Photo of an ABHA/Aadhaar card in, best-effort ID number out.
    Never verifies identity against anything — the patient can correct it."""
    content = await image.read()
    if not content:
        raise HTTPException(422, "An identity photo is required")
    result = await run_in_threadpool(extract_identity, content, image.content_type or "image/jpeg")
    raw = result.get("identifier")
    # null when unreadable — the kiosk then asks the patient to type it.
    identifier = (normalize_abha(raw) if identity_method == "abha" else normalize_aadhaar(raw)) or None
    return {"identity_method": identity_method, "identifier": identifier, "name": result.get("name")}


# ─── Intake ───────────────────────────────────────────────────────────────────


@kiosk_router.get("/intake/complaints")
def complaints(language: str = "en"):
    return engine.complaint_list(language)


@kiosk_router.post("/intake/match-complaint")
def match_complaint(body: Dict[str, Any]):
    """Spoken words → every complaint they mention (a patient may say two)."""
    text = str(body.get("transcript") or "").strip()
    language = str(body.get("language") or "en")
    items = [{"id": cid, "label": engine.complaint_label(cid, language), "icon": engine.COMPLAINTS_BY_ID[cid].icon}
             for cid in engine.match_complaints(text)]
    return {"complaint": items[0] if items else None, "complaints": items, "transcript": text}


@kiosk_router.post("/intake/start")
def start_intake(request: StartIntakeRequestV2, background: BackgroundTasks, db: Session = Depends(get_db)):
    session = _session_or_404(db, request.session_id)
    if not _consented(db, session):
        raise HTTPException(409, "Consent is required before clinical intake")
    current = _load_encounter(db, session.encounter_id)
    if current and current.status == "intake_in_progress":
        return kiosk_question(current, request.language)

    complaints = engine.normalize_complaints(request.chief_complaints or [request.chief_complaint or ""])
    text = (request.chief_complaint_text or "").strip() or None
    if not request.chief_complaints and complaints == ["other"] and not text and request.chief_complaint:
        text = request.chief_complaint.strip()  # an older client's free-text complaint
    try:
        doctor_username = assign_doctor(db, canonical_specialty(request.history_mode))
    except NoDoctorAvailable as exc:
        raise HTTPException(503, str(exc)) from exc

    labels = ", ".join(engine.complaint_label(c) for c in complaints if c != "other")
    summary = f"{labels} — {text}" if labels and text else (labels or text or "Not recorded")
    encounter = Encounter(encounter_id=ref("enc"), patient_id=session.patient_id, intake_framework=request.history_mode,
                          chief_complaint=summary, language=request.language, assigned_doctor_username=doctor_username)
    db.add(encounter)
    db.flush()
    session.encounter_id = encounter.encounter_id
    issue_queue_token(db, encounter)  # token order = arrival order at the kiosk
    persist_answer(db, encounter, "chief_complaints", "patient_spoken" if text else "patient_touch", complaints, text,
                   request.language, readable=summary, question_label="Chief complaint")
    add_timeline_event(db, encounter.patient_id, encounter.encounter_id, "consultation", f"New encounter: {summary}",
                       "encounter", encounter.encounter_id)
    # A spoken complaint can itself carry a red flag ("chest pain going to my left arm").
    reconcile_red_flags(db, encounter)
    db.commit()
    if text:
        background.add_task(_enrich_from_text, db.get_bind(), encounter.encounter_id, encounter.patient_id, text,
                            request.language, "encounter", encounter.encounter_id)
    return kiosk_question(encounter, request.language)


@kiosk_router.get("/intake/question")
def current_question(session_id: str, language: str = "en", db: Session = Depends(get_db)):
    session = _session_or_404(db, session_id)
    encounter = _load_encounter(db, session.encounter_id)
    if not encounter:
        raise HTTPException(409, "Intake has not started")
    return kiosk_question(encounter, language)


@kiosk_router.get("/intake/queue")
def queue_position(session_id: str, db: Session = Depends(get_db)):
    """The patient's OPD token and how many patients are ahead — counted live."""
    session = _session_or_404(db, session_id)
    encounter = (db.query(Encounter).filter(Encounter.encounter_id == session.encounter_id).first()
                 if session.encounter_id else None)
    if not encounter:
        raise HTTPException(409, "Intake has not started")
    if not encounter.queue_token:  # encounters started before tokens existed
        issue_queue_token(db, encounter)
        db.commit()
    return queue_status(db, encounter)


@kiosk_router.post("/intake/answer")
def submit_intake_answer(request: SubmitIntakeAnswerRequest, background: BackgroundTasks, db: Session = Depends(get_db)):
    session = _session_or_404(db, request.session_id)
    encounter = _active_encounter(db, session)
    ctx = encounter_context(encounter)
    question = engine.ALL_QUESTIONS.get(request.question_id)
    language = request.language
    text = (request.answer.text or "").strip() or None
    values = list(request.answer.values or [])

    # A spoken or typed answer to a multiple-choice question is mapped onto its
    # options, so the red-flag rules see structured findings either way.
    if question and not values and text:
        values = engine.match_options(question, ctx, text)
    if question and values and question.input_type != "voice_or_text":
        valid = {o.value for o in question.resolved_options(ctx)}
        if question.id == "associated":
            valid |= {e.option.value for e in engine._ASSOCIATED} | {"none"}
        values = [v for v in values if v in valid]

    if request.mode == "extract":
        # The "is this what you meant?" step for a spoken answer. Nothing is stored.
        fields = []
        if question and values:
            fields.append({"label": _UNDERSTOOD.get(language, _UNDERSTOOD["en"]),
                           "value": engine.readable_answer(question, ctx, values, None, language)})
        elif text:
            fields.append({"label": _YOUR_ANSWER.get(language, _YOUR_ANSWER["en"]), "value": text})
        return {"question_id": request.question_id, "summary": fields[0]["value"] if fields else "",
                "fields": fields, "source": request.answer.source, "values": values}

    if not values and not text:
        raise HTTPException(422, "An answer is required")

    readable = engine.readable_answer(question, ctx, values, text) if question else (text or ", ".join(values))
    transcript = None
    if request.answer.transcript_id:
        transcript = db.query(Transcript).filter(Transcript.transcript_id == request.answer.transcript_id).first()
    answer = persist_answer(db, encounter, request.question_id, request.answer.source, values, text, language,
                            readable=readable, question_label=question.doctor_label if question else request.question_id,
                            transcript_id=transcript.transcript_id if transcript else None)
    if transcript:
        db.flush()  # the answer row must exist before the transcript's FK points at it
        transcript.answer_id = answer.answer_id
    reconcile_red_flags(db, encounter)
    result = kiosk_question(encounter, language)
    if result["complete"]:
        encounter.status = "ready"
    db.commit()

    if text and question and question.input_type == "voice_or_text":
        background.add_task(_enrich_from_text, db.get_bind(), encounter.encounter_id, encounter.patient_id, text, language,
                            "transcript" if transcript else request.answer.source,
                            transcript.transcript_id if transcript else answer.answer_id)
    return result


@kiosk_router.post("/intake/autofill")
def autofill_intake(request: AutofillRequest, db: Session = Depends(get_db)):
    """Presentation shortcut: answer every remaining question with its default
    (benign) answer and complete the intake. Recorded as `demo_autofill` so the
    stored record never claims the patient said it. Disable with
    KIOSK_DEMO_AUTOFILL=0 outside of demos."""
    if os.getenv("KIOSK_DEMO_AUTOFILL", "1") == "0":
        raise HTTPException(404, "Demo autofill is disabled")
    session = _session_or_404(db, request.session_id)
    encounter = _active_encounter(db, session)
    for _ in range(80):
        ctx = encounter_context(encounter)
        question, _steps = engine.next_question(ctx)
        if question is None:
            break
        default = engine.default_answer(question, ctx)
        persist_answer(db, encounter, question.id, "demo_autofill", default["values"], default["text"], request.language,
                       readable=engine.readable_answer(question, ctx, default["values"], default["text"]),
                       question_label=question.doctor_label)
    reconcile_red_flags(db, encounter)
    encounter.status = "ready"
    add_timeline_event(db, encounter.patient_id, encounter.encounter_id, "intake", "Intake completed (demo defaults)",
                       "encounter", encounter.encounter_id)
    db.commit()
    return kiosk_question(encounter, request.language)


def _enrich_from_text(bind: Engine, encounter_id: str, patient_id: str, text: str, language: str,
                      source_type: str, source_id: str) -> None:
    """Background: Gemini structured extraction of a free-text/spoken answer
    into symptoms, conditions, medicines and allergies for the doctor. Runs
    after the response so the patient never waits on it; silently does nothing
    without GEMINI_API_KEY."""
    try:
        structured = extract_from_transcript(text=text, language=language, patient_id=patient_id)
    except Exception as exc:  # enrichment must never break an intake
        logger.warning("Transcript enrichment failed: %s", exc)
        return
    if not structured:
        return
    db = _bg_session(bind)
    try:
        def fact(fact_type: str, value: str, details: Optional[Dict[str, Any]] = None, confidence=None):
            create_fact(db, patient_id=patient_id, encounter_id=encounter_id, fact_type=fact_type, raw_value=value,
                        source_type=source_type, source_id=source_id, details=details, confidence=confidence)

        for symptom in structured.get("symptoms") or []:
            name = symptom.get("normalized_name") or symptom.get("name")
            if name and not symptom.get("negated"):
                fact("symptom", name, {"site": symptom.get("site"), "duration": symptom.get("duration"),
                                       "severity": symptom.get("severity")}, symptom.get("confidence"))
        for condition in structured.get("medical_history") or []:
            name = condition.get("normalized_name") or condition.get("name")
            if name:
                fact("condition", name)
        for medication in structured.get("medications") or []:
            if medication.get("name"):
                fact("medication", medication["name"], {"dose": medication.get("dose"), "frequency": medication.get("frequency")})
        for allergy in structured.get("allergies") or []:
            if allergy.get("substance"):
                fact("allergy", allergy["substance"], {"reaction": allergy.get("reaction")})
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Could not store transcript enrichment: %s", exc)
    finally:
        db.close()


# ─── Speech ───────────────────────────────────────────────────────────────────


@kiosk_router.post("/speech/transcribe")
async def transcribe_speech(session_id: str = Form(...), question_id: str = Form(""), language: str = Form("en"),
                            audio: UploadFile = File(...), duration_ms: Optional[int] = Form(None),
                            db: Session = Depends(get_db)):
    """Transcribe a kiosk recording with local Whisper.

    Returns text only. Nothing is written to the clinical record here: the
    patient first sees what was heard and confirms it, and only then does the
    kiosk submit the answer (with this transcript_id as its evidence). The
    audio itself is deleted immediately.
    """
    _session_or_404(db, session_id)
    content_type = (audio.content_type or "").lower()
    if content_type and not (content_type.startswith("audio/") or content_type.startswith("video/")):
        raise HTTPException(415, "An audio recording is required")
    content = await audio.read()
    if len(content) < 1024 or (duration_ms is not None and duration_ms < 500):
        raise HTTPException(422, "Recording is too short to transcribe")
    suffix = Path(audio.filename or "answer.webm").suffix or ".webm"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(content)
            temp_path = temp.name
        result = await run_in_threadpool(whisper_provider.transcribe, temp_path, language)
    except SpeechUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    text = (result.get("transcript") or "").strip()
    if not text:
        raise HTTPException(422, "No speech was detected")
    transcript = Transcript(transcript_id=ref("tr"), answer_id=None, text=text, language=result.get("language") or language,
                            confidence=result.get("confidence"), duration_ms=duration_ms or result.get("duration_ms"),
                            provider=result.get("provider", "faster-whisper"))
    db.add(transcript)
    db.commit()
    return {"transcript_id": transcript.transcript_id, "transcript": text, "language": transcript.language,
            "confidence": transcript.confidence or 0.0, "duration_ms": transcript.duration_ms or 0}


@kiosk_router.post("/speech/synthesize")
def synthesize_speech(body: Dict[str, str]):
    """Text-to-speech for question/instruction prompts.

    No TTS provider is configured in this deployment. The frontend's contract
    treats a null audio_url as 'no server audio available' and falls back to
    the browser's own speech synthesis.
    """
    return {"audio_url": None}


# ─── Documents (QR → phone upload) ────────────────────────────────────────────

_EXTRACTION_TO_STATUS = {"processing": "processing", "completed": "processed", "unavailable": "failed", "failed": "failed"}


def _upload_payload(db: Session, upload: UploadSession) -> Dict[str, Any]:
    ids = list(upload.document_ids or [])
    docs = db.query(Document).filter(Document.document_id.in_(ids)).all() if ids else []
    extractions = {e.document_id: e for e in db.query(DocumentExtraction).filter(DocumentExtraction.document_id.in_(ids)).all()} if ids else {}
    documents = []
    for d in docs:
        extraction = extractions.get(d.document_id)
        documents.append({"document_id": d.document_id, "file_name": d.file_name,
                          "size_bytes": os.path.getsize(d.file_path) if os.path.exists(d.file_path) else 0,
                          "status": _EXTRACTION_TO_STATUS.get(extraction.status if extraction else "", "received"),
                          "doc_type": d.document_type, "received_at": d.created_at.isoformat() + "Z"})
    if upload.expires_at and upload.expires_at < now():
        status = "expired"
    elif any(doc["status"] == "processing" for doc in documents):
        status = "uploading"
    elif documents:
        status = "complete"
    else:
        status = "connected" if upload.status == "connected" else "waiting"
    return {"token": upload.token, "upload_url": f"/upload/{upload.token}", "status": status,
            "documents": documents, "expires_at": upload.expires_at.isoformat() + "Z"}


def _upload_or_404(db: Session, token: str) -> UploadSession:
    upload = db.query(UploadSession).filter(UploadSession.token == token).first()
    if not upload:
        raise HTTPException(404, "Upload link not found")
    return upload


@kiosk_router.post("/documents/upload-session")
def create_upload_session(body: Dict[str, Any], db: Session = Depends(get_db)):
    """Idempotent per kiosk session: calling again returns the same live QR
    (so it never changes under a patient mid-scan) unless force_new is set."""
    session = _session_or_404(db, str(body.get("session_id") or ""))
    current = now()
    live = (db.query(UploadSession)
            .filter(UploadSession.session_id == session.session_id, UploadSession.expires_at > current)
            .order_by(UploadSession.created_at.desc()))
    if not body.get("force_new"):
        existing = live.first()
        if existing:
            return _upload_payload(db, existing)
    else:
        for old in live.all():
            old.expires_at = current
    upload = UploadSession(token=ref("upload"), session_id=session.session_id, expires_at=current + UPLOAD_SESSION_TTL)
    db.add(upload)
    db.commit()
    return _upload_payload(db, upload)


@kiosk_router.get("/documents/upload-session/{token}")
def upload_session_status(token: str, db: Session = Depends(get_db)):
    return _upload_payload(db, _upload_or_404(db, token))


@kiosk_router.post("/documents/upload-session/{token}/connect")
def upload_session_connect(token: str, db: Session = Depends(get_db)):
    """The patient's phone opened the QR link — lets the kiosk stop saying 'waiting'."""
    upload = _upload_or_404(db, token)
    if upload.expires_at and upload.expires_at < now():
        raise HTTPException(410, "This upload link has expired")
    if upload.status == "waiting":
        upload.status = "connected"
        db.commit()
    return _upload_payload(db, upload)


@kiosk_router.post("/documents/upload-session/{token}/documents")
async def upload_from_phone(token: str, background: BackgroundTasks, file: UploadFile = File(...),
                            db: Session = Depends(get_db)):
    """Store the photo and return immediately; OCR runs in the background so the
    phone isn't kept waiting on Gemini. The kiosk's status poll shows it
    moving from processing → processed."""
    upload = _upload_or_404(db, token)
    if upload.expires_at and upload.expires_at < now():
        raise HTTPException(410, "This upload link has expired")
    suffix = Path(file.filename or "document").suffix.lower()
    content_type = (file.content_type or "").lower().replace("image/jpg", "image/jpeg")
    if content_type in {"", "application/octet-stream"}:
        content_type = _EXTENSION_TYPES.get(suffix, content_type)
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "That file type isn't supported — send a photo or a PDF.")
    content = await file.read()
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "Document is empty or exceeds the upload limit")
    session = db.query(KioskSession).filter(KioskSession.session_id == upload.session_id).first()
    if not session:
        raise HTTPException(404, "Kiosk session is unavailable")

    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    document_id = ref("doc")
    safe_path = UPLOAD_ROOT / f"{document_id}{suffix or '.bin'}"
    safe_path.write_bytes(content)
    kind = "lab_report" if "lab" in (file.filename or "").lower() else "prescription"
    document = Document(document_id=document_id, patient_id=session.patient_id, file_name=Path(file.filename or "document").name,
                        file_path=str(safe_path), document_type=kind, ocr_text="")
    db.add(document)
    db.add(DocumentExtraction(extraction_id=ref("extract"), document_id=document_id, provider="pending", status="processing",
                              payload={}))
    upload.document_ids = [*(upload.document_ids or []), document_id]
    upload.status = "uploading"
    db.commit()
    background.add_task(_process_document, db.get_bind(), document_id, str(safe_path), kind, session.patient_id,
                        session.encounter_id)
    return {"document_id": document_id, "file_name": document.file_name, "size_bytes": len(content),
            "status": "processing", "doc_type": kind, "received_at": document.created_at.isoformat() + "Z"}


# A vision model that is briefly overloaded (Gemini answers 503 "high demand"
# or 429) usually succeeds seconds later. Anything else — an unreadable photo,
# a bad key — fails the same way every time and is not retried.
_TRANSIENT_MARKERS = ("503", "unavailable", "429", "resource_exhausted", "high demand", "overloaded",
                      "timeout", "timed out", "deadline")
_OCR_RETRY_DELAYS = tuple(int(s) for s in os.getenv("DOC_OCR_RETRY_DELAYS", "3,8,15").split(",") if s.strip())


def _read_document(path: str, kind: str, patient_id: str, document_id: str) -> Dict[str, Any]:
    """The document pipeline (ml_backend), retried while the model is busy."""
    ocr: Dict[str, Any] = {}
    for attempt, delay in enumerate((0, *_OCR_RETRY_DELAYS)):
        if delay:
            time.sleep(delay)
        try:
            ocr = extract_and_normalize(path, document_type=kind, patient_id=patient_id, document_id=document_id)
        except Exception as exc:
            ocr = {"success": False, "error": str(exc), "ocr_text": "", "diagnoses": [], "medications": [],
                   "lab_results": []}
        error = str(ocr.get("error") or "").lower()
        if ocr.get("success") or not any(marker in error for marker in _TRANSIENT_MARKERS):
            return ocr
        logger.info("Document %s: vision model busy (attempt %d), retrying", document_id, attempt + 1)
    logger.warning("Document extraction failed for %s after retries: %s", document_id, ocr.get("error"))
    return ocr


def _process_document(bind: Engine, document_id: str, path: str, kind: str, patient_id: str,
                      encounter_id: Optional[str]) -> None:
    """Background: vision extraction → Document, DocumentExtraction and
    source-linked facts the doctor console reads."""
    ocr = _read_document(path, kind, patient_id, document_id)
    db = _bg_session(bind)
    try:
        document = db.query(Document).filter(Document.document_id == document_id).first()
        extraction = db.query(DocumentExtraction).filter(DocumentExtraction.document_id == document_id).first()
        if not document or not extraction:
            return
        ok = bool(ocr.get("success"))
        detected = (ocr.get("document_type") or "").lower()
        if detected in _KNOWN_DOCUMENT_TYPES:
            document.document_type = detected
        document.document_date = ocr.get("extracted_date")
        document.ocr_text = ocr.get("ocr_text") or ""
        extraction.provider = ocr.get("engine_used", "local")
        extraction.status = "completed" if ok else "unavailable"
        extraction.payload = {"diagnoses": ocr.get("diagnoses") or [], "medications": ocr.get("medications") or [],
                              "labs": ocr.get("lab_results") or [], "error": ocr.get("error")}
        if ok:
            for diagnosis in ocr.get("diagnoses") or []:
                create_fact(db, patient_id=patient_id, encounter_id=encounter_id, fact_type="condition", raw_value=diagnosis,
                            source_type="document", source_id=document_id)
            for medication in ocr.get("medications") or []:
                create_fact(db, patient_id=patient_id, encounter_id=encounter_id, fact_type="medication",
                            raw_value=medication.get("name", "Medication"), source_type="document", source_id=document_id,
                            details=medication)
            for lab in ocr.get("lab_results") or []:
                create_fact(db, patient_id=patient_id, encounter_id=encounter_id, fact_type="investigation",
                            raw_value=lab.get("test_name", "Lab result"), source_type="document", source_id=document_id,
                            details={"value": lab.get("value"), "unit": lab.get("unit"), "reference_range": lab.get("reference_range"),
                                     "abnormal": lab.get("abnormal"), "interpretation": lab.get("interpretation")})
        add_timeline_event(db, patient_id, encounter_id, "document",
                           f"Uploaded {document.document_type.replace('_', ' ')}", "document", document_id)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.warning("Could not store document extraction for %s: %s", document_id, exc)
    finally:
        db.close()


# ─── Doctor console ───────────────────────────────────────────────────────────

def _doctor(payload: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    data = decode_token(payload)
    if data.get("role") not in {"doctor", "admin"}: raise HTTPException(403, "Doctor access required")
    return data


def _require_own_encounter(encounter: Encounter, clinician: Dict[str, Any]) -> None:
    """A doctor may only act on encounters assigned to them — this is what keeps
    a general-medicine doctor from ever seeing (or writing to) an Ayurveda
    patient's chart, and vice versa. Admins can see across specialties."""
    if clinician.get("role") != "admin" and encounter.assigned_doctor_username != clinician.get("sub"):
        raise HTTPException(403, "This encounter is assigned to a different doctor")


def _lab_flag(details: Dict[str, Any]) -> Any:
    interpretation = (details.get("interpretation") or "").lower()
    if "low" in interpretation:
        return "low"
    if any(term in interpretation for term in ("high", "elevat", "diabetic")):
        return "high"
    abnormal = details.get("abnormal")
    if abnormal is True:
        return "high"
    if abnormal is False:
        return "normal"
    return None


def _duration_text(answer_facts: List[ClinicalFact]) -> str:
    return next((f.raw_value for f in answer_facts if (f.details or {}).get("question_id") == "duration"), "")


def _snapshot(db: Session, encounter: Encounter) -> Dict[str, Any]:
    patient = encounter.patient; facts = db.query(ClinicalFact).options(joinedload(ClinicalFact.provenance)).filter(ClinicalFact.patient_id == patient.patient_id).all()
    by_type = lambda typ: [f for f in facts if f.fact_type == typ]
    src = lambda f: source_for_fact(f)
    # Resolved alerts (the patient corrected an answer) stay in the audit trail, not on screen.
    alerts = db.query(ClinicalAlert).filter(ClinicalAlert.encounter_id == encounter.encounter_id,
                                            ClinicalAlert.resolved_at.is_(None)).all()
    events = db.query(TimelineEvent).filter(TimelineEvent.patient_id == patient.patient_id).order_by(TimelineEvent.event_date).all()
    docs = db.query(Document).filter(Document.patient_id == patient.patient_id).all()
    # This visit's answers only, in the order they were asked; the complaint itself has its own section.
    answer_facts = sorted((f for f in by_type("intake_answer") if f.encounter_id == encounter.encounter_id
                           and (f.details or {}).get("question_id") not in {"chief_complaints", "q1_chief_complaint"}),
                          key=lambda f: f.recorded_at or now())
    hpi_items = [{"key": f.details.get("question_id", f.fact_id),
                  "label": f.details.get("question_label") or f.details.get("question_id", "Intake response"),
                  "value": f.raw_value, "source": src(f), "status": f.status} for f in answer_facts]
    investigation_items = [{"fact_id": f.fact_id, "test": f.raw_value, "value": (f.details or {}).get("value"),
                             "unit": (f.details or {}).get("unit"), "reference_range": (f.details or {}).get("reference_range"),
                             "flag": _lab_flag(f.details or {}), "dated": f.recorded_at.strftime("%Y-%m-%d") if f.recorded_at else None,
                             "source": src(f), "status": f.status, "alert_ids": []} for f in by_type("investigation")]
    previous_encounter = (db.query(Encounter)
                           .filter(Encounter.patient_id == patient.patient_id, Encounter.encounter_id != encounter.encounter_id, Encounter.status == "finalized")
                           .order_by(Encounter.finalized_at.desc()).first())
    ayush_block = build_ayush_block(encounter)
    ayush_status = "present" if ayush_block else ("not_captured" if encounter.intake_framework != "ayush" else "in_progress")
    snap = {"encounter_id": encounter.encounter_id, "generated_at": now().isoformat() + "Z", "status": encounter.status,
            "intake_framework": encounter.intake_framework, "patient": {"patient_id": patient.patient_id, "name": patient.name, "age_years": patient.age, "sex": patient.gender.lower(), "abha_id": patient.abha_id, "preferred_language": patient.language, "department": "OPD"},
            "alerts": [{"alert_id": a.alert_id, "severity": a.severity, "rule": a.rule, "headline": a.headline, "detail": a.detail, "conflicting_sources": a.sources} for a in alerts],
            "sections": {"chief_complaint": {"label": "Chief complaint", "text": {"value": encounter.chief_complaint or "Not recorded", "duration": _duration_text(answer_facts), "source": contract_source("encounter", encounter.encounter_id), "status": "patient_reported"}},
                         "hpi": {"label": "History of present illness", "framework": "SOCRATES", "items": hpi_items},
                         "past_medical_surgical": {"label": "Past medical and surgical", "items": [{"fact_id": f.fact_id, "value": f.normalized_value or f.raw_value, "normalized": None, "source": src(f), "status": f.status} for f in by_type("condition")]},
                         "drug_and_allergy": {"label": "Drug and allergy", "medications": [{"fact_id": f.fact_id, "value": f.raw_value, "source": src(f), "status": f.status} for f in by_type("medication")], "allergies": [{"fact_id": f.fact_id, "value": f.raw_value, "reaction": f.details.get("reaction"), "source": src(f), "status": f.status, "alert_ids": []} for f in by_type("allergy")]},
                         "family_history": {"label": "Family history", "collapsed_by_default": True, "count": 0, "items": []}, "personal_history": {"label": "Personal history", "collapsed_by_default": True, "count": 0, "items": []}, "review_of_systems": {"label": "Review of systems", "collapsed_by_default": True, "systems_reviewed": 0, "positive_count": 0, "items": []},
                         "prior_investigations": {"label": "Prior investigations", "items": investigation_items}},
            "trend": {"label": "Timeline", "dates": [e.event_date.strftime("%d %b") for e in events if e.event_date], "groups": [{"label": "Clinical events", "rows": [{"key": e.event_id, "label": e.event_type, "values": [e.summary], "flags": [None], "ref": "—", "source": {"type": e.source_type, "id": e.source_id}} for e in events]}]},
            "ayush": ayush_block, "ayush_status": ayush_status,
            "last_visit": ({"encounter_id": previous_encounter.encounter_id,
                            "date": previous_encounter.finalized_at.strftime("%Y-%m-%d") if previous_encounter.finalized_at else None,
                            "summary": previous_encounter.chief_complaint or "Previous encounter",
                            "source": {"type": "prior_encounter", "id": previous_encounter.encounter_id}} if previous_encounter else None),
            "documents": [{"document_id": d.document_id, "doc_type": d.document_type, "dated": d.document_date, "title": d.file_name, "page_count": 1} for d in docs]}
    db.add(PhysicianSnapshot(snapshot_id=ref("snap"), encounter_id=encounter.encounter_id, payload=snap)); db.commit()
    return snap


@doctor_router.get("/queue")
def doctor_queue(clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    username = clinician.get("sub")
    profile = db.query(DoctorProfile).filter(DoctorProfile.username == username).first()
    encounters = (db.query(Encounter).options(joinedload(Encounter.patient))
                  .filter(Encounter.status != "finalized", Encounter.assigned_doctor_username == username)
                  .order_by(Encounter.started_at).all())
    department = ("Ayurveda OPD" if profile and profile.practitioner_type == "ayurveda" else "General Medicine OPD") if profile else "MediKiosk OPD"

    current_time = now()
    wait_by_id = {e.encounter_id: max(0, int((current_time - e.started_at).total_seconds() // 60)) if e.started_at else None for e in encounters}
    wait_minutes = [w for w in wait_by_id.values() if w is not None]
    today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
    seen_today = (db.query(Encounter)
                  .filter(Encounter.assigned_doctor_username == username, Encounter.status == "finalized", Encounter.finalized_at >= today_start)
                  .count())
    stats = {
        "in_queue": len(encounters),
        "seen_today": seen_today,
        "median_wait_min": int(statistics.median(wait_minutes)) if wait_minutes else 0,
        "intake_complete": sum(1 for e in encounters if e.status == "ready"),
    }
    return {"department": department, "doctor": {"name": profile.name if profile else "Authenticated clinician", "hpr": profile.registration if profile else None}, "stats": stats,
            "patients": [{"encounter_id": e.encounter_id, "token": str(e.queue_token) if e.queue_token else str(i + 1), "name": e.patient.name, "age_years": e.patient.age, "sex": e.patient.gender.lower(), "complaint": e.chief_complaint, "department": department, "intake_framework": e.intake_framework, "intake_state": e.status, "wait_min": wait_by_id[e.encounter_id], "priority": e.priority in {"urgent", "priority"}} for i, e in enumerate(encounters)]}


@doctor_router.get("/encounters/{encounter_id}/snapshot")
def doctor_snapshot(encounter_id: str, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).options(joinedload(Encounter.patient)).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    _require_own_encounter(encounter, clinician)
    return _snapshot(db, encounter)


@doctor_router.get("/encounters/{encounter_id}/carry-forward")
def carry_forward(encounter_id: str, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    """What the patient's previous finalized encounter left behind, offered for reuse."""
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    _require_own_encounter(encounter, clinician)
    previous = (db.query(Encounter)
                .filter(Encounter.patient_id == encounter.patient_id, Encounter.encounter_id != encounter_id, Encounter.status == "finalized")
                .order_by(Encounter.finalized_at.desc()).first())
    if not previous:
        return {"from_encounter": None, "from_date": None, "groups": []}
    facts = db.query(ClinicalFact).filter(ClinicalFact.encounter_id == previous.encounter_id).all()
    by_type = lambda typ: [f for f in facts if f.fact_type == typ]
    ledger = db.query(LedgerEntry).filter(LedgerEntry.encounter_id == previous.encounter_id).order_by(LedgerEntry.created_at.desc()).first()
    groups = []
    if previous.chief_complaint:
        groups.append({"key": "symptoms", "label": "Symptoms and findings", "value": previous.chief_complaint})
    conditions = [f.raw_value for f in by_type("condition")]
    if conditions: groups.append({"key": "diagnosis", "label": "Diagnosis", "value": "; ".join(conditions)})
    medications = [f.raw_value for f in by_type("medication")]
    if medications: groups.append({"key": "medicines", "label": "Medicines", "value": "; ".join(medications)})
    investigations = [f.raw_value for f in by_type("investigation")]
    if investigations: groups.append({"key": "investigations", "label": "Investigations", "value": "; ".join(investigations)})
    if ledger and ledger.advice:
        advice_text = "; ".join(a.get("text", str(a)) if isinstance(a, dict) else str(a) for a in ledger.advice)
        if advice_text: groups.append({"key": "advice", "label": "Advice", "value": advice_text})
    return {"from_encounter": previous.encounter_id,
            "from_date": previous.finalized_at.strftime("%Y-%m-%d") if previous.finalized_at else None,
            "groups": groups}


@doctor_router.get("/advice-library")
def advice_library(db: Session = Depends(get_db)):
    entries = db.query(AdviceLibraryEntry).order_by(AdviceLibraryEntry.used_count.desc()).all()
    return [{"id": e.advice_id, "kind": e.kind, "text": e.text, "hi": e.text_hi, "used_count": e.used_count} for e in entries]


@doctor_router.get("/reports/due-back")
def due_back(_: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    """Patients with a doctor-recorded follow-up due, most overdue first.
    Populated from ledger entries — real, not simulated — but only where the
    doctor's free-text follow-up note contains a parseable duration."""
    entries = db.query(LedgerEntry).options(joinedload(LedgerEntry.encounter).joinedload(Encounter.patient)).filter(LedgerEntry.follow_up_required == True).order_by(LedgerEntry.created_at.desc()).all()
    today = now().date()
    rows, seen_patients = [], set()
    for entry in entries:
        encounter = entry.encounter
        if not encounter or encounter.patient_id in seen_patients:
            continue
        days = parse_follow_up_days(entry.follow_up_timeframe)
        if days is None:
            continue
        seen_patients.add(encounter.patient_id)
        due_on = entry.created_at.date() + timedelta(days=days)
        patient = encounter.patient
        rows.append({"patient_id": patient.patient_id, "name": patient.name, "age_years": patient.age, "sex": patient.gender.lower(),
                     "due_on": due_on.isoformat(), "days_overdue": (today - due_on).days, "reason": entry.follow_up_timeframe,
                     "last_seen": encounter.finalized_at.strftime("%Y-%m-%d") if encounter.finalized_at else None,
                     "contact": "ABHA-linked app" if patient.abha_id else "Phone"})
    return sorted(rows, key=lambda r: r["days_overdue"], reverse=True)


def _profile_payload(p: DoctorProfile) -> Dict[str, Any]:
    return {"doctor_id": f"doc_{p.id}", "name": p.name, "initials": p.initials, "qualifications": p.qualifications,
            "title": p.title, "registration": p.registration, "practitioner_type": p.practitioner_type,
            "clinic_name": p.clinic_name, "tagline": p.tagline, "slogan": p.slogan, "address": p.address,
            "department": p.department, "languages": p.languages or []}


@doctor_router.get("/me")
def get_doctor_profile(clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.username == clinician.get("sub")).first()
    if not profile: raise HTTPException(404, "No profile on file for this account")
    return _profile_payload(profile)


@doctor_router.put("/me")
def update_doctor_profile(update: Dict[str, Any], clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    profile = db.query(DoctorProfile).filter(DoctorProfile.username == clinician.get("sub")).first()
    if not profile: raise HTTPException(404, "No profile on file for this account")
    # practitioner_type is intentionally excluded — it's fixed at signup and
    # drives patient routing + which console the doctor sees; editable here
    # would let a doctor silently reroute their own specialty's patients.
    for field in ("name", "initials", "qualifications", "title", "registration",
                  "clinic_name", "tagline", "slogan", "address", "department", "languages"):
        if field in update: setattr(profile, field, update[field])
    db.commit(); db.refresh(profile)
    return _profile_payload(profile)


@doctor_router.get("/documents/{document_id}")
def doctor_document(document_id: str, _: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc: raise HTTPException(404, "Document not found")
    return {"document_id": doc.document_id, "dated": doc.document_date, "lines": [{"text": line} for line in (doc.ocr_text or "").splitlines()]}


@doctor_router.post("/encounters/{encounter_id}/qa")
def doctor_qa(encounter_id: str, request: DoctorQuestionRequest, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    _require_own_encounter(encounter, clinician)
    terms = [word.lower() for word in request.question.split() if len(word) > 3]
    facts = db.query(ClinicalFact).options(joinedload(ClinicalFact.provenance)).filter(ClinicalFact.patient_id == encounter.patient_id).all()
    found = [f for f in facts if any(term in (f.raw_value + " " + (f.normalized_value or "")).lower() for term in terms)]
    if not found: return {"question": request.question, "answer": "The requested information was not found in this patient's records.", "sources": [], "data_available": False}
    return {"question": request.question, "answer": "; ".join(f.normalized_value or f.raw_value for f in found), "sources": [source_for_fact(f) for f in found], "data_available": True}


@doctor_router.post("/encounters/{encounter_id}/ledger")
def save_ledger(encounter_id: str, request: LedgerRequest, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    _require_own_encounter(encounter, clinician)
    if encounter.status == "finalized": raise HTTPException(409, "Finalized encounters require an explicit amendment")
    if request.treatment_change and (not request.deviation_reason or not request.doctor_rationale): raise HTTPException(422, "A reason and doctor-authored rationale are required for treatment changes")
    if not request.doctor_confirmed: raise HTTPException(422, "Doctor confirmation is required")
    entry = LedgerEntry(ledger_id=ref("ledger"), encounter_id=encounter_id, clinician_id=clinician.get("sub", "doctor"), treatment_change=request.treatment_change,
                        previous_treatment=request.previous_treatment, new_treatment=request.new_treatment, deviation_reason=request.deviation_reason,
                        doctor_rationale=request.doctor_rationale, advice=request.advice, medicines=request.medicines, notes=request.notes,
                        follow_up_required=request.follow_up_required, follow_up_timeframe=request.follow_up_timeframe)
    db.add(entry); db.flush(); add_timeline_event(db, encounter.patient_id, encounter_id, "clinical_decision", "Doctor-authored ledger entry", "clinician", entry.ledger_id)
    advice_ids = [a.get("id") for a in request.advice if isinstance(a, dict) and a.get("id")]
    if advice_ids:
        db.query(AdviceLibraryEntry).filter(AdviceLibraryEntry.advice_id.in_(advice_ids)).update(
            {AdviceLibraryEntry.used_count: AdviceLibraryEntry.used_count + 1}, synchronize_session=False)
    db.commit(); return {"ok": True, "encounter_id": encounter_id, "ledger_id": entry.ledger_id}


@doctor_router.post("/encounters/{encounter_id}/finalize")
def finalize_encounter(encounter_id: str, clinician: Dict[str, Any] = Depends(_doctor), db: Session = Depends(get_db)):
    encounter = db.query(Encounter).filter(Encounter.encounter_id == encounter_id).first()
    if not encounter: raise HTTPException(404, "Encounter not found")
    _require_own_encounter(encounter, clinician)
    if not db.query(LedgerEntry).filter(LedgerEntry.encounter_id == encounter_id).first(): raise HTTPException(409, "A ledger entry is required before finalization")
    encounter.status = "finalized"; encounter.finalized_at = now(); encounter.finalized_by = clinician.get("sub", "doctor")
    if not encounter.share_token:
        encounter.share_token = secrets.token_urlsafe(16)
    add_timeline_event(db, encounter.patient_id, encounter_id, "finalization", "Encounter finalized", "encounter", encounter_id); db.commit()
    return {"ok": True, "encounter_id": encounter_id, "status": encounter.status, "share_token": encounter.share_token}
