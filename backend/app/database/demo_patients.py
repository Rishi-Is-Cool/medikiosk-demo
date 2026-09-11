"""
Demo returning patients for presentations.

Twenty fictional patients, each with an ABHA number, an Aadhaar number and one
finalized previous visit (complaint, conditions, medicines, allergies), so
that looking one up at the kiosk opens a record with real-looking history on
the doctor's console.

The IDs are fake by construction:
- ABHA numbers follow one obvious demo pattern, 91-5000-2026-00NN.
- Every Aadhaar number deliberately FAILS the Verhoeff checksum UIDAI uses,
  so none of them can ever be a real person's Aadhaar.
They are stored exactly like a real patient's: the ABHA number as-is, the
Aadhaar number only as an HMAC plus its last four digits.

Seeding is idempotent (rows are keyed by fixed ids) and is never run
automatically. From backend/:

    python -m app.database.demo_patients          # insert into DATABASE_URL (.env)
    python -m app.database.demo_patients --list   # print the IDs only
"""
from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Run as a script, .env must be loaded BEFORE app.database.connection is
# imported (below, via schemas): it reads DATABASE_URL once, at import, and
# would otherwise fall back to the local SQLite file instead of Supabase.
if __name__ == "__main__":
    try:
        from dotenv import load_dotenv
        load_dotenv(_PROJECT_ROOT / ".env")
    except ImportError:
        pass

from sqlalchemy.orm import Session

from app.database.schemas import ClinicalFact, Encounter, FactProvenance, Patient, TimelineEvent
from app.utils.identity import aadhaar_hash, mask_aadhaar, normalize_abha

# ─── Verhoeff (UIDAI's Aadhaar check digit) ───────────────────────────────────

