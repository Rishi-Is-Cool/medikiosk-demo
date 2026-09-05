"""
MediKiosk Backend — AI Engine Unit Tests
Tests individual AI components in isolation without HTTP layer.
"""
import json
import pytest

from app.ai.red_flag_detector import red_flag_detector, RedFlagDetector
from app.ai.history_extractor import history_extractor
from app.ai.question_engine import question_engine, ALLOPATHY_STEPS, AYUSH_STEPS
from app.ai.medical_extractor import medical_extractor
from app.ai.summary_generator import summary_generator
from app.ai.speech_to_text import stt_engine
from app.integrations.fhir import fhir_converter


# ═══════════════════════════════════════════════════════════════════════════════
# Red Flag Detector Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRedFlagDetectorUnit:
    def test_acs_detected_from_english_text(self):
        flags = red_flag_detector.check_red_flags("severe chest pain radiating to left arm")
        assert any(f["flag_id"] == "ACUTE_CORONARY_SYNDROME" for f in flags)
        assert flags[0]["priority"] == "P1_CRITICAL"

    def test_acs_detected_from_hindi_text(self):
        flags = red_flag_detector.check_red_flags("छाती में दर्द और सांस फूलना")
        assert any(f["flag_id"] == "ACUTE_CORONARY_SYNDROME" for f in flags)

    def test_stroke_detected(self):
        flags = red_flag_detector.check_red_flags("facial droop and slurred speech suddenly")
        assert any(f["flag_id"] == "STROKE_FAST" for f in flags)

    def test_meningitis_detected(self):
        flags = red_flag_detector.check_red_flags("neck stiffness with high fever and severe headache")
        assert any(f["flag_id"] == "BACTERIAL_MENINGITIS" for f in flags)

    def test_anaphylaxis_detected(self):
        flags = red_flag_detector.check_red_flags("throat swelling after eating peanuts")
        assert any(f["flag_id"] == "ANAPHYLAXIS" for f in flags)

    def test_respiratory_distress_detected(self):
        flags = red_flag_detector.check_red_flags("unable to breathe, stridor, gasping")
        assert any(f["flag_id"] == "SEVERE_RESPIRATORY_DISTRESS" for f in flags)

    def test_no_flag_for_routine_complaint(self):
        flags = red_flag_detector.check_red_flags("mild knee pain for 2 weeks")
        assert len(flags) == 0

    def test_is_emergency_true_for_acs(self):
        assert red_flag_detector.is_emergency("chest pain radiating to arm") is True

    def test_is_emergency_false_for_routine(self):
        assert red_flag_detector.is_emergency("mild headache after long drive") is False

    def test_flags_sorted_p1_before_p2(self):
        """P1_CRITICAL flags must appear before P2_URGENT in output."""
        flags = red_flag_detector.check_red_flags(
            "chest pain AND fainting confusion sweating diabetes"
        )
        if len(flags) > 1:
            priorities = [f["priority"] for f in flags]
            p1_indices = [i for i, p in enumerate(priorities) if p == "P1_CRITICAL"]
            p2_indices = [i for i, p in enumerate(priorities) if p == "P2_URGENT"]
            if p1_indices and p2_indices:
                assert min(p1_indices) < min(p2_indices)

    def test_answers_dict_screening(self):
        """Red flags detected from structured answers dict."""
        flags = red_flag_detector.check_red_flags(
            "",
            answers={"q5": ["shortness_of_breath", "chest_pain"], "q1": "chest_pain"}
        )
        assert any(f["flag_id"] == "ACUTE_CORONARY_SYNDROME" for f in flags)


