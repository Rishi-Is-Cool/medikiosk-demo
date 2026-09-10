"""Medicine catalog, prescription templates (ownership + copy-on-signup),
finalize now generating a share_token, and the public visit page."""
import uuid


def _register_doctor(client, practitioner_type, name="Test Doctor"):
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


class TestMedicineCatalog:
    def test_medicines_scoped_to_own_specialty(self, client):
        _, general_headers = _register_doctor(client, "general")
        _, ayurveda_headers = _register_doctor(client, "ayurveda")
        general_meds = client.get("/api/medicines", headers=general_headers).json()
        ayurveda_meds = client.get("/api/medicines", headers=ayurveda_headers).json()
        assert general_meds and ayurveda_meds
        assert {m["name"] for m in general_meds}.isdisjoint({m["name"] for m in ayurveda_meds})
        assert any("Paracetamol" in m["name"] for m in general_meds)
        assert any("Churna" in m["name"] or "Vati" in m["name"] or "Kadha" in m["name"] or "Avaleha" in m["name"] or "Arishta" in m["name"] for m in ayurveda_meds)


class TestTemplates:
    def test_new_doctor_gets_starter_templates(self, client):
        _, headers = _register_doctor(client, "general")
        templates = client.get("/api/templates", headers=headers).json()
        assert len(templates) >= 2
        assert all(t["medicines"] for t in templates)

    def test_ayurveda_doctor_gets_ayurveda_starter_templates(self, client):
        _, headers = _register_doctor(client, "ayurveda")
        templates = client.get("/api/templates", headers=headers).json()
        assert len(templates) >= 2
        names = {t["name"] for t in templates}
        assert any("jwara" in n.lower() or "agnimandya" in n.lower() for n in names)

    def test_doctor_cannot_see_another_doctors_templates(self, client):
        _, headers_a = _register_doctor(client, "general", "Dr. A")
        _, headers_b = _register_doctor(client, "general", "Dr. B")
        created = client.post("/api/templates", headers=headers_a, json={
            "name": "Dr A's private template", "medicines": [{"name": "Paracetamol", "dosage": "650mg"}], "advice_ids": [],
        })
        assert created.status_code == 201
        template_id = created.json()["id"]

        b_templates = client.get("/api/templates", headers=headers_b).json()
        assert template_id not in {t["id"] for t in b_templates}

        forbidden_get = client.put(f"/api/templates/{template_id}", headers=headers_b, json={"name": "Hijacked", "medicines": [], "advice_ids": []})
        assert forbidden_get.status_code == 403
        forbidden_delete = client.delete(f"/api/templates/{template_id}", headers=headers_b)
        assert forbidden_delete.status_code == 403

    def test_owner_can_edit_and_delete_own_template(self, client):
        _, headers = _register_doctor(client, "general")
        created = client.post("/api/templates", headers=headers, json={
            "name": "Editable", "medicines": [], "advice_ids": [],
        })
        template_id = created.json()["id"]
        updated = client.put(f"/api/templates/{template_id}", headers=headers, json={
            "name": "Renamed", "medicines": [{"name": "Amoxicillin", "dosage": "250mg"}], "advice_ids": [],
        })
        assert updated.status_code == 200
        assert updated.json()["name"] == "Renamed"
        deleted = client.delete(f"/api/templates/{template_id}", headers=headers)
        assert deleted.status_code == 204
        remaining_ids = {t["id"] for t in client.get("/api/templates", headers=headers).json()}
        assert template_id not in remaining_ids


class TestFinalizeAndPublicVisit:
    def test_finalize_returns_share_token_and_removes_from_queue(self, client):
        doctor_username, headers = _register_doctor(client, "general", "Dr. Finalizer")
        import app.api.integration as integration_module
        original = integration_module.assign_doctor
        integration_module.assign_doctor = lambda db, specialty: doctor_username
        try:
            _start_kiosk_intake(client, "general_medicine", "Finalize Test Patient")
        finally:
            integration_module.assign_doctor = original

        queue = client.get("/api/queue", headers=headers).json()["patients"]
        encounter_id = next(p["encounter_id"] for p in queue if p["name"] == "Finalize Test Patient")

        ledger = client.post(f"/api/encounters/{encounter_id}/ledger", headers=headers, json={
            "treatment_change": False, "advice": [], "medicines": [{"name": "Paracetamol", "dosage": "650mg"}],
            "notes": "Patient advised rest.", "follow_up_required": False, "doctor_confirmed": True,
        })
        assert ledger.status_code == 200

        finalized = client.post(f"/api/encounters/{encounter_id}/finalize", headers=headers)
        assert finalized.status_code == 200
        share_token = finalized.json()["share_token"]
        assert share_token

        queue_after = client.get("/api/queue", headers=headers).json()["patients"]
        assert "Finalize Test Patient" not in {p["name"] for p in queue_after}

        public_page = client.get(f"/api/public/visit/{share_token}")
        assert public_page.status_code == 200
        assert "Finalize Test Patient" in public_page.text
        assert "Paracetamol" in public_page.text
        assert "Patient advised rest." in public_page.text

    def test_unknown_share_token_404s(self, client):
        response = client.get("/api/public/visit/does-not-exist")
        assert response.status_code == 404
