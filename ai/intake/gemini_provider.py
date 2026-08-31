"""Gemini-based Clinical Information Extraction Provider for MediKiosk."""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from ai.intake.provider import ClinicalExtractionProvider
from ai.intake.schemas import IntakeResponse


class GeminiClinicalExtractionProvider(ClinicalExtractionProvider):
    """Concrete extraction provider using Google's Gemini LLMs."""

    # Default model suitable for fast structured extraction
    DEFAULT_MODEL = "gemini-3.6-flash"

    # Core instruction enforcing strict extraction bounds
    SYSTEM_INSTRUCTION = (
        "You are a clinical information extraction system. "
        "Your task is to extract structured clinical information exclusively from the patient's explicitly stated words.\n"
        "RULES:\n"
        "1. Extract ONLY information explicitly stated by the patient.\n"
        "2. DO NOT diagnose diseases, infer conditions from symptoms, recommend treatment, or prescribe medication.\n"
        "3. DO NOT invent or guess symptoms, duration, severity, or missing information.\n"
        "4. Preserve negations explicitly (e.g., if a patient says 'I have no cough', include 'cough' in symptoms with negated=True).\n"
        "5. Leave fields empty/null if the information is not explicitly provided.\n"
        "6. Do not perform emergency/red-flag classification.\n"
        "7. Format your response strictly according to the provided JSON schema."
    )

    def __init__(self, api_key: Optional[str] = None, model_name: str = DEFAULT_MODEL):
        """Initialize the Gemini extraction provider.

        Args:
            api_key: Optional API key. If not provided, reads from GEMINI_API_KEY environment variable.
            model_name: The Gemini model to use. Defaults to gemini-2.5-flash.
        """
        self.model_name = model_name
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        
        # Don't initialize client yet, to fail gracefully only when called
        self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set and no api_key was provided.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _do_extract(
        self,
        text: str,
        language: Optional[str] = None,
        patient_id: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Perform extraction using Gemini API and return raw JSON dict."""
        
        # Construct the prompt
        prompt = f"Patient transcript:\n{text}"
        if language:
            prompt += f"\n\nContext: The patient is speaking in {language}."

        # Configure the request to return strictly JSON matching IntakeResponse
        config = types.GenerateContentConfig(
            system_instruction=self.SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=IntakeResponse,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config,
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API request failed: {str(e)}")

        if not response.text:
            raise RuntimeError("Gemini API returned an empty response.")

        try:
            raw_dict = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Gemini JSON response: {str(e)}")
            
        # Inject metadata if not properly populated by the model
        if "metadata" not in raw_dict or not raw_dict["metadata"]:
            raw_dict["metadata"] = {}
        
        metadata = raw_dict["metadata"]
        if "patient_id" not in metadata or not metadata["patient_id"]:
            metadata["patient_id"] = patient_id
        if "language" not in metadata or not metadata["language"]:
            metadata["language"] = language or "unknown"
        if "intake_mode" not in metadata or not metadata["intake_mode"]:
            metadata["intake_mode"] = "transcript"
        if "timestamp" not in metadata or not metadata["timestamp"]:
            metadata["timestamp"] = datetime.now(timezone.utc).isoformat()
            
        # Ensure top-level fields match metadata if missing
        if "patient_id" not in raw_dict or not raw_dict["patient_id"]:
            raw_dict["patient_id"] = patient_id
        if "language" not in raw_dict or not raw_dict["language"]:
            raw_dict["language"] = language or "unknown"

        return raw_dict
