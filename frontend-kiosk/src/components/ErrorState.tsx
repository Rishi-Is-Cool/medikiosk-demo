"use client";

import type { ReactNode } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { Icon } from "./Icon";

/**
 * Patient-safe failure.
 *
 * Build spec §15: no stack traces, no HTTP status codes, no model output. The
 * caller passes a message already chosen from a translated key; anything the
 * kiosk actually needs for debugging goes to the console, not the screen.
 */
export function ErrorState({
  title,
  message,
  actions,
  severity = "warning",
}: {
  title: string;
  message?: string;
  actions?: ReactNode;
  severity?: "warning" | "critical";
}) {
  const { t } = useLanguage();

  return (
    <div className="mk-alert mk-errorstate" data-sev={severity} role="alert">
      <Icon name="alert" size={32} />
      <div className="mk-stack mk-stack--tight">
        <strong>{title}</strong>
        <span className="mk-help">{message ?? t("error.generic")}</span>
        {actions && <div className="mk-row mk-row--wrap mk-errorstate__actions">{actions}</div>}
      </div>
    </div>
  );
}
