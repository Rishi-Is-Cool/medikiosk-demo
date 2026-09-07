import unittest
from ml_backend.services.doctor_qa import DoctorQAService
from ml_backend.schemas.qa import DoctorQARequest, QueryPatternEnum
from ml_backend.schemas.medical_fact import PatientFact, FactTypeEnum
from ml_backend.schemas.timeline import TimelineEvent, TimelineEventType
from ml_backend.schemas.document import ExtractedDocument, DocumentTypeEnum, LabResultItem, DiagnosisItem, MedicationItem


class TestDoctorQA(unittest.TestCase):
    def setUp(self):
        self.qa_service = DoctorQAService()

    def test_query_classification(self):
        self.assertEqual(self.qa_service.classify_query("What happened during the last visit?"), QueryPatternEnum.LAST_VISIT)
        self.assertEqual(self.qa_service.classify_query("Show me the diabetes history"), QueryPatternEnum.DIABETES_HISTORY)
        self.assertEqual(self.qa_service.classify_query("Why was the medication changed?"), QueryPatternEnum.MEDICATION_CHANGE)
        self.assertEqual(self.qa_service.classify_query("Has the patient been hospitalized?"), QueryPatternEnum.HOSPITALIZATION)
        self.assertEqual(self.qa_service.classify_query("What allergies are documented?"), QueryPatternEnum.ALLERGIES)

    def test_qa_with_evidence_and_sources(self):
        doc1 = ExtractedDocument(
            document_id="DOC_001",
            document_type=DocumentTypeEnum.PRESCRIPTION,
            document_date="2019-05-10",
            diagnoses=[DiagnosisItem(condition="Diabetes Mellitus")],
            medications=[MedicationItem(name="Metformin", dosage="500 mg", frequency="BD")]
        )
        facts = [
            PatientFact(
                type=FactTypeEnum.CONDITION,
                raw_value="DM",
                normalized_value="Diabetes Mellitus",
                date_recorded="2019-05-10",
                source_document_id="DOC_001"
            )
        ]

        req = DoctorQARequest(
            patient_id="P_DEMO_001",
            question="Show me the diabetes history.",
            context_facts=facts,
            context_documents=[doc1]
        )

        response = self.qa_service.answer_question(req)

        self.assertTrue(response.data_available)
        self.assertTrue(len(response.source_references) > 0)
        self.assertIn("DOC_001", [s.document_id for s in response.source_references])

    def test_qa_empty_records_returns_uncertainty(self):
        req = DoctorQARequest(
            patient_id="P_EMPTY_001",
            question="Has the patient undergone any neurosurgery?",
            context_facts=[],
            context_timeline=[],
            context_documents=[]
        )

        response = self.qa_service.answer_question(req)
        self.assertFalse(response.data_available)
        self.assertIn("No documentation found", response.answer)


if __name__ == "__main__":
    unittest.main()
