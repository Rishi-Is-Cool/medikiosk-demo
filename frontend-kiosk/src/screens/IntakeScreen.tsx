"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { intakeApi } from "@/api/intakeApi";
import type { AnswerPayload, ExtractionResult, IntakeResponse } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Icon } from "@/components/Icon";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { Modal } from "@/components/Modal";
import { ProcessingState } from "@/components/ProcessingState";
import { ProgressBar } from "@/components/ProgressBar";
import { QuestionCard } from "@/components/QuestionCard";
import { TextAnswer } from "@/components/TextAnswer";
import { TouchOptions, type OptionMode } from "@/components/TouchOptions";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * The core screen (build spec §6.6).
 *
 * It renders whatever question the engine returns and submits whatever the
 * patient answers. It contains no question list, no ordering, no branching
 * and no notion of what any answer means — every one of those lives behind
 * intakeApi. Adding a question, reordering the interview or plugging in the
 * AYUSH set changes nothing in this file.
 */
export function IntakeScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const session = usePatientSession();
  const ready = useJourneyGuard("complaint");

  const { patient, complaint, question, consentGranted, dispatch } = session;
  const voiceAllowed = consentGranted.includes("voice");

  const [phase, setPhase] = useState<"loading" | "question" | "submitting" | "error">("loading");
  const [selected, setSelected] = useState<string[]>([]);
  const [typing, setTyping] = useState(false);
  const [text, setText] = useState("");
  const [confirmBack, setConfirmBack] = useState(false);
  /** Idle means the patient has not started speaking, so the touch options are
   *  still the live alternative. Anything else means they are mid-answer. */
  const [voiceIdle, setVoiceIdle] = useState(true);
  const startedRef = useRef(false);

  /* --- Response handling --------------------------------------------------- */

  const applyResponse = useCallback(
    (response: IntakeResponse) => {
      dispatch({ type: "setPriority", priority: response.priority });

      // Build spec §6.11: the kiosk stops because it was told to, not because
      // it worked anything out.
      if (response.priority.red_flag) {
        router.push(ROUTES.priority);
        return;
      }

      if (response.complete || !response.question) {
        dispatch({ type: "setIntakeComplete", complete: true });
        router.push(consentGranted.includes("documents") ? ROUTES.documents : ROUTES.complete);
        return;
      }

      dispatch({ type: "setQuestion", question: response.question });
      setPhase("question");
    },
    [dispatch, router, consentGranted],
  );

  /* --- Start the interview ------------------------------------------------- */

  useEffect(() => {
    if (!ready || !patient || !complaint || startedRef.current) return;
    startedRef.current = true;

    intakeApi
      .startIntake({
        session_id: patient.session_id,
        history_mode: session.historyMode ?? "general_medicine",
        chief_complaint: complaint.id,
        chief_complaint_text: complaint.text,
        language,
      })
      .then(applyResponse)
      .catch((error) => {
        console.warn("[intake] start failed", error);
        setPhase("error");
      });
  }, [ready, patient, complaint, session.historyMode, language, applyResponse]);

  /* --- Language changed mid-interview -------------------------------------
     The top bar can switch language on any screen. Chrome re-renders from the
     dictionary on its own; question text is localised by the engine, so it has
     to be asked for again or the patient is left reading the old language.  */

  const lastLanguageRef = useRef(language);

  useEffect(() => {
    if (lastLanguageRef.current === language) return;
    lastLanguageRef.current = language;
    if (!patient || !question) return;

    intakeApi
      .getCurrentQuestion(patient.session_id, language)
      .then((response) => {
        if (response.question) dispatch({ type: "setQuestion", question: response.question });
      })
      .catch((error) => {
        // Keep the question that is already on screen rather than blanking it.
        console.warn("[intake] could not re-localise question", error);
      });
  }, [language, patient, question, dispatch]);

  // Fresh controls for each question. Carrying a selection across questions
  // would be a data-integrity bug, not just a UI glitch.
  useEffect(() => {
    setSelected([]);
    setTyping(false);
    setText("");
    setVoiceIdle(true);
  }, [question?.question_id]);

  /* --- Answering ----------------------------------------------------------- */

  const submit = useCallback(
    async (payload: AnswerPayload, extraction?: ExtractionResult | null) => {
      if (!patient || !question) return;

      dispatch({
        type: "recordAnswer",
        answer: {
          question_id: question.question_id,
          question_text: question.text,
          payload,
          extraction: extraction ?? undefined,
        },
      });

      setPhase("submitting");

      try {
        const response = await intakeApi.submitAnswer({
          session_id: patient.session_id,
          question_id: question.question_id,
          answer: payload,
          language,
        });
        applyResponse(response);
      } catch (error) {
        console.warn("[intake] submit failed", error);
        setPhase("error");
      }
    },
    [patient, question, language, dispatch, applyResponse],
  );

  /** Backend/AI structuring, requested before the patient confirms a spoken
   *  answer so they see what was understood (build spec §6.8, §7). */
  const extractSpoken = useCallback(
    async (transcript: string): Promise<ExtractionResult | null> => {
      if (!patient || !question) return null;
      try {
        return await intakeApi.extractAnswer({
          session_id: patient.session_id,
          question_id: question.question_id,
          answer: { source: "patient_spoken", text: transcript },
          language,
        });
      } catch (error) {
        // Extraction is an enhancement to the confirmation step. If it fails,
        // show the plain transcript rather than blocking the patient.
        console.warn("[intake] extraction unavailable", error);
        return null;
      }
    },
    [patient, question, language],
  );

  if (!ready) return null;

  /* --- Render -------------------------------------------------------------- */

  const back = (
    <BackButton
      onClick={() => (session.answeredCount > 0 ? setConfirmBack(true) : router.push(ROUTES.complaint))}
      label={t("common.back")}
    />
  );

  if (phase === "error") {
    return (
      <KioskScreen step="intake" actions={back}>
        <div className="mk-container mk-container--narrow">
          <ErrorState
            title={t("error.title")}
            message={t("error.offline")}
            actions={
              <button
                type="button"
                className="mk-btn mk-btn--secondary"
                onClick={() => window.location.reload()}
              >
                <Icon name="refresh" />
                {t("common.retry")}
              </button>
            }
          />
        </div>
      </KioskScreen>
    );
  }

  if (phase === "loading" || !question) {
    return (
      <KioskScreen step="intake" actions={back}>
        <ProcessingState label={t("intake.loadingQuestion")} />
      </KioskScreen>
    );
  }

  const mode: OptionMode =
    question.input_type === "multi_select"
      ? "multi"
      : question.input_type === "scale"
        ? "scale"
        : "single";

  const hasOptions = question.options.length > 0;
  const showVoice = question.allow_voice && voiceAllowed && !typing;
  // Once the patient is speaking, the touch list is no longer an alternative —
  // it is clutter under the transcript they are being asked to confirm, and on
  // a 768px panel it pushes the confirm buttons off the screen. "No, say it
  // again" brings them straight back.
  const showOptions = hasOptions && voiceIdle;
  const showText = (question.allow_text || typing) && !hasOptions;

  return (
    <KioskScreen
      step="intake"
      align="top"
      actions={
        <>
          {back}
          <div className="mk-actionbar__spacer" />
          {mode === "multi" && phase === "question" && showOptions && (
            <button
              type="button"
              className="mk-btn mk-btn--primary mk-btn--lg"
              disabled={selected.length === 0}
              onClick={() => submit({ source: "patient_touch", values: selected })}
            >
              {t("common.next")}
              <Icon name="chevronRight" />
            </button>
          )}
        </>
      }
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <ProgressBar progress={question.progress} section={question.section} />

        <QuestionCard question={question} autoRead>
          {phase === "submitting" ? (
            <ProcessingState label={t("intake.savingAnswer")} />
          ) : (
            <div className="mk-answer">
              {showOptions && (
                <TouchOptions
                  options={question.options}
                  mode={mode}
                  selected={selected}
                  scaleTone={question.scale_tone}
                  onSelect={(update) => {
                    setSelected(update);
                    // Single-choice commits on tap; multi-select waits for the
                    // explicit Next, since there is no way to know the patient
                    // has finished choosing.
                    if (mode !== "multi" && Array.isArray(update) && update.length > 0) {
                      void submit({ source: "patient_touch", values: update });
                    }
                  }}
                />
              )}

              {showText && (
                <TextAnswer
                  value={text}
                  onChange={setText}
                  autoFocus={typing}
                  onSubmit={() => submit({ source: "patient_typed", text: text.trim() })}
                  onCancel={typing ? () => setTyping(false) : undefined}
                />
              )}

              {showVoice && (
                <div className="mk-answer__voice" data-bare={!showOptions}>
                  {showOptions && <p className="mk-help mk-center">{t("intake.orSpeak")}</p>}
                  <VoiceRecorder
                    sessionId={patient!.session_id}
                    questionId={question.question_id}
                    onTranscribed={extractSpoken}
                    onAccept={(transcript, extraction) =>
                      submit({ source: "patient_spoken", text: transcript }, extraction)
                    }
                    onTypeInstead={() => setTyping(true)}
                    onPhaseChange={(voicePhase) => setVoiceIdle(voicePhase === "idle")}
                  />
                </div>
              )}

              {question.allow_voice && !voiceAllowed && (
                <p className="mk-help mk-center">{t("intake.voiceOff")}</p>
              )}

              {showOptions && !typing && question.allow_text && (
                <button type="button" className="mk-btn mk-btn--ghost" onClick={() => setTyping(true)}>
                  <Icon name="keyboard" />
                  {t("common.typeInstead")}
                </button>
              )}
            </div>
          )}
        </QuestionCard>
      </div>

      <Modal
        open={confirmBack}
        title={t("intake.backTitle")}
        onClose={() => setConfirmBack(false)}
        closeLabel={t("common.cancel")}
      >
        {/* An adaptive interview cannot be rewound one question at a time
            without a backend contract for it, so going back restarts the
            complaint rather than silently dropping answers. */}
        <div className="mk-stack">
          <p className="mk-lead">{t("intake.backBody")}</p>
          <div className="mk-row">
            <button
              type="button"
              className="mk-btn mk-btn--secondary"
              onClick={() => {
                setConfirmBack(false);
                router.push(ROUTES.complaint);
              }}
            >
              {t("intake.backConfirm")}
            </button>
            <button type="button" className="mk-btn mk-btn--ghost" onClick={() => setConfirmBack(false)}>
              {t("common.cancel")}
            </button>
          </div>
        </div>
      </Modal>
    </KioskScreen>
  );
}
