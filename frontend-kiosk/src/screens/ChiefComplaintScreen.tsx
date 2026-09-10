"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { intakeApi } from "@/api/intakeApi";
import type { ChiefComplaintOption } from "@/api/types";
import { ChoiceTile } from "@/components/ChoiceTile";
import { ErrorState } from "@/components/ErrorState";
import { Icon, isIconName } from "@/components/Icon";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { SourceChip } from "@/components/SourceChip";
import { TextAnswer } from "@/components/TextAnswer";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { speakChoice } from "@/hooks/useSpeech";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.5, and the problem statement's own opening move.
 *
 * Patients rarely come with one problem: chest pain with a headache, fever
 * with a cough. Every complaint they tick is sent to the question service,
 * which builds a single interview that covers all of them without asking the
 * shared questions (how long, how bad) twice.
 *
 * The complaint list comes from the question service, not from a constant in
 * this file. The patient can also simply say what is wrong: the service maps
 * the words onto the list — possibly several at once — and the patient checks
 * the ticks before continuing. Unmatched words are kept as the patient's own
 * description, because they still said something true.
 */
export function ChiefComplaintScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { patient, consentGranted, dispatch } = usePatientSession();
  const ready = useJourneyGuard("consent");

  const [options, setOptions] = useState<ChiefComplaintOption[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<string[]>([]);
  const [freeText, setFreeText] = useState("");
  const [showOther, setShowOther] = useState(false);
  const [spoken, setSpoken] = useState<string | null>(null);
  const [matchedFromVoice, setMatchedFromVoice] = useState(false);

  const voiceAllowed = consentGranted.includes("voice");
  // The question service's list carries its own "other" entry; the mock's does not.
  const serviceHasOther = options?.some((option) => option.id === "other") ?? false;

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

  function toggle(id: string, label: string) {
    const on = !selected.includes(id);
    if (on) speakChoice(label, language);
    setSelected((current) => (on ? [...current, id] : current.filter((c) => c !== id)));
    if (id === "other") setShowOther(on);
  }

  const words = (freeText.trim() || spoken || "").trim();
  const canContinue = selected.length > 0 || words.length > 0;

  function proceed() {
    if (!canContinue) return;
    const ids = selected.length > 0 ? selected : ["other"];
    const label = ids
      .map((id) => options?.find((o) => o.id === id)?.label ?? (id === "other" ? t("complaint.other") : id))
      .join(", ");
    dispatch({ type: "setComplaint", complaint: { ids, label, text: words || undefined } });
    router.push(ROUTES.intake);
  }

  /* Spoken words go to the question service to be matched. Hits are ticked
     for the patient to check; a miss keeps the words as their description. */
  const handleSpoken = useCallback(
    async (transcript: string) => {
      setSpoken(transcript);
      try {
        const match = await intakeApi.matchComplaint(transcript, language);
        const ids = (match.complaints ?? (match.complaint ? [match.complaint] : [])).map((c) => c.id);
        if (ids.length > 0) {
          setSelected((current) => Array.from(new Set([...current, ...ids])));
          setMatchedFromVoice(true);
          return;
        }
      } catch (error) {
        console.warn("[complaints] match failed", error);
      }
      setMatchedFromVoice(false);
      setSelected((current) => (current.includes("other") ? current : [...current, "other"]));
      setFreeText((current) => current || transcript);
      setShowOther(true);
    },
    [language],
  );

  if (!ready) return null;

  const otherTile = !serviceHasOther && (
    <ChoiceTile
      icon="dots"
      label={t("complaint.other")}
      sub={t("complaint.otherSub")}
      selected={selected.includes("other")}
      onClick={() => toggle("other", t("complaint.other"))}
    />
  );

  return (
    <KioskScreen
      step="complaint"
      align="top"
      actions={
        <>
          <BackButton onClick={() => router.push(ROUTES.mode)} label={t("common.back")} />
          <div className="mk-actionbar__spacer" />
          {selected.length > 0 && (
            <span className="mk-pill">{t("complaint.selectedCount", { count: selected.length })}</span>
          )}
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--lg"
            disabled={!canContinue}
            onClick={proceed}
          >
            {t("common.continue")}
            <Icon name="chevronRight" />
          </button>
        </>
      }
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight mk-center">
          <h1 className="mk-h1">{t("complaint.title")}</h1>
          <p className="mk-lead">{t("complaint.subtitleMulti")}</p>
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
            <p className="mk-help">{t(matchedFromVoice ? "complaint.heardMatched" : "complaint.noMatch")}</p>
            <button type="button" className="mk-btn mk-btn--ghost" onClick={() => setSpoken(null)}>
              <Icon name="mic" />
              {t("intake.recordAgain")}
            </button>
          </div>
        )}

        {options && (
          <div className="mk-choices mk-choices--wide">
            {options.map((option) => (
              <ChoiceTile
                key={option.id}
                icon={isIconName(option.icon) ? option.icon : "stethoscope"}
                label={option.label}
                sub={option.id === "other" ? t("complaint.otherSub") : undefined}
                selected={selected.includes(option.id)}
                onClick={() => toggle(option.id, option.label)}
              />
            ))}
            {otherTile}
          </div>
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
              autoFocus={!spoken}
              onSubmit={proceed}
              onCancel={() => {
                setShowOther(false);
                setFreeText("");
                setSelected((current) => current.filter((c) => c !== "other"));
              }}
            />
          </div>
        )}

        {options && voiceAllowed && patient && !spoken && (
          <div className="mk-answer__voice">
            <p className="mk-help mk-center">{t("complaint.speak")}</p>
            <VoiceRecorder
              sessionId={patient.session_id}
              questionId="chief_complaint"
              onAccept={(transcript) => void handleSpoken(transcript)}
              onTypeInstead={() => {
                setShowOther(true);
                setSelected((current) => (current.includes("other") ? current : [...current, "other"]));
              }}
            />
          </div>
        )}
      </div>
    </KioskScreen>
  );
}
