"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { speechApi } from "@/api/speechApi";
import { ApiError, type ExtractionResult } from "@/api/types";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ErrorState } from "./ErrorState";
import { Icon } from "./Icon";
import { ProcessingState } from "./ProcessingState";
import { RecordingIndicator } from "./RecordingIndicator";
import { SourceChip } from "./SourceChip";

/* Build spec §6.7 — the required visible states, in order:
   Idle → Recording → Processing → Transcript Ready → Accepted | Error.

   Audio goes out through speechApi. Whisper, or whatever replaces it, is on
   the far side of that call and this component knows nothing about it. */

type Phase = "idle" | "recording" | "processing" | "ready" | "error";

export function VoiceRecorder({
  sessionId,
  questionId,
  /** Lets the intake screen enrich the transcript with backend extraction
   *  before the patient confirms. Returning null simply shows the transcript. */
  onTranscribed,
  onAccept,
  onTypeInstead,
  onPhaseChange,
  disabled = false,
}: {
  sessionId: string;
  questionId: string;
  onTranscribed?: (transcript: string) => Promise<ExtractionResult | null>;
  /** `transcriptId` links the confirmed answer to the stored transcript. */
  onAccept: (transcript: string, extraction: ExtractionResult | null, transcriptId?: string) => void;
  onTypeInstead?: () => void;
  /** Lets the screen show only the controls that matter right now — the touch
   *  options are noise while a spoken answer is being confirmed. */
  onPhaseChange?: (phase: Phase) => void;
  disabled?: boolean;
}) {
  const { t, language } = useLanguage();
  const recorder = useVoiceRecorder();
  const [phase, setPhase] = useState<Phase>("idle");
  const [transcript, setTranscript] = useState("");
  const [transcriptId, setTranscriptId] = useState<string | undefined>(undefined);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [failure, setFailure] = useState<"mic" | "speech" | null>(null);
  const liveRef = useRef(true);
  const rootRef = useRef<HTMLDivElement>(null);

  /* The recorder sits below the touch options, so on a 768px kiosk panel the
     transcript and its "is this correct?" buttons can land under the fold. A
     patient who cannot see the confirm button is stuck, and will not think to
     scroll. Bring each new state into view instead. */
  useEffect(() => {
    onPhaseChange?.(phase);
    if (phase === "idle") return;
    // "center" rather than "nearest": the transcript plus its confirm buttons
    // can be taller than the viewport, and "nearest" is a no-op in that case.
    rootRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [phase, onPhaseChange]);

  useEffect(() => {
    liveRef.current = true;
    return () => {
      liveRef.current = false;
    };
  }, []);

  // A new question resets the recorder completely — a transcript left over
  // from the previous question must never be attributable to this one.
  useEffect(() => {
    setPhase("idle");
    setTranscript("");
    setTranscriptId(undefined);
    setExtraction(null);
    setFailure(null);
  }, [questionId]);

  const beginRecording = useCallback(async () => {
    setFailure(null);
    const started = await recorder.start();
    if (started) {
      setPhase("recording");
    } else {
      setFailure("mic");
      setPhase("error");
    }
  }, [recorder]);

  const finishRecording = useCallback(async () => {
    const recording = await recorder.stop();
    if (!recording) {
      setPhase("idle");
      return;
    }

    setPhase("processing");

    try {
      const result = await speechApi.transcribe({
        session_id: sessionId,
        question_id: questionId,
        language,
        audio: recording.blob,
        duration_ms: recording.durationMs,
      });

      if (!liveRef.current) return;

      const structured = onTranscribed ? await onTranscribed(result.transcript) : null;
      if (!liveRef.current) return;

      setTranscript(result.transcript);
      setTranscriptId(result.transcript_id);
      setExtraction(structured);
      setPhase("ready");
    } catch (error) {
      if (!liveRef.current) return;
      // Detail goes to the console for the team; the patient gets a sentence.
      console.warn("[speech] transcription failed", error instanceof ApiError ? error.code : error);
      setFailure("speech");
      setPhase("error");
    }
  }, [recorder, sessionId, questionId, language, onTranscribed]);

  const cancelRecording = useCallback(async () => {
    await recorder.cancel();
    setPhase("idle");
  }, [recorder]);

  /* --- Idle ---------------------------------------------------------------- */

  if (phase === "idle") {
    return (
      <div className="mk-recorder" ref={rootRef}>
        <button
          type="button"
          className="mk-mic"
          onClick={beginRecording}
          disabled={disabled || recorder.status === "requesting"}
        >
          <span className="mk-mic__ring">
            <Icon name="mic" size={40} strokeWidth={1.6} />
          </span>
          <span className="mk-mic__label">{t("intake.tapToSpeak")}</span>
        </button>
      </div>
    );
  }

  /* --- Recording ----------------------------------------------------------- */

  if (phase === "recording") {
    return (
      <div className="mk-recorder mk-stack" ref={rootRef}>
        <RecordingIndicator
          durationMs={recorder.durationMs}
          level={recorder.level}
          label={t("intake.recording")}
        />
        <div className="mk-row">
          <button type="button" className="mk-btn mk-btn--primary mk-btn--lg" onClick={finishRecording}>
            <Icon name="check" />
            {t("intake.stopRecording")}
          </button>
          <button type="button" className="mk-btn mk-btn--ghost" onClick={cancelRecording}>
            {t("common.cancel")}
          </button>
        </div>
      </div>
    );
  }

  /* --- Processing ---------------------------------------------------------- */

  if (phase === "processing") {
    return (
      <div className="mk-recorder" ref={rootRef}>
        <ProcessingState label={t("intake.transcribing")} hint={t("common.pleaseWait")} />
      </div>
    );
  }

  /* --- Transcript ready ---------------------------------------------------- */

  if (phase === "ready") {
    return (
      <div className="mk-recorder mk-stack" ref={rootRef}>
        <div className="mk-transcript">
          <div className="mk-row mk-transcript__head">
            <span className="mk-label">{t("intake.youSaid")}</span>
            <SourceChip source="patient_spoken" />
          </div>
          <p className="mk-transcript__text">{transcript}</p>

          {extraction && extraction.fields.length > 0 && (
            <dl className="mk-extracted">
              {extraction.fields.map((field) => (
                <div key={field.label} className="mk-extracted__row">
                  <dt>{field.label}</dt>
                  <dd>{field.value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>

        <p className="mk-lead">{t("intake.isThatRight")}</p>

        <div className="mk-row mk-row--wrap">
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--lg"
            onClick={() => onAccept(transcript, extraction, transcriptId)}
          >
            <Icon name="check" />
            {t("intake.yesCorrect")}
          </button>
          <button type="button" className="mk-btn mk-btn--secondary" onClick={beginRecording}>
            <Icon name="refresh" />
            {t("intake.recordAgain")}
          </button>
        </div>
      </div>
    );
  }

  /* --- Error --------------------------------------------------------------- */

  return (
    <div className="mk-recorder" ref={rootRef}>
      <ErrorState
        title={failure === "mic" ? t("intake.micDenied") : t("intake.speechFailed")}
        message={failure === "mic" ? t("intake.micDeniedHelp") : t("intake.speechFailedHelp")}
        actions={
          <>
            {failure !== "mic" && (
              <button type="button" className="mk-btn mk-btn--secondary" onClick={beginRecording}>
                <Icon name="refresh" />
                {t("common.retry")}
              </button>
            )}
            {onTypeInstead && (
              <button type="button" className="mk-btn mk-btn--secondary" onClick={onTypeInstead}>
                <Icon name="keyboard" />
                {t("common.typeInstead")}
              </button>
            )}
          </>
        }
      />
    </div>
  );
}
