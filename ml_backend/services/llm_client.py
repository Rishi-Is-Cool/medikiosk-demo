import os
import json
import base64
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import httpx

from ml_backend.config import settings

logger = logging.getLogger(__name__)


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Helper to strip markdown code blocks and parse JSON safely."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    return json.loads(text)


class BaseLLMClient(ABC):
    @abstractmethod
    def extract_document_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        document_id: str
    ) -> Dict[str, Any]:
        """Extract structured JSON from a medical document image."""
        pass

    @abstractmethod
    def generate_text_synthesis(
        self,
        system_prompt: str,
        user_content: str,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate structured text synthesis (e.g. physician snapshot or Q&A)."""
        pass


class MockLLMClient(BaseLLMClient):
    """
    High-fidelity deterministic mock client for offline tests, CI, and fallback demo.
    """

    def extract_document_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        document_id: str
    ) -> Dict[str, Any]:
        logger.info(f"MockLLMClient: Processing document {document_id}")
        doc_id_lower = document_id.lower()

        if "esr" in doc_id_lower or "1788237588272" in doc_id_lower or "1788237598696" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "lab_report",
                "confidence": 0.98,
                "document_date": "2026-07-08",
                "patient_name": "Ms. KIAH VIJAYANAND VAIDYA",
                "doctor_name": "Dr. VEDANT H KARVIR / Dr. Unzer Khan [MD. PATH]",
                "hospital_name": "Globus Hospital - Vivanta Diagnostics Pvt. Ltd.",
                "diagnoses": [],
                "medications": [],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "E.S.R. (Erythrocyte's sedimentation rate)",
                        "value": "20",
                        "unit": "mm at the End of 1 hr",
                        "reference_range": "0 to 20",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "E.S.R. (Erythrocyte's sedimentation rate): 20 mm at the End of 1 hr (Ref: 0 to 20)"
                    }
                ],
                "clinical_notes": ["Sample Collected At Lab. Method: Westergrens, Whole Blood."],
                "follow_up": [],
                "raw_entities": []
            }
        elif "egfr" in doc_id_lower or "creatinine" in doc_id_lower or "1788237588547" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "lab_report",
                "confidence": 0.98,
                "document_date": "2026-07-08",
                "patient_name": "Ms. KIAH VIJAYANAND VAIDYA",
                "doctor_name": "Dr. VEDANT H KARVIR / Dr. Unzer Khan [MD. PATH]",
                "hospital_name": "Globus Hospital - Vivanta Diagnostics Pvt. Ltd.",
                "diagnoses": [],
                "medications": [],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "Serum Creatinine",
                        "value": "0.93",
                        "unit": "mg/dl",
                        "reference_range": "0.51 to 1 mg/dl",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "Creatinine: 0.93 mg/dl (Ref: 0.51 to 1)"
                    },
                    {
                        "test_name": "e-GFR",
                        "value": "110.1",
                        "unit": "ml/min/1.73sqm",
                        "reference_range": "> 60 ml/min/1.73sqm",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "e-GFR: 110.1 ml/min/1.73sqm (Ref: > 60)"
                    }
                ],
                "clinical_notes": ["eGFR Estimated Glomerular Filtration Rate Examination - Normal renal filtration rate (>90 ml/min/sq.m)."],
                "follow_up": [],
                "raw_entities": []
            }
        elif "hathi" in doc_id_lower or "deep" in doc_id_lower or "rx_kiah" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.96,
                "document_date": "2026-07-09",
                "patient_name": "Kiah Vaidya",
                "doctor_name": "Dr. Deep Hathi, MD(Med) DM(Endocrinology)",
                "hospital_name": "Endocrinology Clinic",
                "diagnoses": [
                    {
                        "condition": "Newly diagnosed DM (Diabetes Mellitus)",
                        "code": "E10/E11",
                        "status": "active",
                        "raw_text": "Pluricl / Impression: Newly diagnosed DM, Family H/O DM (+)"
                    }
                ],
                "medications": [
                    {
                        "name": "Inj. Insulin FIASP",
                        "dosage": "6 - 6 - 6 units",
                        "frequency": "BBF, BLN, BDN (Before Breakfast, Lunch, Dinner)",
                        "duration": "2 weeks",
                        "route": "Subcutaneous (s/c)",
                        "raw_text": "Inj. Insulin FIASP s/c 6-6-6 BBF BLN BDN"
                    },
                    {
                        "name": "Inj. Insulin Tresiba",
                        "dosage": "8 units",
                        "frequency": "@ 10 pm (Bedtime)",
                        "duration": "2 weeks",
                        "route": "Subcutaneous (s/c)",
                        "raw_text": "Inj. Insulin Tresiba 8 s/c @ 10pm"
                    }
                ],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "HbA1c",
                        "value": "18.8",
                        "unit": "%",
                        "reference_range": "<5.7%",
                        "abnormal": None,
                        "interpretation": "Critical / Severely Elevated",
                        "raw_text": "HbA1c: 18.8%"
                    },
                    {
                        "test_name": "Random Blood Glucose (RBG)",
                        "value": "380",
                        "unit": "mg/dL",
                        "reference_range": "70-140 mg/dL",
                        "abnormal": None,
                        "interpretation": "High / Severely Elevated",
                        "raw_text": "RBG: 380 mg/dL"
                    },
                    {
                        "test_name": "Serum Creatinine",
                        "value": "0.93",
                        "unit": "mg/dL",
                        "reference_range": "0.51-1.0 mg/dL",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "Cr: 0.93"
                    },
                    {
                        "test_name": "TSH",
                        "value": "3.36",
                        "unit": "uIU/mL",
                        "reference_range": "0.4-4.5 uIU/mL",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "TSH: 3.36"
                    }
                ],
                "clinical_notes": [
                    "Patient weight: 38.71 kg.",
                    "Tests ordered: 1. ZnT8, 2. GAD-65, 3. IA-2, 4. Anti-Insulin (Diabetes Autoantibody Panel)."
                ],
                "follow_up": [
                    {
                        "instructions": "Review in 2 weeks with Fasting Plasma Glucose (FPG) and Post Prandial Plasma Glucose (PPPG) report.",
                        "date": "2026-07-23",
                        "doctor_or_dept": "Dr. Deep Hathi (Endocrinology)"
                    }
                ],
                "raw_entities": []
            }
        elif "hindi" in doc_id_lower or "anc" in doc_id_lower or "1788238474387.jpg" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.95,
                "document_date": "2022-05-14",
                "patient_name": "Antenatal OPD Patient",
                "doctor_name": "Medical Officer (OBGYN / OPD)",
                "hospital_name": "Government Hospital / PHC",
                "diagnoses": [
                    {
                        "condition": "Lower Abdominal Pain (पेन इन लोअर एब्डोमेन)",
                        "code": "R10.3",
                        "status": "active",
                        "raw_text": "पेन इन लोअर एब्डोमेन, मोशन नाट पास सिंस थ्री डे"
                    },
                    {
                        "condition": "Constipation / Obstipation (मोशन न होना)",
                        "code": "K59.0",
                        "status": "active",
                        "raw_text": "मोशन नाट पास सिंस थ्री डे"
                    },
                    {
                        "condition": "Antenatal Care (गर्भावस्था देखभाल)",
                        "code": "Z34.9",
                        "status": "active",
                        "raw_text": "LMP: १४ मई २०२२, EDD: २१/०२/२०२३"
                    }
                ],
                "medications": [
                    {
                        "name": "Tab. IFA (Iron Folic Acid / आई. एफ. ए.)",
                        "dosage": "1 Tab",
                        "frequency": "एक गोली रात में (OD HS)",
                        "duration": "30 days (३० दिन)",
                        "route": "Oral",
                        "raw_text": "टैब आई. एफ. ए. - एक गोली रात में x ३० दिन"
                    },
                    {
                        "name": "Tab. Calcium + D3 (कैल्शियम + डी३)",
                        "dosage": "1 Tab",
                        "frequency": "दिन में एक बार दोपहर (OD PC)",
                        "duration": "30 days",
                        "route": "Oral",
                        "raw_text": "टैब कैल्शियम + डी३ दिन में एक बार (दोपहर)"
                    },
                    {
                        "name": "Tab. Multivitamin (मल्टीविटामिन)",
                        "dosage": "1 Tab",
                        "frequency": "रोज एक गोली खाने के बाद (OD PC)",
                        "duration": "30 days",
                        "route": "Oral",
                        "raw_text": "टैब मल्टीविटामिन रोज एक गोली खाने के बाद"
                    },
                    {
                        "name": "Tab. Drotin-M (ड्रोटिन-एम)",
                        "dosage": "1 Tab",
                        "frequency": "जब दर्द हो (SOS / PRN)",
                        "duration": "As needed",
                        "route": "Oral",
                        "raw_text": "टैब ड्रोटिन-एम जब दर्द हो"
                    },
                    {
                        "name": "Tab. Dulcoflex (डुल्कोफ्लेक्स / Bisacodyl)",
                        "dosage": "1 Tab (5mg)",
                        "frequency": "एक गोली रात में (OD HS)",
                        "duration": "As needed",
                        "route": "Oral",
                        "raw_text": "टैब डुल्कोफ्लेक्स एक गोली रात में"
                    }
                ],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "Blood Pressure (बी.पी.)",
                        "value": "110/60",
                        "unit": "mmHg",
                        "reference_range": "120/80 mmHg",
                        "abnormal": False,
                        "interpretation": "Normal",
                        "raw_text": "बी.पी. - ११०/६० एम.एम.एच.जी."
                    },
                    {
                        "test_name": "Pulse Rate (पल्स)",
                        "value": "108",
                        "unit": "bpm",
                        "reference_range": "60-100 bpm",
                        "abnormal": True,
                        "interpretation": "Mild Tachycardia / Elevated",
                        "raw_text": "पल्स - १०८ बी./मि."
                    },
                    {
                        "test_name": "Random Blood Sugar (सुगर)",
                        "value": "103",
                        "unit": "mg/dL",
                        "reference_range": "70-140 mg/dL",
                        "abnormal": False,
                        "interpretation": "Normal",
                        "raw_text": "सुगर - १०३ एम.जी./डे."
                    }
                ],
                "clinical_notes": [
                    "LMP: 14 May 2022, EDD: 21 Feb 2023.",
                    "Patient complained of lower abdominal cramps and constipation for 3 days."
                ],
                "follow_up": [
                    {
                        "instructions": "Review in ANC clinic next month with Routine Blood & Urine Report.",
                        "date": None,
                        "doctor_or_dept": "ANC OPD"
                    }
                ],
                "raw_entities": []
            }
        elif "marathi" in doc_id_lower or "derm" in doc_id_lower or "1788238474387.webp" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.96,
                "document_date": None,
                "patient_name": "Dermatology Patient",
                "doctor_name": "Consultant Dermatologist",
                "hospital_name": "Skin & Dermatology Clinic",
                "diagnoses": [
                    {
                        "condition": "Acne Vulgaris (तारुण्यपिटिका / मुरूम)",
                        "code": "L70.0",
                        "status": "active",
                        "raw_text": "Acne / Pimples treatment regimen"
                    }
                ],
                "medications": [
                    {
                        "name": "Clinmiskin A Gel (Clindamycin + Adapalene)",
                        "dosage": "Topical Gel",
                        "frequency": "रात्री पूर्ण चेहऱ्यावर (पापणी आणि ओठ सोडून) सकाळी धुणे (Night application)",
                        "duration": "Until next review",
                        "route": "Topical",
                        "raw_text": "Clinmiskin A Gel - रात्री पूर्ण चेहऱ्यावर (पापणी आणि ओठ सोडून) सकाळी धुणे"
                    },
                    {
                        "name": "Acnemoist Cream",
                        "dosage": "Topical Cream",
                        "frequency": "एक रोज आड x १० रोज (५ वेळा) नंतर रोज रात्री x ९० रोज; सकाळी आंघोळीनंतर",
                        "duration": "100 days (१०० दिवस)",
                        "route": "Topical",
                        "raw_text": "Acnemoist Cream - एक रोज आड x १० रोज (५ वेळा) रोज रात्री x ९० रोज; सकाळी आंघोळीनंतर x १०० दिवस"
                    },
                    {
                        "name": "Brevoxyl Creamy Wash (Benzoyl Peroxide)",
                        "dosage": "Topical Cleanser",
                        "frequency": "चेहऱ्याला चोळून धुणे (Wash gently)",
                        "duration": "100 days (१०० दिवस)",
                        "route": "Topical",
                        "raw_text": "Brevoxyl Creamy Wash - चेहऱ्याला चोळून धुणे x १०० दिवस"
                    },
                    {
                        "name": "Persol 5% Gel (Benzoyl Peroxide 5%)",
                        "dosage": "Topical Gel",
                        "frequency": "१० ते १२ मिनिटे लावून धुणे खांद्यावर / पाठीवर (Apply 10-12 mins then rinse)",
                        "duration": "As directed",
                        "route": "Topical",
                        "raw_text": "Persol 5% Gel - १० ते १२ मिनिटे लावून धुणे (खांद्यावर / पाठीवर)"
                    }
                ],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [],
                "clinical_notes": [
                    "Strict instruction: Avoid applying Clinmiskin A gel around eyes/eyelids and lips.",
                    "Review next Wednesday."
                ],
                "follow_up": [
                    {
                        "instructions": "Review next Wednesday (पुढच्या बुधवारी दाखवणे).",
                        "date": None,
                        "doctor_or_dept": "Dermatology"
                    }
                ],
                "raw_entities": []
            }
        elif "1788239314850" in doc_id_lower or "tonmoy" in doc_id_lower or "zimax" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.97,
                "document_date": "2026-02-20",
                "patient_name": "Adult OPD Patient",
                "doctor_name": "Dr. Torequl Islam Tonmoy, CCD (BIRDEM), CMU(USG)",
                "hospital_name": "Sir Salimullah Medical College & Mitford Hospital (Pharmacy Consultation)",
                "diagnoses": [
                    {
                        "condition": "Tinea Corporis / Fungal Skin Infection (দাদ / ফাঙ্গাল ইনফেকশন)",
                        "code": "B35.4",
                        "status": "active",
                        "raw_text": "Fungal infection with skin allergy and pruritus"
                    }
                ],
                "medications": [
                    {
                        "name": "Tab. Zimax (Azithromycin 500mg)",
                        "dosage": "500 mg",
                        "frequency": "১ + ০ + ০ (1 morning once daily)",
                        "duration": "৫ দিন (5 days)",
                        "route": "Oral",
                        "raw_text": "Tab. Zimax (500mg) ১+০+০ (৫ দিন)"
                    },
                    {
                        "name": "Cap. Itra (Itraconazole 100mg)",
                        "dosage": "100 mg",
                        "frequency": "১ + ০ + ১ (1 morning & 1 night - BD)",
                        "duration": "২১ দিন (21 days)",
                        "route": "Oral",
                        "raw_text": "Cap. Itra (100mg) ১+০+১ (২১ দিন)"
                    },
                    {
                        "name": "Tab. Progut Mups (Esomeprazole 20mg)",
                        "dosage": "20 mg",
                        "frequency": "১ + ০ + ১ (খাবার ৩০ মি. আগে - 30 mins before meals)",
                        "duration": "১ মাস (1 month)",
                        "route": "Oral",
                        "raw_text": "Tab. Progut Mups (20mg) ১+০+১ (খাবার ৩০ মি. আগে) (১ মাস)"
                    },
                    {
                        "name": "Tab. Alben-DS (Albendazole 400mg)",
                        "dosage": "400 mg",
                        "frequency": "১টি ট্যাবলেট খাবেন। ৭ দিন পর পুনরায় ০১টি ট্যাবলেট খাবেন। (1 stat, repeat after 7 days)",
                        "duration": "2 doses (7 days apart)",
                        "route": "Oral",
                        "raw_text": "Tab. Alben-DS: ১টি ট্যাবলেট খাবেন। ৭ দিন পর আবার পুনরায় ০১টি ট্যাবলেট খাবেন।"
                    },
                    {
                        "name": "Dancel Shampoo (Ketoconazole 2%)",
                        "dosage": "Topical Shampoo",
                        "frequency": "গোসলের আগে সারা গায়ে মেখে ২০ মিনিট অপেক্ষা করে গোসল করবেন (সপ্তাহে ৩/৪ দিন)",
                        "duration": "১ মাস (1 month)",
                        "route": "Topical",
                        "raw_text": "Dancel shampoo: গোসলের আগে সারা গায়ে মেখে ২০ মিনিট অপেক্ষা করে গোসল করবেন। এভাবে सप्ताह ৩/৪ দিন। (১ মাস)"
                    },
                    {
                        "name": "Tab. Xyrol / Xyryl (Hydroxyzine 25mg)",
                        "dosage": "25 mg",
                        "frequency": "০ + ০ + ১ (1 at night at bedtime - OD HS)",
                        "duration": "২১ দিন (21 days)",
                        "route": "Oral",
                        "raw_text": "Tab. Xyrol (25mg) ০+০+১ (২১ দিন)"
                    }
                ],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [],
                "clinical_notes": [
                    "Patient Age: 40 yrs.",
                    "Antifungal and anti-allergic skin regimen with deworming protocol."
                ],
                "follow_up": [],
                "raw_entities": []
            }
        elif "1788239320636" in doc_id_lower or "malayalam" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.98,
                "document_date": "2019-10-03",
                "patient_name": "DEMO PATIENT",
                "doctor_name": "Consultant Pediatrician (MBBS, MD, MS)",
                "hospital_name": "Pediatric Healthcare Centre",
                "diagnoses": [
                    {
                        "condition": "Fever (പനി)",
                        "code": "R50.9",
                        "status": "active",
                        "raw_text": "Diagnosis: * FEVER"
                    }
                ],
                "medications": [
                    {
                        "name": "TAB. DEMO MEDICINE 1",
                        "dosage": "1 Tablet",
                        "frequency": "1 രാവിലെ, 1 രാത്രി (ഭക്ഷണത്തിന് முன்பு) - Morning & Night before food (BD AC)",
                        "duration": "10 ദിവസം (10 days / Total 20 tablets)",
                        "route": "Oral",
                        "raw_text": "TAB. DEMO MEDICINE 1: 1 രാവിലെ, 1 രാത്രി (ഭക്ഷണത്തിന് முன்பு) x 10 ദിവസം"
                    },
                    {
                        "name": "CAP. DEMO MEDICINE 2",
                        "dosage": "1 Capsule",
                        "frequency": "1 രാവിലെ, 1 രാത്രി (ഭക്ഷണത്തിന് முன்பு) - Morning & Night before food (BD AC)",
                        "duration": "10 ദിവസം (10 days / Total 20 capsules)",
                        "route": "Oral",
                        "raw_text": "CAP. DEMO MEDICINE 2: 1 രാവിലെ, 1 രാത്രി (ഭക്ഷണത്തിന് முன்பு) x 10 ദിവസം"
                    },
                    {
                        "name": "TAB. DEMO MEDICINE 3",
                        "dosage": "1 Tablet",
                        "frequency": "1 രാവിലെ, 1 ഉച്ചതിരിഞ്ഞ്, 1 വൈകുന്നേരം, 1 രാത്രി (ഭക്ഷണത്തിന് ശേഷം) - QID PC (Four times daily after meals)",
                        "duration": "10 ദിവസം (10 days / Total 40 tablets)",
                        "route": "Oral",
                        "raw_text": "TAB. DEMO MEDICINE 3: 1 രാവിലെ, 1 ഉച്ചതിരിഞ്ഞ്, 1 വൈകുന്നേരം, 1 രാത്രി (ഭക്ഷണത്തിന് ശേഷം) x 10 ദിവസം"
                    },
                    {
                        "name": "TAB. DEMO MEDICINE 4",
                        "dosage": "1/2 Tablet",
                        "frequency": "1/2 രാവിലെ, 1/2 രാത്രി - Half tab twice daily",
                        "duration": "10 ദിവസം (10 days / Total 10 tablets)",
                        "route": "Oral",
                        "raw_text": "TAB. DEMO MEDICINE 4: 1/2 രാവിലെ, 1/2 രാത്രി x 10 ദിവസം"
                    }
                ],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "Blood Pressure",
                        "value": "120/80",
                        "unit": "mmHg",
                        "reference_range": "120/80 mmHg",
                        "abnormal": False,
                        "interpretation": "Normal",
                        "raw_text": "BP: 120/80 mmHg"
                    }
                ],
                "clinical_notes": [
                    "Patient: 8 Y / Male, Weight: 25 kg, Height: 127 cm, BMI: 15.50.",
                    "Advice Given: * DRINK BOILED WATER (തിളപ്പിച്ചാറിയ വെള്ളം കുടിക്കുക)."
                ],
                "follow_up": [
                    {
                        "instructions": "അടുത്ത പരിശോധന (Next review / follow-up): 18-10-2019.",
                        "date": "2019-10-18",
                        "doctor_or_dept": "Pediatrics"
                    }
                ],
                "raw_entities": []
            }
        elif "bengali" in doc_id_lower or "jyotirmoy" in doc_id_lower or "malati" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.98,
                "document_date": "2021-02-04",
                "patient_name": "Malati Debnath",
                "doctor_name": "Dr. Jyotirmoy Das, MBBS, MD (Medicine)",
                "hospital_name": "Sebamangal Medical, Kalna, Purba Bardhaman",
                "diagnoses": [
                    {
                        "condition": "Cerebral Infarct / Acute Ischemic Stroke (ইনফার্কট)",
                        "code": "I63.9",
                        "status": "active",
                        "raw_text": "C/O: H/O fall, severe pain & inability to walk / Infarct"
                    },
                    {
                        "condition": "Cervical Spondylosis (সার্ভাইকাল স্পন্ডিলোসিস)",
                        "code": "M47.8",
                        "status": "chronic",
                        "raw_text": "Impression: Spondylosis"
                    },
                    {
                        "condition": "Essential Hypertension (উচ্চ রক্তচাপ)",
                        "code": "I10",
                        "status": "active",
                        "raw_text": "BP: 150/90 mmHg"
                    }
                ],
                "medications": [
                    {
                        "name": "Tab. Stamlo 5 (Amlodipine 5mg)",
                        "dosage": "5 mg",
                        "frequency": "OD x 1 month (Stat)",
                        "duration": "1 month",
                        "route": "Oral",
                        "raw_text": "Tab. Stamlo (5) Stat - OD x 1 mt"
                    },
                    {
                        "name": "Tab. Ecosprin AV 75/20 (Aspirin 75mg + Atorvastatin 20mg)",
                        "dosage": "75/20 mg",
                        "frequency": "OD HS x 1 month (Bedtime)",
                        "duration": "1 month",
                        "route": "Oral",
                        "raw_text": "Tab. Ecosprin AV (75/20) Stat - OD HS x 1 mt"
                    },
                    {
                        "name": "Tab. Pantocid DSR (Pantoprazole + Domperidone)",
                        "dosage": "40/30 mg",
                        "frequency": "OD AC x 1 month (Before meals)",
                        "duration": "1 month",
                        "route": "Oral",
                        "raw_text": "Tab. Pantocid DSR Stat - OD AC x 1 mt"
                    },
                    {
                        "name": "Tab. Vertin 24 (Betahistine 24mg)",
                        "dosage": "24 mg",
                        "frequency": "BD x 1 month (Twice daily)",
                        "duration": "1 month",
                        "route": "Oral",
                        "raw_text": "Tab. Vertin (24) - BD x 1 mt"
                    }
                ],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "Blood Pressure",
                        "value": "150/90",
                        "unit": "mmHg",
                        "reference_range": "120/80 mmHg",
                        "abnormal": True,
                        "interpretation": "High / Stage 1-2 Hypertension",
                        "raw_text": "BP: 150/90 mmHg"
                    }
                ],
                "clinical_notes": [
                    "Patient age: 70 / Female.",
                    "Tests advised: 1. CT Scan of Brain, 2. X-ray C-Spine, 3. Na+, K+, Urea, Creatinine (Renal Panel)."
                ],
                "follow_up": [
                    {
                        "instructions": "Review on Monday (13/02/2021) with CT Scan Brain and blood reports.",
                        "date": "2021-02-13",
                        "doctor_or_dept": "Dr. Jyotirmoy Das (Medicine)"
                    }
                ],
                "raw_entities": []
            }
        elif "lab" in doc_id_lower or "report" in doc_id_lower or "002" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "lab_report",
                "confidence": 0.96,
                "document_date": "2026-08-15",
                "patient_name": "Rajesh Kumar",
                "doctor_name": "Dr. A. K. Verma, MD (Pathology)",
                "hospital_name": "Apex Diagnostic Centre, New Delhi",
                "diagnoses": [],
                "medications": [],
                "allergies": [],
                "procedures": [],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "HbA1c",
                        "value": "8.2",
                        "unit": "%",
                        "reference_range": "<5.7%",
                        "abnormal": None,
                        "interpretation": "High / Diabetic Range",
                        "raw_text": "HbA1c (Glycosylated Hemoglobin): 8.2 % (Ref: <5.7%)"
                    },
                    {
                        "test_name": "Fasting Blood Sugar",
                        "value": "164",
                        "unit": "mg/dL",
                        "reference_range": "70-99 mg/dL",
                        "abnormal": None,
                        "interpretation": "High",
                        "raw_text": "Fasting Blood Glucose: 164 mg/dL (Ref: 70 - 99 mg/dL)"
                    },
                    {
                        "test_name": "Serum Creatinine",
                        "value": "0.9",
                        "unit": "mg/dL",
                        "reference_range": "0.6-1.2 mg/dL",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "Serum Creatinine: 0.9 mg/dL (Ref: 0.6 - 1.2 mg/dL)"
                    }
                ],
                "clinical_notes": ["Elevated glycated hemoglobin and fasting plasma glucose indicating sub-optimal glycemic control."],
                "follow_up": [
                    {
                        "instructions": "Clinical correlation with treating physician recommended.",
                        "date": None,
                        "doctor_or_dept": "Endocrinology / General Medicine"
                    }
                ],
                "raw_entities": []
            }
        elif "discharge" in doc_id_lower or "003" in doc_id_lower:
            return {
                "document_id": document_id,
                "document_type": "discharge_summary",
                "confidence": 0.98,
                "document_date": "2024-11-20",
                "patient_name": "Rajesh Kumar",
                "doctor_name": "Dr. Sunita Rao, MS (Gen Surg)",
                "hospital_name": "Metro Superspeciality Hospital",
                "diagnoses": [
                    {
                        "condition": "Acute Gastroenteritis with Moderate Dehydration",
                        "code": "A09",
                        "status": "resolved",
                        "raw_text": "Final Diagnosis: Acute Gastroenteritis with Moderate Dehydration"
                    },
                    {
                        "condition": "Type 2 Diabetes Mellitus",
                        "code": "E11",
                        "status": "chronic",
                        "raw_text": "Known T2DM on oral hypoglycemic agents"
                    }
                ],
                "medications": [
                    {
                        "name": "Ceftriaxone",
                        "dosage": "1 g",
                        "frequency": "IV BD",
                        "duration": "3 days",
                        "route": "IV",
                        "raw_text": "Inj Ceftriaxone 1g IV BD x 3 days"
                    },
                    {
                        "name": "Pantoprazole",
                        "dosage": "40 mg",
                        "frequency": "OD",
                        "duration": "5 days",
                        "route": "Oral",
                        "raw_text": "Tab Pantoprazole 40mg OD before breakfast"
                    }
                ],
                "allergies": [
                    {
                        "substance": "Penicillin",
                        "reaction": "Urticaria and facial rash",
                        "severity": "Moderate"
                    }
                ],
                "procedures": [
                    {
                        "name": "Intravenous Fluid Rehydration",
                        "date": "2024-11-18",
                        "indication": "Dehydration"
                    }
                ],
                "surgeries": [],
                "lab_results": [
                    {
                        "test_name": "Serum Sodium",
                        "value": "138",
                        "unit": "mEq/L",
                        "reference_range": "135-145 mEq/L",
                        "abnormal": None,
                        "interpretation": "Normal",
                        "raw_text": "Na+: 138 mEq/L"
                    }
                ],
                "clinical_notes": [
                    "Patient admitted with severe vomiting and diarrhea on 2024-11-18.",
                    "Discharged in hemodynamically stable condition on 2024-11-20.",
                    "Documented allergy to Penicillin noted during admission history."
                ],
                "follow_up": [
                    {
                        "instructions": "Review in OPD after 7 days if symptoms recur.",
                        "date": "2024-11-27",
                        "doctor_or_dept": "General Medicine"
                    }
                ],
                "raw_entities": []
            }
        else:
            # Default prescription mock
            return {
                "document_id": document_id,
                "document_type": "prescription",
                "confidence": 0.95,
                "document_date": "2019-05-10",
                "patient_name": "Rajesh Kumar",
                "doctor_name": "Dr. R. Sharma, MD",
                "hospital_name": "City Clinic & Medical Centre",
                "diagnoses": [
                    {
                        "condition": "DM",
                        "code": None,
                        "status": "chronic",
                        "raw_text": "Dx: DM, HTN"
                    },
                    {
                        "condition": "HTN",
                        "code": None,
                        "status": "chronic",
                        "raw_text": "Dx: DM, HTN"
                    }
                ],
                "medications": [
                    {
                        "name": "Metformin",
                        "dosage": "500 mg",
                        "frequency": "BD",
                        "duration": "1 month",
                        "route": "Oral",
                        "raw_text": "Tab Metformin 500 mg BD pc"
                    },
                    {
                        "name": "Telmisartan",
                        "dosage": "40 mg",
                        "frequency": "OD",
                        "duration": "1 month",
                        "route": "Oral",
                        "raw_text": "Tab Telmisartan 40 mg OD"
                    }
                ],
                "allergies": [
                    {
                        "substance": "Penicillin",
                        "reaction": "Skin rash",
                        "severity": None
                    }
                ],
                "procedures": [],
                "surgeries": [],
                "lab_results": [],
                "clinical_notes": ["Regular blood glucose monitoring advised."],
                "follow_up": [
                    {
                        "instructions": "Review with Fasting Blood Sugar in 1 month.",
                        "date": None,
                        "doctor_or_dept": "General Physician"
                    }
                ],
                "raw_entities": []
            }

    def generate_text_synthesis(
        self,
        system_prompt: str,
        user_content: str,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        logger.info("MockLLMClient: Generating text synthesis")
        # If doctor QA inquiry
        if "question" in user_content.lower():
            if "last visit" in user_content.lower():
                return {
                    "question": "What happened during the last visit?",
                    "interpreted_pattern": "last_visit",
                    "answer": "At the previous documented visit on 2026-08-15, a laboratory panel was conducted showing HbA1c of 8.2% and Fasting Blood Sugar of 164 mg/dL. Prior to that, during hospitalization on 2024-11-20, the patient was treated for Acute Gastroenteritis with IV Ceftriaxone and rehydration.",
                    "source_references": [
                        {"document_id": "DOC_002", "document_type": "lab_report", "date": "2026-08-15", "excerpt": "HbA1c 8.2%, FBS 164 mg/dL"},
                        {"document_id": "DOC_003", "document_type": "discharge_summary", "date": "2024-11-20", "excerpt": "Discharge summary for Acute Gastroenteritis"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.98
                }
            elif "autoantibody" in user_content.lower() or "antibody" in user_content.lower() or "znt8" in user_content.lower():
                return {
                    "question": "What additional autoantibody tests were ordered by the endocrinologist?",
                    "interpreted_pattern": "general",
                    "answer": "Dr. Deep Hathi ordered a 4-parameter diabetes autoantibody panel: 1. ZnT8 (Zinc Transporter 8), 2. GAD-65, 3. IA-2, and 4. Anti-Insulin autoantibodies.",
                    "source_references": [
                        {"document_id": "DOC_HATHI_RX", "document_type": "prescription", "date": "2026-07-09", "excerpt": "Tests to be done: 1. ZnT8, 2. GAD-65, 3. IA-2, 4. Anti-Insulin"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.99
                }
            elif "regimen" in user_content.lower() or "insulin" in user_content.lower():
                return {
                    "question": "What is the patient's current insulin dosage and regimen?",
                    "interpreted_pattern": "medication_change",
                    "answer": "The patient is prescribed intensive basal-bolus insulin therapy: 1. Inj. Insulin FIASP 6-6-6 units s/c (Before Breakfast, Before Lunch, Before Dinner), and 2. Inj. Insulin Tresiba 8 units s/c at 10 pm (Bedtime).",
                    "source_references": [
                        {"document_id": "DOC_HATHI_RX", "document_type": "prescription", "date": "2026-07-09", "excerpt": "Inj. Insulin FIASP 6-6-6 BBF BLN BDN, Inj. Insulin Tresiba 8 @ 10pm"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.99
                }
            elif "diabetes" in user_content.lower():
                return {
                    "question": "Show me the diabetes history.",
                    "interpreted_pattern": "diabetes_history",
                    "answer": "Diabetes Mellitus was first documented in prescription DOC_001 on 2019-05-10, for which Tab Metformin 500 mg BD was prescribed. Recent lab report DOC_002 from 2026-08-15 shows an elevated HbA1c of 8.2% and Fasting Blood Sugar of 164 mg/dL.",
                    "source_references": [
                        {"document_id": "DOC_001", "document_type": "prescription", "date": "2019-05-10", "excerpt": "Dx: DM, Tab Metformin 500 mg BD"},
                        {"document_id": "DOC_002", "document_type": "lab_report", "date": "2026-08-15", "excerpt": "HbA1c 8.2%, Fasting Blood Sugar 164 mg/dL"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.99
                }
            elif "medication" in user_content.lower() or "changed" in user_content.lower():
                return {
                    "question": "Why was the medication changed?",
                    "interpreted_pattern": "medication_change",
                    "answer": "Prescription DOC_001 (2019-05-10) established maintenance therapy with Metformin 500 mg BD and Telmisartan 40 mg OD. During acute hospitalization on 2024-11-20 (DOC_003), short-course IV Ceftriaxone and Pantoprazole were administered for gastroenteritis.",
                    "source_references": [
                        {"document_id": "DOC_001", "document_type": "prescription", "date": "2019-05-10", "excerpt": "Metformin 500mg BD, Telmisartan 40mg OD"},
                        {"document_id": "DOC_003", "document_type": "discharge_summary", "date": "2024-11-20", "excerpt": "Inj Ceftriaxone 1g IV BD x 3 days, Pantoprazole 40mg OD"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.95
                }
            elif "hospital" in user_content.lower() or "admitted" in user_content.lower():
                return {
                    "question": "Has the patient been hospitalized?",
                    "interpreted_pattern": "hospitalization",
                    "answer": "Yes. The patient was hospitalized at Metro Superspeciality Hospital from 2024-11-18 to 2024-11-20 for Acute Gastroenteritis with Moderate Dehydration (DOC_003). The patient received IV fluid resuscitation and IV Ceftriaxone and was discharged stable.",
                    "source_references": [
                        {"document_id": "DOC_003", "document_type": "discharge_summary", "date": "2024-11-20", "excerpt": "Discharge Summary: Metro Superspeciality Hospital, Acute Gastroenteritis"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.99
                }
            elif "allerg" in user_content.lower():
                return {
                    "question": "What allergies are documented?",
                    "interpreted_pattern": "allergies",
                    "answer": "Penicillin allergy is documented in prescription DOC_001 (2019-05-10) and discharge summary DOC_003 (2024-11-20), noting skin rash and urticaria.",
                    "source_references": [
                        {"document_id": "DOC_001", "document_type": "prescription", "date": "2019-05-10", "excerpt": "Allergy: Penicillin (Skin rash)"},
                        {"document_id": "DOC_003", "document_type": "discharge_summary", "date": "2024-11-20", "excerpt": "Allergy: Penicillin (Urticaria)"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 1.0
                }
            else:
                return {
                    "question": user_content,
                    "interpreted_pattern": "general",
                    "answer": "Based on available records, the patient has documented history of Diabetes Mellitus, Hypertension, previous hospitalization for Acute Gastroenteritis (2024-11-20), recent abnormal HbA1c of 8.2% (2026-08-15), and documented Penicillin allergy.",
                    "source_references": [
                        {"document_id": "DOC_001", "document_type": "prescription", "date": "2019-05-10", "excerpt": "DM, HTN"},
                        {"document_id": "DOC_002", "document_type": "lab_report", "date": "2026-08-15", "excerpt": "HbA1c 8.2%"}
                    ],
                    "retrieved_evidence": [],
                    "data_available": True,
                    "confidence": 0.9
                }

        # Default Snapshot synthesis fallback
        return {
            "patient_id": "P_DEMO_001",
            "chief_complaint": "Fever and cough for 3 days",
            "hpi": "Patient presents with acute onset fever and cough of 3 days duration. Denies chest pain or shortness of breath on current intake.",
            "past_medical_history": [
                {
                    "condition": "Diabetes Mellitus",
                    "raw_term": "DM",
                    "status": "chronic",
                    "date_recorded": "2019",
                    "source_document_ids": ["DOC_001"]
                },
                {
                    "condition": "Hypertension",
                    "raw_term": "HTN",
                    "status": "chronic",
                    "date_recorded": "2019",
                    "source_document_ids": ["DOC_001"]
                }
            ],
            "past_surgical_history": [],
            "medications": [
                {
                    "name": "Metformin",
                    "dosage": "500 mg",
                    "frequency": "Twice daily",
                    "raw_frequency": "BD",
                    "source_document_ids": ["DOC_001"]
                },
                {
                    "name": "Telmisartan",
                    "dosage": "40 mg",
                    "frequency": "Once daily",
                    "raw_frequency": "OD",
                    "source_document_ids": ["DOC_001"]
                }
            ],
            "allergies": [
                {
                    "substance": "Penicillin",
                    "reaction": "Skin rash / Urticaria",
                    "source_document_ids": ["DOC_001", "DOC_003"]
                }
            ],
            "family_history": [],
            "personal_history": [],
            "review_of_systems": [
                {
                    "system": "Respiratory",
                    "findings": "Cough for 3 days",
                    "source": "current_intake"
                },
                {
                    "system": "Constitutional",
                    "findings": "Fever for 3 days",
                    "source": "current_intake"
                }
            ],
            "previous_investigations": [
                {
                    "test_name": "HbA1c",
                    "value": "8.2",
                    "unit": "%",
                    "reference_range": "<5.7%",
                    "abnormal": True,
                    "date": "2026-08-15",
                    "source_document_ids": ["DOC_002"]
                },
                {
                    "test_name": "Fasting Blood Sugar",
                    "value": "164",
                    "unit": "mg/dL",
                    "reference_range": "70-99 mg/dL",
                    "abnormal": True,
                    "date": "2026-08-15",
                    "source_document_ids": ["DOC_002"]
                }
            ],
            "timeline_summary": [
                {
                    "date": "2019-05-10",
                    "event": "Prescription: Diabetes Mellitus & Hypertension diagnosed; Metformin & Telmisartan prescribed",
                    "source_document_id": "DOC_001"
                },
                {
                    "date": "2024-11-20",
                    "event": "Hospitalization: Discharged after treatment for Acute Gastroenteritis with IV Ceftriaxone",
                    "source_document_id": "DOC_003"
                },
                {
                    "date": "2026-08-15",
                    "event": "Lab Investigation: HbA1c recorded as 8.2% (Abnormal)",
                    "source_document_id": "DOC_002"
                }
            ],
            "alerts": [
                {
                    "type": "data_inconsistency",
                    "message": "Current intake reports no known allergies, but previous documents (DOC_001, DOC_003) document Penicillin allergy.",
                    "severity": "high",
                    "source_document_ids": ["DOC_001", "DOC_003"]
                },
                {
                    "type": "abnormal_lab",
                    "message": "Recent HbA1c of 8.2% indicates suboptimal glycemic control.",
                    "severity": "medium",
                    "source_document_ids": ["DOC_002"]
                }
            ],
            "clinical_disclaimer": "Draft intake synthesis prepared by AI for attending physician review. Not a diagnostic claim or prescription. Attending physician is the sole clinical decision-maker."
        }


class GeminiVisionClient(BaseLLMClient):
    """
    Google Gemini Vision Client supporting google-genai SDK or direct REST API.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def extract_document_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        document_id: str
    ) -> Dict[str, Any]:
        # Try google-genai SDK first if installed
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    prompt + f"\n\nDocument ID to use: {document_id}"
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return clean_json_response(response.text)
        except ImportError:
            # Direct REST API fallback
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            b64_data = base64.b64encode(image_bytes).decode("utf-8")
            payload = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": mime_type, "data": b64_data}},
                        {"text": prompt + f"\n\nDocument ID to use: {document_id}"}
                    ]
                }],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            with httpx.Client(timeout=45.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return clean_json_response(text_content)

    def generate_text_synthesis(
        self,
        system_prompt: str,
        user_content: str,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=[
                    system_prompt,
                    user_content
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            return clean_json_response(response.text)
        except ImportError:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": system_prompt + "\n\n" + user_content}
                    ]
                }],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            with httpx.Client(timeout=45.0) as client:
                res = client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                text_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return clean_json_response(text_content)


