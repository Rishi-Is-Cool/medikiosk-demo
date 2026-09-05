"""Contract-level MVP flow using deterministic local services only."""


def _doctor_headers(client):
    response = client.post("/api/auth/token", data={"username": "doctor_opd_101", "password": "doc@MediK2026"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_patient_to_doctor_longitudinal_flow(client, monkeypatch):
    registration = client.post("/patient/register", json={"identity_method": "new", "language": "en", "new_patient": {"name": "Integration Patient", "age": "42", "sex": "female"}})
    assert registration.status_code == 200
    session_id = registration.json()["session_id"]

    consent = client.post("/patient/consent", json={"session_id": session_id, "granted": ["clinical_intake"], "declined": [], "language": "en", "audio_explanation_played": True})
    assert consent.status_code == 200

    started = client.post("/intake/start", json={"session_id": session_id, "history_mode": "general_medicine", "chief_complaint": "chest pain", "language": "en"})
    assert started.status_code == 200
    assert started.json()["question"]["question_id"] == "q2_duration_onset"

    from app.api.integration import whisper_provider
    monkeypatch.setattr(whisper_provider, "transcribe", lambda *_: {
        "transcript": "The pain started one hour ago.", "language": "en", "confidence": 0.9,
        "duration_ms": 1000, "provider": "fixture-whisper",
    })
    speech = client.post("/speech/transcribe", data={"session_id": session_id, "question_id": "q2_duration_onset", "language": "en"},
                         files={"audio": ("answer.wav", b"a" * 700, "audio/wav")})
    assert speech.status_code == 200
    assert speech.json()["answer_id"]
    assert speech.json()["transcript_id"]

    answer = client.post("/intake/answer", json={"session_id": session_id, "question_id": "q2_duration_onset", "answer": {"source": "patient_touch", "values": ["acute_1h"]}, "language": "en"})
    assert answer.status_code == 200

    upload = client.post("/documents/upload-session", json={"session_id": session_id})
    token = upload.json()["token"]
    document = client.post(f"/documents/upload-session/{token}/documents", files={"file": ("lab_report.jpg", b"demo-image", "image/jpeg")})
    assert document.status_code == 200

    headers = _doctor_headers(client)
    queue = client.get("/api/queue", headers=headers)
    assert queue.status_code == 200
    encounter_id = next(item["encounter_id"] for item in queue.json()["patients"] if item["name"] == "Integration Patient")

    snapshot = client.get(f"/api/encounters/{encounter_id}/snapshot", headers=headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["patient"]["name"] == "Integration Patient"
    assert any(item["source"]["type"] == "transcript" for item in snapshot.json()["sections"]["hpi"]["items"])

    qa = client.post(f"/api/encounters/{encounter_id}/qa", headers=headers, json={"question": "What chest pain history is recorded?"})
    assert qa.status_code == 200
    assert qa.json()["data_available"]

    unavailable_qa = client.post(f"/api/encounters/{encounter_id}/qa", headers=headers, json={"question": "What allergy is recorded?"})
    assert unavailable_qa.status_code == 200
    assert unavailable_qa.json()["data_available"] is False

    ledger = client.post(f"/api/encounters/{encounter_id}/ledger", headers=headers, json={"treatment_change": True, "deviation_reason": "Clinical assessment", "doctor_rationale": "Doctor reviewed the intake.", "doctor_confirmed": True})
    assert ledger.status_code == 200
    finalized = client.post(f"/api/encounters/{encounter_id}/finalize", headers=headers)
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "finalized"

    next_encounter = client.post("/intake/start", json={"session_id": session_id, "history_mode": "general_medicine", "chief_complaint": "follow up", "language": "en"})
    assert next_encounter.status_code == 200
    queue_after = client.get("/api/queue", headers=headers)
    new_id = next(item["encounter_id"] for item in queue_after.json()["patients"] if item["name"] == "Integration Patient")
    assert new_id != encounter_id
    # The current snapshot is built from patient-scoped facts, proving prior records remain retrievable.
    longitudinal = client.get(f"/api/encounters/{new_id}/snapshot", headers=headers)
    assert longitudinal.status_code == 200
    assert longitudinal.json()["sections"]["hpi"]["items"]
