"""
MediKiosk — doctor-facing clinical summary, derived from what is already stored.

The doctor console used to lead with `Encounter.chief_complaint`, which is the
complaint labels and the patient's entire spoken narration glued together. A
doctor opening a chart therefore read a transcript ("Hello, my name is Shubham
and I am 21 years old...") where the chief complaint should be.

Everything here is *derived*, never stored: the source of truth stays the
`IntakeAnswer` rows the kiosk already writes, plus the `ClinicalFact` rows the
document pipeline and the Gemini enrichment write. Nothing in this module calls
an LLM, so the summary a doctor reads does not depend on a background task that
can fail silently — when enrichment is unavailable the summary is simply built
from the structured interview, which is always present.

Positives and negatives come from *structured option selections* wherever they
exist, because an option that was offered and not ticked is an unambiguous
denial. Free text is read only through `adaptive_engine.scan_narrative`, which
is negation-aware: a symptom is never positive merely because its word appeared
in the transcript.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.ai import adaptive_engine as engine
from app.database.schemas import ClinicalFact, Encounter, IntakeAnswer

# Questions whose answers are bookkeeping rather than clinical content, or that
# are rendered in their own section of the snapshot already.
_COMPLAINT_QUESTION_IDS = {"chief_complaints", "q1_chief_complaint"}

# Yes/no questions where "no" is a pertinent negative worth showing, mapped to
# how a clinician would phrase the denial.
_YES_NO_NEGATIVES = {
    "hx_medicines": "Regular medication use",
    "hx_allergy": "Drug or food allergy",
    "fever_measured": "Temperature measured at home",
}

# The free-text follow-ups whose answers *are* the medication / allergy list.
_MEDICATION_TEXT_IDS = ("hx_medicines_list",)
_ALLERGY_TEXT_IDS = ("hx_allergy_list",)

_NO_VALUES = {"no", "none", "not_sure", "unknown"}

# Placeholder texts the engine writes when a patient skipped a free-text answer.
_EMPTY_TEXTS = {"not recorded", "not recalled", "none", "no", "-", "--"}


def _answers_by_id(encounter: Encounter) -> Dict[str, IntakeAnswer]:
    return {a.question_id: a for a in (encounter.answers or [])}


def _source(answer: Optional[IntakeAnswer], fallback_id: Optional[str] = None) -> Dict[str, Any]:
    from app.services.integration import contract_source

    if answer is None:
        return contract_source("encounter", fallback_id)
    return contract_source(answer.source or "patient_touch", answer.answer_id,
                           {"question_id": answer.question_id})


def _is_blank_text(text: Optional[str]) -> bool:
    return not text or text.strip().lower() in _EMPTY_TEXTS


def _concept_key(option: engine.Option) -> str:
    """One identity per clinical concept, across every source it can come from.

    The associated-symptom option "sob", the complaint "breathlessness" and the
    free-text finding "breathless" are the same thing to a doctor; they all
    carry the finding code `breathless`, so that is the key. Without this, a
    symptom denied while narrating and then confirmed in the structured
    question appears as both a positive and a pertinent negative.
    """
    return option.findings[0] if option.findings else option.value


def _option_labels(question: engine.Question, ctx: engine.Context,
                   values: Sequence[str]) -> List[Tuple[str, str]]:
    """(concept key, English label) for the given values, using the options that
    were actually on offer for this encounter."""
    by_value = {o.value: o for o in question.resolved_options(ctx)}
    if question.id == "associated":
        by_value.update({e.option.value: e.option for e in engine._ASSOCIATED})
    return [(_concept_key(by_value[v]), engine.loc(by_value[v].label, "en")) for v in values if v in by_value]


def _offered_but_not_selected(question: engine.Question, ctx: engine.Context,
                              selected: Sequence[str]) -> List[Tuple[str, str]]:
    """The clinical heart of "pertinent negative": the patient was shown this
    option and did not tick it, so they were asked and said no."""
    chosen = set(selected)
    return [(_concept_key(o), engine.loc(o.label, "en"))
            for o in question.resolved_options(ctx)
            if o.value not in chosen and o.value != "none" and not o.exclusive]


def _describe_patient(encounter: Encounter) -> str:
    patient = encounter.patient
    if patient is None:
        return "Patient"
    bits: List[str] = []
    if patient.age:
        bits.append(f"{patient.age}-year-old")
    gender = (patient.gender or "").strip().lower()
    bits.append({"m": "male", "male": "male", "f": "female", "female": "female"}.get(gender, "patient"))
    return " ".join(bits) if bits else "Patient"


def _join(items: Sequence[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{', '.join(items[:-1])} and {items[-1]}"


def build_clinical_summary(encounter: Encounter,
                           facts: Optional[Sequence[ClinicalFact]] = None) -> Dict[str, Any]:
    """The doctor-facing summary for one encounter. Pure derivation — no writes."""
    from app.services.integration import encounter_context, source_for_fact

    ctx = encounter_context(encounter)
    answers = _answers_by_id(encounter)
    complaint_answer = answers.get("chief_complaints")

    # ─── Chief complaint: labels only. The narration is kept, but separately. ──
    complaint_ids = [c for c in ctx.complaints if c != "other"]
    complaint_labels = [engine.complaint_label(c, "en") for c in complaint_ids]
    patient_words = (complaint_answer.answer_text or "").strip() if complaint_answer else ""
    chief_complaint = ", ".join(complaint_labels)
    if not chief_complaint:
        # Only a free-text complaint was given ("Something else"). A short lead
        # is better than nothing, but the full narration still goes to
        # patient_words rather than being presented as the complaint.
        chief_complaint = summarise_free_text(patient_words) or (encounter.chief_complaint or "Not recorded")

    narrative = engine.scan_narrative(patient_words) if patient_words else {"positives": [], "negatives": []}
    narration_source = _source(complaint_answer, encounter.encounter_id)

    positives: List[Dict[str, Any]] = []
    negatives: List[Dict[str, Any]] = []
    seen_pos: Set[str] = set()
    seen_neg: Set[str] = set()

    # A concept lands in exactly one list. Structured answers are recorded first
    # and win, because the patient was asked the question directly and answered
    # it after narrating — so they are the later and more explicit statement.
    def add_positive(key: str, label: str, source: Dict[str, Any], detail: str = "") -> None:
        if not label or key in seen_pos or key in seen_neg:
            return
        seen_pos.add(key)
        positives.append({"key": key, "label": label, "detail": detail, "source": source})

    def add_negative(key: str, label: str, source: Dict[str, Any]) -> None:
        if not label or key in seen_neg or key in seen_pos:
            return
        seen_neg.add(key)
        negatives.append({"key": key, "label": label, "source": source})

    # Complaints the patient ticked are positive by definition.
    for cid, label in zip(complaint_ids, complaint_labels):
        complaint = engine.COMPLAINTS_BY_ID.get(cid)
        key = complaint.findings[0] if complaint and complaint.findings else cid
        add_positive(key, label, narration_source)

    # Structured associated-symptom question: ticked = positive, offered and not
    # ticked = pertinent negative.
    associated_answer = answers.get("associated")
    associated_q = engine.ALL_QUESTIONS.get("associated")
    if associated_answer and associated_q:
        selected = list(associated_answer.values or [])
        source = _source(associated_answer)
        for value, label in _option_labels(associated_q, ctx, selected):
            if value != "none":
                add_positive(value, label, source)
        for value, label in _offered_but_not_selected(associated_q, ctx, selected):
            add_negative(value, label, source)

    # The narration fills gaps the structured questions never covered.
    for item in narrative["positives"]:
        add_positive(item["key"], item["label"], narration_source)
    for item in narrative["negatives"]:
        add_negative(item["key"], item["label"], narration_source)

    # ─── History, medications, allergies ──────────────────────────────────────
    history, med_items, allergy_items = _history_blocks(ctx, answers, narrative, narration_source)
    _merge_facts(facts or [], history, med_items, allergy_items, source_for_fact)

    # Explicit "no" answers to yes/no history questions are pertinent negatives.
    for qid, label in _YES_NO_NEGATIVES.items():
        answer = answers.get(qid)
        if answer and set(answer.values or []) & _NO_VALUES:
            add_negative(qid, label, _source(answer))

    interview = _interview_rows(ctx, answers)
    hpi = _compose_hpi(encounter, ctx, answers, complaint_labels, positives)

    return {
        "chief_complaint": chief_complaint,
        "patient_words": patient_words or None,
        "patient_words_source": narration_source if patient_words else None,
        "hpi": hpi,
        "positives": positives,
        "negatives": negatives,
        "history": history,
        "medications": med_items,
        "allergies": allergy_items,
        "interview": interview,
        "basis": "structured_interview",
    }


def summarise_free_text(text: str, limit: int = 90) -> str:
    """A short lead for a complaint the taxonomy could not classify. Never the
    whole narration — that is what patient_words is for."""
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    first = cleaned.split(".")[0].strip()
    if len(first) > limit:
        first = first[:limit].rsplit(" ", 1)[0] + "…"
    return first


def _history_blocks(ctx: engine.Context, answers: Dict[str, IntakeAnswer],
                    narrative: Dict[str, List[Dict[str, str]]],
                    narration_source: Dict[str, Any]):
    """Conditions, medicines and allergies straight out of the interview —
    available with no LLM call at all."""
    history: List[Dict[str, Any]] = []
    medications: List[Dict[str, Any]] = []
    allergies: List[Dict[str, Any]] = []
    seen = {"history": set(), "medications": set(), "allergies": set()}

    def add(bucket: List[Dict[str, Any]], kind: str, key: str, value: str,
            source: Dict[str, Any], detail: str = "") -> None:
        norm = (value or "").strip()
        if not norm or norm.lower() in seen[kind]:
            return
        seen[kind].add(norm.lower())
        bucket.append({"key": key, "value": norm, "detail": detail, "source": source})

    conditions_answer = answers.get("hx_conditions")
    conditions_q = engine.ALL_QUESTIONS.get("hx_conditions")
    if conditions_answer and conditions_q:
        source = _source(conditions_answer)
        for value, label in _option_labels(conditions_q, ctx, list(conditions_answer.values or [])):
            if value != "none":
                add(history, "history", value, label, source)

    # Conditions the patient volunteered while narrating, before being asked.
    for item in narrative["positives"]:
        if item.get("kind") == "condition":
            add(history, "history", item["key"], item["label"], narration_source)

    for qid in _MEDICATION_TEXT_IDS:
        answer = answers.get(qid)
        if answer and not _is_blank_text(answer.answer_text):
            add(medications, "medications", qid, answer.answer_text.strip(), _source(answer))

    for qid in _ALLERGY_TEXT_IDS:
        answer = answers.get(qid)
        if answer and not _is_blank_text(answer.answer_text):
            add(allergies, "allergies", qid, answer.answer_text.strip(), _source(answer))

    return history, medications, allergies


def _merge_facts(facts: Sequence[ClinicalFact], history: List[Dict[str, Any]],
                 medications: List[Dict[str, Any]], allergies: List[Dict[str, Any]],
                 source_for_fact) -> None:
    """Fold in facts from documents and (when it ran) Gemini enrichment, without
    duplicating anything the interview already gave us."""
    buckets = {"condition": history, "medication": medications, "allergy": allergies}
    for fact in facts:
        bucket = buckets.get(fact.fact_type)
        if bucket is None:
            continue
        value = (fact.normalized_value or fact.raw_value or "").strip()
        if not value or any(item["value"].strip().lower() == value.lower() for item in bucket):
            continue
        details = fact.details or {}
        detail = details.get("reaction") or details.get("dose") or ""
        bucket.append({"key": fact.fact_id, "value": value, "detail": detail,
                       "source": source_for_fact(fact)})


def _interview_rows(ctx: engine.Context, answers: Dict[str, IntakeAnswer]) -> List[Dict[str, Any]]:
    """Every follow-up answer, ordered the way a doctor reads a chart: the
    presenting problem first, then history, then constitution. Previously these
    were emitted in answer order, so ten Dashavidha rows sat between the doctor
    and the five that described the actual illness."""
    order = {"problem": 0, "history": 1, "ayush": 2}
    rows: List[Dict[str, Any]] = []
    for question_id, answer in answers.items():
        if question_id in _COMPLAINT_QUESTION_IDS:
            continue
        question = engine.ALL_QUESTIONS.get(question_id)
        values = list(answer.values or [])
        label = question.doctor_label if question else question_id.replace("_", " ").capitalize()
        value = engine.readable_answer(question, ctx, values, answer.answer_text) if question else (
            answer.answer_text or ", ".join(values))
        if not (value or "").strip():
            continue
        section = question.section if question else "history"
        rows.append({"key": question_id, "label": label, "value": value,
                     "section": section, "source": _source(answer)})
    rows.sort(key=lambda r: order.get(r["section"], 3))
    return rows


def _compose_hpi(encounter: Encounter, ctx: engine.Context, answers: Dict[str, IntakeAnswer],
                 complaint_labels: Sequence[str], positives: Sequence[Dict[str, Any]]) -> str:
    """A concise history of present illness, generated from this patient's own
    answers. Deterministic: the same answers always produce the same sentence."""
    complaints = _join([label.lower() for label in complaint_labels]) or "an unspecified complaint"
    lead = f"{_describe_patient(encounter)} with {complaints}"

    duration = _readable(ctx, answers, "duration")
    if duration:
        # Some duration labels are already a phrase ("Since today (less than a
        # day)"); prefixing "for" onto those reads as "for since today".
        phrase = duration.lower()
        lead += f" {phrase}" if phrase.startswith(("since", "for ")) else f" for {phrase}"
    severity = _readable(ctx, answers, "severity")
    if severity:
        lead += f", {severity.lower()} in severity"
    sentences = [lead.rstrip(".") + "."]

    # Associated positives the patient confirmed, excluding the complaints
    # themselves (already named above). Compared on concept keys, not complaint
    # ids, or "cough_cold" and its finding code "cough" read as two things.
    complaint_keys = set(ctx.complaints)
    for cid in ctx.complaints:
        complaint = engine.COMPLAINTS_BY_ID.get(cid)
        if complaint and complaint.findings:
            complaint_keys.add(complaint.findings[0])
    associated = [p["label"].lower() for p in positives if p["key"] not in complaint_keys]
    if associated:
        sentences.append(f"Reports {_join(associated)}.")

    # Whatever else the problem-focused modules established, in their own words.
    detail_rows = []
    for question_id, answer in answers.items():
        question = engine.ALL_QUESTIONS.get(question_id)
        if not question or question.section != "problem":
            continue
        if question_id in {"duration", "severity", "associated"}:
            continue
        value = engine.readable_answer(question, ctx, list(answer.values or []), answer.answer_text)
        if value and value.strip():
            detail_rows.append(f"{question.doctor_label.lower()}: {value.strip()}")
    if detail_rows:
        joined = "; ".join(detail_rows)
        sentences.append(joined[:1].upper() + joined[1:] + ".")

    return " ".join(sentences)


def _readable(ctx: engine.Context, answers: Dict[str, IntakeAnswer], question_id: str) -> str:
    answer = answers.get(question_id)
    question = engine.ALL_QUESTIONS.get(question_id)
    if not answer or not question:
        return ""
    return engine.readable_answer(question, ctx, list(answer.values or []), None).strip()
