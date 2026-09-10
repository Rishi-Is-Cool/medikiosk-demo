"use client";

import type { ReactNode } from "react";
import type { IntakeQuestion } from "@/api/types";
import { VoicePlayer } from "./VoicePlayer";

/**
 * Renders whatever question the engine sent (build spec §6.6).
 *
 * It knows about question text, helper text and progress — and nothing about
 * which question this is, what comes next, or what any answer means. That is
 * the whole point: the interview can be rewritten server-side without this
 * component changing.
 */
export function QuestionCard({
  question,
  children,
  autoRead = false,
}: {
  question: IntakeQuestion;
  children: ReactNode;
  /** Reads each new question aloud as it appears. */
  autoRead?: boolean;
}) {
  return (
    <section className="mk-question" aria-labelledby="mk-question-text">
      <div className="mk-question__head">
        <h1 id="mk-question-text" className="mk-h1 mk-question__text">
          {question.text}
        </h1>
        <VoicePlayer
          text={[question.text, question.helper].filter(Boolean).join(". ")}
          autoPlayKey={autoRead ? question.question_id : undefined}
        />
      </div>

      {question.helper && <p className="mk-lead mk-question__helper">{question.helper}</p>}

      <div className="mk-question__body">{children}</div>
    </section>
  );
}
