"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/Icon";
import { KioskScreen } from "@/components/KioskScreen";
import { VoicePlayer } from "@/components/VoicePlayer";
import { usePatientSession } from "@/context/PatientSession";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.11.
 *
 * The frontend determines nothing here. It renders the state the backend
 * returned, stops the interview, and says one calm, unmistakable thing. The
 * `reason_code` is deliberately not shown: a patient must not read a machine's
 * guess about their heart, and the spec forbids exposing model reasoning.
 */
export function PriorityAlertScreen() {
  const router = useRouter();
  const { t } = useLanguage();
  const { priority, reset } = usePatientSession();

  // Reached without a priority state — nothing to show, go back to the start.
  useEffect(() => {
    if (!priority?.red_flag) router.replace(ROUTES.start);
  }, [priority, router]);

  if (!priority?.red_flag) return null;

  const immediate = priority.action === "immediate_assistance";
  const title = immediate ? t("priority.urgentTitle") : t("priority.title");
  const body = immediate ? t("priority.urgentBody") : t("priority.body");

  return (
    <KioskScreen>
      <div className="mk-container mk-container--narrow mk-stack mk-stack--loose mk-center">
        <div className="mk-priority" data-sev={immediate ? "critical" : "warning"}>
          <span className="mk-priority__icon">
            <Icon name={immediate ? "alert" : "hand"} size={56} strokeWidth={1.6} />
          </span>

          <h1 className="mk-h1">{title}</h1>
          <p className="mk-lead mk-priority__body">{body}</p>
          <p className="mk-lead">{t("priority.stay")}</p>
        </div>

        <div className="mk-row mk-row--wrap mk-priority__actions">
          <span className="mk-pill mk-pill--success">
            <Icon name="check" size={18} strokeWidth={3} />
            {t("priority.called")}
          </span>
          <VoicePlayer text={`${title}. ${body} ${t("priority.stay")}`} autoPlayKey={priority.action} />
        </div>

        {/* Staff control. Once the patient has been collected, the kiosk has
            to be returned to a clean state for the next person. */}
        <button
          type="button"
          className="mk-btn mk-btn--ghost"
          onClick={() => {
            reset();
            router.push(ROUTES.start);
          }}
        >
          <Icon name="refresh" />
          {t("common.startOver")}
        </button>
      </div>
    </KioskScreen>
  );
}
