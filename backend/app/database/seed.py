"""
Seeds reference data that has no AI or patient-data source of truth — a
doctor profile row to edit, the standard Ayurvedic pathya/apathya advice
library, and a starter medicine catalog per specialty. Idempotent: only
inserts rows that don't already exist.
"""
import os
import uuid

from sqlalchemy.orm import Session

from app.database.schemas import AdviceLibraryEntry, DoctorProfile, Medicine, PrescriptionTemplate, User
from app.utils.security import get_password_hash

_ADVICE_SEED = [
    ("adv_001", "pathya", "Drink lukewarm water through the day", "दिनभर गुनगुना पानी पिएँ"),
    ("adv_002", "apathya", "Avoid curd at night", "रात में दही से परहेज़ करें"),
    ("adv_003", "pathya", "Steam inhalation twice daily", "दिन में दो बार भाप लें"),
    ("adv_004", "apathya", "Avoid cold and refrigerated foods", "ठंडे और फ्रिज़ के भोजन से बचें"),
    ("adv_005", "pathya", "Light, warm, freshly cooked meals", "हल्का, गर्म, ताज़ा बना भोजन लें"),
    ("adv_006", "apathya", "Avoid daytime sleep", "दिन में सोने से बचें"),
    ("adv_007", "pathya", "Walk 30 minutes daily", "रोज़ 30 मिनट टहलें"),
    ("adv_008", "apathya", "Avoid spicy and fermented food", "मसालेदार और खमीरी भोजन से बचें"),
    ("adv_009", "pathya", "Sleep by 10 pm", "रात 10 बजे तक सो जाएँ"),
    ("adv_010", "pathya", "Pranayama for 10 minutes each morning", "हर सुबह 10 मिनट प्राणायाम करें"),
    ("adv_011", "apathya", "Avoid suppressing natural urges", "प्राकृतिक वेगों को न रोकें"),
    ("adv_012", "pathya", "Reduce added salt", "नमक की मात्रा कम करें"),
    ("adv_013", "apathya", "Avoid exertion until fever settles", "बुखार उतरने तक परिश्रम न करें"),
    ("adv_014", "pathya", "Buttermilk with roasted cumin after lunch", "दोपहर के भोजन के बाद भुने जीरे के साथ छाछ"),
]

# (medicine_id, name, form, strength, practitioner_type)
_MEDICINE_SEED = [
    ("med_g01", "Paracetamol", "tab", "650mg", "general"),
    ("med_g02", "Azithromycin", "tab", "500mg", "general"),
    ("med_g03", "Amoxicillin", "cap", "250mg", "general"),
    ("med_g04", "Pantoprazole", "tab", "40mg", "general"),
    ("med_g05", "Omeprazole", "tab", "20mg", "general"),
    ("med_g06", "Cetirizine", "tab", "10mg", "general"),
    ("med_g07", "Metformin", "tab", "500mg", "general"),
    ("med_g08", "Amlodipine", "tab", "5mg", "general"),
    ("med_g09", "Atorvastatin", "tab", "10mg", "general"),
    ("med_g10", "Ibuprofen", "tab", "400mg", "general"),
    ("med_g11", "Domperidone", "tab", "10mg", "general"),
    ("med_g12", "ORS", "sachet", None, "general"),
    ("med_a01", "Triphala Churna", "churna", "5gm", "ayurveda"),
    ("med_a02", "Chyawanprash", "avaleha", "10gm", "ayurveda"),
    ("med_a03", "Ashwagandha Churna", "churna", "3gm", "ayurveda"),
    ("med_a04", "Sitopaladi Churna", "churna", "3gm", "ayurveda"),
    ("med_a05", "Trikatu Churna", "churna", "1gm", "ayurveda"),
    ("med_a06", "Dashmoolarishta", "arishta", "15ml", "ayurveda"),
    ("med_a07", "Punarnavadi Kadha", "kadha", "20ml", "ayurveda"),
    ("med_a08", "Hingwashtak Churna", "churna", "2gm", "ayurveda"),
    ("med_a09", "Yashtimadhu Churna", "churna", "3gm", "ayurveda"),
    ("med_a10", "Arogyavardhini Vati", "vati", "250mg", "ayurveda"),
]

# Copied into a doctor's own PrescriptionTemplate rows at signup time — not a
# live shared table, just the starting point each doctor then owns and can
# edit or delete independently. Medicine entries are self-contained (name,
# dosage, frequency, duration) rather than referencing _MEDICINE_SEED ids, so
# a template still reads correctly even if the catalog changes later.
_DEFAULT_TEMPLATES = {
    "general": [
        {
            "name": "Common cold / fever",
            "diagnosis_label": "Viral upper respiratory infection",
            "medicines": [
                {"name": "Paracetamol", "dosage": "650mg", "frequency": "twice daily", "duration": "3 days"},
                {"name": "Cetirizine", "dosage": "10mg", "frequency": "once daily, at night", "duration": "3 days"},
            ],
            "advice_ids": ["adv_001", "adv_003", "adv_007"],
        },
        {
            "name": "Acid reflux / gastritis",
            "diagnosis_label": "Gastro-oesophageal reflux",
            "medicines": [
                {"name": "Pantoprazole", "dosage": "40mg", "frequency": "once daily, before breakfast", "duration": "2 weeks"},
                {"name": "Domperidone", "dosage": "10mg", "frequency": "three times daily, before meals", "duration": "1 week"},
            ],
            "advice_ids": ["adv_004", "adv_008", "adv_005"],
        },
    ],
    "ayurveda": [
        {
            "name": "Jwara (fever) protocol",
            "diagnosis_label": "Jwara",
            "medicines": [
                {"name": "Sitopaladi Churna", "dosage": "3gm", "frequency": "twice daily with honey", "duration": "5 days"},
                {"name": "Trikatu Churna", "dosage": "1gm", "frequency": "twice daily", "duration": "5 days"},
            ],
            "advice_ids": ["adv_001", "adv_013", "adv_006"],
        },
        {
            "name": "Agnimandya (digestive weakness)",
            "diagnosis_label": "Agnimandya",
            "medicines": [
                {"name": "Trikatu Churna", "dosage": "1gm", "frequency": "before meals", "duration": "2 weeks"},
                {"name": "Hingwashtak Churna", "dosage": "2gm", "frequency": "with first bite of each meal", "duration": "2 weeks"},
            ],
            "advice_ids": ["adv_005", "adv_004", "adv_002"],
        },
    ],
}


