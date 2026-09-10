"""Contract-level MVP flow using deterministic local services only."""

CONTRACT_SOURCE_TYPES = {"patient_spoken", "document", "prior_encounter", "clinician"}


def _doctor_headers(client):
    response = client.post("/api/auth/token", data={"username": "doctor_opd_101", "password": "doc@MediK2026"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _answer(client, session_id, question_id, values=None, text=None, source="patient_touch", transcript_id=None):
    answer = {"source": source, "values": values or []}
    if text:
        answer["text"] = text
    if transcript_id:
        answer["transcript_id"] = transcript_id
    response = client.post("/intake/answer", json={"session_id": session_id, "question_id": question_id,
                                                   "answer": answer, "language": "en"})
    assert response.status_code == 200, response.text
    return response.json()


def test_identity_new_and_returning(client):
    new = client.post("/patient/register", json={"identity_method": "new", "language": "hi", "abha_number": "91 7267 4417 6579",
                                                 "new_patient": {"name": "Asha Patil", "age": "58", "sex": "F"}})
    assert new.status_code == 200, new.text
    assert new.json()["identity_method"] == "abha"
    assert new.json()["masked_id"] == "XX-XXXX-XXXX-6579"
    assert new.json()["returning"] is False

    duplicate = client.post("/patient/register", json={"identity_method": "new", "abha_number": "91-7267-4417-6579",
                                                       "new_patient": {"name": "Someone Else", "age": "30", "sex": "M"}})
    assert duplicate.status_code == 409

    returning = client.post("/patient/lookup", json={"identity_method": "abha", "identifier": "91-7267-4417-6579", "language": "mr"})
    assert returning.status_code == 200
    assert returning.json()["returning"] is True
    assert returning.json()["patient_ref"] == new.json()["patient_ref"]

    aadhaar = client.post("/patient/register", json={"identity_method": "new", "aadhaar_number": "2345 6789 0123",
                                                     "new_patient": {"name": "Ravi Kumar", "age": "40", "sex": "M"}})
    assert aadhaar.status_code == 200
    assert aadhaar.json()["masked_id"] == "XXXX XXXX 0123"
    by_aadhaar = client.post("/patient/lookup", json={"identity_method": "aadhaar", "identifier": "234567890123"})
    assert by_aadhaar.status_code == 200 and by_aadhaar.json()["display_name"] == "Ravi Kumar"

    assert client.post("/patient/lookup", json={"identity_method": "aadhaar", "identifier": "999999999999"}).status_code == 404
    assert client.post("/patient/lookup", json={"identity_method": "abha", "identifier": "123"}).status_code == 422
    invalid = client.post("/patient/register", json={"identity_method": "new", "new_patient": {"name": "", "age": "42"}})
    assert invalid.status_code == 422


def test_patient_to_doctor_longitudinal_flow(client, monkeypatch):
    monkeypatch.setenv("KIOSK_DOCTOR_GENERAL", "doctor_opd_101")
    registration = client.post("/patient/register", json={"identity_method": "new", "language": "en", "new_patient": {"name": "Integration Patient", "age": "42", "sex": "female"}})
    assert registration.status_code == 200
    session_id = registration.json()["session_id"]

    blocked = client.post("/intake/start", json={"session_id": session_id, "history_mode": "general_medicine",
                                                 "chief_complaints": ["chest_pain"], "language": "en"})
    assert blocked.status_code == 409  # consent first

    consent = client.post("/patient/consent", json={"session_id": session_id, "granted": ["clinical_intake"], "declined": [], "language": "en", "audio_explanation_played": True})
    assert consent.status_code == 200

    complaints = client.get("/intake/complaints", params={"language": "hi"}).json()
    assert {"chest_pain", "headache", "fever"} <= {c["id"] for c in complaints}
    matched = client.post("/intake/match-complaint", json={"transcript": "I have chest pain and a headache", "language": "en"}).json()
    assert [c["id"] for c in matched["complaints"]] == ["chest_pain", "headache"]

    started = client.post("/intake/start", json={"session_id": session_id, "history_mode": "general_medicine",
                                                 "chief_complaints": ["chest_pain", "headache"], "language": "en"})
    assert started.status_code == 200
    assert started.json()["question"]["question_id"] == "duration"

    from app.api.integration import whisper_provider
    monkeypatch.setattr(whisper_provider, "transcribe", lambda *_: {
        "transcript": "It started 3 days ago.", "language": "en", "confidence": 0.9,
        "duration_ms": 1000, "provider": "fixture-whisper",
    })
    speech = client.post("/speech/transcribe", data={"session_id": session_id, "question_id": "duration", "language": "en"},
                         files={"audio": ("answer.webm", b"a" * 2048, "audio/webm")})
    assert speech.status_code == 200, speech.text
    transcript_id = speech.json()["transcript_id"]
    assert speech.json()["transcript"] == "It started 3 days ago."
    assert "answer_id" not in speech.json()  # nothing is stored until the patient confirms

    extracted = client.post("/intake/answer", json={"session_id": session_id, "question_id": "duration", "mode": "extract",
                                                    "answer": {"source": "patient_spoken", "text": "It started 3 days ago."}, "language": "en"})
    assert extracted.status_code == 200
    assert extracted.json()["values"] == ["d1_3"]

    step = _answer(client, session_id, "duration", text="It started 3 days ago.", source="patient_spoken", transcript_id=transcript_id)
    assert step["question"]["question_id"] == "cp_character"
    step = _answer(client, session_id, "cp_character", ["pressing"])
    assert step["question"]["question_id"] == "cp_radiation"
    step = _answer(client, session_id, "cp_radiation", ["left_arm"])
    assert step["priority"]["priority"] == "urgent" and step["priority"]["reason_code"] == "ACS_SUSPECTED"

    # A corrected answer resolves the alert instead of leaving a stale red flag.
    step = _answer(client, session_id, "cp_radiation", ["none"])
    assert step["priority"]["priority"] == "normal"
    step = _answer(client, session_id, "cp_radiation", ["left_arm"])
    assert step["priority"]["priority"] == "urgent"

    done = client.post("/intake/autofill", json={"session_id": session_id, "language": "en"})
    assert done.status_code == 200
    assert done.json()["complete"] is True and done.json()["question"] is None

    upload = client.post("/documents/upload-session", json={"session_id": session_id})
    token = upload.json()["token"]
    assert client.post("/documents/upload-session", json={"session_id": session_id}).json()["token"] == token  # stable QR
    assert client.post(f"/documents/upload-session/{token}/connect").json()["status"] == "connected"
    document = client.post(f"/documents/upload-session/{token}/documents", files={"file": ("lab_report.JPG", b"demo-image", "")})
    assert document.status_code == 200, document.text
    status = client.get(f"/documents/upload-session/{token}").json()
    assert status["documents"][0]["status"] in {"processed", "failed"}
    assert status["status"] == "complete"

    headers = _doctor_headers(client)
    queue = client.get("/api/queue", headers=headers)
    assert queue.status_code == 200
    row = next(item for item in queue.json()["patients"] if item["name"] == "Integration Patient")
    encounter_id = row["encounter_id"]
    assert row["intake_state"] == "ready" and row["priority"] is True
    assert row["complaint"] == "Chest pain, Headache"

    snapshot = client.get(f"/api/encounters/{encounter_id}/snapshot", headers=headers)
    assert snapshot.status_code == 200
    body = snapshot.json()
    assert body["patient"]["name"] == "Integration Patient"
    assert [a["rule"] for a in body["alerts"]] == ["ACS_SUSPECTED"]
    items = body["sections"]["hpi"]["items"]
    assert items[0]["key"] == "duration" and items[0]["label"] != "duration"
    assert items[0]["source"]["raw_type"] == "transcript"
    assert "1 to 3 days" in items[0]["value"]
    assert all(item["source"]["type"] in CONTRACT_SOURCE_TYPES for item in items)
    assert body["sections"]["chief_complaint"]["text"]["duration"]

    qa = client.post(f"/api/encounters/{encounter_id}/qa", headers=headers, json={"question": "What chest pain history is recorded?"})
    assert qa.status_code == 200
    assert qa.json()["data_available"]

    unavailable_qa = client.post(f"/api/encounters/{encounter_id}/qa", headers=headers, json={"question": "What penicillin reaction is recorded?"})
    assert unavailable_qa.status_code == 200
    assert unavailable_qa.json()["data_available"] is False

    ledger = client.post(f"/api/encounters/{encounter_id}/ledger", headers=headers, json={"treatment_change": True, "deviation_reason": "Clinical assessment", "doctor_rationale": "Doctor reviewed the intake.", "doctor_confirmed": True})
    assert ledger.status_code == 200
    finalized = client.post(f"/api/encounters/{encounter_id}/finalize", headers=headers)
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "finalized"

    next_encounter = client.post("/intake/start", json={"session_id": session_id, "history_mode": "general_medicine",
                                                        "chief_complaints": ["fever"], "language": "en"})
    assert next_encounter.status_code == 200
    queue_after = client.get("/api/queue", headers=headers)
    new_id = next(item["encounter_id"] for item in queue_after.json()["patients"] if item["name"] == "Integration Patient")
    assert new_id != encounter_id
    # The new visit starts with a clean HPI but still links back to the finalized one.
    longitudinal = client.get(f"/api/encounters/{new_id}/snapshot", headers=headers)
    assert longitudinal.status_code == 200
    assert longitudinal.json()["sections"]["hpi"]["items"] == []
    assert longitudinal.json()["last_visit"]["encounter_id"] == encounter_id
    assert longitudinal.json()["documents"]
