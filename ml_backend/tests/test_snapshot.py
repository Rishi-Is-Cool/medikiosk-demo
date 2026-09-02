import unittest
from ml_backend.services.snapshot_generator import SnapshotGeneratorService
from ml_backend.schemas.snapshot import SnapshotRequest, CurrentIntakeHistory
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum
from ml_backend.schemas.timeline import TimelineEvent, TimelineEventType
from ml_backend.schemas.document import ExtractedDocument, DocumentTypeEnum, LabResultItem


class TestSnapshot(unittest.TestCase):
    def setUp(self):
        self.service = SnapshotGeneratorService()

    def test_snapshot_generation_with_provenance(self):
        current_history = CurrentIntakeHistory(
            chief_complaint="Fever and cough",
            duration="3 days",
            symptoms=["cough", "fever"],
            allergies=["No known allergies"]
        )

        facts = [
            PatientFact(
                type=FactTypeEnum.CONDITION,
                raw_value="DM",
                normalized_value="Diabetes Mellitus",
                date_recorded="2019",
                source_document_id="DOC_001"
            ),
            PatientFact(
                type=FactTypeEnum.MEDICATION,
                raw_value="Metformin",
                normalized_value="Metformin",
                date_recorded="2019",
                source_document_id="DOC_001",
                details={"dosage": "500 mg", "frequency": "Twice daily"}
            ),
            PatientFact(
                type=FactTypeEnum.ALLERGY,
                raw_value="Penicillin",
                normalized_value="Penicillin",
                date_recorded="2024-11-20",
                source_document_id="DOC_003"
            )
        ]

        labs = [
            LabResultItem(
                test_name="HbA1c",
                value="8.2",
                unit="%",
                reference_range="<5.7%",
                abnormal=True
            )
        ]

        req = SnapshotRequest(
            patient_id="P_DEMO_001",
            current_history=current_history,
            facts=facts,
            timeline=[],
            documents=[],
            lab_results=labs
        )

        snapshot = self.service.generate_snapshot(req)

        self.assertIn("Fever", snapshot.chief_complaint)
        self.assertTrue(len(snapshot.past_medical_history) > 0)
        self.assertTrue(len(snapshot.allergies) > 0)
        self.assertTrue(len(snapshot.alerts) > 0)

        # Verify source IDs exist in past history
        has_doc_001 = any("DOC_001" in item.get("source_document_ids", []) for item in snapshot.past_medical_history)
        self.assertTrue(has_doc_001)


if __name__ == "__main__":
    unittest.main()