def copy_default_templates(db: Session, owner_username: str, practitioner_type: str) -> None:
    """Give a newly-registered doctor their own editable copy of the starter
    templates for their specialty. Not a shared/live table — from this point
    each doctor's copy is independent."""
    for tpl in _DEFAULT_TEMPLATES.get(practitioner_type, []):
        db.add(PrescriptionTemplate(
            template_id=f"tpl_{uuid.uuid4().hex[:16]}",
            owner_username=owner_username,
            name=tpl["name"],
            diagnosis_label=tpl.get("diagnosis_label"),
            medicines=tpl["medicines"],
            advice_ids=tpl["advice_ids"],
        ))


def seed_reference_data(db: Session) -> None:
    if db.query(AdviceLibraryEntry).count() == 0:
        for advice_id, kind, text, text_hi in _ADVICE_SEED:
            db.add(AdviceLibraryEntry(advice_id=advice_id, kind=kind, text=text, text_hi=text_hi, used_count=0))

    if db.query(Medicine).count() == 0:
        for medicine_id, name, form, strength, practitioner_type in _MEDICINE_SEED:
            db.add(Medicine(medicine_id=medicine_id, name=name, form=form, strength=strength,
                            practitioner_type=practitioner_type, used_count=0))

    # The demo doctor account backend/tests/ (test_api.py, test_integrated_flow.py)
    # and the frontend's stopgap auto-login both log in as. It's seeded as a real,
    # DB-backed account (not the old in-memory-dict special case) so doctor login
    # has exactly one code path. practitioner_type is "general" because the
    # existing integration test drives a "general_medicine" intake and expects
    # this account to receive it — changing that would break doctor assignment
    # for that test, not just cosmetics.
    doctor_username = os.getenv("DOCTOR_USERNAME", "doctor_opd_101")
    doctor_password = os.getenv("DOCTOR_PASSWORD", "doc@MediK2026")
    is_new_demo_doctor = not db.query(User).filter(User.username == doctor_username).first()
    if is_new_demo_doctor:
        db.add(User(username=doctor_username, role="doctor", display_name="Dr. S. Nair",
                    hashed_password=get_password_hash(doctor_password)))
    if not db.query(DoctorProfile).filter(DoctorProfile.username == doctor_username).first():
        db.add(DoctorProfile(
            username=doctor_username,
            name="Dr. S. Nair",
            initials="SN",
            qualifications="M.B.B.S., M.D. (General Medicine)",
            title="Consultant Physician",
            registration="HPR 71-4402-9915",
            practitioner_type="general",
            clinic_name="All India Institute of Ayurveda",
            tagline="Sarve santu niramayah",
            slogan="May all be free from illness",
            address="Mathura Road, Gautam Puri, Sarita Vihar, New Delhi 110076",
            department="General Medicine OPD",
            languages=["hi", "en"],
        ))
    db.flush()
    if is_new_demo_doctor:
        copy_default_templates(db, doctor_username, "general")

    # AYUSH intakes are routed to an "ayurveda" doctor and fail with 503 when
    # none exists — which is the case on any fresh database. Seed one only when
    # the database has no Ayurveda doctor at all, so a shared database whose
    # team has already registered one keeps its routing exactly as it was.
    if not db.query(DoctorProfile).filter(DoctorProfile.practitioner_type == "ayurveda").first():
        vaidya_username = os.getenv("AYURVEDA_DOCTOR_USERNAME", "vaidya_opd_201")
        vaidya_password = os.getenv("AYURVEDA_DOCTOR_PASSWORD", "vaidya@MediK2026")
        if not db.query(User).filter(User.username == vaidya_username).first():
            db.add(User(username=vaidya_username, role="doctor", display_name="Vd. R. Kulkarni",
                        hashed_password=get_password_hash(vaidya_password)))
        db.add(DoctorProfile(
            username=vaidya_username, name="Vd. R. Kulkarni", initials="RK",
            qualifications="B.A.M.S., M.D. (Ayurveda)", title="Consultant Vaidya",
            practitioner_type="ayurveda", clinic_name="All India Institute of Ayurveda",
            department="Ayurveda OPD", languages=["hi", "en", "mr"],
        ))
        db.flush()
        copy_default_templates(db, vaidya_username, "ayurveda")

    # The hospital-overview console (reception/admin, not tied to one
    # specialty) logs in as a real DB-backed account too, same as doctors —
    # no separate in-memory credential path to keep in sync. It has no
    # DoctorProfile row on purpose: practitioner_type/department belong to a
    # doctor's own console, not to a role that looks across all of them.
    admin_username = os.getenv("ADMIN_USERNAME", "reception_admin_01")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin@MediK2026")
    if not db.query(User).filter(User.username == admin_username).first():
        db.add(User(username=admin_username, role="admin", display_name="Hospital Admin",
                    hashed_password=get_password_hash(admin_password)))

    db.commit()
