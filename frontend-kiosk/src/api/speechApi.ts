/* Audio in, transcript out — and text in, audio out (build spec §8).

   Whisper, or whatever ASR the team lands on, runs behind this boundary.
   No model, no key and no prompt appears on the client (§19). */

import { ENDPOINTS, MOCK_LATENCY, USE_MOCKS, mockDelay } from "./config";
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
    form.append("audio", payload.audio, "answer.webm");
    form.append("session_id", payload.session_id);
    form.append("question_id", payload.question_id);
    form.append("language", payload.language);

    return request<TranscriptResult>(ENDPOINTS.speech.transcribe, {
      method: "POST",
      body: form,
      timeoutMs: 30000,
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

    const result = await request<{ audio_url: string }>(ENDPOINTS.speech.synthesize, {
      method: "POST",
      body: JSON.stringify({ text, language }),
    });
    return result.audio_url;
  },
};
