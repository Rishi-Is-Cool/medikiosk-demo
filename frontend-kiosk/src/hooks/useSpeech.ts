"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { speechApi } from "@/api/speechApi";
import { useLanguage } from "@/i18n/LanguageProvider";

/* Audio output (build spec §6.9).

   The interface the rest of the app sees is speakQuestion(text). Where the
   audio comes from is this hook's business: a real TTS endpoint when the
   backend has one, and the browser's own synthesis while it does not. No
   screen needs to know which. */

export function useSpeech() {
  const { language, locale } = useLanguage();
  const [speaking, setSpeaking] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  /** Guards against a late-resolving synthesize() for a question the patient
   *  has already moved past — audio must match the question on screen. */
  const requestRef = useRef(0);

  const stop = useCallback(() => {
    requestRef.current += 1;

    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
    setSpeaking(false);
  }, []);

  // Leaving a screen must silence it. Otherwise a question keeps being read
  // aloud over the next one.
  useEffect(() => stop, [stop]);

  const speakQuestion = useCallback(
    async (text: string) => {
      if (!text) return;
      stop();

      const requestId = ++requestRef.current;
      setSpeaking(true);

      try {
        const audioUrl = await speechApi.synthesize(text, language);
        if (requestId !== requestRef.current) return;

        if (audioUrl) {
          const audio = new Audio(audioUrl);
          audioRef.current = audio;
          audio.onended = () => setSpeaking(false);
          audio.onerror = () => setSpeaking(false);
          await audio.play();
          return;
        }
      } catch {
        // Fall through to browser synthesis below — a failed TTS call must
        // not leave the Listen button dead.
        if (requestId !== requestRef.current) return;
      }

      if (typeof window === "undefined" || !("speechSynthesis" in window)) {
        setSpeaking(false);
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = locale;
      utterance.rate = 0.92; // Slightly slow. The audience is elderly and unwell.
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = () => setSpeaking(false);

      const voice = window.speechSynthesis
        .getVoices()
        .find((v) => v.lang === locale || v.lang.startsWith(language));
      if (voice) utterance.voice = voice;

      window.speechSynthesis.speak(utterance);
    },
    [language, locale, stop],
  );

  const supported =
    typeof window !== "undefined" && ("speechSynthesis" in window || process.env.NEXT_PUBLIC_API_BASE_URL != null);

  return { speakQuestion, stop, speaking, supported };
}
