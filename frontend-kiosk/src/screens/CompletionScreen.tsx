"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { intakeApi } from "@/api/intakeApi";
import type { QueueInfo } from "@/api/types";
import { Icon } from "@/components/Icon";
import { KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { VoicePlayer } from "@/components/VoicePlayer";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/** Seconds before the kiosk clears itself. Long enough to note the token and
 *  read the next steps, short enough that a patient who walks away does not
 *  leave their session on screen for the next person. */
const AUTO_CLEAR_SECONDS = 60;

/** Token times are shown in hospital time, whatever the kiosk's clock says. */
const HOSPITAL_TIME_ZONE = "Asia/Kolkata";

/**
 * Build spec §6.14 and Module D's session-termination requirement.
 *
 * The token number is the one thing shown: the patient needs it to be called,
 * and on its own it identifies nobody. No session ids and no summary of what
 * was extracted — a public screen in a foyer shows nothing that the person
 * behind them should not see. The token and the count ahead come from the
 * backend, counted live against the day's queue.
 */
export function CompletionScreen() {
  const router = useRouter();
  const { t, locale } = useLanguage();
  const { patient, reset } = usePatientSession();
  const ready = useJourneyGuard("patient");
  const [remaining, setRemaining] = useState(AUTO_CLEAR_SECONDS);
  const [queue, setQueue] = useState<QueueInfo | null>(null);
  const [queueFailed, setQueueFailed] = useState(false);

  const finish = useCallback(() => {
    if (patient) intakeApi.clearMockSession(patient.session_id);
    reset();
    router.push(ROUTES.start);
  }, [patient, reset, router]);

  useEffect(() => {
    if (!ready || !patient) return;
    let cancelled = false;
    intakeApi
      .getQueue(patient.session_id)
      .then((result) => {
        if (!cancelled) setQueue(result);
      })
      .catch((error) => {
        console.warn("[complete] token unavailable", error);
        if (!cancelled) setQueueFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [ready, patient]);

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

  const ahead = queue
    ? queue.patients_ahead === 0
      ? t("complete.aheadNone")
      : queue.patients_ahead === 1
        ? t("complete.aheadOne")
        : t("complete.ahead", { count: queue.patients_ahead })
    : "";
  const issued = queue
    ? new Intl.DateTimeFormat(locale, {
        timeZone: HOSPITAL_TIME_ZONE,
        weekday: "short",
        day: "numeric",
        month: "short",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(queue.issued_at))
    : "";
  const tokenSpeech = queue ? `${t("complete.tokenSpeech", { token: queue.token })} ${ahead}. ` : "";

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

        <div className="mk-token" aria-live="polite">
          {queue ? (
            <>
              <span className="mk-label">{t("complete.tokenLabel")}</span>
              <span className="mk-token__number mk-num">{queue.token}</span>
              {queue.doctor_name && (
                <span className="mk-lead">
                  {queue.doctor_name}
                  {queue.department ? ` · ${queue.department}` : ""}
                </span>
              )}
              <span className="mk-token__ahead">{ahead}</span>
              <span className="mk-meta">{t("complete.issuedAt", { time: issued })}</span>
            </>
          ) : queueFailed ? (
            <p className="mk-lead">{t("complete.tokenUnavailable")}</p>
          ) : (
            <ProcessingState label={t("common.pleaseWait")} />
          )}
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
          {/* Reads the token out once it arrives, in the patient's language. */}
          <VoicePlayer
            text={`${tokenSpeech}${t("complete.title")}. ${t("complete.body")} ${steps.join(". ")}`}
            autoPlayKey={queue ? `token-${queue.token}` : undefined}
          />
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
