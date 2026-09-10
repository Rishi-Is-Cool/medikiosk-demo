"use client";

import { useRouter } from "next/navigation";
import type { HistoryMode } from "@/api/types";
import { ChoiceTile } from "@/components/ChoiceTile";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { speakChoice } from "@/hooks/useSpeech";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.4 — the seam where a history framework is chosen.
 *
 * Both frameworks are live. The choice travels to the question service as
 * `history_mode`, and the service decides what to ask; this screen does not
 * know what a Dashavidha Pariksha is, and the question components below it
 * do not either. That is what "framework-agnostic" was supposed to buy, and
 * it is why turning AYUSH on was a question-bank change rather than a rewrite.
 */
export function ConsultationTypeScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { dispatch } = usePatientSession();
  const ready = useJourneyGuard("consent");

  if (!ready) return null;

  const choose = (mode: HistoryMode, label: string) => {
    speakChoice(label, language);
    dispatch({ type: "setHistoryMode", mode });
    router.push(ROUTES.complaint);
  };

  return (
    <KioskScreen
      step="complaint"
      actions={<BackButton onClick={() => router.push(ROUTES.consent)} label={t("common.back")} />}
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight mk-center">
          <h1 className="mk-h1">{t("mode.title")}</h1>
          <p className="mk-lead">{t("mode.subtitle")}</p>
        </div>

        <div className="mk-choices mk-choices--wide">
          <ChoiceTile
            icon="stethoscope"
            label={t("mode.general")}
            sub={t("mode.generalSub")}
            showCheck={false}
            onClick={() => choose("general_medicine", t("mode.general"))}
          />
          <ChoiceTile
            icon="leaf"
            label={t("mode.ayush")}
            sub={t("mode.ayushSub")}
            showCheck={false}
            onClick={() => choose("ayush", t("mode.ayush"))}
          />
        </div>

        {/* Said before the choice, not after it. The Ayurveda interview is
            three times longer, and a patient who was not warned will assume
            something has gone wrong around question twenty. */}
        <p className="mk-meta mk-center">{t("mode.ayushNote")}</p>
      </div>
    </KioskScreen>
  );
}
