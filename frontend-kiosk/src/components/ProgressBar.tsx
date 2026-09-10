"use client";

import { useLanguage } from "@/i18n/LanguageProvider";
import type { QuestionProgress, QuestionSection } from "@/api/types";

/**
 * Build spec §6.10: the total is an estimate the engine may revise, so it is
 * shown as "about N" and the bar is capped rather than allowed to overflow
 * when a branch adds questions mid-interview.
 *
 * When the engine sends sections — which it does for the thirty-odd question
 * AYUSH interview — the section name leads. "Part 2 of 4 · About your body"
 * tells a patient where they are in a way "question 9 of 34" cannot.
 */
export function ProgressBar({
  progress,
  section,
}: {
  progress: QuestionProgress;
  section?: QuestionSection;
}) {
  const { t } = useLanguage();
  const total = Math.max(progress.estimated_total, progress.current);
  const percent = Math.min(100, Math.round((progress.current / total) * 100));

  return (
    <div className="mk-stack mk-stack--tight">
      {section && (
        <div className="mk-sectionbar">
          <span className="mk-pill mk-pill--primary">
            {t("intake.section", { index: section.index, total: section.total })}
          </span>
          <span className="mk-sectionbar__label">{section.label}</span>
        </div>
      )}

      <div className="mk-progress">
        <div
          className="mk-progress__track"
          role="progressbar"
          aria-valuenow={progress.current}
          aria-valuemin={0}
          aria-valuemax={total}
          aria-label={t("intake.progress", { current: progress.current, total })}
        >
          <div className="mk-progress__fill" style={{ width: `${percent}%` }} />
        </div>
        <span className="mk-progress__label">
          {t("intake.progress", { current: progress.current, total })}
        </span>
      </div>
    </div>
  );
}
