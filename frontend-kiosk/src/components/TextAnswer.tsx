"use client";

import { useEffect, useRef, useState } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { Icon } from "./Icon";

/* The typed fallback (build spec §14: minimal typing, but always a way that
   does not need a working microphone). Never the default path — it is offered
   beside the microphone, and it is what the error states fall back to. */

export function TextAnswer({
  value,
  onChange,
  onSubmit,
  onCancel,
  autoFocus = false,
  disabled = false,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel?: () => void;
  autoFocus?: boolean;
  disabled?: boolean;
}) {
  const { t } = useLanguage();
  const ref = useRef<HTMLTextAreaElement>(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (autoFocus) ref.current?.focus();
  }, [autoFocus]);

  const empty = value.trim().length === 0;

  return (
    <div className="mk-stack mk-stack--tight">
      <label className="mk-field">
        <span className="mk-label">{t("intake.textLabel")}</span>
        <textarea
          ref={ref}
          className="mk-textarea"
          rows={3}
          value={value}
          placeholder={t("intake.textPlaceholder")}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onBlur={() => setTouched(true)}
        />
      </label>

      {touched && empty && <p className="mk-help">{t("intake.noneSelected")}</p>}

      <div className="mk-row">
        <button
          type="button"
          className="mk-btn mk-btn--primary"
          disabled={disabled || empty}
          onClick={onSubmit}
        >
          <Icon name="check" />
          {t("intake.saveAnswer")}
        </button>
        {onCancel && (
          <button type="button" className="mk-btn mk-btn--ghost" onClick={onCancel}>
            {t("common.cancel")}
          </button>
        )}
      </div>
    </div>
  );
}