# ═══════════════════════════════════════════════════════════════════════════════
# History Extractor Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestHistoryExtractorUnit:
    def test_allopathy_chief_complaint_extracted(self):
        answers = {"q1_chief_complaint": "chest_pain", "q2_duration_onset": "1_3_days"}
        history = history_extractor.extract_history(answers, "Allopathy")
        assert "chest" in history["chief_complaint"].lower() or "pain" in history["chief_complaint"].lower()

    def test_allopathy_hpi_includes_socrates_elements(self):
        answers = {
            "q1_chief_complaint": "chest_pain",
            "q2_duration_onset": "1_3_days",
            "q3_severity_scale": "severe_7_9",
            "q4_character_radiation": "pressing",
            "q5_associated_symptoms": ["shortness_of_breath"]
        }
        history = history_extractor.extract_history(answers, "Allopathy")
        hpi = history["hpi"]
        assert "1 to 3 days" in hpi
        assert "Severe" in hpi
        assert "Pressing" in hpi
        assert "Shortness of breath" in hpi

    def test_allopathy_allergy_detection(self):
        answers = {"q8_medications_allergies": "penicillin_sulfa_allergy"}
        history = history_extractor.extract_history(answers, "Allopathy")
        assert "Penicillin" in history["allergies"]

    def test_allopathy_no_allergy(self):
        answers = {"q8_medications_allergies": "nkda_no_meds"}
        history = history_extractor.extract_history(answers, "Allopathy")
        assert "NKDA" in history["allergies"]

    def test_ayush_prakriti_extraction(self):
        answers = {
            "ayush_q1_chief_complaint": "digestive",
            "ayush_q2_prakriti": "pitta",
            "ayush_q3_vikriti": "pitta_vikriti",
            "ayush_q6_agni_koshtha": "tikshna_mridu"
        }
        history = history_extractor.extract_history(answers, "AYUSH")
        ayush = json.loads(history["ayush_data"])
        assert "Pitta Pradhana" in ayush["Prakriti"]
        assert "Pitta Vikriti" in ayush["Vikriti"]
        assert "Tikshna Agni" in ayush["Agni_Koshtha"]

    def test_ayush_returns_all_dashavidha_keys(self):
        answers = {}
        history = history_extractor.extract_history(answers, "AYUSH")
        ayush = json.loads(history["ayush_data"])
        expected_keys = ["Prakriti", "Vikriti", "Sara", "Samhanana",
                         "Agni_Koshtha", "Satmya", "Sattva",
                         "Ahara_Vyayama_Shakti", "Vaya_Ahara_Vihara"]
        for key in expected_keys:
            assert key in ayush, f"Missing Dashavidha key: {key}"

    def test_ayush_data_is_none_in_allopathy_mode(self):
        history = history_extractor.extract_history({}, "Allopathy")
        assert history["ayush_data"] is None


# ═══════════════════════════════════════════════════════════════════════════════
# Question Engine Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestQuestionEngineUnit:
    def test_allopathy_has_10_steps(self):
        assert len(ALLOPATHY_STEPS) == 10

    def test_ayush_has_11_steps(self):
        assert len(AYUSH_STEPS) == 11

    def test_all_allopathy_steps_have_trilingual_prompts(self):
        for step in ALLOPATHY_STEPS:
            qt = step["question_text"]
            assert "en" in qt, f"Step {step['id']} missing English prompt"
            assert "hi" in qt, f"Step {step['id']} missing Hindi prompt"
            assert "mr" in qt, f"Step {step['id']} missing Marathi prompt"

    def test_all_ayush_steps_have_trilingual_prompts(self):
        for step in AYUSH_STEPS:
            qt = step["question_text"]
            assert "en" in qt
            assert "hi" in qt

    def test_completion_flag_beyond_allopathy_steps(self):
        result = question_engine.get_next_question(99, {}, "Allopathy")
        assert result["is_complete"] is True

    def test_step_1_allopathy_returns_correct_question(self):
        result = question_engine.get_next_question(1, {}, "Allopathy")
        assert result["step"] == 1
        assert result["question_id"] == "q1_chief_complaint"
        assert result["is_complete"] is False

    def test_step_2_ayush_is_prakriti_question(self):
        result = question_engine.get_next_question(2, {}, "AYUSH")
        assert "prakriti" in result["question_id"]

    def test_get_all_steps_helper(self):
        allopathy_steps = question_engine.get_all_steps("Allopathy")
        assert len(allopathy_steps) == 10
        ayush_steps = question_engine.get_all_steps("AYUSH")
        assert len(ayush_steps) == 11

    def test_red_flag_surfaced_in_question_response(self):
        """Red flag in answers is surfaced in the next question response."""
        answers = {"q1": "chest pain radiating to left arm"}
        result = question_engine.get_next_question(2, answers, "Allopathy")
        assert result["red_flag_alert"] is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Medical Extractor Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestMedicalExtractorUnit:
    def test_extracts_diagnoses_from_ocr(self):
        ocr_text = "Diagnosis: Essential Hypertension, Type 2 Diabetes Mellitus"
        result = medical_extractor.extract_entities(ocr_text)
        assert len(result["diagnoses"]) > 0
        assert any("Hypertension" in d or "Diabetes" in d for d in result["diagnoses"])

    def test_extracts_medications_from_prescription_ocr(self):
        ocr_text = "Rx:\n1. Tab. Metformin 500mg - 1 tablet twice daily\n2. Tab. Telmisartan 40mg - once daily"
        result = medical_extractor.extract_entities(ocr_text)
        assert len(result["medications"]) > 0

    def test_extracts_lab_results_with_abnormal_flag(self):
        ocr_text = "Hemoglobin (Hb) 11.2 g/dL 13.5-17.5 (LOW)\nFasting Blood Sugar 168 mg/dL 70-100 (HIGH)"
        result = medical_extractor.extract_entities(ocr_text)
        # Should get lab results (real extraction or simulated fallback)
        assert len(result["lab_results"]) > 0

    def test_unknown_text_does_not_create_clinical_defaults(self):
        """Unrecognised text must not be converted into invented facts."""
        result = medical_extractor.extract_entities("random unrelated text blah blah")
        assert result == {"diagnoses": [], "medications": [], "lab_results": []}