_D = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5], [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
      [3, 4, 0, 1, 2, 8, 9, 5, 6, 7], [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
      [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3], [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
      [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
_P = [[0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4], [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
      [8, 9, 1, 6, 0, 4, 3, 5, 2, 7], [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
      [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]]


def verhoeff_valid(number: str) -> bool:
    check = 0
    for i, ch in enumerate(reversed(number)):
        check = _D[check][_P[i % 8][int(ch)]]
    return check == 0


def demo_abha(n: int) -> str:
    return normalize_abha(f"915000202600{n:02d}")


def demo_aadhaar(n: int) -> str:
    """12 digits that can never be a real Aadhaar: the check digit is wrong."""
    base = f"50002026{n:03d}"
    return next(base + str(d) for d in range(10) if not verhoeff_valid(base + str(d)))


# ─── The patients ─────────────────────────────────────────────────────────────
# (name, age, sex, language, framework, days since last visit, last complaint,
#  conditions, medicines [(name, dose, frequency)], allergies [(substance, reaction)])

DemoPatient = Tuple[str, int, str, str, str, int, str, List[str], List[Tuple[str, str, str]], List[Tuple[str, str]]]

DEMO_PATIENTS: List[DemoPatient] = [
    ("Sunita Deshmukh", 54, "female", "mr", "general_medicine", 42, "Follow-up for diabetes",
     ["Type 2 diabetes mellitus"], [("Metformin", "500 mg", "1-0-1 after food")], []),
    ("Ramesh Kumar", 61, "male", "hi", "general_medicine", 30, "Headache with high BP readings",
     ["Essential hypertension"], [("Amlodipine", "5 mg", "1-0-0")], []),
    ("Anjali Sharma", 29, "female", "hi", "general_medicine", 75, "Cough and wheezing",
     ["Bronchial asthma"], [("Salbutamol inhaler", "100 mcg", "2 puffs when needed")], [("Penicillin", "Skin rash")]),
    ("Mohammed Irfan", 45, "male", "hi", "general_medicine", 21, "Chest discomfort on walking",
     ["Essential hypertension", "Dyslipidaemia"], [("Telmisartan", "40 mg", "1-0-0"), ("Atorvastatin", "10 mg", "0-0-1")], []),
    ("Lakshmi Iyer", 67, "female", "en", "general_medicine", 60, "Knee pain",
     ["Osteoarthritis of both knees"], [("Paracetamol", "650 mg", "when needed")], []),
    ("Rahul Patil", 34, "male", "mr", "general_medicine", 18, "Burning stomach pain",
     ["Acid peptic disease"], [("Pantoprazole", "40 mg", "1-0-0 before breakfast")], []),
    ("Priya Nair", 38, "female", "en", "general_medicine", 90, "Tiredness and weight gain",
     ["Hypothyroidism"], [("Levothyroxine", "50 mcg", "1-0-0 empty stomach")], []),
    ("Suresh Yadav", 58, "male", "hi", "general_medicine", 35, "Routine diabetes review",
     ["Type 2 diabetes mellitus", "Essential hypertension"], [("Metformin", "1000 mg", "1-0-1"), ("Amlodipine", "5 mg", "1-0-0")], []),
    ("Kavita Joshi", 42, "female", "mr", "general_medicine", 50, "Recurring one-sided headache",
     ["Migraine without aura"], [("Naproxen", "250 mg", "when needed")], []),
    ("Arjun Reddy", 25, "male", "en", "general_medicine", 120, "Fever and body ache",
     ["Viral fever (resolved)"], [], []),
    ("Fatima Shaikh", 50, "female", "hi", "general_medicine", 28, "Tingling in the feet",
     ["Type 2 diabetes mellitus", "Peripheral neuropathy"], [("Glimepiride", "1 mg", "1-0-0"), ("Methylcobalamin", "1500 mcg", "0-0-1")], []),
    ("Vijay Kulkarni", 72, "male", "mr", "general_medicine", 45, "Breathlessness on exertion",
     ["Chronic obstructive pulmonary disease"], [("Tiotropium inhaler", "18 mcg", "once daily")], []),
    ("Meena Gupta", 63, "female", "hi", "general_medicine", 33, "Dizziness",
     ["Essential hypertension"], [("Losartan", "50 mg", "1-0-0")], []),
    ("Sanjay Verma", 47, "male", "hi", "general_medicine", 65, "Lower back pain",
     ["Chronic low back pain"], [("Diclofenac gel", "topical", "twice daily")], []),
    ("Neha Singh", 31, "female", "en", "general_medicine", 80, "Weakness and breathlessness",
     ["Iron deficiency anaemia"], [("Ferrous sulphate", "200 mg", "0-1-0")], []),
    ("Ganesh Pawar", 55, "male", "mr", "general_medicine", 25, "Big toe pain and swelling",
     ["Gout"], [("Febuxostat", "40 mg", "1-0-0")], []),
    ("Deepa Menon", 44, "female", "en", "general_medicine", 100, "Sneezing and blocked nose",
     ["Allergic rhinitis"], [("Cetirizine", "10 mg", "0-0-1")], [("Dust mites", "Sneezing, watery eyes")]),
    ("Harish Chandra", 69, "male", "hi", "general_medicine", 20, "Follow-up after angioplasty",
     ["Ischaemic heart disease", "Post PTCA (2025)"], [("Aspirin", "75 mg", "0-1-0"), ("Atorvastatin", "20 mg", "0-0-1")],
     [("Sulfa drugs", "Hives")]),
    ("Rekha Bhosale", 36, "female", "mr", "ayush", 40, "Acidity and indigestion",
     ["Amlapitta (hyperacidity)"], [("Avipattikar churna", "3 g", "before meals")], []),
    ("Imran Khan", 40, "male", "hi", "general_medicine", 15, "Frequent urination and thirst",
     ["Type 2 diabetes mellitus (newly diagnosed)"], [("Metformin", "500 mg", "0-0-1 after food")], []),
]


def demo_rows() -> List[Dict[str, Any]]:
    return [{"n": n, "name": p[0], "age": p[1], "sex": p[2], "language": p[3], "framework": p[4],
             "abha": demo_abha(n), "aadhaar": demo_aadhaar(n)} for n, p in enumerate(DEMO_PATIENTS, start=1)]


# ─── Seeding ──────────────────────────────────────────────────────────────────


def seed_demo_patients(db: Session) -> Dict[str, int]:
    """Insert whichever demo patients are missing. Returns counts."""
    from app.services.integration import create_fact, now, ref

    created = skipped = 0
    today = now()
    for n, (name, age, sex, language, framework, days_ago, complaint, conditions, medicines, allergies) \
            in enumerate(DEMO_PATIENTS, start=1):
        patient_id = f"pat_demo_{n:02d}"
        abha, aadhaar = demo_abha(n), demo_aadhaar(n)
        if (db.query(Patient).filter((Patient.patient_id == patient_id) | (Patient.abha_id == abha)
                                     | (Patient.aadhaar_hash == aadhaar_hash(aadhaar))).first()):
            skipped += 1
            continue

        visited = today - timedelta(days=days_ago)
        db.add(Patient(patient_id=patient_id, name=name, age=age, gender=sex, language=language,
                       abha_id=abha, aadhaar_hash=aadhaar_hash(aadhaar), aadhaar_last4=aadhaar[-4:],
                       phone=None, consent_granted=True, created_at=visited))
        encounter_id = f"enc_demo_{n:02d}"
        db.add(Encounter(encounter_id=encounter_id, patient_id=patient_id, intake_framework=framework,
                         status="finalized", priority="normal", chief_complaint=complaint, language=language,
                         assigned_doctor_username=None, started_at=visited, finalized_at=visited,
                         finalized_by="demo_seed"))
        db.flush()

        def fact(fact_type: str, value: str, details: Dict[str, Any] | None = None) -> ClinicalFact:
            item = create_fact(db, patient_id=patient_id, encounter_id=encounter_id, fact_type=fact_type,
                               raw_value=value, source_type="clinician", source_id=encounter_id, details=details)
            item.status = "doctor_confirmed"
            item.recorded_at = visited
            return item

        for condition in conditions:
            fact("condition", condition)
        for medicine, dose, frequency in medicines:
            fact("medication", f"{medicine} {dose}", {"dose": dose, "frequency": frequency})
        for substance, reaction in allergies:
            fact("allergy", substance, {"reaction": reaction})
        db.add(TimelineEvent(event_id=ref("evt"), patient_id=patient_id, encounter_id=encounter_id, event_date=visited,
                             event_type="consultation", summary=f"OPD visit: {complaint}",
                             source_type="clinician", source_id=encounter_id, details={}))
        created += 1
    db.commit()
    return {"created": created, "skipped": skipped}


def demo_markdown() -> str:
    lines = ["# Demo returning patients", "",
             "Fictional patients for kiosk demos. The Aadhaar numbers deliberately fail UIDAI's checksum,",
             "so none of them can belong to a real person. Seed with `python -m app.database.demo_patients`",
             "from `backend/`.", "",
             "| # | Name | Age | Sex | Language | ABHA number | Aadhaar number | Last visit for |",
             "|---|------|-----|-----|----------|-------------|----------------|----------------|"]
    for row, patient in zip(demo_rows(), DEMO_PATIENTS):
        a = row["aadhaar"]
        lines.append(f"| {row['n']} | {row['name']} | {row['age']} | {row['sex']} | {row['language']} | "
                     f"{row['abha']} | {a[:4]} {a[4:8]} {a[8:]} | {patient[6]} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    project_root = _PROJECT_ROOT
    (project_root / "DEMO_PATIENTS.md").write_text(demo_markdown(), encoding="utf-8")
    if "--list" in sys.argv:
        print(demo_markdown())
        sys.exit(0)

    from app.database.connection import Base, SessionLocal, engine
    from app.database.migrations import ensure_columns

    Base.metadata.create_all(bind=engine)
    ensure_columns(engine)
    session = SessionLocal()
    try:
        result = seed_demo_patients(session)
    finally:
        session.close()
    print(f"Demo patients: {result['created']} created, {result['skipped']} already present "
          f"({engine.url.host or engine.url.database})")
    print(f"ID list written to {project_root / 'DEMO_PATIENTS.md'}")
