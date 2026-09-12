/* Audio in, transcript out — and text in, audio out (build spec §8).

   Whisper runs behind this boundary, on the backend. No model, no key and no
   prompt appears on the client (§19). */

import { ENDPOINTS, KIOSK_BACKEND_ORIGIN, MOCK_LATENCY, USE_MOCKS, mockDelay } from "./config";
import { request } from "./http";
import { FORCE_SPEECH_FAILURE, mockTranscript } from "@/mocks/transcripts";
import { ApiError, type LanguageCode, type TranscriptResult } from "./types";

export interface TranscribeRequest {
  session_id: string;
  question_id: string;
  language: LanguageCode;
  audio: Blob;
  duration_ms: number;
}

/** MediaRecorder hands back webm on Chrome, ogg on Firefox and mp4 on
 *  Safari; the file name tells the decoder which one it is getting. */
function audioFileName(blob: Blob): string {
  const type = blob.type.toLowerCase();
  if (type.includes("ogg")) return "answer.ogg";
  if (type.includes("mp4") || type.includes("aac")) return "answer.m4a";
  if (type.includes("wav")) return "answer.wav";
  return "answer.webm";
}

export const speechApi = {
  async transcribe(payload: TranscribeRequest): Promise<TranscriptResult> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.slow);

      if (FORCE_SPEECH_FAILURE) {
        throw new ApiError("speech_failed", "Mock speech failure (NEXT_PUBLIC_MOCK_SPEECH_FAILS)");
      }

      // A recording this short is almost always a misfire — the patient
      // touched the button and let go. The real service will reject it too.
      if (payload.duration_ms < 700) {
        throw new ApiError("speech_too_short", "Recording too short to transcribe");
      }

      return {
        transcript: mockTranscript(payload.question_id, payload.language),
        language: payload.language,
        confidence: 0.93,
        duration_ms: payload.duration_ms,
      };
    }

    const form = new FormData();
    form.append("audio", payload.audio, audioFileName(payload.audio));
    form.append("session_id", payload.session_id);
    form.append("question_id", payload.question_id);
    form.append("language", payload.language);
    form.append("duration_ms", String(Math.round(payload.duration_ms)));

    // Direct call to FastAPI backend to bypass Next.js 30-second rewrite proxy timeout
    // Whisper Medium on CPU can take 30-60+ seconds.
    const directUrl = `${KIOSK_BACKEND_ORIGIN}${ENDPOINTS.speech.transcribe}`;
    return request<TranscriptResult>(directUrl, {
      method: "POST",
      body: form,
      timeoutMs: 90000,
    });
  },

  /**
   * Text to speech for questions and instructions (build spec §6.9).
   *
   * Returns an audio URL when a TTS service exists. Returning null is a valid
   * answer meaning "no server audio available" — the caller then falls back to
   * the browser's own speech synthesis, which is what happens in mock mode.
   */
  async synthesize(text: string, language: LanguageCode): Promise<string | null> {
    if (USE_MOCKS) {
      return null;
    }

    const result = await request<{ audio_url: string | null }>(ENDPOINTS.speech.synthesize, {
      method: "POST",
      body: JSON.stringify({ text, language }),
    });
    return result.audio_url;
  },
};
