"""Small, testable orchestration helpers for the integrated API.

No service in this module diagnoses or routes clinical questions using an LLM.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.database.schemas import (
    ClinicalAlert, ClinicalFact, Encounter, FactProvenance, IntakeAnswer,
    KioskSession, TimelineEvent,
)
from app.ai.question_engine import question_engine
from app.ai.red_flag_detector import red_flag_detector


def ref(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def kiosk_question(encounter: Encounter, language: str) -> Dict[str, Any]:
    """Render the deterministic question engine in the kiosk API shape."""
    answers = {a.question_id: (a.values or a.answer_text) for a in encounter.answers}
    mode = "AYUSH" if encounter.intake_framework == "ayush" else "Allopathy"
    response = question_engine.get_next_question(len(encounter.answers) + 1, answers, mode)
    if response.get("is_complete"):
        return {"question": None, "priority": priority_state([]), "complete": True}
    text = response.get("question_text", {})
    raw_type = response.get("input_type", "voice_or_text")
    input_type = {"options": "single_select", "multi_select": "multi_select", "voice_or_text": "voice_or_text"}.get(raw_type, "voice_or_text")
    options = [{"value": item["value"], "label": item["label"], "exclusive": item["value"] in {"none", "fh_none"}}
               for item in (response.get("options") or [])]
    question = {"question_id": response["question_id"], "text": text.get(language) or text.get("en") or "Please answer the question.",
                "input_type": input_type, "options": options, "allow_voice": raw_type == "voice_or_text",
                "allow_text": raw_type == "voice_or_text",
                "progress": {"current": response["step"], "estimated_total": response["total_steps"]}}
    return {"question": question, "priority": priority_state([]), "complete": False}


def priority_state(flags: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    flags = list(flags)
    if any(flag.get("priority") == "P1_CRITICAL" for flag in flags):
        return {"priority": "urgent", "red_flag": True, "action": "immediate_assistance", "reason_code": "P1_CRITICAL"}
    if flags:
        return {"priority": "priority", "red_flag": True, "action": "staff_assistance", "reason_code": flags[0].get("priority", "P2_URGENT")}
    return {"priority": "normal", "red_flag": False, "action": "continue"}


def require_session(db: Session, session_id: str) -> KioskSession:
    session = db.query(KioskSession).filter(KioskSession.session_id == session_id, KioskSession.status == "active").first()
    if not session or (session.expires_at and session.expires_at < now()):
        raise ValueError("Kiosk session is unknown or expired")
    return session


def create_fact(db: Session, *, patient_id: str, encounter_id: Optional[str], fact_type: str, raw_value: str,
                source_type: str, source_id: str, normalized_value: Optional[str] = None,
                details: Optional[Dict[str, Any]] = None, confidence: Optional[float] = None) -> ClinicalFact:
    fact = ClinicalFact(fact_id=ref("fact"), patient_id=patient_id, encounter_id=encounter_id, fact_type=fact_type,
                        raw_value=raw_value, normalized_value=normalized_value, details=details or {}, confidence=confidence)
    db.add(fact)
    db.flush()
    db.add(FactProvenance(provenance_id=ref("prov"), fact_id=fact.fact_id, source_type=source_type,
                          source_id=source_id, locator={}))
    return fact


def persist_answer(db: Session, encounter: Encounter, question_id: str, source: str, values: List[str], text: Optional[str], language: str) -> IntakeAnswer:
    existing = db.query(IntakeAnswer).filter(IntakeAnswer.encounter_id == encounter.encounter_id, IntakeAnswer.question_id == question_id).first()
    if existing:
        existing.answer_text, existing.values, existing.source, existing.language = text, values, source, language
        return existing
    answer = IntakeAnswer(answer_id=ref("ans"), encounter_id=encounter.encounter_id, question_id=question_id,
                          answer_text=text, values=values, source=source, language=language)
    db.add(answer)
    db.flush()
    raw = text or ", ".join(values)
    if raw:
        create_fact(db, patient_id=encounter.patient_id, encounter_id=encounter.encounter_id, fact_type="intake_answer",
                    raw_value=raw, source_type=source, source_id=answer.answer_id, details={"question_id": question_id})
    if question_id.endswith("chief_complaint") and raw:
        encounter.chief_complaint = raw
    return answer


def persist_red_flags(db: Session, encounter: Encounter, text: str) -> List[Dict[str, Any]]:
    flags = red_flag_detector.check_red_flags(text)
    for flag in flags:
        rule = flag.get("rule", flag.get("title", "red_flag"))
        duplicate = db.query(ClinicalAlert).filter(ClinicalAlert.encounter_id == encounter.encounter_id, ClinicalAlert.rule == rule).first()
        if not duplicate:
            db.add(ClinicalAlert(alert_id=ref("alert"), patient_id=encounter.patient_id, encounter_id=encounter.encounter_id,
                                 severity="critical" if flag.get("priority") == "P1_CRITICAL" else "warning", rule=rule,
                                 headline=flag.get("title", "Clinical alert"), detail=flag.get("message"), sources=[]))
    encounter.priority = priority_state(flags)["priority"]
    return flags


def add_timeline_event(db: Session, patient_id: str, encounter_id: Optional[str], event_type: str, summary: str,
                       source_type: str, source_id: str, details: Optional[Dict[str, Any]] = None) -> None:
    db.add(TimelineEvent(event_id=ref("evt"), patient_id=patient_id, encounter_id=encounter_id, event_date=now(),
                         event_type=event_type, summary=summary, source_type=source_type, source_id=source_id,
                         details=details or {}))


def source_for_fact(fact: ClinicalFact) -> Dict[str, Any]:
    prov = fact.provenance[0] if fact.provenance else None
    return {"type": prov.source_type if prov else "unknown", "id": prov.source_id if prov else fact.fact_id,
            "locator": prov.locator if prov else None}
