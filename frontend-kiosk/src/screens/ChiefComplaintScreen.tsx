"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { intakeApi } from "@/api/intakeApi";
import type { ChiefComplaintOption } from "@/api/types";
import { ChoiceTile } from "@/components/ChoiceTile";
import { ErrorState } from "@/components/ErrorState";
import { Icon, type IconName } from "@/components/Icon";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { SourceChip } from "@/components/SourceChip";
import { TextAnswer } from "@/components/TextAnswer";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.5, and the problem statement's own opening move.
 *
 * The complaint list comes from the question service, not from a constant in
 * this file. And the patient can simply say what is wrong — the problem
 * statement's example starts with the patient *stating* "chest pain" and the
 * engine probing from there, so this screen carries a microphone like every
 * question screen does. Which words mean which complaint is the question
 * service's decision; an unmatched answer is kept as free text rather than
 * thrown away, because the patient still said something true.
 */
export function ChiefComplaintScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { patient, consentGranted, dispatch } = usePatientSession();
  const ready = useJourneyGuard("consent");

  const [options, setOptions] = useState<ChiefComplaintOption[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [freeText, setFreeText] = useState("");
  const [showOther, setShowOther] = useState(false);
  const [spoken, setSpoken] = useState<string | null>(null);

  const voiceAllowed = consentGranted.includes("voice");

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;

    intakeApi
      .getComplaints(language)
      .then((result) => {
        if (!cancelled) setOptions(result);
      })
      .catch((error) => {
        console.warn("[complaints] failed", error);
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [ready, language]);

  const choose = useCallback(
    (id: string, label: string, text?: string) => {
      dispatch({ type: "setComplaint", complaint: { id, label, text } });
      router.push(ROUTES.intake);
    },
    [dispatch, router],
  );

  /* A spoken complaint goes to the question service to be matched. A hit
     starts that complaint's line of questioning; a miss keeps the words. */
  const handleSpoken = useCallback(
    async (transcript: string) => {
      try {
        const match = await intakeApi.matchComplaint(transcript, language);
        if (match.complaint) {
          choose(match.complaint.id, match.complaint.label, transcript);
          return;
        }
      } catch (error) {
        console.warn("[complaints] match failed", error);
      }
      // Unmatched, or the matcher is unavailable: show what we heard and let
      // the patient pick the closest, or carry on in their own words.
      setSpoken(transcript);
    },
    [language, choose],
  );

  if (!ready) return null;

  return (
    <KioskScreen
      step="complaint"
      align="top"
      actions={
        <BackButton
          onClick={() => {
            if (spoken) return setSpoken(null);
            if (showOther) return setShowOther(false);
            router.push(ROUTES.mode);
          }}
          label={t("common.back")}
        />
      }
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight mk-center">
          <h1 className="mk-h1">{t("complaint.title")}</h1>
          <p className="mk-lead">{t("complaint.subtitle")}</p>
        </div>

        {failed && <ErrorState title={t("error.title")} message={t("error.offline")} />}

        {!options && !failed && <ProcessingState label={t("common.pleaseWait")} />}

        {spoken && (
          <div className="mk-transcript">
            <div className="mk-row mk-transcript__head">
              <span className="mk-label">{t("complaint.heard")}</span>
              <SourceChip source="patient_spoken" />
            </div>
            <p className="mk-transcript__text">{spoken}</p>
            <p className="mk-help">{t("complaint.noMatch")}</p>
            <button
              type="button"
              className="mk-btn mk-btn--secondary"
              onClick={() => choose("other", t("complaint.other"), spoken)}
            >
              <Icon name="chevronRight" />
              {t("complaint.continueOwn")}
            </button>
          </div>
        )}

        {options && !showOther && (
          <>
            <div className="mk-choices mk-choices--wide">
              {options.map((option) => (
                <ChoiceTile
                  key={option.id}
                  icon={option.icon as IconName}
                  label={option.label}
                  showCheck={false}
                  onClick={() => choose(option.id, option.label, spoken ?? undefined)}
                />
              ))}
              <ChoiceTile
                icon="dots"
                label={t("complaint.other")}
                sub={t("complaint.otherSub")}
                showCheck={false}
                onClick={() => setShowOther(true)}
              />
            </div>

            {voiceAllowed && patient && !spoken && (
              <div className="mk-answer__voice">
                <p className="mk-help mk-center">{t("complaint.speak")}</p>
                <VoiceRecorder
                  sessionId={patient.session_id}
                  questionId="chief_complaint"
                  onAccept={(transcript) => void handleSpoken(transcript)}
                  onTypeInstead={() => setShowOther(true)}
                />
              </div>
            )}
          </>
        )}

        {showOther && (
          <div className="mk-card mk-stack">
            <div className="mk-row">
              <Icon name="keyboard" />
              <span className="mk-label">{t("complaint.otherLabel")}</span>
            </div>
            <TextAnswer
              value={freeText}
              onChange={setFreeText}
              autoFocus
              onSubmit={() => choose("other", t("complaint.other"), freeText.trim())}
              onCancel={() => setShowOther(false)}
            />
          </div>
        )}
      </div>
    </KioskScreen>
  );
}
