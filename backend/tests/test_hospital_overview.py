"""GET /api/admin/overview — the hospital-wide queue + red-flag feed a
doctor's own console deliberately never shows (see _require_own_encounter)."""


def _token(client, username, password):
    res = client.post("/api/auth/token", data={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


def _admin_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'reception_admin_01', 'admin@MediK2026')}"}


class TestHospitalOverview:
    def test_requires_admin_role(self, client):
        assert client.get("/api/admin/overview").status_code == 401
        doctor_headers = {"Authorization": f"Bearer {_token(client, 'doctor_opd_101', 'doc@MediK2026')}"}
        assert client.get("/api/admin/overview", headers=doctor_headers).status_code == 403

    def test_admin_sees_every_doctor(self, client):
        res = client.post("/api/auth/register-doctor", json={
            "username": "overview_gp_01", "password": "TestPass123",
            "name": "Dr. Overview Test", "practitioner_type": "general",
        })
        assert res.status_code == 201

        res = client.get("/api/admin/overview", headers=_admin_headers(client))
        assert res.status_code == 200
        data = res.json()
        assert "hospital_stats" in data and "doctors" in data and "alerts" in data
        usernames = {d["username"] for d in data["doctors"]}
        assert "overview_gp_01" in usernames
        stats = data["hospital_stats"]
        assert stats["total_in_queue"] == sum(d["in_queue"] for d in data["doctors"])
