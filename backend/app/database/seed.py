"""
Seeds reference data that has no AI or patient-data source of truth — a
doctor profile row to edit, and the standard Ayurvedic pathya/apathya advice
library. Idempotent: only inserts rows that don't already exist.
"""
import os

from sqlalchemy.orm import Session

from app.database.schemas import AdviceLibraryEntry, DoctorProfile

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


def seed_reference_data(db: Session) -> None:
    if db.query(AdviceLibraryEntry).count() == 0:
        for advice_id, kind, text, text_hi in _ADVICE_SEED:
            db.add(AdviceLibraryEntry(advice_id=advice_id, kind=kind, text=text, text_hi=text_hi, used_count=0))

    doctor_username = os.getenv("DOCTOR_USERNAME", "doctor_opd_101")
    if not db.query(DoctorProfile).filter(DoctorProfile.username == doctor_username).first():
        db.add(DoctorProfile(
            username=doctor_username,
            name="Dr. S. Nair",
            initials="SN",
            qualifications="B.A.M.S., M.D. (Ayurveda)",
            title="Consultant Physician",
            registration="HPR 71-4402-9915",
            practitioner_type="ayurveda",
            clinic_name="All India Institute of Ayurveda",
            tagline="Sarve santu niramayah",
            slogan="May all be free from illness",
            address="Mathura Road, Gautam Puri, Sarita Vihar, New Delhi 110076",
            department="Ayurveda OPD, Ground floor",
            languages=["hi", "en"],
        ))

    db.commit()
