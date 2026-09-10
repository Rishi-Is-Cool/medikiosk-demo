"use client";

import type { QuestionOption, ScaleTone } from "@/api/types";
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
  onChoose,
  scaleTone = "severity",
  disabled = false,
}: {
  options: QuestionOption[];
  mode: OptionMode;
  selected: string[];
  onSelect: (update: SelectionUpdate) => void;
  /** Fires on every tap — `chosen` is false when a multi-select option is
   *  being un-ticked. Used to read the choice aloud. */
  onChoose?: (option: QuestionOption, chosen: boolean) => void;
  scaleTone?: ScaleTone;
  disabled?: boolean;
}) {
  const { t } = useLanguage();

  if (mode === "scale") {
    return (
      <ScaleOptions
        options={options}
        selected={selected}
        onSelect={onSelect}
        onChoose={onChoose}
        tone={scaleTone}
        disabled={disabled}
      />
    );
  }

  const toggle = (option: QuestionOption) => {
    if (mode === "single") {
      onChoose?.(option, true);
      onSelect([option.value]);
      return;
    }
    onChoose?.(option, !selected.includes(option.value));
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

/**
 * Ordinal answers read better as a slope than as a list of identical tiles.
 *
 * The ramp depends entirely on which way the scale means. A severity scale
 * climbs toward alarm. A Dashavidha grading axis climbs toward *optimum* —
 * running the same red ramp over it would paint "strong and glossy hair" as
 * the danger end, and would tell a patient their own constitution is an
 * emergency. Grading axes get a neutral ramp of the brand colour instead:
 * the pip count still encodes the order, without a value judgement.
 */
function ScaleOptions({
  options,
  selected,
  onSelect,
  onChoose,
  tone,
  disabled,
}: {
  options: QuestionOption[];
  selected: string[];
  onSelect: (update: SelectionUpdate) => void;
  onChoose?: (option: QuestionOption, chosen: boolean) => void;
  tone: ScaleTone;
  disabled: boolean;
}) {
  const { t } = useLanguage();
  // Severity climbs through the warning colours. Grading stays one neutral
  // colour — the number of filled pips already carries the order, so hue is
  // free to say nothing, which is exactly what it should say here.
  const severityRamp = ["grade-high", "grade-mid", "grade-low", "emergency"];
  const colourFor = (index: number) =>
    tone === "grade"
      ? "var(--primary)"
      : `var(--${severityRamp[Math.min(index, severityRamp.length - 1)]})`;

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
            style={{ "--step-colour": colourFor(index) } as React.CSSProperties}
            disabled={disabled}
            onClick={() => {
              onChoose?.(option, true);
              onSelect([option.value]);
            }}
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