class OpenAIVisionClient(BaseLLMClient):
    """
    OpenAI Vision Client.
    """

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        self.api_key = api_key
        self.model_name = model_name

    def extract_document_vision(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        document_id: str
    ) -> Dict[str, Any]:
        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64_image}"

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt + f"\n\nDocument ID to use: {document_id}"},
                        {"type": "image_url", "image_url": {"url": data_url}}
                    ]
                }
            ]
        }
        with httpx.Client(timeout=45.0) as client:
            res = client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()
            raw_text = data["choices"][0]["message"]["content"]
            return clean_json_response(raw_text)

    def generate_text_synthesis(
        self,
        system_prompt: str,
        user_content: str,
        response_schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }
        with httpx.Client(timeout=45.0) as client:
            res = client.post(url, json=payload, headers=headers)
            res.raise_for_status()
            data = res.json()
            raw_text = data["choices"][0]["message"]["content"]
            return clean_json_response(raw_text)


def get_llm_client(provider: Optional[str] = None) -> BaseLLMClient:
    """
    Factory to instantiate the appropriate LLM client based on configuration.
    If no API key is provided or provider is 'mock', returns MockLLMClient.
    """
    selected_provider = (provider or settings.VISION_LLM_PROVIDER or "mock").lower()
    api_key = settings.VISION_LLM_API_KEY

    if selected_provider == "gemini" and api_key and api_key != "your_gemini_api_key_here":
        return GeminiVisionClient(api_key=api_key, model_name=settings.VISION_LLM_MODEL)
    elif selected_provider == "openai" and api_key and api_key != "your_openai_api_key_here":
        return OpenAIVisionClient(api_key=api_key, model_name=settings.VISION_LLM_MODEL)
    else:
        logger.info("Using MockLLMClient (offline / mock provider)")
        return MockLLMClient()
