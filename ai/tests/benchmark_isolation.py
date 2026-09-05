import os
import sys
import time
import statistics

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

from ai.speech.transcription import FasterWhisperProvider
from ai.intake.gemini_provider import GeminiClinicalExtractionProvider

def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Sanjana\.gemini\antigravity-ide\scratch\MediKiosk\shivani-audio.ogg"
    
    if not os.path.exists(audio_path):
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)

    prompt = (
        "This is a medical conversation in Hinglish, Hindi, and English. "
        "The speaker may switch between Hindi and English within the same sentence. "
        "Accurately transcribe medical symptoms, diseases, medications, body parts, "
        "and clinical terminology. Do not translate or invent words. "
        "Common terms may include fever, headache, cough, cold, body pain, weakness, "
        "throat pain, chest pain, diabetes, blood pressure, allergy, and medicine."
    )

    print("==========================================")
    print("      FASTER-WHISPER BENCHMARK            ")
    print("==========================================\n")

    transcripts = {}

    for model_size in ["small", "medium"]:
        print(f"--- Benchmarking model: {model_size} ---")
        
        t0 = time.time()
        transcriber = FasterWhisperProvider(model_size=model_size, compute_type="int8", initial_prompt=prompt)
        t_init = time.time() - t0
        
        t0 = time.time()
        res = transcriber.transcribe(audio_path)
        t_transcribe = time.time() - t0
        
        dur = res.duration_seconds if res.duration_seconds else 1.0
        rtf = t_transcribe / dur
        
        print(f"Audio Duration:      {dur:.2f} s")
        print(f"Initialization:      {t_init:.2f} s")
        print(f"Transcription Time:  {t_transcribe:.2f} s")
        print(f"Real-Time Factor:    {rtf:.2f}")
        print(f"Transcript excerpt:  {res.text[:100]}...\n")
        
        if model_size == "medium":
            transcripts['medium'] = res.text

    print("==========================================")
    print("         GEMINI API BENCHMARK             ")
    print("==========================================\n")

    extractor = GeminiClinicalExtractionProvider()
    transcript_text = transcripts.get('medium', "Patient complains of fever and headache since yesterday.")
    
    extraction_times = []
    print("Running 5 extraction iterations...")
    for i in range(5):
        t0 = time.time()
        extractor.extract(text=transcript_text, language="hi")
        t_ex = time.time() - t0
        extraction_times.append(t_ex)
        print(f"Iteration {i+1}: {t_ex:.2f} s")
        
    avg_ex = statistics.mean(extraction_times)
    min_ex = min(extraction_times)
    max_ex = max(extraction_times)
    
    print(f"\nExtraction Min: {min_ex:.2f} s")
    print(f"Extraction Max: {max_ex:.2f} s")
    print(f"Extraction Avg: {avg_ex:.2f} s")

if __name__ == '__main__':
    main()
