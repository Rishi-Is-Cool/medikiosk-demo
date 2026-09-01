"use client";

import { useLanguage } from "@/i18n/LanguageProvider";
import type { QuestionProgress } from "@/api/types";

/** Build spec §6.10: the total is an estimate the engine may revise, so it is
 *  shown as "about N" and the bar is capped rather than allowed to overflow
 *  when a branch adds questions mid-interview. */
export function ProgressBar({ progress }: { progress: QuestionProgress }) {
  const { t } = useLanguage();
  const total = Math.max(progress.estimated_total, progress.current);
  const percent = Math.min(100, Math.round((progress.current / total) * 100));

  return (
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
  );
}
