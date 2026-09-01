"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { patientApi } from "@/api/patientApi";
import type { ConsentItem } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Icon } from "@/components/Icon";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { VoicePlayer } from "@/components/VoicePlayer";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import type { DictionaryKey } from "@/i18n";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.3 — consent before any clinical information is collected.
 *
 * The items are genuinely granular: declining "voice" removes the microphone
 * from the intake screen, declining "documents" skips the upload step. A
 * consent checkbox that changes nothing is not consent.
 *
 * This screen captures and transmits a decision. It is not, on its own, DPDP
 * 2023 or ABDM consent-framework compliance — that lives in the backend's
 * consent artefact and audit trail, which the project plan scopes as roadmap.
 */

const ITEMS: Array<ConsentItem & { titleKey: DictionaryKey; bodyKey: DictionaryKey }> = [
  { id: "intake", required: true, titleKey: "consent.item.intake.title", bodyKey: "consent.item.intake.body" },
  { id: "share", required: true, titleKey: "consent.item.share.title", bodyKey: "consent.item.share.body" },
  { id: "voice", required: false, titleKey: "consent.item.voice.title", bodyKey: "consent.item.voice.body" },
  { id: "documents", required: false, titleKey: "consent.item.documents.title", bodyKey: "consent.item.documents.body" },
];

export function ConsentScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { patient, dispatch } = usePatientSession();
  const ready = useJourneyGuard("patient");

  // Optional items start on — the patient is opting out, not hunting for
  // switches. Required items are not pre-granted: they are an explicit act.
  const [granted, setGranted] = useState<string[]>(["voice", "documents"]);
  const [audioPlayed, setAudioPlayed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [declined, setDeclined] = useState(false);

  if (!ready) return null;

  const missingRequired = ITEMS.filter((item) => item.required && !granted.includes(item.id));

  const explanation = [t("consent.subtitle"), ...ITEMS.map((i) => `${t(i.titleKey)}. ${t(i.bodyKey)}`)].join(" ");

  function toggle(id: string) {
    setGranted((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id],
    );
  }

  async function accept() {
    if (missingRequired.length > 0 || !patient) return;
    setBusy(true);
    setFailed(false);

    try {
      const receipt = await patientApi.submitConsent({
        session_id: patient.session_id,
        granted,
        declined: ITEMS.filter((i) => !granted.includes(i.id)).map((i) => i.id),
        language,
        audio_explanation_played: audioPlayed,
      });
      dispatch({ type: "setConsent", granted, consentId: receipt.consent_id });
      router.push(ROUTES.mode);
    } catch (error) {
      console.warn("[consent] failed", error);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  /* A patient who declines is not argued with. They are pointed at a human. */
  if (declined) {
    return (
      <KioskScreen step="consent">
        <div className="mk-container mk-container--narrow mk-stack mk-stack--loose mk-center">
          <span className="mk-bigicon" data-tone="info">
            <Icon name="hand" size={48} />
          </span>
          <h1 className="mk-h1">{t("consent.declinedTitle")}</h1>
          <p className="mk-lead">{t("consent.declinedBody")}</p>
          <button
            type="button"
            className="mk-btn mk-btn--secondary mk-btn--lg"
            onClick={() => setDeclined(false)}
          >
            <Icon name="chevronLeft" />
            {t("common.back")}
          </button>
        </div>
      </KioskScreen>
    );
  }

  return (
    <KioskScreen
      step="consent"
      align="top"
      actions={
        <>
          <BackButton onClick={() => router.push(ROUTES.register)} label={t("common.back")} />
          <button type="button" className="mk-btn mk-btn--ghost" onClick={() => setDeclined(true)}>
            {t("consent.declineAll")}
          </button>
          <div className="mk-actionbar__spacer" />
          {missingRequired.length > 0 && <span className="mk-help">{t("consent.blocked")}</span>}
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--lg"
            disabled={missingRequired.length > 0 || busy}
            onClick={accept}
          >
            <Icon name="check" />
            {t("consent.agree")}
          </button>
        </>
      }
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight">
          <h1 className="mk-h1">{t("consent.title")}</h1>
          <p className="mk-lead">{t("consent.subtitle")}</p>
          <div className="mk-row">
            <VoicePlayer
              text={explanation}
              label={t("consent.listen")}
              onPlay={() => setAudioPlayed(true)}
            />
          </div>
        </div>

        {busy ? (
          <ProcessingState label={t("common.pleaseWait")} />
        ) : (
          <ul className="mk-stack mk-stack--tight">
            {ITEMS.map((item) => {
              const on = granted.includes(item.id);
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className="mk-consent"
                    data-selected={on}
                    aria-pressed={on}
                    onClick={() => toggle(item.id)}
                  >
                    <span className="mk-consent__check" aria-hidden="true">
                      <Icon name="check" size={22} strokeWidth={3} />
                    </span>
                    <span className="mk-consent__body">
                      <span className="mk-consent__title">
                        {t(item.titleKey)}
                        <span className={item.required ? "mk-pill mk-pill--warning" : "mk-pill"}>
                          {item.required ? t("consent.required") : t("consent.optional")}
                        </span>
                      </span>
                      <span className="mk-consent__text">{t(item.bodyKey)}</span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        {failed && <ErrorState title={t("error.title")} message={t("error.generic")} />}
      </div>
    </KioskScreen>
  );
}
