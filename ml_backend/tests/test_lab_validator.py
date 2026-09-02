import unittest
from ml_backend.services.lab_validator import LabValidatorService
from ml_backend.schemas.document import LabResultItem


class TestLabValidator(unittest.TestCase):
    def setUp(self):
        self.validator = LabValidatorService()

    def test_hba1c_elevated(self):
        item = LabResultItem(
            test_name="HbA1c",
            value="8.2",
            unit="%",
            reference_range="<5.7%"
        )
        validated = self.validator.validate_lab_item(item)
        self.assertTrue(validated.abnormal)
        self.assertEqual(validated.interpretation, "High")

    def test_fasting_blood_sugar_normal(self):
        item = LabResultItem(
            test_name="Fasting Blood Sugar",
            value="85",
            unit="mg/dL",
            reference_range="70 - 99 mg/dL"
        )
        validated = self.validator.validate_lab_item(item)
        self.assertFalse(validated.abnormal)
        self.assertEqual(validated.interpretation, "Normal")

    def test_fasting_blood_sugar_high(self):
        item = LabResultItem(
            test_name="Fasting Blood Sugar",
            value="164",
            unit="mg/dL",
            reference_range="70 - 99 mg/dL"
        )
        validated = self.validator.validate_lab_item(item)
        self.assertTrue(validated.abnormal)
        self.assertEqual(validated.interpretation, "High")

    def test_missing_reference_range_with_unknown_test(self):
        item = LabResultItem(
            test_name="Custom Novel Experimental Biomarker",
            value="42.5",
            unit="ng/mL",
            reference_range=None
        )
        validated = self.validator.validate_lab_item(item)
        self.assertIsNone(validated.abnormal)
        self.assertIn("Indeterminate", validated.interpretation)

    def test_missing_reference_range_with_known_test_fallback(self):
        # HbA1c with no reference range provided in doc should look up dictionary
        item = LabResultItem(
            test_name="HbA1c",
            value="8.2",
            unit=None,
            reference_range=None
        )
        validated = self.validator.validate_lab_item(item)
        self.assertTrue(validated.abnormal)
        self.assertEqual(validated.reference_range, "<5.7%")

    def test_qualitative_result(self):
        item = LabResultItem(
            test_name="Dengue NS1 Antigen",
            value="Positive",
            reference_range="Negative"
        )
        validated = self.validator.validate_lab_item(item)
        self.assertTrue(validated.abnormal)


if __name__ == "__main__":
    unittest.main()
