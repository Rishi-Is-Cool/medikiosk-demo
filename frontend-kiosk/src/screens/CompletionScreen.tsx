"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { intakeApi } from "@/api/intakeApi";
import { Icon } from "@/components/Icon";
import { KioskScreen } from "@/components/KioskScreen";
import { VoicePlayer } from "@/components/VoicePlayer";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/** Seconds before the kiosk clears itself. Long enough to read the next
 *  steps, short enough that a patient who walks away does not leave their
 *  session on screen for the next person. */
const AUTO_CLEAR_SECONDS = 45;

/**
 * Build spec §6.14 and Module D's session-termination requirement.
 *
 * No token numbers, no session ids, no summary of what was extracted — a
 * public screen in a foyer shows the patient they are finished and nothing
 * that the person behind them should not see.
 */
export function CompletionScreen() {
  const router = useRouter();
  const { t } = useLanguage();
  const { patient, reset } = usePatientSession();
  const ready = useJourneyGuard("patient");
  const [remaining, setRemaining] = useState(AUTO_CLEAR_SECONDS);

  const finish = useCallback(() => {
    if (patient) intakeApi.clearMockSession(patient.session_id);
    reset();
    router.push(ROUTES.start);
  }, [patient, reset, router]);

  useEffect(() => {
    if (!ready) return;
    const timer = setInterval(() => setRemaining((value) => value - 1), 1000);
    return () => clearInterval(timer);
  }, [ready]);

  useEffect(() => {
    if (remaining <= 0) finish();
  }, [remaining, finish]);

  if (!ready) return null;

  const steps = [t("complete.next1"), t("complete.next2"), t("complete.next3")];

  return (
    <KioskScreen step="done">
      <div className="mk-container mk-container--narrow mk-stack mk-stack--loose mk-center">
        <span className="mk-bigicon" data-tone="success">
          <Icon name="check" size={52} strokeWidth={2.5} />
        </span>

        <div className="mk-stack mk-stack--tight">
          <h1 className="mk-display">{t("complete.title")}</h1>
          <p className="mk-lead">{t("complete.body")}</p>
        </div>

        <div className="mk-card mk-stack mk-stack--tight mk-complete__next">
          <span className="mk-label">{t("complete.next")}</span>
          <ol className="mk-steplist">
            {steps.map((step, index) => (
              <li key={step} className="mk-steplist__item">
                <span className="mk-steplist__num mk-num">{index + 1}</span>
                {step}
              </li>
            ))}
          </ol>
        </div>

        <div className="mk-row mk-row--wrap mk-complete__actions">
          <VoicePlayer text={`${t("complete.title")}. ${t("complete.body")} ${steps.join(". ")}`} />
          <button type="button" className="mk-btn mk-btn--primary mk-btn--lg" onClick={finish}>
            {t("complete.finish")}
          </button>
        </div>

        <p className="mk-meta">
          {t("complete.autoClear")} · <span className="mk-num">{Math.max(0, remaining)}s</span>
        </p>
      </div>
    </KioskScreen>
  );
}
