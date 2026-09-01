"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { speechApi } from "@/api/speechApi";
import { useLanguage } from "@/i18n/LanguageProvider";

/* Audio output (build spec §6.9).

   The interface the rest of the app sees is speakQuestion(text). Where the
   audio comes from is this hook's business: a real TTS endpoint when the
   backend has one, and the browser's own synthesis while it does not. No
   screen needs to know which. */

function getAvailableVoices(): Promise<SpeechSynthesisVoice[]> {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return Promise.resolve([]);
  const immediate = window.speechSynthesis.getVoices();
  if (immediate.length > 0) return Promise.resolve(immediate);

  return new Promise((resolve) => {
    let resolved = false;
    const onVoicesChanged = () => {
      if (!resolved) {
        resolved = true;
        window.speechSynthesis.removeEventListener("voiceschanged", onVoicesChanged);
        resolve(window.speechSynthesis.getVoices());
      }
    };
    window.speechSynthesis.addEventListener("voiceschanged", onVoicesChanged);
    setTimeout(() => {
      if (!resolved) {
        resolved = true;
        window.speechSynthesis.removeEventListener("voiceschanged", onVoicesChanged);
        resolve(window.speechSynthesis.getVoices());
      }
    }, 300);
  });
}

function findVoice(
  voices: SpeechSynthesisVoice[],
  language: string,
  locale: string,
): { voice: SpeechSynthesisVoice | undefined; lang: string } {
  const normLoc = locale.toLowerCase().replace("_", "-");
  const normLang = language.toLowerCase();

  // 1. Exact locale match (e.g. mr-IN, mr_IN, hi-IN, en-IN)
  let match = voices.find((v) => v.lang.toLowerCase().replace("_", "-") === normLoc);
  if (match) return { voice: match, lang: match.lang || locale };

  // 2. Language prefix match (e.g. mr, hi, en)
  match = voices.find((v) => v.lang.toLowerCase().replace("_", "-").startsWith(normLang));
  if (match) return { voice: match, lang: match.lang || locale };

  // 3. Name match for regional language
  if (normLang === "mr") {
    match = voices.find((v) => {
      const name = v.name.toLowerCase();
      return name.includes("marathi") || name.includes("मराठी");
    });
    if (match) return { voice: match, lang: match.lang || locale };
  }

  // 4. Graceful script-level fallback:
  // If the patient chose Marathi (Devanagari script) and the device/browser provides no native
  // Marathi voice, fall back to an available Indian Devanagari voice (e.g. Hindi hi-IN) to produce
  // audible speech rather than failing silently.
  if (normLang === "mr") {
    const devanagariVoice = voices.find((v) => {
      const l = v.lang.toLowerCase().replace("_", "-");
      return l === "hi-in" || l.startsWith("hi") || v.name.toLowerCase().includes("hindi");
    });
    if (devanagariVoice) {
      return { voice: devanagariVoice, lang: devanagariVoice.lang || "hi-IN" };
    }
  }

  return { voice: undefined, lang: locale };
}

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

  // Leaving a screen or changing language must silence speech. Otherwise a question keeps
  // being read aloud over the next one or in the old language.
  //
  // Both halves matter, and they are not the same event. Calling stop() on a
  // language change silences a question mid-sentence in the old language;
  // returning it as cleanup silences one that is still playing when the screen
  // unmounts. Without the cleanup, a "Listen" press on a screen that does not
  // auto-read — consent, completion — keeps talking over whatever comes next,
  // because VoicePlayer only registers its own cleanup when autoPlayKey is set.
  useEffect(() => {
    stop();
    return stop;
  }, [language, stop]);

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

      const voices = await getAvailableVoices();
      if (requestId !== requestRef.current) return;

      const { voice, lang } = findVoice(voices, language, locale);

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = 0.92; // Slightly slow. The audience is elderly and unwell.
      utterance.onend = () => setSpeaking(false);
      utterance.onerror = (event) => {
        console.warn("[speech] synthesis error", event.error);
        setSpeaking(false);
      };

      if (voice) utterance.voice = voice;

      window.speechSynthesis.speak(utterance);
    },
    [language, locale, stop],
  );

  const supported =
    typeof window !== "undefined" && ("speechSynthesis" in window || process.env.NEXT_PUBLIC_API_BASE_URL != null);

  return { speakQuestion, stop, speaking, supported };
}
