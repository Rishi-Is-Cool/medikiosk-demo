"""Unit tests for the Clinical Information Extraction provider architecture."""

from datetime import datetime, timezone
import pytest

from ai.intake.provider import ClinicalExtractionProvider
from ai.intake.schemas import IntakeResponse


class MockExtractionProvider(ClinicalExtractionProvider):
    """A mock implementation of the ClinicalExtractionProvider for testing."""
    
    def __init__(self):
        self.mock_response = None
        self.should_fail = False

    def _do_extract(self, text: str, language: str = None, patient_id: str = None, **kwargs):
        if self.should_fail:
            raise RuntimeError("Mock extraction provider failed")
            
        if self.mock_response is not None:
            return self.mock_response

        # Default fallback if nothing is set
        return {}


@pytest.fixture
def provider():
    return MockExtractionProvider()


def test_successful_extraction(provider):
    """Test 1: Successful extraction producing a valid IntakeResponse-compatible result."""
    provider.mock_response = {
        "patient_id": "123",
        "language": "en",
        "chief_complaint": {
            "name": "Chest pain",
            "duration": "2 days",
            "severity": 8
        },
        "symptoms": [
            {
                "name": "Chest pain",
                "severity": 8,
                "duration": "2 days"
            }
        ],
        "metadata": {
            "patient_id": "123",
            "language": "en",
            "intake_mode": "text",
            "timestamp": datetime.now(timezone.utc)
        }
    }

    result = provider.extract(text="I have had chest pain for 2 days.")
    assert result.success is True
    assert isinstance(result.data, IntakeResponse)
    assert result.data.chief_complaint.name == "Chest pain"
    assert result.data.symptoms[0].severity == 8


def test_missing_optional_information(provider):
    """Test 2: Extraction where optional clinical information is missing."""
    provider.mock_response = {
        "language": "es",
        "metadata": {
            "language": "es",
            "intake_mode": "text",
            "timestamp": datetime.now(timezone.utc)
        }
    }
    
    # Missing chief complaint, symptoms, patient_id, etc.
    result = provider.extract(text="Hola.")
    assert result.success is True
    assert isinstance(result.data, IntakeResponse)
    assert result.data.language == "es"
    assert result.data.chief_complaint is None
    assert len(result.data.symptoms) == 0


def test_negated_symptom(provider):
    """Test 3: A structured negated symptom."""
    provider.mock_response = {
        "language": "en",
        "symptoms": [
            {
                "name": "Fever",
                "negated": False
            },
            {
                "name": "Cough",
                "negated": True
            }
        ],
        "metadata": {
            "language": "en",
            "intake_mode": "text",
            "timestamp": datetime.now(timezone.utc)
        }
    }

    result = provider.extract(text="I have fever but no cough.")
    assert result.success is True
    symptoms = result.data.symptoms
    assert len(symptoms) == 2
    fever = next(s for s in symptoms if s.name == "Fever")
    cough = next(s for s in symptoms if s.name == "Cough")
    
    assert fever.negated is False
    assert cough.negated is True


def test_invalid_provider_output(provider):
    """Test 4: Invalid provider output is rejected."""
    # The output is missing required fields like 'language' and 'metadata'
    provider.mock_response = {
        "chief_complaint": {
            "name": "Headache"
        }
    }

    result = provider.extract(text="I have a headache.")
    assert result.success is False
    assert result.data is None
    assert "Validation failed" in result.error


def test_provider_failure(provider):
    """Test 5: Provider failure is handled safely."""
    provider.should_fail = True
    
    result = provider.extract(text="I have a headache.")
    assert result.success is False
    assert result.data is None
    assert "Mock extraction provider failed" in result.error


def test_empty_input(provider):
    """Test 6: Empty or invalid transcript input."""
    result1 = provider.extract(text="")
    assert result1.success is False
    assert "empty or invalid" in result1.error
    
    result2 = provider.extract(text="   ")
    assert result2.success is False
    assert "empty or invalid" in result2.error

    result3 = provider.extract(text=None)
    assert result3.success is False
    assert "empty or invalid" in result3.error
