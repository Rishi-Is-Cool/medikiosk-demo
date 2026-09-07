import os
import sys
import time

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

from faster_whisper import WhisperModel

def main():
    audio_path = r"C:\Users\Sanjana\.gemini\antigravity-ide\scratch\MediKiosk\shivani-audio.ogg"
    
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
    print("  FASTER-WHISPER COMPUTE TYPE TEST (CPU)  ")
    print("==========================================\n")

    for c_type in ["int8", "float32"]:
        print(f"--- Benchmarking compute_type: {c_type} ---")
        t0 = time.time()
        model = WhisperModel("medium", device="cpu", compute_type=c_type)
        t_init = time.time() - t0
        
        t0 = time.time()
        segments, info = model.transcribe(
            audio_path,
            beam_size=5,
            initial_prompt=prompt,
            vad_filter=True,
        )
        
        full_text = " ".join(segment.text.strip() for segment in segments).strip()
        t_transcribe = time.time() - t0
        dur = info.duration if info.duration else 62.99
        rtf = t_transcribe / dur
        
        print(f"Audio Duration:      {dur:.2f} s")
        print(f"Initialization:      {t_init:.2f} s")
        print(f"Transcription Time:  {t_transcribe:.2f} s")
        print(f"Real-Time Factor:    {rtf:.2f}")
        print(f"Full Transcript:\n{full_text}\n")
        print("-" * 50)

if __name__ == '__main__':
    main()
