import os
import sys

def load_env_safely():
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = val

load_env_safely()

from ai.pipeline import ClinicalIntakePipeline
from ai.speech.transcription import FasterWhisperProvider
from ai.intake.gemini_provider import GeminiClinicalExtractionProvider
import time

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
    t_start_e2e = time.time()
    
    prompt = (
        "This is a medical conversation in Hinglish, Hindi, and English. "
        "The speaker may switch between Hindi and English within the same sentence. "
        "Accurately transcribe medical symptoms, diseases, medications, body parts, "
        "and clinical terminology. Do not translate or invent words. "
        "Common terms may include fever, headache, cough, cold, body pain, weakness, "
        "throat pain, chest pain, diabetes, blood pressure, allergy, and medicine."
    )
    
    t0 = time.time()
    transcriber = FasterWhisperProvider(model_size="medium", compute_type="int8", initial_prompt=prompt)
    t_init = time.time() - t0
    
    extractor = GeminiClinicalExtractionProvider()
    
    print(f"[*] Compute Config: Device={transcriber._device}, ComputeType={transcriber._compute_type}")
    print(f"[*] Starting pipeline on: {audio_path}\n")
    
    t0 = time.time()
    transcription = transcriber.transcribe(audio_path)
    t_transcribe = time.time() - t0
    
    if not transcription or not transcription.success:
        print(f"[a] Transcription: FAILED\n    Error: {transcription.error}")
        sys.exit(1)
        
    transcript_text = transcription.text.strip() if transcription.text else ""
    
    t0 = time.time()
    extraction = extractor.extract(text=transcript_text, language=transcription.language)
    t_extract = time.time() - t0
    
    t_total_e2e = time.time() - t_start_e2e
    
    audio_duration = transcription.duration_seconds if transcription.duration_seconds else 0.0

    print("-" * 50)
    print("PIPELINE RESULT SUMMARY")
    print("-" * 50)
    print(f"[c] Transcript:\n    \"{transcript_text}\"\n")
    
    if extraction.success and extraction.data:
        print("[e] Structured Clinical JSON:")
        print(extraction.data.model_dump_json(indent=2))
        
    print("-" * 50)
    print("PERFORMANCE METRICS")
    print("-" * 50)
    print(f"Audio duration:       {audio_duration} seconds")
    print(f"Model initialization: {t_init:.2f} seconds")
    print(f"Transcription:        {t_transcribe:.2f} seconds")
    print(f"Extraction:           {t_extract:.2f} seconds")
    print(f"Total pipeline time:  {t_total_e2e:.2f} seconds")
    if audio_duration > 0:
        rtf = t_transcribe / audio_duration
        print(f"Real-time factor:     {rtf:.2f}")
    else:
        print("Real-time factor:     Unknown")

if __name__ == '__main__':
    main()
