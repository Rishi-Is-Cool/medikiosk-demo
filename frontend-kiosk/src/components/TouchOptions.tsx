"use client";

import type { QuestionOption } from "@/api/types";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ChoiceTile } from "./ChoiceTile";

export type OptionMode = "single" | "multi" | "scale";

/* The touch half of every question (build spec §6.6: every question is
   answerable by tapping as well as speaking).

   Single-choice lists commit on tap rather than making the patient tap an
   answer and then tap Next. Multi-select cannot — there is no way to know the
   patient is finished — so it keeps an explicit action. */

/** Accepts a plain array or a React-style updater. Multi-select always sends
 *  an updater: two taps inside one frame — a double-tap, or an unsteady hand
 *  on a touchscreen — would otherwise both read the same stale selection and
 *  the first would be silently lost. */
export type SelectionUpdate = string[] | ((current: string[]) => string[]);

/** Pure toggle so the caller can apply it against the freshest state. */
export function toggleSelection(
  current: string[],
  option: QuestionOption,
  options: QuestionOption[],
): string[] {
  // "None of these" and a symptom cannot both be true. Whichever the patient
  // touched last wins, and the other clears.
  if (option.exclusive) {
    return current.includes(option.value) ? [] : [option.value];
  }

  const withoutExclusives = current.filter(
    (value) => !options.find((o) => o.value === value)?.exclusive,
  );

  return withoutExclusives.includes(option.value)
    ? withoutExclusives.filter((value) => value !== option.value)
    : [...withoutExclusives, option.value];
}

export function TouchOptions({
  options,
  mode,
  selected,
  onSelect,
  disabled = false,
}: {
  options: QuestionOption[];
  mode: OptionMode;
  selected: string[];
  onSelect: (update: SelectionUpdate) => void;
  disabled?: boolean;
}) {
  const { t } = useLanguage();

  if (mode === "scale") {
    return <ScaleOptions options={options} selected={selected} onSelect={onSelect} disabled={disabled} />;
  }

  const toggle = (option: QuestionOption) => {
    if (mode === "single") {
      onSelect([option.value]);
      return;
    }
    onSelect((current) => toggleSelection(current, option, options));
  };

  return (
    <div className="mk-stack mk-stack--tight">
      <p className="mk-help">{mode === "multi" ? t("intake.selectMany") : t("intake.selectOne")}</p>
      <div className="mk-choices">
        {options.map((option) => (
          <ChoiceTile
            key={option.value}
            label={option.label}
            selected={selected.includes(option.value)}
            showCheck={mode === "multi"}
            disabled={disabled}
            onClick={() => toggle(option)}
          />
        ))}
      </div>
    </div>
  );
}

/** Ordinal answers get the graded ramp from tokens.css rather than four
 *  identical tiles — severity is easier to read as a slope than as a list. */
function ScaleOptions({
  options,
  selected,
  onSelect,
  disabled,
}: {
  options: QuestionOption[];
  selected: string[];
  onSelect: (update: SelectionUpdate) => void;
  disabled: boolean;
}) {
  const { t } = useLanguage();
  const ramp = ["grade-high", "grade-mid", "grade-low", "emergency"];

  return (
    <div className="mk-stack mk-stack--tight">
      <p className="mk-help">{t("intake.selectOne")}</p>
      <div className="mk-scale">
        {options.map((option, index) => (
          <button
            key={option.value}
            type="button"
            className="mk-scale__step"
            data-selected={selected.includes(option.value)}
            style={{ "--step-colour": `var(--${ramp[Math.min(index, ramp.length - 1)]})` } as React.CSSProperties}
            disabled={disabled}
            onClick={() => onSelect([option.value])}
          >
            <span className="mk-scale__pips" aria-hidden="true">
              {options.map((_, pip) => (
                <span key={pip} className="mk-scale__pip" data-on={pip <= index} />
              ))}
            </span>
            <span className="mk-scale__label">{option.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
