import type { LanguageCode } from "@/api/types";

export interface LanguageOption {
  code: LanguageCode;
  /** Endonym — what the language calls itself. A patient looking for their
   *  language scans for this, not for the English name. */
  native: string;
  english: string;
  /** Devanagari needs the --font-deva stack and a size bump (tokens.css). */
  script: "latn" | "deva" | "beng" | "taml" | "telu";
  /**
   * A translated dictionary exists for this language.
   *
   * Languages without one are shown but disabled. Offering a language button
   * that silently renders English would be worse than not offering it — a
   * patient who cannot read English has no way back. Adding a language is one
   * dictionary file in src/i18n/dictionaries and flipping this flag.
   */
  translated: boolean;
}

export const LANGUAGES: LanguageOption[] = [
  { code: "hi", native: "हिन्दी", english: "Hindi", script: "deva", translated: true },
  { code: "en", native: "English", english: "English", script: "latn", translated: true },
  { code: "mr", native: "मराठी", english: "Marathi", script: "deva", translated: true },
  { code: "bn", native: "বাংলা", english: "Bengali", script: "beng", translated: false },
  { code: "ta", native: "தமிழ்", english: "Tamil", script: "taml", translated: false },
  { code: "te", native: "తెలుగు", english: "Telugu", script: "telu", translated: false },
];

export const DEFAULT_LANGUAGE: LanguageCode = "en";

export function getLanguage(code: LanguageCode): LanguageOption {
  return LANGUAGES.find((l) => l.code === code) ?? LANGUAGES[1];
}

/** BCP-47 tag for lang attributes, speech synthesis and ASR hints. */
export function bcp47(code: LanguageCode): string {
  const map: Record<LanguageCode, string> = {
    en: "en-IN",
    hi: "hi-IN",
    mr: "mr-IN",
    bn: "bn-IN",
    ta: "ta-IN",
    te: "te-IN",
  };
  return map[code];
}
