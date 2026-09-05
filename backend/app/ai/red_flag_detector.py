"""
MediKiosk Backend — Emergency Red Flag Detection Engine
Screens patient answers and free-text narration for life-threatening emergency patterns.
Triggers immediate P1/P2 triage alerts before the patient reaches the consultation room.
"""
from typing import List, Dict, Any, Optional

# ─── Emergency Red Flag Rule Library ──────────────────────────────────────────
RED_FLAG_PATTERNS = [
    {
        "id": "ACUTE_CORONARY_SYNDROME",
        "priority": "P1_CRITICAL",
        "title": "EMERGENCY: Suspected Acute Coronary Syndrome / Myocardial Infarction",
        "message": (
            "Patient reports chest pain with associated dyspnoea, diaphoresis, "
            "or radiation to left arm/jaw — classic ACS presentation."
        ),
        "action": (
            "Route patient IMMEDIATELY to Emergency Triage. "
            "Alert duty doctor. Prepare 12-lead ECG and aspirin protocol."
        ),
        # Must match at least 1 primary keyword
        "primary_keywords": [
            "chest pain", "chest tightness", "छाती में दर्द", "छातीत वेदना",
            "chest_pain", "tightness in chest", "pressing chest",
            "हृदय दर्द", "heart pain"
        ],
        # Elevated urgency if any co-symptom present (not required for trigger)
        "co_symptoms": [
            "shortness of breath", "breathlessness", "diaphoresis",
            "cold sweat", "cold_sweats", "left arm pain", "radiates_arm_jaw",
            "सांस फूलना", "ठंडा पसीना", "shortness_of_breath"
        ]
    },
    {
        "id": "STROKE_FAST",
        "priority": "P1_CRITICAL",
        "title": "EMERGENCY: Suspected Acute Cerebrovascular Accident (Stroke) — FAST Criteria",
        "message": (
            "Patient exhibits acute neurological symptoms consistent with FAST stroke criteria: "
            "Facial droop, Arm weakness, Speech difficulty, or sudden onset severe headache."
        ),
        "action": (
            "Activate STROKE ALERT. Transfer patient immediately to Stroke Triage Bay. "
            "CT scan head urgent. Time is brain."
        ),
        "primary_keywords": [
            "facial droop", "face drooping", "slurred speech", "speech difficulty",
            "weakness in arm", "one side paralysis", "arm weakness", "sudden weakness",
            "लकवा", "चेहरे का टेढ़ापन", "बोलने में दिक्कत", "एक तरफ कमजोरी",
            "face paralysis", "sudden severe headache", "worst headache of life"
        ],
        "co_symptoms": []
    },
    {
        "id": "SEVERE_RESPIRATORY_DISTRESS",
        "priority": "P1_CRITICAL",
        "title": "HIGH URGENCY: Severe Acute Respiratory Distress / Airway Compromise",
        "message": (
            "Patient reports acute severe shortness of breath, stridor, gasping, or inability to breathe."
        ),
        "action": (
            "Immediate oxygen support. Alert OPD triage staff. "
            "Prepare nebulisation. Move to emergency bay."
        ),
        "primary_keywords": [
            "unable to breathe", "cannot breathe", "severe breathlessness",
            "stridor", "gasping", "respiratory failure",
            "सांस नहीं आ रही", "सांस बंद हो रही है", "श्वास घेता येत नाही",
            "breathlessness", "unbearable_10", "severe_7_9"
        ],
        "co_symptoms": [
            "shortness_of_breath", "shortness of breath", "पसीना"
        ]
    },
    {
        "id": "ANAPHYLAXIS",
        "priority": "P1_CRITICAL",
        "title": "EMERGENCY: Suspected Anaphylaxis / Severe Allergic Reaction",
        "message": (
            "Patient displays acute throat swelling, lip swelling, or severe allergic reaction "
            "— potential airway compromise."
        ),
        "action": (
            "Immediate medical intervention required. Prepare emergency IM Adrenaline (Epinephrine). "
            "Call crash team."
        ),
        "primary_keywords": [
            "throat swelling", "swelling of lips", "lip swelling", "tongue swelling",
            "severe allergic reaction", "anaphylaxis", "angioedema",
            "गले में सूजन", "होठ सूज रहे हैं", "allergic reaction"
        ],
        "co_symptoms": [
            "shortness of breath", "breathlessness", "rash", "hives"
        ]
    },
    {
        "id": "BACTERIAL_MENINGITIS",
        "priority": "P1_CRITICAL",
        "title": "EMERGENCY: Suspected Bacterial Meningitis",
        "message": (
            "Patient reports high fever combined with neck stiffness and severe headache — "
            "classical triad of bacterial meningitis."
        ),
        "action": (
            "Immediate isolation and neurology alert. "
            "LP and urgent IV antibiotics protocol. Do NOT delay."
        ),
        "primary_keywords": [
            "neck stiffness", "stiff neck", "cannot bend neck", "गर्दन की अकड़न",
            "meningismus", "neck rigidity", "गर्दन अकड़ी है"
        ],
        "co_symptoms": [
            "high fever", "high_fever", "तेज बुखार", "severe headache",
            "photophobia", "light sensitivity", "vomiting"
        ]
    },
    {
        "id": "HYPOGLYCAEMIA_CRISIS",
        "priority": "P2_URGENT",
        "title": "URGENT: Suspected Severe Hypoglycaemia",
        "message": (
            "Patient (known diabetic or unknown) presents with altered consciousness, "
            "sweating, shaking, and confusion — suspect severe low blood sugar."
        ),
        "action": (
            "Immediate blood glucose check. "
            "If < 70 mg/dL and symptomatic, oral glucose or IV dextrose protocol."
        ),
        "primary_keywords": [
            "unconscious", "fainting", "losing consciousness", "shaking",
            "trembling", "confusion", "altered consciousness", "dizziness_syncope",
            "बेहोशी", "चक्कर आना और कंपकंपी", "होश खो देना"
        ],
        "co_symptoms": [
            "diabetes", "sweating", "cold_sweats", "cold sweat", "पसीना"
        ]
    }
]


