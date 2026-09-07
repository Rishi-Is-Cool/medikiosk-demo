import unittest
from ml_backend.services.vision_extract import vision_extraction_service
from ml_backend.services.normalization import normalization_service
from ml_backend.services.lab_validator import lab_validator_service
from ml_backend.services.timeline import timeline_service
from ml_backend.services.conflict_detector import conflict_detector_service
from ml_backend.services.snapshot_generator import snapshot_generator_service
from ml_backend.services.doctor_qa import doctor_qa_service
from ml_backend.schemas.snapshot import CurrentIntakeHistory, SnapshotRequest
from ml_backend.schemas.qa import DoctorQARequest
from ml_backend.schemas.document import DocumentTypeEnum


class TestEndToEndPipeline(unittest.TestCase):
    def test_full_hackathon_demo_scenario(self):
        # ----------------------------------------------------
        # 1. Process 3 Documents
        # ----------------------------------------------------
        # Doc 1: Prescription
        res1 = vision_extraction_service.extract_document(
            image_bytes=b"prescription_data",
            mime_type="image/jpeg",
            document_id="DOC_001",
            provider="mock"
        )
        self.assertTrue(res1.success)
        self.assertEqual(res1.document_type, DocumentTypeEnum.PRESCRIPTION)

        # Doc 2: Lab Report
        res2 = vision_extraction_service.extract_document(
            image_bytes=b"lab_report_data",
            mime_type="image/jpeg",
            document_id="DOC_002",
            provider="mock"
        )
        self.assertTrue(res2.success)
        self.assertEqual(res2.document_type, DocumentTypeEnum.LAB_REPORT)

        # Doc 3: Discharge Summary
        res3 = vision_extraction_service.extract_document(
            image_bytes=b"discharge_summary_data",
            mime_type="image/jpeg",
            document_id="DOC_003",
            provider="mock"
        )
        self.assertTrue(res3.success)
        self.assertEqual(res3.document_type, DocumentTypeEnum.DISCHARGE_SUMMARY)

        docs = [res1.extraction, res2.extraction, res3.extraction]

        # ----------------------------------------------------
        # 2. Verify Normalization
        # ----------------------------------------------------
        all_facts = res1.normalized_facts + res2.normalized_facts + res3.normalized_facts
        dm_fact = next((f for f in all_facts if f.raw_value == "DM"), None)
        self.assertIsNotNone(dm_fact)
        self.assertEqual(dm_fact.normalized_value, "Diabetes Mellitus")
        self.assertEqual(dm_fact.source_document_id, "DOC_001")

        # ----------------------------------------------------
        # 3. Verify Deterministic Lab Validation
        # ----------------------------------------------------
        hba1c_lab = next((l for l in res2.extraction.lab_results if l.test_name == "HbA1c"), None)
        self.assertIsNotNone(hba1c_lab)
        self.assertTrue(hba1c_lab.abnormal)
        self.assertEqual(hba1c_lab.interpretation, "High")

        # ----------------------------------------------------
        # 4. Verify Chronological Timeline
        # ----------------------------------------------------
        timeline_res = timeline_service.build_chronological_timeline(docs)
        self.assertTrue(timeline_res.total_events > 0)
        # Verify 2019 event precedes 2026 event
        dated_events = [e for e in timeline_res.events if e.event_date]
        self.assertEqual(dated_events[0].event_date, "2019-05-10")
        self.assertEqual(dated_events[-1].event_date, "2026-08-15")

        # ----------------------------------------------------
        # 5. Current Intake History + Conflict Detection
        # ----------------------------------------------------
        current_history = CurrentIntakeHistory(
            chief_complaint="Fever and cough",
            duration="3 days",
            symptoms=["fever", "cough"],
            allergies=["No known allergies", "NKDA"],
            past_history=[]
        )

        alerts = conflict_detector_service.detect_conflicts(
            current_history=current_history,
            extracted_documents=docs,
            patient_facts=all_facts
        )

        # Check that Penicillin allergy conflict was raised
        penicillin_alerts = [a for a in alerts if "Penicillin" in a.message]
        self.assertTrue(len(penicillin_alerts) > 0)
        self.assertEqual(penicillin_alerts[0].severity, "high")

        # ----------------------------------------------------
        # 6. Physician Snapshot Generation
        # ----------------------------------------------------
        all_labs = res1.extraction.lab_results + res2.extraction.lab_results + res3.extraction.lab_results
        snapshot_req = SnapshotRequest(
            patient_id="P_DEMO_001",
            current_history=current_history,
            facts=all_facts,
            timeline=timeline_res.events,
            documents=docs,
            lab_results=all_labs
        )

        snapshot = snapshot_generator_service.generate_snapshot(snapshot_req, provider="mock")
        self.assertIn("Fever", snapshot.chief_complaint)
        self.assertTrue(len(snapshot.past_medical_history) > 0)
        self.assertTrue(len(snapshot.allergies) > 0)
        self.assertTrue(len(snapshot.alerts) > 0)

        # ----------------------------------------------------
        # 7. Doctor Q&A Synthesis
        # ----------------------------------------------------
        qa_queries = [
            "What happened during the last visit?",
            "Show me the diabetes history.",
            "Why was the medication changed?",
            "Has the patient been hospitalized?",
            "What allergies are documented?"
        ]

        for q in qa_queries:
            qa_req = DoctorQARequest(
                patient_id="P_DEMO_001",
                question=q,
                context_facts=all_facts,
                context_timeline=timeline_res.events,
                context_documents=docs,
                current_history=current_history
            )
            qa_res = doctor_qa_service.answer_question(qa_req, provider="mock")
            self.assertTrue(qa_res.data_available)
            self.assertTrue(len(qa_res.answer) > 0)
            self.assertTrue(len(qa_res.source_references) > 0)


if __name__ == "__main__":
    unittest.main()
