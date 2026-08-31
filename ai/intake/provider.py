"""Clinical Information Extraction Provider for MediKiosk.

Defines the abstract interface for extracting structured clinical data
from unstructured text (e.g., transcripts) into validated Pydantic models.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import ValidationError

from ai.intake.schemas import IntakeResponse


class ExtractionResult:
    """Represents the outcome of a clinical extraction attempt."""

    def __init__(
        self,
        success: bool,
        data: Optional[IntakeResponse] = None,
        error: Optional[str] = None,
        raw_output: Optional[Any] = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.raw_output = raw_output


class ClinicalExtractionProvider(ABC):
    """Abstract base class for clinical extraction engines.

    Implementations (e.g., LLMs) should override `_do_extract` to produce
    a dictionary matching the IntakeResponse schema. This base class handles
    the strict Pydantic validation.
    """

    def extract(
        self,
        text: str,
        language: Optional[str] = None,
        patient_id: Optional[str] = None,
        **kwargs,
    ) -> ExtractionResult:
        """Extracts structured clinical information from text.

        Args:
            text: The unstructured patient transcript or text input.
            language: Optional language code of the text.
            patient_id: Optional patient identifier.
            kwargs: Additional provider-specific parameters.

        Returns:
            An ExtractionResult containing either validated data or error info.
        """
        if not text or not text.strip():
            return ExtractionResult(
                success=False,
                error="Input text is empty or invalid.",
            )

        try:
            # Concrete providers implement this to return a raw dict
            raw_dict = self._do_extract(text, language, patient_id, **kwargs)
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Extraction provider failed: {str(e)}",
            )

        try:
            # Validate the raw dict against the existing IntakeResponse schema
            validated_data = IntakeResponse(**raw_dict)
            return ExtractionResult(
                success=True,
                data=validated_data,
                raw_output=raw_dict,
            )
        except ValidationError as ve:
            return ExtractionResult(
                success=False,
                error=f"Validation failed: {str(ve)}",
                raw_output=raw_dict,
            )
        except Exception as e:
            return ExtractionResult(
                success=False,
                error=f"Unexpected validation error: {str(e)}",
                raw_output=raw_dict,
            )

    @abstractmethod
    def _do_extract(
        self,
        text: str,
        language: Optional[str] = None,
        patient_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Perform the actual extraction. Must return a dict compatible with IntakeResponse."""
        pass
