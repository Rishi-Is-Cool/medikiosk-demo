"""Manual testing script for the Gemini Clinical Extraction Provider.

Tests the provider with real inputs using the Gemini API.
Requires GEMINI_API_KEY environment variable.
"""

import os
import json
from ai.intake.gemini_provider import GeminiClinicalExtractionProvider

def run_tests():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("="*60)
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("To run this manual test, please set the API key:")
        print("On Windows (PowerShell): $env:GEMINI_API_KEY=\"your_key_here\"")
        print("On Mac/Linux: export GEMINI_API_KEY=\"your_key_here\"")
        print("Then run: python ai/tests/manual_test.py")
        print("="*60)
        return

    provider = GeminiClinicalExtractionProvider()

    test_cases = [
        "I have had fever for three days and body pain.",
        "I have fever but no cough.",
        "My chest hurts when I walk.",
        "I take metformin 500 mg every day and I am allergic to penicillin."
    ]

    print("=== MediKiosk Gemini Clinical Extraction Manual Test ===")
    print(f"Using Model: {provider.model_name}")
    print("="*60)

    for i, test_text in enumerate(test_cases, 1):
        print(f"\n[Test {i}] Input: \"{test_text}\"")
        try:
            result = provider.extract(text=test_text)
            if result.success:
                print("SUCCESS! Validated IntakeResponse:")
                # Print the model dumped to json with indentation
                print(result.data.model_dump_json(indent=2))
            else:
                print("FAILED!")
                print(f"Error: {result.error}")
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
        print("-" * 60)

if __name__ == "__main__":
    run_tests()
