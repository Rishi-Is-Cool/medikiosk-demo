"""
MediKiosk Backend — Comprehensive API Integration Test Suite
Tests the full end-to-end patient journey:
  Patient Registration → ABHA Verification → Adaptive Interview → Voice Input →
  Document OCR Upload → Summary Generation → Physician Confirmation → FHIR Export → HIS Push
"""
import io
import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Auth Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuthentication:
    def test_kiosk_login_success(self, client):
        """Kiosk terminal can authenticate and receive JWT token."""
        response = client.post(
            "/api/auth/token",
            data={"username": "kiosk_terminal_01", "password": "kiosk@MediK2026"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "kiosk"

    def test_doctor_login_success(self, client):
        """Doctor can authenticate and receive JWT token."""
        response = client.post(
            "/api/auth/token",
            data={"username": "doctor_opd_101", "password": "doc@MediK2026"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "doctor"

    def test_invalid_credentials_rejected(self, client):
        """Wrong password must return 401."""
        response = client.post(
            "/api/auth/token",
            data={"username": "kiosk_terminal_01", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_me_endpoint_with_valid_token(self, client):
        """Authenticated /me endpoint returns username and role."""
        token_response = client.post(
            "/api/auth/token",
            data={"username": "admin", "password": "admin@MediK2026"}
        )
        token = token_response.json()["access_token"]
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert me_response.status_code == 200
        assert me_response.json()["role"] == "admin"


# ═══════════════════════════════════════════════════════════════════════════════
# Health & System Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSystemEndpoints:
    def test_health_check(self, client):
        """Health endpoint returns 200 with healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "gemini_ai" in data

    def test_root_endpoint(self, client):
        """Root endpoint returns platform identity."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["fhir_r4_ready"] is True


# ═══════════════════════════════════════════════════════════════════════════════
# Patient Registration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPatientRegistration:
    def test_register_patient_with_abha(self, client):
        """Register a new patient with valid ABHA ID — returns 201 with patient_id."""
        payload = {
            "name": "Rajesh Sharma",
            "age": 45,
            "gender": "Male",
            "language": "hi",
            "abha_id": "91-1234-5678-9012",
            "phone": "9876543210",
            "consent_granted": True
        }
        response = client.post("/api/patients/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert "patient_id" in data
        assert data["patient_id"].startswith("PAT-")
        assert data["name"] == "Rajesh Sharma"
        assert data["abha_id"] == "91-1234-5678-9012"
        assert data["consent_granted"] is True

    def test_register_patient_without_abha(self, client):
        """Patients without ABHA ID can still register."""
        payload = {
            "name": "Sunita Devi",
            "age": 62,
            "gender": "Female",
            "language": "hi",
            "phone": "9000000099",
            "consent_granted": True
        }
        response = client.post("/api/patients/register", json=payload)
        assert response.status_code == 201
        assert response.json()["name"] == "Sunita Devi"

    def test_get_patient_by_id(self, client, registered_patient):
        """Fetch a registered patient by patient_id."""
        token = client.post("/api/auth/token", data={"username": "doctor_opd_101", "password": "doc@MediK2026"}).json()["access_token"]
        response = client.get(f"/api/patients/{registered_patient}", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["patient_id"] == registered_patient

    def test_get_nonexistent_patient_returns_404(self, client):
        """Requesting a non-existent patient returns 404."""
        token = client.post("/api/auth/token", data={"username": "doctor_opd_101", "password": "doc@MediK2026"}).json()["access_token"]
        response = client.get("/api/patients/PAT-DOESNOTEXIST", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 404

    def test_abha_verification(self, client):
        """ABHA verification endpoint returns valid/invalid status."""
        response = client.get("/api/patients/verify-abha/91-9999-0000-1111")
        assert response.status_code == 200
        data = response.json()
        assert "verified" in data
        assert "abha_id" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Adaptive Interview Engine Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInterviewEngine:
    def test_allopathy_step1_returns_chief_complaint(self, client, registered_patient):
        """Step 1 in Allopathy mode asks about chief complaint with options."""
        payload = {
            "patient_id": registered_patient,
            "current_step": 1,
            "answers": {},
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/next-question", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["step"] == 1
        assert data["total_steps"] == 10
        assert "chest_pain" in [opt["value"] for opt in data["options"]]
        assert data["is_complete"] is False
        assert "en" in data["question_text"]

    def test_allopathy_step6_socrates_aggravating(self, client, registered_patient):
        """Step 6 in Allopathy mode should ask about aggravating/relieving factors."""
        payload = {
            "patient_id": registered_patient,
            "current_step": 6,
            "answers": {"q1_chief_complaint": "chest_pain"},
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/next-question", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["step"] == 6
        assert "worse_exertion" in [opt["value"] for opt in data["options"]]

    def test_ayush_step1_returns_chief_complaint(self, client, registered_patient):
        """Step 1 in AYUSH mode asks about chief complaint."""
        payload = {
            "patient_id": registered_patient,
            "current_step": 1,
            "answers": {},
            "department_mode": "AYUSH"
        }
        response = client.post("/api/interview/next-question", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["step"] == 1
        assert "ayush" in data["question_id"]
        assert data["total_steps"] == 11

    def test_ayush_step2_prakriti_question(self, client, registered_patient):
        """Step 2 in AYUSH mode should ask Prakriti assessment."""
        payload = {
            "patient_id": registered_patient,
            "current_step": 2,
            "answers": {"ayush_q1_chief_complaint": "digestive"},
            "department_mode": "AYUSH"
        }
        response = client.post("/api/interview/next-question", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "prakriti" in data["question_id"]
        assert any("vata" in opt["value"] for opt in data["options"])

    def test_interview_completion_flag(self, client, registered_patient):
        """Step beyond total_steps returns is_complete=True."""
        payload = {
            "patient_id": registered_patient,
            "current_step": 99,
            "answers": {},
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/next-question", json=payload)
        assert response.status_code == 200
        assert response.json()["is_complete"] is True

    def test_get_all_allopathy_questions(self, client):
        """Pre-loading endpoint returns all 10 Allopathy questions."""
        response = client.get("/api/interview/questions/Allopathy")
        assert response.status_code == 200
        data = response.json()
        assert data["total_steps"] == 10
        assert len(data["questions"]) == 10

    def test_get_all_ayush_questions(self, client):
        """Pre-loading endpoint returns all 11 AYUSH questions."""
        response = client.get("/api/interview/questions/AYUSH")
        assert response.status_code == 200
        data = response.json()
        assert data["total_steps"] == 11

    def test_audio_prompt_endpoint(self, client):
        """Audio prompt endpoint returns trilingual prompt text."""
        response = client.get("/api/interview/audio-prompt/q1_chief_complaint?language=hi")
        assert response.status_code == 200
        data = response.json()
        assert data["tts_ready"] is True
        assert len(data["audio_prompt_text"]) > 10


# ═══════════════════════════════════════════════════════════════════════════════
# Emergency Red Flag Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedFlagDetection:
    def test_acs_red_flag_detected(self, client, registered_patient):
        """Chest pain + breathlessness triggers ACS red flag."""
        payload = {
            "patient_id": registered_patient,
            "question_id": "q1_chief_complaint",
            "step": 1,
            "answer_text": "Severe chest pain radiating to my left arm and shortness of breath.",
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/submit-answer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["red_flag_detected"] is True
        assert data["is_emergency"] is True
        flag_ids = [rf["flag_id"] for rf in data["red_flags"]]
        assert "ACUTE_CORONARY_SYNDROME" in flag_ids

    def test_stroke_red_flag_detected(self, client, registered_patient):
        """Facial droop + slurred speech triggers stroke FAST alert."""
        payload = {
            "patient_id": registered_patient,
            "question_id": "q1_chief_complaint",
            "step": 1,
            "answer_text": "My face is drooping and I have slurred speech and left arm weakness.",
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/submit-answer", json=payload)
        assert response.status_code == 200
        flag_ids = [rf["flag_id"] for rf in response.json()["red_flags"]]
        assert "STROKE_FAST" in flag_ids

    def test_meningitis_red_flag_detected(self, client, registered_patient):
        """Neck stiffness + high fever triggers meningitis alert."""
        payload = {
            "patient_id": registered_patient,
            "question_id": "q5_associated_symptoms",
            "step": 5,
            "answer_text": "I have severe neck stiffness and high fever for 2 days.",
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/submit-answer", json=payload)
        assert response.status_code == 200
        flag_ids = [rf["flag_id"] for rf in response.json()["red_flags"]]
        assert "BACTERIAL_MENINGITIS" in flag_ids

    def test_no_red_flag_for_normal_complaint(self, client, registered_patient):
        """Routine joint pain does not trigger emergency alert."""
        payload = {
            "patient_id": registered_patient,
            "question_id": "q1_chief_complaint",
            "step": 1,
            "answer_text": "I have mild knee pain for 2 weeks.",
            "department_mode": "Allopathy"
        }
        response = client.post("/api/interview/submit-answer", json=payload)
        assert response.status_code == 200
        assert response.json()["red_flag_detected"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Voice Input / STT Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoiceInput:
    def test_voice_input_hindi_transcript(self, client, registered_patient):
        """Hindi audio file returns transcript and checks red flags."""
        fake_audio = io.BytesIO(b"RIFF" + b"\x00" * 44)  # fake WAV header
        response = client.post(
            "/api/interview/voice-input",
            data={"patient_id": registered_patient, "language": "hi"},
            files={"audio_file": ("test.wav", fake_audio, "audio/wav")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "transcript" in data
        assert data["language"] == "hi"
        assert "confidence" in data
        # Simulated Hindi transcript mentions chest pain → should detect red flag
        assert data["red_flag_detected"] is True

    def test_voice_input_english_transcript(self, client, registered_patient):
        """English audio file returns English transcript."""
        fake_audio = io.BytesIO(b"RIFF" + b"\x00" * 44)
        response = client.post(
            "/api/interview/voice-input",
            data={"patient_id": registered_patient, "language": "en"},
            files={"audio_file": ("test.wav", fake_audio, "audio/wav")}
        )
        assert response.status_code == 200
        assert response.json()["language"] == "en"

    def test_empty_audio_returns_400(self, client, registered_patient):
        """Empty audio bytes should return 400."""
        empty_audio = io.BytesIO(b"")
        response = client.post(
            "/api/interview/voice-input",
            data={"patient_id": registered_patient, "language": "en"},
            files={"audio_file": ("empty.wav", empty_audio, "audio/wav")}
        )
        assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# Document Upload & OCR Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDocumentOCR:
    def test_lab_report_upload_extracts_abnormal_results(self, client, registered_patient):
        """Uploading a lab report triggers OCR and extracts abnormal lab values."""
        fake_file = io.BytesIO(b"Fake Lab Report Image Content")
        response = client.post(
            "/api/documents/upload",
            data={"patient_id": registered_patient, "document_type": "lab_report"},
            files={"file": ("lab_report.png", fake_file, "image/png")}
        )
        assert response.status_code == 201
        data = response.json()
        assert "document_id" in data
        assert data["document_id"].startswith("DOC-")
        assert len(data["lab_results"]) > 0
        # At least one abnormal result should be present in simulated data
        assert any(lab["abnormal"] for lab in data["lab_results"])

    def test_prescription_upload_extracts_medications(self, client, registered_patient):
        """Uploading a prescription triggers OCR and extracts medications."""
        fake_file = io.BytesIO(b"Fake Prescription Image Content")
        response = client.post(
            "/api/documents/upload",
            data={"patient_id": registered_patient, "document_type": "prescription"},
            files={"file": ("rx.jpg", fake_file, "image/jpeg")}
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["extracted_medications"]) > 0

    def test_discharge_summary_upload(self, client, registered_patient):
        """Uploading a discharge summary processes correctly."""
        fake_file = io.BytesIO(b"Fake Discharge Summary Content")
        response = client.post(
            "/api/documents/upload",
            data={"patient_id": registered_patient, "document_type": "discharge_summary"},
            files={"file": ("discharge.pdf", fake_file, "application/pdf")}
        )
        assert response.status_code == 201
        assert "document_id" in response.json()

    def test_get_patient_documents_timeline(self, client, registered_patient):
        """Patient documents timeline endpoint returns all uploaded docs and labs."""
        response = client.get(f"/api/documents/patient/{registered_patient}")
        assert response.status_code == 200
        data = response.json()
        assert "documents_count" in data
        assert "lab_timeline" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Clinical Summary Generation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummaryGeneration:
    def test_generate_allopathy_summary(self, client, registered_patient):
        """Generate Allopathy clinical summary from complete interview answers."""
        answers = {
            "q1_chief_complaint": "chest_pain",
            "q2_duration_onset": "1_3_days",
            "q3_severity_scale": "severe_7_9",
            "q4_character_radiation": "pressing",
            "q5_associated_symptoms": ["shortness_of_breath", "cold_sweats"],
            "q6_aggravating_relieving": ["worse_exertion", "relieved_rest"],
            "q7_past_medical_history": ["diabetes", "hypertension"],
            "q8_medications_allergies": "chronic_meds",
            "q9_family_personal_history": ["fh_cardiac_stroke", "fh_diabetes"],
            "q10_personal_social_history": ["sedentary"]
        }
        response = client.post(
            f"/api/summary/generate/{registered_patient}?department_mode=Allopathy",
            json=answers
        )
        assert response.status_code == 200
        data = response.json()
        assert "history_id" in data
        assert data["history_id"].startswith("HIST-")
        assert data["patient_id"] == registered_patient
        assert "MEDIKIOSK CLINICAL INTAKE SUMMARY" in data["formatted_summary_markdown"]
        assert len(data["chief_complaint"]) > 0
        assert data["status"] == "draft"

    def test_generate_ayush_summary(self, client, registered_patient):
        """Generate AYUSH Dashavidha Pariksha summary."""
        answers = {
            "ayush_q1_chief_complaint": "digestive",
            "ayush_q2_prakriti": "pitta",
            "ayush_q3_vikriti": "pitta_vikriti",
            "ayush_q4_sara": "rakta_sara",
            "ayush_q5_samhanana": "madhyama",
            "ayush_q6_agni_koshtha": "tikshna_mridu",
            "ayush_q7_satmya": "heat_intolerant",
            "ayush_q8_sattva": "madhyama_sattva",
            "ayush_q9_ahara_shakti": "moderate_ahara_vyayama",
            "ayush_q10_vaya_ahara_vihara": "madhyama_guru_irregular"
        }
        response = client.post(
            f"/api/summary/generate/{registered_patient}?department_mode=AYUSH",
            json=answers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["department_mode"] == "AYUSH"
        assert data["ayush_dashavidha_summary"] is not None
        assert "Prakriti" in data["ayush_dashavidha_summary"]
        assert "AYUSH DASHAVIDHA PARIKSHA" in data["formatted_summary_markdown"]

    def test_get_patient_summary(self, client, registered_patient):
        """GET /api/summary/{patient_id} returns the latest stored summary."""
        response = client.get(f"/api/summary/{registered_patient}")
        assert response.status_code == 200
        data = response.json()
        assert data["patient_id"] == registered_patient

    def test_physician_confirm_summary(self, client, registered_patient):
        """Physician can confirm and edit the draft summary."""
        # First generate a summary
        gen_response = client.post(
            f"/api/summary/generate/{registered_patient}?department_mode=Allopathy",
            json={"q1_chief_complaint": "headache"}
        )
        history_id = gen_response.json()["history_id"]

        # Physician edits and confirms
        update_payload = {
            "chief_complaint": "Persistent bifrontal headache with photophobia (Physician Confirmed)",
            "status": "confirmed"
        }
        confirm_response = client.put(f"/api/summary/confirm/{history_id}", json=update_payload)
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"

    def test_summary_not_found_returns_404(self, client):
        """Non-existent patient summary returns 404."""
        response = client.get("/api/summary/PAT-DOESNOTEXIST")
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR R4 & ABDM Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFHIRABDM:
    def test_fhir_export_returns_valid_bundle(self, client, registered_patient):
        """FHIR export produces valid R4 Bundle with Patient and Condition resources."""
        response = client.get(f"/api/fhir/export/{registered_patient}")
        assert response.status_code == 200
        data = response.json()
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "document"
        assert len(data["entry"]) >= 2
        # Check Patient resource exists
        resource_types = [entry["resource"]["resourceType"] for entry in data["entry"]]
        assert "Patient" in resource_types
        assert "Condition" in resource_types

    def test_fhir_observations_for_lab_results(self, client, registered_patient):
        """FHIR Bundle includes Observation resources for extracted lab results."""
        # Upload a lab report first to create lab results
        fake_file = io.BytesIO(b"Lab Report for FHIR test")
        client.post(
            "/api/documents/upload",
            data={"patient_id": registered_patient, "document_type": "lab_report"},
            files={"file": ("test.png", fake_file, "image/png")}
        )
        response = client.get(f"/api/fhir/export/{registered_patient}")
        assert response.status_code == 200
        data = response.json()
        resource_types = [entry["resource"]["resourceType"] for entry in data["entry"]]
        assert "Observation" in resource_types

    def test_his_push_returns_success(self, client, registered_patient):
        """HIS push endpoint returns success with encounter ID."""
        response = client.post(f"/api/fhir/push-to-his/{registered_patient}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "his_encounter_id" in data
        assert data["status"] == "PUSHED_TO_DOCTOR_SCREEN"

    def test_consent_artefact_generation(self, client, registered_patient):
        """Consent artefact generated for patient with consent_granted=True."""
        response = client.post(f"/api/fhir/consent/{registered_patient}")
        assert response.status_code == 200
        data = response.json()
        assert "consent_id" in data
        assert data["status"] == "GRANTED"
        assert "CLINICAL_HISTORY" in data["data_types"]


# ═══════════════════════════════════════════════════════════════════════════════
# Admin Dashboard Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminDashboard:
    def test_system_stats(self, client):
        """Admin stats endpoint returns aggregate counts."""
        response = client.get("/api/admin/stats")
        assert response.status_code == 200
        data = response.json()
        assert "patients" in data
        assert "clinical_summaries" in data
        assert data["system_health"] == "operational"

    def test_list_patients_paginated(self, client):
        """Admin patient list returns paginated results."""
        response = client.get("/api/admin/patients?skip=0&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "patients" in data
        assert isinstance(data["patients"], list)

    def test_today_queue(self, client):
        """Today's OPD queue returns patients registered today."""
        response = client.get("/api/admin/queue/today")
        assert response.status_code == 200
        data = response.json()
        assert "queue" in data
        assert "emergencies" in data
        assert "total_in_queue" in data
