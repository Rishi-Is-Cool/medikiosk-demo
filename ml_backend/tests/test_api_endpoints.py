import unittest
import base64
from fastapi.testclient import TestClient
from ml_backend.app import app


class TestFastAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("service", data)
        self.assertEqual(data["model"], "gemini-3.6-flash")

    def test_normalize_endpoint(self):
        payload = {
            "terms": ["DM", "high BP", "pcm", "BD"]
        }
        response = self.client.post("/ml/documents/normalize", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        results = data["results"]
        self.assertEqual(results["DM"]["normalized"], "Diabetes Mellitus")
        self.assertEqual(results["high BP"]["normalized"], "Hypertension")
        self.assertEqual(results["pcm"]["normalized"], "Paracetamol")
        self.assertEqual(results["BD"]["normalized"], "Twice daily")

    def test_lab_validator_endpoint(self):
        payload = {
            "labs": [
                {
                    "test_name": "HbA1c",
                    "value": "8.2",
                    "unit": "%",
                    "reference_range": "<5.7%"
                },
                {
                    "test_name": "Fasting Blood Sugar",
                    "value": "85",
                    "unit": "mg/dL",
                    "reference_range": "70 - 99 mg/dL"
                }
            ]
        }
        response = self.client.post("/ml/validate/labs", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data[0]["abnormal"])
        self.assertFalse(data[1]["abnormal"])

    def test_conflicts_endpoint(self):
        payload = {
            "current_history": {
                "chief_complaint": "Fever",
                "allergies": ["No known allergies"]
            },
            "historical_documents": [
                {
                    "document_id": "DOC_001",
                    "document_type": "prescription",
                    "confidence": 0.95,
                    "allergies": [{"substance": "Penicillin"}]
                }
            ],
            "historical_facts": []
        }
        response = self.client.post("/ml/validate/conflicts", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["conflicts_detected"] > 0)
        self.assertIn("Penicillin", data["alerts"][0]["message"])

    def test_doctor_qa_endpoint(self):
        payload = {
            "patient_id": "P_DEMO_001",
            "question": "What happened during the last visit?",
            "context_documents": [
                {
                    "document_id": "DOC_002",
                    "document_type": "lab_report",
                    "confidence": 0.95,
                    "document_date": "2026-08-15",
                    "lab_results": [
                        {"test_name": "HbA1c", "value": "8.2", "unit": "%"}
                    ]
                }
            ]
        }
        response = self.client.post("/ml/doctor/qa", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["data_available"])
        self.assertTrue(len(data["answer"]) > 0)

    def test_extract_endpoint_rejects_empty_payload(self):
        """P0 Test: Empty payload must fail with HTTP 400."""
        response = self.client.post("/ml/documents/extract")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("No document image provided", data["error"]["message"])

    def test_extract_endpoint_rejects_dummy_bytes(self):
        """P0 Test: Dummy placeholder bytes must be explicitly rejected with HTTP 400."""
        payload = {
            "document_id": "DOC_TEST_001",
            "image_base64": base64.b64encode(b"DUMMY_IMAGE_BYTES").decode("utf-8")
        }
        response = self.client.post("/ml/documents/extract", json=payload)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Dummy placeholder bytes are rejected", data["error"]["message"])

    def test_extract_endpoint_success_with_valid_upload(self):
        """Test valid extraction when valid image payload is provided."""
        valid_b64 = base64.b64encode(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00").decode("utf-8")
        payload = {
            "document_id": "DOC_001",
            "image_base64": valid_b64,
            "mime_type": "image/jpeg"
        }
        response = self.client.post("/ml/documents/extract", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["document_id"], "DOC_001")


if __name__ == "__main__":
    unittest.main()
