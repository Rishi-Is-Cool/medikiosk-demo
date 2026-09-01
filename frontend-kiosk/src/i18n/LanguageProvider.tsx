"use client";

import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";
import type { LanguageCode } from "@/api/types";
import { createTranslator, type Translator } from "./index";
import { bcp47, getLanguage, type LanguageOption } from "./languages";

interface LanguageContextValue {
  language: LanguageCode;
  option: LanguageOption;
  locale: string;
  t: Translator;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({
  language,
  children,
}: {
  language: LanguageCode;
  children: ReactNode;
}) {
  const value = useMemo<LanguageContextValue>(
    () => ({
      language,
      option: getLanguage(language),
      locale: bcp47(language),
      t: createTranslator(language),
    }),
    [language],
  );

  // Keeps <html lang> honest, which is what screen readers and the browser's
  // own speech synthesis read to pick a voice.
  useEffect(() => {
    document.documentElement.lang = value.locale;
  }, [value.locale]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used inside a LanguageProvider");
  return ctx;
}

/** Convenience for the common case. */
export function useT(): Translator {
  return useLanguage().t;
}
