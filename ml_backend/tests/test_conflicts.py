import unittest
from ml_backend.services.conflict_detector import ConflictDetectorService
from ml_backend.schemas.snapshot import CurrentIntakeHistory
from ml_backend.schemas.document import ExtractedDocument, DocumentTypeEnum, AllergyItem, DiagnosisItem
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum


class TestConflicts(unittest.TestCase):
    def setUp(self):
        self.detector = ConflictDetectorService()

    def test_allergy_conflict_detected(self):
        current_history = CurrentIntakeHistory(
            chief_complaint="Fever",
            allergies=["No known allergies", "NKDA"]
        )
        doc = ExtractedDocument(
            document_id="DOC_003",
            document_type=DocumentTypeEnum.DISCHARGE_SUMMARY,
            allergies=[AllergyItem(substance="Penicillin", reaction="Skin rash")]
        )
        facts = [
            PatientFact(
                type=FactTypeEnum.ALLERGY,
                raw_value="Penicillin",
                normalized_value="Penicillin",
                source_document_id="DOC_003"
            )
        ]

        alerts = self.detector.detect_conflicts(
            current_history=current_history,
            extracted_documents=[doc],
            patient_facts=facts
        )

        allergy_alerts = [a for a in alerts if a.type == "data_inconsistency" and "Penicillin" in a.message]
        self.assertTrue(len(allergy_alerts) > 0)
        self.assertEqual(allergy_alerts[0].severity, "high")
        self.assertIn("DOC_003", allergy_alerts[0].source_document_ids)

    def test_past_history_conflict_detected(self):
        current_history = CurrentIntakeHistory(
            chief_complaint="Cough",
            past_history=["No past medical history", "None"]
        )
        doc = ExtractedDocument(
            document_id="DOC_001",
            document_type=DocumentTypeEnum.PRESCRIPTION,
            diagnoses=[DiagnosisItem(condition="Diabetes Mellitus")]
        )
        facts = [
            PatientFact(
                type=FactTypeEnum.CONDITION,
                raw_value="DM",
                normalized_value="Diabetes Mellitus",
                source_document_id="DOC_001"
            )
        ]

        alerts = self.detector.detect_conflicts(
            current_history=current_history,
            extracted_documents=[doc],
            patient_facts=facts
        )

        history_alerts = [a for a in alerts if "past medical history" in a.message]
        self.assertTrue(len(history_alerts) > 0)
        self.assertEqual(history_alerts[0].severity, "high")
        self.assertIn("DOC_001", history_alerts[0].source_document_ids)


if __name__ == "__main__":
    unittest.main()
