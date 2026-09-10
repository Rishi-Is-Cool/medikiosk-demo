"""Doctor signup/login, and specialty-based patient-to-doctor routing."""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.connection import Base
from app.database.schemas import DoctorProfile, Encounter, Patient
from app.services.integration import NoDoctorAvailable, assign_doctor, canonical_specialty


@pytest.fixture
def isolated_db():
    """A fresh in-memory DB per test, independent of the module-scoped `client`
    fixture's accumulating state — assign_doctor's edge cases (zero doctors,
    exact tie-breaking) need a database whose doctor roster is fully known,
    not whatever earlier tests in this module happened to register."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


class TestAssignDoctorUnit:
    def test_no_doctor_of_specialty_raises(self, isolated_db):
        with pytest.raises(NoDoctorAvailable):
            assign_doctor(isolated_db, "ayurveda")

    def test_picks_the_doctor_with_fewer_active_encounters(self, isolated_db):
        db = isolated_db
        db.add(Patient(patient_id="p1", name="P", age=30, gender="f"))
        db.add(DoctorProfile(username="busy_doc", name="Busy", practitioner_type="general"))
        db.add(DoctorProfile(username="free_doc", name="Free", practitioner_type="general"))
        db.add(Encounter(encounter_id="e1", patient_id="p1", intake_framework="general_medicine",
                         assigned_doctor_username="busy_doc"))
        db.add(Encounter(encounter_id="e2", patient_id="p1", intake_framework="general_medicine",
                         assigned_doctor_username="busy_doc"))
        db.commit()
        assert assign_doctor(db, "general") == "free_doc"

    def test_finalized_encounters_dont_count_toward_load(self, isolated_db):
        db = isolated_db
        db.add(Patient(patient_id="p1", name="P", age=30, gender="f"))
        db.add(DoctorProfile(username="doc_a", name="A", practitioner_type="general"))
        db.add(DoctorProfile(username="doc_b", name="B", practitioner_type="general"))
        db.add(Encounter(encounter_id="e1", patient_id="p1", intake_framework="general_medicine",
                         assigned_doctor_username="doc_a", status="finalized"))
        db.add(Encounter(encounter_id="e2", patient_id="p1", intake_framework="general_medicine",
                         assigned_doctor_username="doc_a", status="finalized"))
        db.commit()
        # doc_a's finalized encounters shouldn't count against them, so a tie
        # remains — resolved alphabetically.
        assert assign_doctor(db, "general") == "doc_a"

    def test_canonical_specialty_mapping(self):
        assert canonical_specialty("ayush") == "ayurveda"
        assert canonical_specialty("general_medicine") == "general"
        assert canonical_specialty("allopathic") == "general"


def _register_doctor(client, practitioner_type, name="Test Doctor"):
    # The test sqlite DB is shared across the whole pytest session (not just
    # this file), so doctors registered here outlive this test and are
    # visible to real (non-monkeypatched) assign_doctor calls in other test
    # modules — notably test_integrated_flow.py, which assumes the seeded
    # demo account ("doctor_opd_101") is the one that gets a "general_medicine"
    # patient. "zzz_" sorts after "doctor_opd_101", so on a tie (both at zero
    # active encounters) the demo account keeps winning by default, exactly
    # as it did before this file existed. This file's own routing tests don't
    # depend on natural tie-break at all — they pin the assignment with
    # monkeypatch — so losing ties here costs nothing.
    username = f"zzz_{uuid.uuid4().hex[:10]}"
    response = client.post("/api/auth/register-doctor", json={
        "username": username, "password": "TestPass123", "name": name, "practitioner_type": practitioner_type,
    })
    assert response.status_code == 201, response.text
    return username, {"Authorization": f"Bearer {response.json()['access_token']}"}


def _start_kiosk_intake(client, history_mode, name):
    registration = client.post("/patient/register", json={
        "identity_method": "new", "language": "en", "new_patient": {"name": name, "age": "30", "sex": "female"},
    })
    session_id = registration.json()["session_id"]
    client.post("/patient/consent", json={
        "session_id": session_id, "granted": ["clinical_intake"], "declined": [], "language": "en",
        "audio_explanation_played": True,
    })
    return client.post("/intake/start", json={
        "session_id": session_id, "history_mode": history_mode, "chief_complaint": "test complaint", "language": "en",
    })


class TestDoctorSignup:
    def test_register_doctor_returns_token(self, client):
        _, headers = _register_doctor(client, "general")
        me = client.get("/api/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["practitioner_type"] == "general"

    def test_duplicate_username_rejected(self, client):
        username, _ = _register_doctor(client, "general")
        dupe = client.post("/api/auth/register-doctor", json={
            "username": username, "password": "AnotherPass123", "name": "Someone Else", "practitioner_type": "ayurveda",
        })
        assert dupe.status_code == 409

    def test_invalid_practitioner_type_rejected(self, client):
        response = client.post("/api/auth/register-doctor", json={
            "username": f"doc_{uuid.uuid4().hex[:10]}", "password": "TestPass123", "name": "X", "practitioner_type": "cardiology",
        })
        assert response.status_code == 422

    def test_registered_doctor_can_log_in_again(self, client):
        username, _ = _register_doctor(client, "ayurveda")
        login = client.post("/api/auth/token", data={"username": username, "password": "TestPass123"})
        assert login.status_code == 200
        assert login.json()["role"] == "doctor"

    def test_practitioner_type_not_editable_via_profile_update(self, client):
        _, headers = _register_doctor(client, "general")
        update = client.put("/api/me", headers=headers, json={"practitioner_type": "ayurveda", "name": "Renamed"})
        assert update.status_code == 200
        assert update.json()["practitioner_type"] == "general"
        assert update.json()["name"] == "Renamed"


class TestDoctorRouting:
    """assign_doctor's own picking logic is covered by TestAssignDoctorUnit
    above, against an isolated DB. These tests instead prove the *wiring*:
    whatever assign_doctor returns actually ends up on Encounter.assigned_
    doctor_username, and drives queue visibility + access control correctly
    end to end — so each test pins the assignment with a monkeypatch rather
    than depending on where the real algorithm's tie-breaks land amid
    whatever other doctors earlier tests in this module have registered into
    the shared, module-scoped `client` database."""

    def test_assigned_doctor_sees_the_patient_and_other_general_doctor_does_not(self, client, monkeypatch):
        doc_a, headers_a = _register_doctor(client, "general", "Dr. A")
        _, headers_b = _register_doctor(client, "general", "Dr. B")
        monkeypatch.setattr("app.api.integration.assign_doctor", lambda db, specialty: doc_a)

        started = _start_kiosk_intake(client, "general_medicine", "Routing Patient")
        assert started.status_code == 200

        names_a = {p["name"] for p in client.get("/api/queue", headers=headers_a).json()["patients"]}
        names_b = {p["name"] for p in client.get("/api/queue", headers=headers_b).json()["patients"]}
        assert "Routing Patient" in names_a
        assert "Routing Patient" not in names_b

    def test_ayurveda_patient_never_reaches_a_general_doctor(self, client, monkeypatch):
        _, general_headers = _register_doctor(client, "general", "Dr. General")
        doc_ayur, ayurveda_headers = _register_doctor(client, "ayurveda", "Dr. Ayur")
        monkeypatch.setattr("app.api.integration.assign_doctor", lambda db, specialty: doc_ayur)

        result = _start_kiosk_intake(client, "ayush", "Ayush Only Patient")
        assert result.status_code == 200

        general_queue = client.get("/api/queue", headers=general_headers).json()["patients"]
        ayurveda_queue = client.get("/api/queue", headers=ayurveda_headers).json()["patients"]
        assert "Ayush Only Patient" not in {p["name"] for p in general_queue}
        assert "Ayush Only Patient" in {p["name"] for p in ayurveda_queue}

    def test_patients_directory_scoped_to_doctors_own_patients(self, client, monkeypatch):
        """GET /api/patients is the doctor console's roster screen — without
        scoping, a general-medicine account could browse Ayurveda patients'
        names and department labels there even though it never treats them."""
        _, general_headers = _register_doctor(client, "general", "Dr. General Roster")
        doc_ayur, ayurveda_headers = _register_doctor(client, "ayurveda", "Dr. Ayur Roster")
        monkeypatch.setattr("app.api.integration.assign_doctor", lambda db, specialty: doc_ayur)

        _start_kiosk_intake(client, "ayush", "Roster Scoping Patient")

        general_names = {p["name"] for p in client.get("/api/patients", headers=general_headers).json()}
        ayurveda_names = {p["name"] for p in client.get("/api/patients", headers=ayurveda_headers).json()}
        assert "Roster Scoping Patient" not in general_names
        assert "Roster Scoping Patient" in ayurveda_names

    def test_doctor_cannot_open_another_doctors_encounter(self, client, monkeypatch):
        doc_owner, headers_a = _register_doctor(client, "general", "Dr. Owner")
        _, headers_b = _register_doctor(client, "general", "Dr. Other")
        monkeypatch.setattr("app.api.integration.assign_doctor", lambda db, specialty: doc_owner)

        _start_kiosk_intake(client, "general_medicine", "Privacy Test Patient")
        encounter_id = next(p["encounter_id"] for p in client.get("/api/queue", headers=headers_a).json()["patients"]
                            if p["name"] == "Privacy Test Patient")
        forbidden = client.get(f"/api/encounters/{encounter_id}/snapshot", headers=headers_b)
        assert forbidden.status_code == 403
        allowed = client.get(f"/api/encounters/{encounter_id}/snapshot", headers=headers_a)
        assert allowed.status_code == 200
