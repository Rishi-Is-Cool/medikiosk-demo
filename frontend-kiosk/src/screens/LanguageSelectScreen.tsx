"use client";

import { useRouter } from "next/navigation";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ChoiceTile } from "@/components/ChoiceTile";
import { usePatientSession } from "@/context/PatientSession";
import { useLanguage } from "@/i18n/LanguageProvider";
import { LANGUAGES } from "@/i18n/languages";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.1. Shown in every language at once — a patient who cannot
 * read the current UI language must still be able to find their own, so each
 * tile is labelled with the endonym and nothing else needs translating.
 */
export function LanguageSelectScreen() {
  const router = useRouter();
  const { dispatch } = usePatientSession();
  const { t, language } = useLanguage();

  const available = LANGUAGES.filter((l) => l.translated);
  const pending = LANGUAGES.filter((l) => !l.translated);

  return (
    <KioskScreen
      step="language"
      align="top"
      actions={<BackButton onClick={() => router.push(ROUTES.start)} label={t("common.back")} />}
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight mk-center">
          <h1 className="mk-h1">{t("language.title")}</h1>
          <p className="mk-lead">{t("language.subtitle")}</p>
        </div>

        <div className="mk-choices mk-choices--wide">
          {available.map((option) => (
            <ChoiceTile
              key={option.code}
              label={option.native}
              sub={option.english}
              lang={option.code}
              selected={option.code === language}
              showCheck={false}
              onClick={() => {
                dispatch({ type: "setLanguage", language: option.code });
                router.push(ROUTES.register);
              }}
            />
          ))}
        </div>

        {pending.length > 0 && (
          <div className="mk-stack mk-stack--tight">
            <p className="mk-meta">{t("language.moreLanguages")}</p>
            <div className="mk-choices mk-choices--wide">
              {pending.map((option) => (
                <ChoiceTile
                  key={option.code}
                  label={option.native}
                  sub={option.english}
                  lang={option.code}
                  disabled
                  showCheck={false}
                  badge={<span className="mk-pill">{t("language.comingSoon")}</span>}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </KioskScreen>
  );
}