# ═══════════════════════════════════════════════════════════════════════════════
# Summary Generator Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSummaryGeneratorUnit:
    def _make_patient(self, lang="en"):
        return {"name": "Test Patient", "age": 40, "gender": "Male",
                "abha_id": "91-0000-1111-2222", "language": lang}

    def _make_history(self):
        return {
            "chief_complaint": "Chest pain",
            "hpi": "Patient presents with chest pain for 3 days.",
            "past_history": "Hypertension",
            "surgical_history": "None",
            "medications": "Telmisartan 40mg",
            "allergies": "NKDA",
            "family_history": "Cardiac disease",
            "personal_history": "Smoker",
            "ros": "Cardiovascular: Chest pain",
            "ayush_data": None
        }

    def test_generates_markdown_with_correct_headers(self):
        summary = summary_generator.generate_physician_summary(
            self._make_patient(), self._make_history(), [], [], "Allopathy"
        )
        md = summary["formatted_summary_markdown"]
        assert "MEDIKIOSK CLINICAL INTAKE SUMMARY" in md
        assert "Chief Complaint" in md
        assert "History of Present Illness" in md

    def test_red_flags_appear_in_markdown(self):
        red_flags = [{
            "flag_id": "ACUTE_CORONARY_SYNDROME",
            "title": "EMERGENCY: Suspected ACS",
            "message": "Chest pain with breathlessness",
            "priority": "P1_CRITICAL",
            "recommended_action": "Route to ER immediately"
        }]
        summary = summary_generator.generate_physician_summary(
            self._make_patient(), self._make_history(), [], red_flags, "Allopathy"
        )
        assert "RED FLAG" in summary["formatted_summary_markdown"]
        assert len(summary["red_flags"]) == 1

    def test_lab_results_table_rendered(self):
        labs = [
            {"test_name": "HbA1c", "value": "8.4", "unit": "%",
             "reference_range": "< 5.7", "abnormal": True}
        ]
        summary = summary_generator.generate_physician_summary(
            self._make_patient(), self._make_history(), labs, [], "Allopathy"
        )
        md = summary["formatted_summary_markdown"]
        assert "HbA1c" in md
        assert "ABNORMAL" in md

    def test_ayush_dashavidha_table_rendered(self):
        ayush_data = json.dumps({
            "Prakriti": "Pitta Pradhana",
            "Vikriti": "Pitta Vikriti",
            "Sara": "Rakta Sara",
            "Samhanana": "Madhyama",
            "Agni_Koshtha": "Tikshna Agni",
            "Satmya": "Sarva Satmya",
            "Sattva": "Madhyama Sattva",
            "Ahara_Vyayama_Shakti": "High",
            "Vaya_Ahara_Vihara": "Madhyama"
        })
        history = self._make_history()
        history["ayush_data"] = ayush_data
        summary = summary_generator.generate_physician_summary(
            self._make_patient(), history, [], [], "AYUSH"
        )
        md = summary["formatted_summary_markdown"]
        assert "AYUSH DASHAVIDHA PARIKSHA" in md
        assert "Pitta Pradhana" in md
        assert summary["ayush_dashavidha_summary"] is not None

    def test_hindi_audio_summary(self):
        summary = summary_generator.generate_physician_summary(
            self._make_patient("hi"), self._make_history(), [], [], "Allopathy"
        )
        assert "धन्यवाद" in summary["audio_summary_text"] or "नमस्कार" in summary["audio_summary_text"]

    def test_english_audio_summary(self):
        summary = summary_generator.generate_physician_summary(
            self._make_patient("en"), self._make_history(), [], [], "Allopathy"
        )
        assert "clinical history" in summary["audio_summary_text"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# FHIR Builder Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFHIRBuilderUnit:
    def _build_bundle(self, with_labs=True):
        patient_dict = {
            "patient_id": "PAT-TESTFHIR",
            "name": "FHIR Test Patient",
            "age": 50,
            "gender": "Female",
            "abha_id": "91-FHIR-TEST-0001",
            "phone": "9000000000"
        }
        history_dict = {
            "chief_complaint": "Persistent headache",
            "hpi": "Patient presents with 2-week history of headache.",
            "summary": "Physician summary here."
        }
        labs = [
            {"test_name": "HbA1c", "value": "8.4", "unit": "%",
             "reference_range": "< 5.7", "abnormal": True},
            {"test_name": "Hemoglobin", "value": "11.2", "unit": "g/dL",
             "reference_range": "12-16", "abnormal": True}
        ] if with_labs else []
        return fhir_converter.build_fhir_bundle(patient_dict, history_dict, labs)

    def test_bundle_has_correct_resource_type(self):
        bundle = self._build_bundle()
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "document"

    def test_bundle_has_patient_resource(self):
        bundle = self._build_bundle()
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        assert "Patient" in types

    def test_bundle_has_condition_resource(self):
        bundle = self._build_bundle()
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        assert "Condition" in types

    def test_bundle_has_observation_resources_for_labs(self):
        bundle = self._build_bundle(with_labs=True)
        types = [e["resource"]["resourceType"] for e in bundle["entry"]]
        assert "Observation" in types
        # One Observation per lab result
        obs_count = sum(1 for t in types if t == "Observation")
        assert obs_count == 2

    def test_patient_resource_has_abha_identifier(self):
        bundle = self._build_bundle()
        patient_resource = next(
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "Patient"
        )
        identifier_systems = [i["system"] for i in patient_resource.get("identifier", [])]
        assert "https://healthid.ndhm.gov.in" in identifier_systems

    def test_observation_abnormal_interpretation(self):
        bundle = self._build_bundle(with_labs=True)
        obs_resources = [
            e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "Observation"
        ]
        # Both lab results are abnormal — should have "H" interpretation
        for obs in obs_resources:
            interp_codes = [
                code["code"]
                for interp in obs.get("interpretation", [])
                for code in interp.get("coding", [])
            ]
            assert "H" in interp_codes

    def test_bundle_without_labs_still_valid(self):
        bundle = self._build_bundle(with_labs=False)
        assert bundle["resourceType"] == "Bundle"
        assert len(bundle["entry"]) >= 2  # Patient + Condition at minimum


# ═══════════════════════════════════════════════════════════════════════════════
# STT Engine Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSTTEngineUnit:
    def test_hindi_transcription_simulation(self):
        audio = b"fake audio data" * 100
        result = stt_engine.transcribe_audio(audio, language="hi")
        assert result["success"] is True
        assert result["language"] == "hi"
        assert len(result["transcript"]) > 0
        assert result["confidence"] > 0

    def test_english_transcription_simulation(self):
        audio = b"fake audio data" * 100
        result = stt_engine.transcribe_audio(audio, language="en")
        assert result["success"] is True
        assert "chest pain" in result["transcript"].lower() or len(result["transcript"]) > 5

    def test_empty_audio_fails_gracefully(self):
        result = stt_engine.transcribe_audio(b"", language="hi")
        assert result["success"] is False
        assert result["transcript"] == ""
