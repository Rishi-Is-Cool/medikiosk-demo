"""OPD tokens: per doctor, per India day, in arrival order; 'ahead' is live."""
from datetime import datetime

from app.services.integration import ist_day


def _doctor_headers(client):
    response = client.post("/api/auth/token", data={"username": "doctor_opd_101", "password": "doc@MediK2026"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _arrive(client, name):
    session_id = client.post("/patient/register", json={"identity_method": "new", "language": "en",
                                                        "new_patient": {"name": name, "age": "40", "sex": "M"}}).json()["session_id"]
    client.post("/patient/consent", json={"session_id": session_id, "granted": ["intake"], "declined": [],
                                          "language": "en", "audio_explanation_played": False})
    started = client.post("/intake/start", json={"session_id": session_id, "history_mode": "general_medicine",
                                                 "chief_complaints": ["fever"], "language": "en"})
    assert started.status_code == 200, started.text
    queue = client.get("/intake/queue", params={"session_id": session_id})
    assert queue.status_code == 200, queue.text
    return session_id, queue.json()


def test_india_day_boundary():
    # 18:29 UTC is 23:59 in India; 18:30 UTC is already the next day there.
    assert ist_day(datetime(2026, 9, 10, 18, 29)) == "2026-09-10"
    assert ist_day(datetime(2026, 9, 10, 18, 30)) == "2026-09-11"


def test_tokens_follow_arrival_and_ahead_is_live(client, monkeypatch):
    monkeypatch.setenv("KIOSK_DOCTOR_GENERAL", "doctor_opd_101")
    _, first = _arrive(client, "Token Patient One")
    second_session, second = _arrive(client, "Token Patient Two")

    assert second["token"] == first["token"] + 1
    assert second["patients_ahead"] == first["patients_ahead"] + 1
    assert first["queue_date"] == second["queue_date"] == ist_day()
    assert first["doctor_name"] == "Dr. S. Nair" and first["issued_at"].endswith("Z")

    # The doctor's console shows the same token number.
    headers = _doctor_headers(client)
    rows = {p["name"]: p for p in client.get("/api/queue", headers=headers).json()["patients"]}
    assert rows["Token Patient One"]["token"] == str(first["token"])

    # Once the first patient is seen, the second has one fewer ahead.
    encounter_id = rows["Token Patient One"]["encounter_id"]
    client.post(f"/api/encounters/{encounter_id}/ledger", headers=headers, json={"doctor_confirmed": True})
    assert client.post(f"/api/encounters/{encounter_id}/finalize", headers=headers).status_code == 200
    after = client.get("/intake/queue", params={"session_id": second_session}).json()
    assert after["token"] == second["token"]
    assert after["patients_ahead"] == second["patients_ahead"] - 1