class RedFlagDetector:
    """
    Analyzes patient complaints, voice transcripts, and questionnaire answers
    for immediate life-threatening emergency conditions.
    Triggers P1_CRITICAL or P2_URGENT priority alerts.
    """

    def check_red_flags(
        self,
        text_content: str,
        answers: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate free-text and structured answers against all red flag patterns.

        Args:
            text_content: Raw free-text (voice transcript, typed answer, etc.)
            answers: Structured answers dict from the interview session

        Returns:
            List of detected alert dictionaries, ordered by priority.
        """
        # Build a combined lower-case corpus from all inputs
        corpus = text_content.lower() if text_content else ""

        if answers:
            for key, val in answers.items():
                if isinstance(val, str):
                    corpus += " " + val.lower()
                elif isinstance(val, list):
                    corpus += " " + " ".join([str(v).lower() for v in val])

        detected_alerts: List[Dict[str, Any]] = []

        for pattern in RED_FLAG_PATTERNS:
            primary_match = any(
                kw.lower() in corpus
                for kw in pattern["primary_keywords"]
            )

            if primary_match:
                co_symptom_count = sum(
                    1 for co in pattern["co_symptoms"]
                    if co.lower() in corpus
                )

                detected_alerts.append({
                    "flag_id": pattern["id"],
                    "title": pattern["title"],
                    "message": pattern["message"],
                    "priority": pattern["priority"],
                    "recommended_action": pattern["action"],
                    "co_symptoms_matched": co_symptom_count,
                    "escalation_level": "IMMEDIATE" if pattern["priority"] == "P1_CRITICAL" else "URGENT"
                })

        # Sort: P1_CRITICAL first, then P2_URGENT
        detected_alerts.sort(key=lambda x: x["priority"])
        return detected_alerts

    def is_emergency(self, text_content: str, answers: Optional[Dict[str, Any]] = None) -> bool:
        """Quick boolean check — True if any P1_CRITICAL flag detected."""
        flags = self.check_red_flags(text_content, answers)
        return any(f["priority"] == "P1_CRITICAL" for f in flags)


red_flag_detector = RedFlagDetector()
