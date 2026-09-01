"use client";

import { useRouter } from "next/navigation";
import { ChoiceTile } from "@/components/ChoiceTile";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.4 — the seam where a history framework is chosen.
 *
 * The project plan explicitly does NOT build AYUSH/Dashavidha Pariksha for
 * the demo, so it is present here as a disabled stub and nothing more. The
 * question components below it are framework-agnostic: they render whatever
 * the engine sends, so plugging in a Dashavidha question set later is a
 * server-side change, not a rewrite of this app.
 */
export function ConsultationTypeScreen() {
  const router = useRouter();
  const { t } = useLanguage();
  const { dispatch } = usePatientSession();
  const ready = useJourneyGuard("consent");

  if (!ready) return null;

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
            onClick={() => {
              dispatch({ type: "setHistoryMode", mode: "general_medicine" });
              router.push(ROUTES.complaint);
            }}
          />
          <ChoiceTile
            icon="leaf"
            label={t("mode.ayush")}
            sub={t("mode.ayushSub")}
            disabled
            showCheck={false}
            badge={<span className="mk-pill">{t("language.comingSoon")}</span>}
          />
        </div>

        <p className="mk-meta mk-center">{t("mode.ayushUnavailable")}</p>
      </div>
    </KioskScreen>
  );
}
