"""Small, testable orchestration helpers for the integrated API.

No service in this module diagnoses or routes clinical questions using an LLM.
The kiosk interview itself is app.ai.adaptive_engine.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai import adaptive_engine as engine
from app.database.schemas import (
    ClinicalAlert, ClinicalFact, DoctorProfile, Encounter, FactProvenance, IntakeAnswer,
    KioskSession, TimelineEvent,
)

# Answers that describe the visit rather than answer an interview question.
COMPLAINT_ANSWER_IDS = {"chief_complaints", "q1_chief_complaint"}


def ref(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ─── Interview state ──────────────────────────────────────────────────────────


def encounter_context(encounter: Encounter) -> engine.Context:
    """Rebuild the adaptive engine's view of an encounter from its stored answers."""
    complaints: List[str] = []
    complaint_text: Optional[str] = None
    answers: Dict[str, Dict[str, Any]] = {}
    for a in encounter.answers:
        if a.question_id == "chief_complaints":
            complaints = list(a.values or [])
            complaint_text = a.answer_text if a.source in {"patient_spoken", "patient_typed", "patient_voice"} else None
            continue
        if a.question_id in COMPLAINT_ANSWER_IDS:
            continue
        answers[a.question_id] = {"values": list(a.values or []), "text": a.answer_text}
    if not complaints:
        # Encounters started by older clients carry only a free-text complaint.
        complaints = engine.normalize_complaints([encounter.chief_complaint or ""])
    framework = "ayush" if encounter.intake_framework == "ayush" else "general_medicine"
    return engine.build_context(complaints, framework, answers, complaint_text)


def kiosk_question(encounter: Encounter, language: str) -> Dict[str, Any]:
    """Render the next adaptive question, with the encounter's *current* priority.

    Priority is evaluated over the whole encounter every time, so resuming a
    session or switching language can never report "normal" for a patient who
    has already tripped a red flag.
    """
    ctx = encounter_context(encounter)
    priority = priority_state(engine.evaluate_red_flags(ctx.findings))
    question, steps = engine.next_question(ctx)
    if question is None:
        return {"question": None, "priority": priority, "complete": True}
    return {"question": engine.render(question, ctx, steps, language), "priority": priority, "complete": False}


