"""Demo returning patients: fake-by-construction IDs, idempotent seeding, lookup."""
from app.database.connection import get_db
from app.database.demo_patients import DEMO_PATIENTS, demo_aadhaar, demo_abha, seed_demo_patients, verhoeff_valid
from app.main import app


def test_demo_ids_are_well_formed_and_never_real():
    abhas = {demo_abha(n) for n in range(1, len(DEMO_PATIENTS) + 1)}
    aadhaars = {demo_aadhaar(n) for n in range(1, len(DEMO_PATIENTS) + 1)}
    assert len(DEMO_PATIENTS) == 20 and len(abhas) == 20 and len(aadhaars) == 20
    assert all(a and len(a.replace("-", "")) == 14 for a in abhas)
    assert all(len(a) == 12 and a.isdigit() for a in aadhaars)
    # A known-valid Aadhaar test number passes, so the checksum itself is right...
    assert verhoeff_valid("234123412346")
    # ...and no demo number can be a real person's.
    assert not any(verhoeff_valid(a) for a in aadhaars)


def test_seeded_demo_patients_are_found_by_either_id(client):
    db = next(app.dependency_overrides[get_db]())
    try:
        first = seed_demo_patients(db)
        again = seed_demo_patients(db)
    finally:
        db.close()
    assert first["created"] + first["skipped"] == 20
    assert again == {"created": 0, "skipped": 20}

    by_abha = client.post("/patient/lookup", json={"identity_method": "abha", "identifier": demo_abha(1)})
    assert by_abha.status_code == 200
    assert by_abha.json()["display_name"] == "Sunita Deshmukh"
    assert by_abha.json()["returning"] is True and by_abha.json()["last_visit"]

    aadhaar = demo_aadhaar(20)
    by_aadhaar = client.post("/patient/lookup", json={"identity_method": "aadhaar",
                                                      "identifier": f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:]}"})
    assert by_aadhaar.status_code == 200
    assert by_aadhaar.json()["display_name"] == "Imran Khan"
    assert by_aadhaar.json()["masked_id"] == f"XXXX XXXX {aadhaar[-4:]}"
