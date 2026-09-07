"""Unit tests for the Gemini Clinical Extraction Provider."""

import json
from unittest.mock import MagicMock, patch
import pytest

from ai.intake.gemini_provider import GeminiClinicalExtractionProvider
from ai.intake.schemas import IntakeResponse


@pytest.fixture
def provider():
    """Returns a provider with a mock API key to avoid real calls."""
    with patch("os.getenv", return_value="fake_key"):
        prov = GeminiClinicalExtractionProvider()
        return prov


def test_missing_api_key():
    """Test 8: Missing API key raises ValueError."""
    with patch("os.getenv", return_value=None):
        prov = GeminiClinicalExtractionProvider()
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            # The client property initializes lazily
            _ = prov.client


@patch("google.genai.Client")
def test_empty_transcript(mock_client, provider):
    """Test 9: Empty transcript is handled safely by the base class."""
    # The base class should intercept this before calling _do_extract
    result = provider.extract(text="")
    assert result.success is False
    assert "empty or invalid" in result.error


@patch("ai.intake.gemini_provider.genai.Client")
def test_successful_extraction(mock_client_class, provider):
    """Test 1: Successful extraction."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "language": "en",
        "chief_complaint": {
            "name": "Fever",
            "duration": "three days",
        },
        "symptoms": [
            {"name": "Fever", "duration": "three days"},
            {"name": "Body pain"}
        ],
        "metadata": {
            "language": "en",
            "intake_mode": "transcript",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    })
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text="I have had fever for three days and body pain.")
    assert result.success is True
    assert result.data.chief_complaint.name == "Fever"
    assert result.data.chief_complaint.duration == "three days"
    
    symptoms = [s.name for s in result.data.symptoms]
    assert "Fever" in symptoms
    assert "Body pain" in symptoms


@patch("ai.intake.gemini_provider.genai.Client")
def test_negation(mock_client_class, provider):
    """Test 2: Negation explicitly preserved."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "language": "en",
        "symptoms": [
            {"name": "Fever", "negated": False},
            {"name": "Cough", "negated": True}
        ],
        "metadata": {
            "language": "en",
            "intake_mode": "transcript",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    })
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text="I have fever but no cough.")
    assert result.success is True
    symptoms = result.data.symptoms
    fever = next(s for s in symptoms if s.name == "Fever")
    cough = next(s for s in symptoms if s.name == "Cough")
    
    assert fever.negated is False
    assert cough.negated is True


@patch("ai.intake.gemini_provider.genai.Client")
def test_medication(mock_client_class, provider):
    """Test 3: Medication explicitly extracted."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "language": "en",
        "medications": [
            {"name": "metformin", "dose": "500 mg", "frequency": "every day"}
        ],
        "metadata": {
            "language": "en",
            "intake_mode": "transcript",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    })
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text="I take metformin 500 mg every day.")
    assert result.success is True
    assert len(result.data.medications) == 1
    assert result.data.medications[0].name == "metformin"
    assert result.data.medications[0].dose == "500 mg"


@patch("ai.intake.gemini_provider.genai.Client")
def test_allergy(mock_client_class, provider):
    """Test 4: Allergy explicitly extracted."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "language": "en",
        "allergies": [
            {"substance": "penicillin"}
        ],
        "metadata": {
            "language": "en",
            "intake_mode": "transcript",
            "timestamp": "2023-01-01T00:00:00Z"
        }
    })
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text="I am allergic to penicillin.")
    assert result.success is True
    assert len(result.data.allergies) == 1
    assert result.data.allergies[0].substance == "penicillin"


@patch("ai.intake.gemini_provider.genai.Client")
def test_invalid_gemini_response(mock_client_class, provider):
    """Test 6: Invalid Gemini JSON response."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.text = "This is not json"
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text="Hello")
    assert result.success is False
    assert "Failed to parse Gemini JSON" in result.error


@patch("ai.intake.gemini_provider.genai.Client")
def test_api_failure(mock_client_class, provider):
    """Test 7: Gemini API failure."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.models.generate_content.side_effect = Exception("API down")
    provider._client = mock_client
    
    result = provider.extract(text="Hello")
    assert result.success is False
    assert "Gemini API request failed: API down" in result.error

@patch('ai.intake.gemini_provider.genai.Client')
def test_metadata_fallback(mock_client_class, provider):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = json.dumps({'symptoms': [{'name': 'Fever'}]})
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text='I have fever', language='es', patient_id='pt-123')
    assert result.success is True
    assert result.data.metadata.patient_id == 'pt-123'
    assert result.data.metadata.language == 'es'
    assert result.data.metadata.intake_mode == 'transcript'
    assert result.data.metadata.timestamp is not None

@patch('ai.intake.gemini_provider.genai.Client')
def test_metadata_no_overwrite(mock_client_class, provider):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_response = MagicMock()
    mock_response.text = json.dumps({'symptoms': [{'name': 'Fever'}], 'metadata': {'language': 'fr', 'patient_id': 'pt-999', 'intake_mode': 'voice', 'timestamp': '2020-01-01T00:00:00Z'}})
    mock_client.models.generate_content.return_value = mock_response
    provider._client = mock_client
    
    result = provider.extract(text='I have fever', language='es', patient_id='pt-123')
    assert result.success is True
    assert result.data.metadata.patient_id == 'pt-999'
    assert result.data.metadata.language == 'fr'
    assert result.data.metadata.intake_mode == 'voice'
    assert result.data.metadata.timestamp.year == 2020

