"""
Builds the doctor-console snapshot's `ayush` block (shared/snapshot-contract.json)
from the real Dashavidha Pariksha answers stored on an Encounter.

Reuses app.ai.history_extractor for the human-readable narrative values, and
maps the AYUSH question engine's raw answer codes onto the contract's
pravara/madhyama/avara grade scale. Two of the ten Dashavidha parameters
(Sara, Satmya) aren't collected on that 3-point scale in this intake flow —
those mappings are a documented best-effort approximation, not a clinical
grading. `pramana` (anthropometry) isn't collected at all, so it's omitted
rather than fabricated.
"""
import json
from typing import Any, Dict, Optional

from app.database.schemas import Encounter, IntakeAnswer


def _source(answer: IntakeAnswer) -> Dict[str, Any]:
    return {
        "type": "patient_spoken" if answer.source == "patient_voice" else "patient_touch",
        "id": answer.answer_id,
    }


def _raw_value(answer: IntakeAnswer) -> str:
    if answer.values:
        return str(answer.values[0])
    return answer.answer_text or ""


def build_ayush_block(encounter: Encounter) -> Optional[Dict[str, Any]]:
    """Returns the contract's `ayush` block, or None if not applicable/nothing captured yet."""
    if encounter.intake_framework != "ayush":
        return None

    answers_by_id: Dict[str, IntakeAnswer] = {
        a.question_id: a for a in encounter.answers if a.question_id.startswith("ayush_")
    }
    if not answers_by_id:
        return None

    from app.ai.history_extractor import history_extractor
    raw_answers = {qid: _raw_value(answer) for qid, answer in answers_by_id.items()}
    narrative = history_extractor.extract_history(raw_answers, department_mode="AYUSH")
    ayush_narrative = json.loads(narrative["ayush_data"]) if narrative.get("ayush_data") else {}

    def claim(question_id: str, value: Optional[str]) -> Optional[Dict[str, Any]]:
        answer = answers_by_id.get(question_id)
        if not answer or not value:
            return None
        return {"value": value, "source": _source(answer), "status": "ai_extracted"}

    graded = []

    def add_graded(key: str, label: str, question_id: str, grade_fn) -> None:
        answer = answers_by_id.get(question_id)
        if not answer:
            return
        grade = grade_fn(_raw_value(answer))
        if not grade:
            return
        graded.append({"key": key, "label": label, "grade": grade, "source": _source(answer), "status": "ai_extracted"})

    # Direct grade scale — the question's own answer codes are pravara/madhyama/avara.
    add_graded("samhanana", "Samhanana", "ayush_q5_samhanana",
               lambda v: v if v in {"pravara", "madhyama", "avara"} else None)
    add_graded("sattva", "Sattva", "ayush_q8_sattva",
               lambda v: v.removesuffix("_sattva") if v.endswith("_sattva") else None)
    add_graded("vyayama_shakti", "Vyayama shakti", "ayush_q10_vyayama_shakti",
               lambda v: {"high_vyayama": "pravara", "moderate_vyayama": "madhyama", "low_vyayama": "avara"}.get(v))
    add_graded("ahara_shakti", "Ahara shakti", "ayush_q9_ahara_shakti",
               lambda v: {"high_ahara_vyayama": "pravara", "moderate_ahara_vyayama": "madhyama",
                          "low_ahara_vyayama": "avara", "irregular_ahara": "madhyama"}.get(v))
    # Approximated — these questions aren't asked on a 3-point scale; see module docstring.
    add_graded("sara", "Sara", "ayush_q4_sara", lambda v: "avara" if v == "avasara" else "pravara")
    add_graded("satmya", "Satmya", "ayush_q7_satmya",
               lambda v: {"sarva_satmya": "pravara", "ekahara_satmya": "madhyama",
                          "cold_intolerant": "avara", "heat_intolerant": "avara"}.get(v))

    return {
        "captured": True,
        "prakriti": claim("ayush_q2_prakriti", ayush_narrative.get("Prakriti")),
        "vikriti": claim("ayush_q3_vikriti", ayush_narrative.get("Vikriti")),
        "vaya": claim("ayush_q11_vaya_ahara_vihara", ayush_narrative.get("Vaya_Ahara_Vihara")),
        "pramana": None,
        "graded": graded,
    }
