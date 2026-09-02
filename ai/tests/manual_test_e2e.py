import os
import sys

def load_env_safely():
    """Loads environment variables from .env file without external dependencies."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    # Set only if not already present to avoid overriding real env vars
                    if key not in os.environ:
                        os.environ[key] = val

# Pre-load environment before importing providers to ensure they see the API key
load_env_safely()

from ai.pipeline import ClinicalIntakePipeline
from ai.speech.transcription import FasterWhisperProvider
from ai.intake.gemini_provider import GeminiClinicalExtractionProvider

def main():
    if len(sys.argv) < 2:
        print("Usage: python ai/tests/manual_test_e2e.py <path_to_audio_file>")
        sys.exit(1)
        
    audio_path = sys.argv[1]
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)
        
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY is not set in the environment or .env file.")
        sys.exit(1)
        
    print("[*] Initializing providers...")
    # Use small model for better multilingual/code-switching capability
    prompt = (
        "This is a medical conversation in Hinglish, Hindi, and English. "
        "The speaker may switch between Hindi and English within the same sentence. "
        "Accurately transcribe medical symptoms, diseases, medications, body parts, "
        "and clinical terminology. Do not translate or invent words. "
        "Common terms may include fever, headache, cough, cold, body pain, weakness, "
        "throat pain, chest pain, diabetes, blood pressure, allergy, and medicine."
    )
    transcriber = FasterWhisperProvider(model_size="small", compute_type="int8", initial_prompt=prompt)
    extractor = GeminiClinicalExtractionProvider()
    
    pipeline = ClinicalIntakePipeline(transcriber, extractor)
    
    print(f"[*] Starting pipeline on: {audio_path}\n")
    result = pipeline.process_audio(audio_path)
    
    print("-" * 50)
    print("PIPELINE RESULT SUMMARY")
    print("-" * 50)
    
    # Transcription Info
    if result.transcript:
        print("[a] Transcription: SUCCESS\n")
        print(f"[c] Transcript:\n    \"{result.transcript}\"\n")
    else:
        if "Transcription failed" in (result.error or ""):
            print("[a] Transcription: FAILED\n")
            print(f"    Error: {result.error}")
            sys.exit(1)
    
    # Extraction & Language Info
    if result.success and result.data:
        language = result.data.language or "Unknown"
        print(f"[b] Detected Language: {language}\n")
        print("[d] Extraction: SUCCESS\n")
        print("[e] Structured Clinical JSON:")
        print(result.data.model_dump_json(indent=2))
    else:
        print("[d] Extraction: FAILED\n")
        print(f"    Error: {result.error}")

if __name__ == "__main__":
    main()
