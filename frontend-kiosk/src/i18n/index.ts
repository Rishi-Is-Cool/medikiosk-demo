import type { LanguageCode } from "@/api/types";
import { en, type DictionaryKey, type PartialDictionary } from "./dictionaries/en";
import { hi } from "./dictionaries/hi";

/** Dictionaries that actually exist. A language absent here falls back to
 *  English — and is disabled on the language screen, so no patient reaches
 *  a fallback without having chosen English themselves. */
const DICTIONARIES: Partial<Record<LanguageCode, PartialDictionary>> = {
  en,
  hi,
};

export type Translator = (key: DictionaryKey, vars?: Record<string, string | number>) => string;

export function createTranslator(language: LanguageCode): Translator {
  const dict = DICTIONARIES[language];

  return (key, vars) => {
    const template = dict?.[key] ?? en[key] ?? key;
    if (!vars) return template;
    return template.replace(/\{(\w+)\}/g, (match, name: string) =>
      name in vars ? String(vars[name]) : match,
    );
  };
}

export type { DictionaryKey };

/* --- Localised content coming from the question service --------------------
   Question text is localised by whoever owns the question engine, not by the
   kiosk. During mock development the mock carries both languages in this
   shape and resolves before handing the question to the UI. Once the real
   backend localises server-side, this type disappears from the api layer. */

export type Localized = { en: string } & Partial<Record<LanguageCode, string>>;

export function resolveLocalized(value: Localized, language: LanguageCode): string {
  return value[language] ?? value.en;
}
