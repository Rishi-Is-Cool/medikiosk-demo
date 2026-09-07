import unittest
from ml_backend.services.normalization import NormalizationService
from ml_backend.schemas.medical_fact import FactTypeEnum


class TestNormalization(unittest.TestCase):
    def setUp(self):
        self.norm = NormalizationService()

    def test_dm_normalization(self):
        res = self.norm.normalize_condition("DM")
        self.assertEqual(res.normalized, "Diabetes Mellitus")
        self.assertEqual(res.raw, "DM")
        self.assertTrue(res.is_known)

    def test_bp_normalization(self):
        res = self.norm.normalize_condition("BP")
        self.assertEqual(res.normalized, "Hypertension")
        self.assertEqual(res.raw, "BP")
        self.assertTrue(res.is_known)

    def test_high_bp_normalization(self):
        res = self.norm.normalize_condition("high BP")
        self.assertEqual(res.normalized, "Hypertension")
        self.assertEqual(res.raw, "high BP")
        self.assertTrue(res.is_known)

    def test_htn_normalization(self):
        res = self.norm.normalize_condition("HTN")
        self.assertEqual(res.normalized, "Hypertension")

    def test_medication_normalization(self):
        res = self.norm.normalize_medication("pcm")
        self.assertEqual(res.normalized, "Paracetamol")
        self.assertEqual(res.raw, "pcm")

    def test_frequency_normalization(self):
        res = self.norm.normalize_frequency("BD")
        self.assertEqual(res.normalized, "Twice daily")
        self.assertEqual(res.raw, "BD")

    def test_unknown_term_remains_unchanged(self):
        unknown = "Rare Idiopathic Syndrome XYZ"
        res = self.norm.normalize_condition(unknown)
        self.assertEqual(res.normalized, unknown)
        self.assertEqual(res.raw, unknown)
        self.assertFalse(res.is_known)

    def test_patient_fact_creation_preserves_raw_and_normalized(self):
        fact = self.norm.create_patient_fact(
            fact_type=FactTypeEnum.CONDITION,
            raw_val="DM",
            source_doc_id="DOC_001",
            date_recorded="2019"
        )
        self.assertEqual(fact.raw_value, "DM")
        self.assertEqual(fact.normalized_value, "Diabetes Mellitus")
    def test_marathi_condition_normalization(self):
        # Devanagari script
        res_dev = self.norm.normalize_condition("मधुमेह")
        self.assertEqual(res_dev.normalized, "Diabetes Mellitus")
        self.assertEqual(res_dev.raw, "मधुमेह")

        res_bp = self.norm.normalize_condition("उच्च रक्तदाब")
        self.assertEqual(res_bp.normalized, "Hypertension")

        # Transliterated Marathi
        res_trans = self.norm.normalize_condition("sakharcha ajar")
        self.assertEqual(res_trans.normalized, "Diabetes Mellitus")

        res_bp_trans = self.norm.normalize_condition("raktadaab")
        self.assertEqual(res_bp_trans.normalized, "Hypertension")

    def test_marathi_medication_and_frequency(self):
        res_med = self.norm.normalize_medication("तापाची गोळी")
        self.assertEqual(res_med.normalized, "Paracetamol")

        res_freq = self.norm.normalize_frequency("सकाळ संध्याकाळ")
        self.assertEqual(res_freq.normalized, "Twice daily")

        res_freq_upashi = self.norm.normalize_frequency("उपाशी पोटी")
        self.assertEqual(res_freq_upashi.normalized, "Before meals / Fasting")


if __name__ == "__main__":
    unittest.main()
