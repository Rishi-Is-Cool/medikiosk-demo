"""The kiosk → doctor console clinical information flow.

Two defects are pinned here:

1. The first spoken complaint was stored as `"<labels> — <whole transcript>"`
   and rendered as the doctor's chief complaint, so the primary clinical line
   was a narration ("Hello, my name is Shubham and I am 21 years old...").
2. Follow-up answers were persisted correctly but reached the doctor as an
   unordered dump, and the history/medication/allergy the interview captured
   never populated those sections at all — they were only ever filled by the
   Gemini enrichment background task, which fails silently.

Everything asserted here is derived from stored `IntakeAnswer` rows, so none of
it depends on an LLM being reachable.
"""
from app.ai import adaptive_engine as engine

NARRATION = (
    "Hello, my name is Shubham and I am 21 years old. I have been having a fever and "
    "headache since last night. I have pain in my throat and discomfort when I swallow. "
    "I don't have vomiting, breathing problems and chest pain. "
    "I don't have asthma or diabetes but I had dengue since childhood."
)


def _doctor_headers(client):
    response = client.post("/api/auth/token", data={"username": "doctor_opd_101", "password": "doc@MediK2026"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _answer(client, session_id, question_id, values=None, text=None, source="patient_touch"):
    answer = {"source": source, "values": values or []}
    if text:
        answer["text"] = text
    response = client.post("/intake/answer", json={"session_id": session_id, "question_id": question_id,
                                                   "answer": answer, "language": "en"})
    assert response.status_code == 200, response.text
    return response.json()


def _start_spoken_encounter(client, monkeypatch, name="Summary Patient"):
    """A patient who speaks the narration above on the first complaint screen."""
    monkeypatch.setenv("KIOSK_DOCTOR_GENERAL", "doctor_opd_101")
    registration = client.post("/patient/register", json={
        "identity_method": "new", "language": "en",
        "new_patient": {"name": name, "age": "21", "sex": "male"}})
    assert registration.status_code == 200, registration.text
    session_id = registration.json()["session_id"]
    client.post("/patient/consent", json={"session_id": session_id, "granted": ["clinical_intake"],
                                          "declined": [], "language": "en", "audio_explanation_played": True})
    started = client.post("/intake/start", json={
        "session_id": session_id, "history_mode": "general_medicine",
        "chief_complaints": ["fever", "cough_cold", "headache"],
        "chief_complaint_text": NARRATION, "language": "en"})
    assert started.status_code == 200, started.text
    return session_id


def _encounter_id(client, headers, name):
    queue = client.get("/api/queue", headers=headers)
    assert queue.status_code == 200, queue.text
    row = next(p for p in queue.json()["patients"] if p["name"] == name)
    return row["encounter_id"]


def _snapshot_for(client, headers, name):
    response = client.get(f"/api/encounters/{_encounter_id(client, headers, name)}/snapshot", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


# ─── 1. The transcript is no longer the chief complaint ───────────────────────

def test_chief_complaint_is_not_the_raw_transcript(client, monkeypatch):
    _start_spoken_encounter(client, monkeypatch, "Verbatim Patient")
    snapshot = _snapshot_for(client, _doctor_headers(client), "Verbatim Patient")
    complaint = snapshot["sections"]["chief_complaint"]

    assert complaint["text"]["value"] == "Fever, Cough, cold or sore throat, Headache"
    assert "Shubham" not in complaint["text"]["value"]
    assert "my name is" not in complaint["text"]["value"].lower()
    # A concise complaint line, not a paragraph.
    assert len(complaint["text"]["value"]) < 80


# ─── 6. ...but the patient's own words are still available ───────────────────

def test_raw_transcript_survives_as_supporting_evidence(client, monkeypatch):
    _start_spoken_encounter(client, monkeypatch, "Supporting Patient")
    snapshot = _snapshot_for(client, _doctor_headers(client), "Supporting Patient")
    complaint = snapshot["sections"]["chief_complaint"]

    assert complaint["patient_words"] == NARRATION
    assert complaint["patient_words_source"]["type"] == "patient_spoken"


# ─── 2 & 5. A generated summary that keeps negation ──────────────────────────

def test_summary_is_generated_from_the_patients_own_answers(client, monkeypatch):
    session_id = _start_spoken_encounter(client, monkeypatch, "Narrative Patient")
    _answer(client, session_id, "duration", ["d1_3"])
    snapshot = _snapshot_for(client, _doctor_headers(client), "Narrative Patient")
    summary = snapshot["sections"]["clinical_summary"]

    # Derived without any LLM call.
    assert summary["basis"] == "structured_interview"
    # The HPI is this patient's own detail, not a template or a transcript.
    assert "21-year-old male" in summary["hpi"]
    assert "fever" in summary["hpi"].lower() and "headache" in summary["hpi"].lower()
    assert "1 to 3 days" in summary["hpi"]
    assert "Shubham" not in summary["hpi"]

    positives = {p["label"] for p in summary["positives"]}
    negatives = {n["label"] for n in summary["negatives"]}

    # Said → positive.
    assert {"Fever", "Headache", "Cough, cold or sore throat"} <= positives
    # Denied → pertinent negative, never positive.
    assert {"Chest pain", "Difficulty breathing", "Vomiting or loose motions"} <= negatives
    assert {"Diabetes", "Asthma or lung disease"} <= negatives
    assert positives.isdisjoint(negatives)
    # The words appear in the transcript but were negated — they must not be positive.
    for denied in ("Chest pain", "Vomiting or loose motions", "Diabetes"):
        assert denied not in positives


def test_denied_conditions_never_become_history(client, monkeypatch):
    _start_spoken_encounter(client, monkeypatch, "Denial Patient")
    snapshot = _snapshot_for(client, _doctor_headers(client), "Denial Patient")
    conditions = {i["value"].lower() for i in snapshot["sections"]["past_medical_surgical"]["items"]}
    assert "diabetes" not in conditions
    assert "asthma or lung disease" not in conditions


# ─── 3 & 4. Follow-up answers are stored and reach the doctor ────────────────

def test_follow_up_answers_are_persisted_and_visible_to_the_doctor(client, monkeypatch):
    session_id = _start_spoken_encounter(client, monkeypatch, "Followup Patient")
    _answer(client, session_id, "duration", ["d1_3"])
    _answer(client, session_id, "fever_pattern", ["on_off"])
    _answer(client, session_id, "severity", ["moderate"])
    _answer(client, session_id, "associated", ["sob"])

    headers = _doctor_headers(client)
    snapshot = _snapshot_for(client, headers, "Followup Patient")
    items = {i["key"]: i for i in snapshot["sections"]["hpi"]["items"]}

    # Persisted...
    for question_id in ("duration", "fever_pattern", "severity", "associated"):
        assert question_id in items, f"{question_id} never reached the doctor"
    # ...and readable, not raw option codes.
    assert items["duration"]["value"] == "1 to 3 days"
    assert items["fever_pattern"]["value"] == "Comes and goes"
    assert items["severity"]["label"] and items["severity"]["value"]
    # Every answer carries provenance the Evidence panel can open.
    assert all(i["source"]["type"] for i in snapshot["sections"]["hpi"]["items"])


def test_follow_up_answer_overrides_the_narration(client, monkeypatch):
    """The patient denied breathlessness while narrating, then ticked it in the
    structured question. The explicit answer wins, and it must not appear as
    both a positive and a negative."""
    session_id = _start_spoken_encounter(client, monkeypatch, "Override Patient")
    _answer(client, session_id, "associated", ["sob"])
    snapshot = _snapshot_for(client, _doctor_headers(client), "Override Patient")
    summary = snapshot["sections"]["clinical_summary"]

    positives = {p["label"] for p in summary["positives"]}
    negatives = {n["label"] for n in summary["negatives"]}
    assert "Difficulty breathing" in positives
    assert "Difficulty breathing" not in negatives


def test_interview_answers_are_ordered_problem_first(client, monkeypatch):
    """Ten Dashavidha rows used to sit between the doctor and the five that
    describe the illness."""
    monkeypatch.setenv("KIOSK_DOCTOR_AYURVEDA", "vaidya_opd_201")
    registration = client.post("/patient/register", json={
        "identity_method": "new", "language": "en",
        "new_patient": {"name": "Ayush Order Patient", "age": "33", "sex": "female"}})
    session_id = registration.json()["session_id"]
    client.post("/patient/consent", json={"session_id": session_id, "granted": ["clinical_intake"],
                                          "declined": [], "language": "en", "audio_explanation_played": True})
    started = client.post("/intake/start", json={"session_id": session_id, "history_mode": "ayush",
                                                 "chief_complaints": ["fever"], "language": "en"})
    assert started.status_code == 200, started.text
    client.post("/intake/autofill", json={"session_id": session_id, "language": "en"})

    # An Ayurveda encounter belongs to the Ayurveda doctor; read it as that doctor.
    vaidya = client.post("/api/auth/token", data={"username": "vaidya_opd_201", "password": "vaidya@MediK2026"})
    assert vaidya.status_code == 200, vaidya.text
    headers = {"Authorization": f"Bearer {vaidya.json()['access_token']}"}
    snapshot = _snapshot_for(client, headers, "Ayush Order Patient")
    sections = [i.get("section") for i in snapshot["sections"]["hpi"]["items"]]
    assert sections, "no interview answers reached the doctor"
    rank = {"problem": 0, "history": 1, "ayush": 2}
    assert sections == sorted(sections, key=lambda s: rank.get(s, 3))
    assert "problem" in sections and "ayush" in sections


# ─── The negation rules themselves ───────────────────────────────────────────

def test_narrative_scan_keeps_positives_and_negatives_apart():
    cases = {
        "I have fever": ("fever", "positive"),
        "I don't have chest pain": ("chest_pain", "negative"),
        "I don't have vomiting": ("gi_upset", "negative"),
        "I feel weak": ("dizziness", "positive"),
        "I don't feel dizzy but I feel weak": ("dizziness", "positive"),
        "I don't have dizziness or weakness": ("dizziness", "negative"),
    }
    for text, (key, expected) in cases.items():
        result = engine.scan_narrative(text)
        positives = {i["key"] for i in result["positives"]}
        negatives = {i["key"] for i in result["negatives"]}
        assert positives.isdisjoint(negatives), text
        assert key in (positives if expected == "positive" else negatives), f"{text!r} → {expected}"


def test_a_negator_does_not_leak_across_a_comma_or_a_new_clause():
    """Regression: "I have fever, no vomiting" used to lose the fever, and
    "I don't have diabetes and I have chest pain" used to lose the chest pain."""
    assert "fever" in engine.match_complaints("I have fever, no vomiting")
    assert "vomiting_diarrhoea" not in engine.match_complaints("I have fever, no vomiting")
    assert "chest_pain" in engine.match_complaints("I don't have diabetes and I have chest pain")
    # A denial still covers a coordinated list of things.
    assert engine.match_complaints("I don't have vomiting, breathing problems and chest pain") == []
    # ...and a red flag is not lost to a trailing denial.
    assert "neck_stiffness" in engine.text_findings("I have a stiff neck, no fever")


def test_inflected_symptoms_are_matched():
    """The taxonomy's keywords are stems; a trailing word boundary meant
    "dizzy", "vomiting", "weakness" and "loose motions" matched nothing."""
    assert "dizziness_weakness" in engine.match_complaints("I feel dizzy")
    assert "dizziness_weakness" in engine.match_complaints("I have weakness")
    assert "vomiting_diarrhoea" in engine.match_complaints("I have vomiting")
    assert "vomiting_diarrhoea" in engine.match_complaints("I have loose motions")
    assert "skin_problem" in engine.match_complaints("I have itching")
    # Short transliterations keep whole-word semantics so "dam" (दम) is safe.
    assert engine.match_complaints("the damage was done") == []