def priority_state(flags: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    flags = list(flags)
    if any(flag.get("priority") == "P1_CRITICAL" for flag in flags):
        critical = next(f for f in flags if f.get("priority") == "P1_CRITICAL")
        return {"priority": "urgent", "red_flag": True, "action": "immediate_assistance",
                "reason_code": critical.get("rule", "P1_CRITICAL")}
    if flags:
        return {"priority": "priority", "red_flag": True, "action": "staff_assistance",
                "reason_code": flags[0].get("rule", "P2_URGENT")}
    return {"priority": "normal", "red_flag": False, "action": "continue"}


def reconcile_red_flags(db: Session, encounter: Encounter, ctx: Optional[engine.Context] = None) -> List[Dict[str, Any]]:
    """Bring the encounter's alerts in line with everything answered so far.

    New rules become ClinicalAlert rows; rules that no longer hold (the patient
    corrected an answer) are *resolved*, not deleted, so the audit trail stays.
    Alerts from the legacy detector (rule ids this engine doesn't own) are left
    untouched.
    """
    ctx = ctx or encounter_context(encounter)
    flags = engine.evaluate_red_flags(ctx.findings)
    active_rules = {f["rule"] for f in flags}

    # Skip the alerts query entirely on the common path: nothing fires now and
    # nothing fired before. The database is a long round-trip away.
    if flags or encounter.priority != "normal":
        open_alerts = (db.query(ClinicalAlert)
                       .filter(ClinicalAlert.encounter_id == encounter.encounter_id, ClinicalAlert.resolved_at.is_(None))
                       .all())
        open_rules = {a.rule for a in open_alerts}
        for alert in open_alerts:
            if alert.rule in engine.RULE_IDS and alert.rule not in active_rules:
                alert.resolved_at = now()
        for flag in flags:
            if flag["rule"] not in open_rules:
                db.add(ClinicalAlert(alert_id=ref("alert"), patient_id=encounter.patient_id, encounter_id=encounter.encounter_id,
                                     severity="critical" if flag["priority"] == "P1_CRITICAL" else "warning", rule=flag["rule"],
                                     headline=flag["title"], detail=flag["message"], sources=[]))
    encounter.priority = priority_state(flags)["priority"]
    return flags


# ─── Persistence ──────────────────────────────────────────────────────────────


def require_session(db: Session, session_id: str) -> KioskSession:
    session = db.query(KioskSession).filter(KioskSession.session_id == session_id, KioskSession.status == "active").first()
    if not session or (session.expires_at and session.expires_at < now()):
        raise ValueError("Kiosk session is unknown or expired")
    return session


def create_fact(db: Session, *, patient_id: str, encounter_id: Optional[str], fact_type: str, raw_value: str,
                source_type: str, source_id: str, normalized_value: Optional[str] = None,
                details: Optional[Dict[str, Any]] = None, confidence: Optional[float] = None,
                locator: Optional[Dict[str, Any]] = None) -> ClinicalFact:
    fact = ClinicalFact(fact_id=ref("fact"), patient_id=patient_id, encounter_id=encounter_id, fact_type=fact_type,
                        raw_value=raw_value, normalized_value=normalized_value, details=details or {}, confidence=confidence)
    db.add(fact)
    db.add(FactProvenance(provenance_id=ref("prov"), fact_id=fact.fact_id, source_type=source_type,
                          source_id=source_id, locator=locator or {}))
    return fact


def persist_answer(db: Session, encounter: Encounter, question_id: str, source: str, values: List[str],
                   text: Optional[str], language: str, *, readable: Optional[str] = None,
                   question_label: Optional[str] = None, transcript_id: Optional[str] = None) -> IntakeAnswer:
    """Store (or overwrite) one answer plus the fact the doctor console reads.

    `readable` is what the doctor sees — English option labels and/or the
    patient's own words — rather than raw option codes like "d1_3".
    """
    existing = next((a for a in encounter.answers if a.question_id == question_id), None)
    raw = (readable or text or ", ".join(values) or "").strip()
    if existing:
        existing.answer_text, existing.values, existing.source, existing.language = text, values, source, language
        fact = (db.query(ClinicalFact)
                .filter(ClinicalFact.encounter_id == encounter.encounter_id, ClinicalFact.fact_type == "intake_answer",
                        ClinicalFact.details["question_id"].as_string() == question_id)
                .first()) if raw else None
        if fact:
            fact.raw_value = raw
        answer = existing
    else:
        answer = IntakeAnswer(answer_id=ref("ans"), encounter_id=encounter.encounter_id, question_id=question_id,
                              answer_text=text, values=values, source=source, language=language)
        encounter.answers.append(answer)
        if raw:
            create_fact(db, patient_id=encounter.patient_id, encounter_id=encounter.encounter_id, fact_type="intake_answer",
                        raw_value=raw, source_type="transcript" if transcript_id else source,
                        source_id=transcript_id or answer.answer_id,
                        details={"question_id": question_id, "question_label": question_label or question_id, "values": values},
                        locator={"answer_id": answer.answer_id, "question_id": question_id})
    return answer


def add_timeline_event(db: Session, patient_id: str, encounter_id: Optional[str], event_type: str, summary: str,
                       source_type: str, source_id: str, details: Optional[Dict[str, Any]] = None) -> None:
    db.add(TimelineEvent(event_id=ref("evt"), patient_id=patient_id, encounter_id=encounter_id, event_date=now(),
                         event_type=event_type, summary=summary, source_type=source_type, source_id=source_id,
                         details=details or {}))


def parse_follow_up_days(text: Optional[str]) -> Optional[int]:
    """Best-effort: pull 'N day(s)/week(s)/month(s)' out of a doctor's free-text
    follow-up note. Returns None when the text doesn't contain a parseable duration
    rather than guessing — a report with a gap is more honest than a wrong date."""
    if not text:
        return None
    match = re.search(r"(\d+)\s*(day|week|month)", text.lower())
    if not match:
        return None
    n, unit = int(match.group(1)), match.group(2)
    return n * {"day": 1, "week": 7, "month": 30}[unit]


# The kiosk speaks its own vocabulary ("general_medicine" / "ayush", per
# frontend-kiosk/src/screens/ConsultationTypeScreen.tsx) which becomes
# Encounter.intake_framework verbatim. Doctor accounts are canonically typed
# as "general" / "ayurveda" — this is the one place that translates between them.
_SPECIALTY_BY_FRAMEWORK = {"ayush": "ayurveda", "general_medicine": "general", "allopathic": "general"}


# The kiosk's gender picker (frontend-kiosk/src/screens/RegistrationScreen.tsx)
# sends single-letter codes ("M"/"F"/"O"). Patient.gender is stored as the
# canonical full word so every downstream reader — the doctor console's
# `sex === "female"` checks, FHIR export, admin reports — sees one consistent
# vocabulary instead of each guessing at case and abbreviation.
_GENDER_BY_CODE = {"m": "male", "f": "female", "o": "other"}


def canonical_gender(raw: str) -> str:
    normalized = (raw or "").strip().lower()
    return _GENDER_BY_CODE.get(normalized, normalized or "unknown")


def canonical_specialty(intake_framework: str) -> str:
    return _SPECIALTY_BY_FRAMEWORK.get(intake_framework, "general")


class NoDoctorAvailable(Exception):
    """Raised when no doctor of the requested specialty is registered."""
    def __init__(self, specialty: str):
        self.specialty = specialty
        super().__init__(f"No {specialty} doctor is currently available")


# Optional, off by default. With several doctors of one specialty registered,
# load-balancing can put a demo patient in any of their queues; these pin kiosk
# intakes to one account (e.g. the one presenting). Ignored if the named
# account doesn't exist or has the wrong specialty.
_PINNED_DOCTOR_ENV = {"general": "KIOSK_DOCTOR_GENERAL", "ayurveda": "KIOSK_DOCTOR_AYURVEDA"}


def assign_doctor(db: Session, specialty: str) -> str:
    """Return the username of the specialty-matching doctor with the fewest
    active (non-finalized) encounters currently assigned. Ties break
    alphabetically by username, for determinism. Raises NoDoctorAvailable if
    no doctor of that specialty is registered at all."""
    doctors = db.query(DoctorProfile).filter(DoctorProfile.practitioner_type == specialty).order_by(DoctorProfile.username).all()
    if not doctors:
        raise NoDoctorAvailable(specialty)
    pinned = os.getenv(_PINNED_DOCTOR_ENV.get(specialty, ""), "").strip()
    if pinned and any(d.username == pinned for d in doctors):
        return pinned
    load = dict.fromkeys((d.username for d in doctors), 0)
    counts = (
        db.query(Encounter.assigned_doctor_username)
        .filter(Encounter.assigned_doctor_username.in_(load.keys()), Encounter.status != "finalized")
        .all()
    )
    for (username,) in counts:
        load[username] += 1
    return min(load.items(), key=lambda item: (item[1], item[0]))[0]


# ─── OPD token ────────────────────────────────────────────────────────────────

# Tokens run on the hospital's calendar day. India has a single time zone and
# no daylight saving, so a fixed +05:30 is exact and needs no tz database.
IST = timezone(timedelta(hours=5, minutes=30))


def ist_day(moment: Optional[datetime] = None) -> str:
    """The date in India for a naive-UTC timestamp (default: now)."""
    return (moment or now()).replace(tzinfo=timezone.utc).astimezone(IST).date().isoformat()


def issue_queue_token(db: Session, encounter: Encounter) -> int:
    """Give the encounter its doctor's next token for the day: 1, 2, 3…

    The doctor's profile row is locked (SELECT … FOR UPDATE) until this
    transaction commits, so two kiosks finishing at the same moment cannot both
    read the same last token; the unique index on (doctor, day, token) backs
    that up. SQLite ignores FOR UPDATE but serialises writers anyway.
    """
    if encounter.queue_token:
        return encounter.queue_token
    day = ist_day(encounter.started_at)
    doctor = encounter.assigned_doctor_username
    db.query(DoctorProfile.id).filter(DoctorProfile.username == doctor).with_for_update().first()
    last = (db.query(func.max(Encounter.queue_token))
            .filter(Encounter.assigned_doctor_username == doctor, Encounter.queue_date == day)
            .scalar()) or 0
    encounter.queue_date, encounter.queue_token = day, last + 1
    return encounter.queue_token


def queue_status(db: Session, encounter: Encounter) -> Dict[str, Any]:
    """The patient's token and how many of the same doctor's patients from the
    same day, with earlier tokens, have not yet been seen (finalized)."""
    ahead = (db.query(func.count(Encounter.id))
             .filter(Encounter.assigned_doctor_username == encounter.assigned_doctor_username,
                     Encounter.queue_date == encounter.queue_date,
                     Encounter.queue_token < encounter.queue_token,
                     Encounter.status != "finalized")
             .scalar()) or 0
    profile = db.query(DoctorProfile).filter(DoctorProfile.username == encounter.assigned_doctor_username).first()
    department = None
    if profile:
        department = profile.department or ("Ayurveda OPD" if profile.practitioner_type == "ayurveda"
                                             else "General Medicine OPD")
    return {"token": encounter.queue_token, "queue_date": encounter.queue_date,
            "issued_at": encounter.started_at.isoformat() + "Z", "patients_ahead": ahead,
            "doctor_name": profile.name if profile else None, "department": department,
            "priority": encounter.priority}


# The doctor console (shared/snapshot-contract.json, SourceChip.jsx) knows four
# provenance types and renders "?" for anything else. Internal source names are
# richer; this maps them onto the contract. `raw_type` keeps the original.
_CONTRACT_SOURCE = {
    "patient_voice": "patient_spoken", "patient_spoken": "patient_spoken", "transcript": "patient_spoken",
    "patient_touch": "patient_spoken", "patient_typed": "patient_spoken", "demo_autofill": "patient_spoken",
    "encounter": "patient_spoken", "kiosk": "patient_spoken",
    "document": "document", "prior_encounter": "prior_encounter", "clinician": "clinician", "doctor": "clinician",
}


def contract_source(source_type: Optional[str], source_id: Optional[str], locator: Any = None) -> Dict[str, Any]:
    raw = source_type or "unknown"
    return {"type": _CONTRACT_SOURCE.get(raw, "patient_spoken"), "raw_type": raw, "id": source_id, "locator": locator}


def source_for_fact(fact: ClinicalFact) -> Dict[str, Any]:
    prov = fact.provenance[0] if fact.provenance else None
    if not prov:
        return contract_source("unknown", fact.fact_id)
    return contract_source(prov.source_type, prov.source_id, prov.locator)
