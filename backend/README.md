# 🩺 MediKiosk — AI Clinical History & Intake Backend

MediKiosk is an AI-powered clinical history software platform designed for high-throughput government hospital OPDs and AYUSH institutions in India. It enables patients to independently record their clinical history (via voice or touch in local Indian languages), digitizes physical medical documents using OCR, detects emergency red flags instantly, and formats physician-ready summaries exported as HL7 FHIR R4 JSON Bundles.

---

## 🌟 Key Features

1. **Module A — Conversational Multimodal History Engine**
   - Adaptive SOCRATES questioning framework (Chief Complaint, HPI, Past, Surgical, Drug/Allergy, Family, Personal, ROS).
   - **AYUSH Dashavidha Pariksha Mode** (*Prakriti, Vikriti, Sara, Samhanana, Pramana, Satmya, Sattva, Ahara Shakti, Vyayama Shakti, Vaya* & *Ahara-Vihara* assessment).
   - Multilingual support for **English**, **Hindi**, and **Marathi**.
   - **Red-Flag Detection**: Instant priority escalation for Acute Coronary Syndrome (chest pain + dyspnoea), Stroke, Severe Dyspnoea, and Anaphylaxis.

2. **Module B — Medical Document Digitization & Intelligence**
   - Optical Character Recognition (OCR) for physical prescriptions and lab diagnostic reports.
   - Extracts diagnoses, active medications with dosages/frequencies, and lab measurements.
   - Highlights out-of-range/abnormal lab values and constructs a chronological clinical timeline.

3. **Module C — Physician-Ready Summary Generator**
   - Synthesizes interview narration and OCR document extractions into standard physician markdown summaries.
   - Generates local language audio summary prompts for patients.
   - Physician editable & verifiable draft workflow before HIS storage.

4. **Module D — ABDM & FHIR Interoperability**
   - ABHA ID verification & Digital Personal Data Protection (DPDP) consent logging.
   - HL7 FHIR R4 JSON Bundle exporter (`Patient`, `Condition`, `Observation`).
   - Mock HIS / EMR push endpoints.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.9+ installed
- `pip` package manager

### Installation

1. Navigate to the backend directory:
   ```bash
   cd C:\Users\karti\.gemini\antigravity-ide\scratch\medikiosk\backend
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. Access interactive API documentation (Swagger UI):
   Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) in your browser.

---

## 🧪 Running Automated Tests

Run the test suite using `pytest`:
```bash
pytest tests/test_api.py -v
```

---

## 📁 API Endpoints Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/patients/register` | Register new patient & record ABHA / DPDP consent |
| `GET` | `/api/patients/verify-abha/{abha_id}` | Verify ABHA number against ABDM registry |
| `POST` | `/api/interview/next-question` | Fetch next adaptive interview question (Allopathy / AYUSH) |
| `POST` | `/api/interview/submit-answer` | Submit answer & check for red-flag emergency alerts |
| `POST` | `/api/interview/voice-input` | Process voice audio input via STT transcription |
| `POST` | `/api/documents/upload` | Upload physical prescription/lab report for OCR extraction |
| `POST` | `/api/summary/generate/{patient_id}` | Generate physician-ready clinical intake summary |
| `PUT` | `/api/summary/confirm/{history_id}` | Doctor review, edit, and confirm summary |
| `GET` | `/api/fhir/export/{patient_id}` | Export HL7 FHIR R4 JSON Bundle for ABDM |
| `POST` | `/api/fhir/push-to-his/{patient_id}` | Route structured history to hospital OPD screen |
