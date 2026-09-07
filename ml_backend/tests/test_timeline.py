import unittest
from ml_backend.services.timeline import TimelineService
from ml_backend.schemas.document import ExtractedDocument, DocumentTypeEnum, DiagnosisItem, MedicationItem, LabResultItem


class TestTimeline(unittest.TestCase):
    def setUp(self):
        self.timeline_service = TimelineService()

    def test_chronological_sorting(self):
        doc1 = ExtractedDocument(
            document_id="DOC_001",
            document_type=DocumentTypeEnum.PRESCRIPTION,
            document_date="2019-05-10",
            diagnoses=[DiagnosisItem(condition="Diabetes Mellitus")]
        )
        doc2 = ExtractedDocument(
            document_id="DOC_002",
            document_type=DocumentTypeEnum.LAB_REPORT,
            document_date="2026-08-15",
            lab_results=[LabResultItem(test_name="HbA1c", value="8.2", unit="%")]
        )
        doc3 = ExtractedDocument(
            document_id="DOC_003",
            document_type=DocumentTypeEnum.DISCHARGE_SUMMARY,
            document_date="2024-11-20",
            hospital_name="Metro Hospital"
        )

        response = self.timeline_service.build_chronological_timeline([doc2, doc1, doc3])
        events = response.events

        # Earliest event should be 2019, followed by 2024, followed by 2026
        dates = [e.event_date for e in events if e.event_date]
        self.assertTrue(len(dates) >= 3)
        self.assertEqual(dates[0], "2019-05-10")
        self.assertEqual(dates[-1], "2026-08-15")

    def test_missing_date_not_invented(self):
        doc_undated = ExtractedDocument(
            document_id="DOC_UNDATED",
            document_type=DocumentTypeEnum.PRESCRIPTION,
            document_date=None,
            diagnoses=[DiagnosisItem(condition="Hypertension")]
        )

        response = self.timeline_service.build_chronological_timeline([doc_undated])
        self.assertEqual(len(response.events), 2)  # Consultation + Diagnosis
        for ev in response.events:
            self.assertIsNone(ev.event_date)
            self.assertEqual(ev.source_document_id, "DOC_UNDATED")


if __name__ == "__main__":
    unittest.main()
