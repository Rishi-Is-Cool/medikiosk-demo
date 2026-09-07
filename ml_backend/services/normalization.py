import json
import re
import logging
import unicodedata
import difflib
from typing import Dict, Any, Optional, Tuple, List
from ml_backend.config import settings
from ml_backend.schemas.medical_fact import NormalizedTerm, PatientFact, FactTypeEnum

logger = logging.getLogger(__name__)


class NormalizationService:
    def __init__(self, dict_path: Optional[str] = None):
        self.dict_path = dict_path or str(settings.NORMALIZATION_DICT_PATH)
        self.dictionary: Dict[str, Dict[str, str]] = self._load_dictionary()

    def _load_dictionary(self) -> Dict[str, Dict[str, str]]:
        try:
            with open(self.dict_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load dictionary from {self.dict_path}: {e}. Using fallback defaults.")
            return {
                "conditions": {
                    "dm": "Diabetes Mellitus",
                    "diabetes": "Diabetes Mellitus",
                    "sugar": "Diabetes Mellitus",
                    "मधुमेह": "Diabetes Mellitus",
                    "साखरेचा आजार": "Diabetes Mellitus",
                    "bp": "Hypertension",
                    "high bp": "Hypertension",
                    "रक्तदाब": "Hypertension",
                    "उच्च रक्तदाब": "Hypertension",
                    "htn": "Hypertension",
                    "mi": "Myocardial Infarction",
                    "heart attack": "Myocardial Infarction"
                },
                "medications": {
                    "pcm": "Paracetamol",
                    "तापाची गोळी": "Paracetamol",
                    "met": "Metformin",
                    "metformin": "Metformin",
                    "amlo": "Amlodipine"
                },
                "frequencies": {
                    "bd": "Twice daily",
                    "od": "Once daily",
                    "tds": "Three times daily",
                    "दिवसातून दोनदा": "Twice daily",
                    "सकाळ संध्याकाळ": "Twice daily",
                    "दिवसातून एकदा": "Once daily"
                },
                "routes": {
                    "po": "Oral",
                    "iv": "Intravenous"
                },
                "allergies": {
                    "pnc": "Penicillin",
                    "penicillin": "Penicillin"
                }
            }

    @staticmethod
    def clean_term(term: str) -> str:
        """
        1. Unicode normalization (NFKC) for Devanagari/Indic scripts
        2. Lowercase input & trim whitespace
        3. Normalize punctuation and strip common colloquial filler suffixes
        """
        if not term:
            return ""
        # Unicode normalization
        normalized_str = unicodedata.normalize("NFKC", term.strip())
        cleaned = normalized_str.lower()
        # Replace multiple spaces / tabs
        cleaned = re.sub(r"\s+", " ", cleaned)
        # Remove trailing periods / commas / dashes
        cleaned = re.sub(r"^[\s.,;:/\-]+|[\s.,;:/\-]+$", "", cleaned)
        return cleaned

    def normalize_term(self, raw_term: str, category: Optional[str] = None) -> NormalizedTerm:
        """
        Normalize a raw medical term, preserving raw input and returning canonical term.
        Supports exact match, colloquial suffix stripping, and fuzzy phonetic matching.
        """
        if not raw_term or not raw_term.strip():
            return NormalizedTerm(raw="", normalized="", category=category, is_known=False)

        raw = raw_term.strip()
        cleaned = self.clean_term(raw)

        # 1. Direct match in requested category
        if category and category in self.dictionary:
            if cleaned in self.dictionary[category]:
                return NormalizedTerm(
                    raw=raw,
                    normalized=self.dictionary[category][cleaned],
                    category=category,
                    is_known=True
                )

        # 2. Direct match across all categories
        for cat_name, mappings in self.dictionary.items():
            if cleaned in mappings:
                return NormalizedTerm(
                    raw=raw,
                    normalized=mappings[cleaned],
                    category=cat_name,
                    is_known=True
                )

        # 3. Colloquial suffix stripped match (e.g. "chi bimari", "cha tras", "ki problem")
        cleaned_no_suffix = re.sub(r"\s+(?:cha\s+ajar|chi\s+bimari|ki\s+bimari|cha\s+tras|ka\s+problem|cha\s+problem|badhla\s+ahe|badhla)$", "", cleaned)
        if cleaned_no_suffix != cleaned:
            for cat_name, mappings in self.dictionary.items():
                if cleaned_no_suffix in mappings:
                    return NormalizedTerm(
                        raw=raw,
                        normalized=mappings[cleaned_no_suffix],
                        category=cat_name,
                        is_known=True
                    )

        # 4. High-confidence Fuzzy Matching (difflib with cutoff 0.85)
        search_dicts = [(category, self.dictionary[category])] if (category and category in self.dictionary) else list(self.dictionary.items())
        for cat_name, mappings in search_dicts:
            matches = difflib.get_close_matches(cleaned, mappings.keys(), n=1, cutoff=0.85)
            if matches:
                matched_key = matches[0]
                return NormalizedTerm(
                    raw=raw,
                    normalized=mappings[matched_key],
                    category=cat_name,
                    is_known=True
                )

        # 5. Fallback: unknown term remains unchanged as canonical representation
        return NormalizedTerm(
            raw=raw,
            normalized=raw,
            category=category,
            is_known=False
        )

    def normalize_condition(self, raw_condition: str) -> NormalizedTerm:
        return self.normalize_term(raw_condition, category="conditions")

    def normalize_medication(self, raw_medication: str) -> NormalizedTerm:
        return self.normalize_term(raw_medication, category="medications")

    def normalize_frequency(self, raw_frequency: str) -> NormalizedTerm:
        return self.normalize_term(raw_frequency, category="frequencies")

    def normalize_route(self, raw_route: str) -> NormalizedTerm:
        return self.normalize_term(raw_route, category="routes")

    def normalize_allergy(self, raw_allergy: str) -> NormalizedTerm:
        return self.normalize_term(raw_allergy, category="allergies")

    def create_patient_fact(
        self,
        fact_type: FactTypeEnum,
        raw_val: str,
        source_doc_id: str,
        date_recorded: Optional[str] = None,
        confidence: float = 1.0,
        details: Optional[Dict[str, Any]] = None
    ) -> PatientFact:
        """
        Create a PatientFact preserving both raw and normalized values with source provenance.
        """
        category_map = {
            FactTypeEnum.CONDITION: "conditions",
            FactTypeEnum.MEDICATION: "medications",
            FactTypeEnum.ALLERGY: "allergies",
        }
        cat = category_map.get(fact_type)
        norm_result = self.normalize_term(raw_val, category=cat)

        return PatientFact(
            type=fact_type,
            raw_value=norm_result.raw,
            normalized_value=norm_result.normalized,
            date_recorded=date_recorded,
            source_document_id=source_doc_id,
            confidence=confidence,
            details=details or {}
        )


normalization_service = NormalizationService()
