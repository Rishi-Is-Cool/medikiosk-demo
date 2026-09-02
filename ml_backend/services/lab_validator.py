import json
import re
import logging
from typing import Dict, Any, Optional, Tuple, Union
from ml_backend.config import settings
from ml_backend.schemas.document import LabResultItem

logger = logging.getLogger(__name__)


class LabValidatorService:
    def __init__(self, ranges_path: Optional[str] = None):
        self.ranges_path = ranges_path or str(settings.LAB_REFERENCE_PATH)
        self.standard_ranges: Dict[str, Dict[str, Any]] = self._load_ranges()

    def _load_ranges(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.ranges_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load lab reference ranges from {self.ranges_path}: {e}")
            return {}

    @staticmethod
    def parse_numeric_value(val: Any) -> Optional[float]:
        """Extract float from value string (e.g. '8.2%', '> 100', '164 mg/dL', 8.2)."""
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        # Find first decimal or integer pattern
        match = re.search(r"[-+]?\d*\.?\d+", val_str)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return None
        return None

    @staticmethod
    def parse_reference_range(ref_str: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse reference range string into (lower_bound, upper_bound).
        Examples:
        - '<5.7%' -> (None, 5.7)
        - '<= 200' -> (None, 200.0)
        - '> 60' -> (60.0, None)
        - '>= 12.0' -> (12.0, None)
        - '70 - 99 mg/dL' -> (70.0, 99.0)
        - '13.5 to 17.5' -> (13.5, 17.5)
        """
        if not ref_str or not ref_str.strip():
            return None, None

        cleaned = ref_str.strip().lower()

        # Less than (< or <=)
        less_match = re.search(r"(?:<|<=|less than)\s*([0-9]+\.?[0-9]*)", cleaned)
        if less_match:
            try:
                return None, float(less_match.group(1))
            except ValueError:
                pass

        # Greater than (> or >=)
        greater_match = re.search(r"(?:>|>=|greater than)\s*([0-9]+\.?[0-9]*)", cleaned)
        if greater_match:
            try:
                return float(greater_match.group(1)), None
            except ValueError:
                pass

        # Range interval: '70 - 99', '70.0-99.0', '13.5 to 17.5'
        range_match = re.search(r"([0-9]+\.?[0-9]*)\s*(?:-|–|—|to)\s*([0-9]+\.?[0-9]*)", cleaned)
        if range_match:
            try:
                low = float(range_match.group(1))
                high = float(range_match.group(2))
                return low, high
            except ValueError:
                pass

        return None, None

    def validate_lab_item(self, item: LabResultItem) -> LabResultItem:
        """
        Deterministically evaluates whether the lab item is abnormal.
        Preserves original fields and sets abnormal boolean + interpretation.
        """
        num_val = self.parse_numeric_value(item.value)
        test_key = item.test_name.strip().lower() if item.test_name else ""

        # Step 1: Parse range from document if provided
        low, high = self.parse_reference_range(item.reference_range)

        # Step 2: If reference range missing from document, check knowledge base
        if low is None and high is None:
            if test_key in self.standard_ranges:
                std = self.standard_ranges[test_key]
                low = std.get("lower_limit")
                high = std.get("upper_limit")
                if not item.reference_range and std.get("default_range_str"):
                    item.reference_range = std.get("default_range_str")
                if not item.unit and std.get("unit"):
                    item.unit = std.get("unit")

        # Step 3: If qualitative test (e.g. Negative, Non-Reactive, Nil, Clear)
        if num_val is None and item.value is not None:
            val_str = str(item.value).strip().lower()
            if val_str in ["positive", "reactive", "detected", "present", "abnormal"]:
                item.abnormal = True
                item.interpretation = "Abnormal / Positive"
                return item
            elif val_str in ["negative", "non-reactive", "non reactive", "not detected", "nil", "normal", "clear"]:
                item.abnormal = False
                item.interpretation = "Normal / Negative"
                return item

        # Step 4: Numeric evaluation against bounds
        if num_val is not None:
            if low is not None and high is not None:
                if num_val < low:
                    item.abnormal = True
                    item.interpretation = "Low"
                elif num_val > high:
                    item.abnormal = True
                    item.interpretation = "High"
                else:
                    item.abnormal = False
                    item.interpretation = "Normal"
                return item

            elif high is not None:  # upper bound only, e.g. <5.7% or <200
                if num_val > high:
                    item.abnormal = True
                    item.interpretation = "High"
                else:
                    item.abnormal = False
                    item.interpretation = "Normal"
                return item

            elif low is not None:  # lower bound only, e.g. >60
                if num_val < low:
                    item.abnormal = True
                    item.interpretation = "Low"
                else:
                    item.abnormal = False
                    item.interpretation = "Normal"
                return item

        # Step 5: Indeterminate - DO NOT GUESS
        item.abnormal = None
        item.interpretation = "Indeterminate / No reference range"
        return item

    def validate_lab_results(self, items: list[LabResultItem]) -> list[LabResultItem]:
        """Validate a list of lab result items."""
        return [self.validate_lab_item(item) for item in items]


lab_validator_service = LabValidatorService()
