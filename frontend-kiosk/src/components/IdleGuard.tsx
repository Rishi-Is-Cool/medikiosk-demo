"use client";

import { usePathname, useRouter } from "next/navigation";
import { usePatientSession } from "@/context/PatientSession";
import { useIdleTimeout } from "@/hooks/useIdleTimeout";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";
import { Icon } from "./Icon";
import { Modal } from "./Modal";

/** Quiet time before the kiosk asks whether anyone is still there. Long
 *  enough that a slow reader is never interrupted mid-question. */
const IDLE_MS = 120_000;
/** How long the question stays up before the session is cleared. */
const WARNING_MS = 20_000;

/**
 * Clears an abandoned session, from any screen in the journey.
 *
 * Two screens are deliberately exempt:
 *
 * - The start screen, because there is no session to abandon.
 * - The priority screen. That screen exists because the backend flagged
 *   something urgent and told the patient to sit still and wait for staff —
 *   sitting still is exactly the behaviour it asked for, and timing out on it
 *   would erase an urgent hand-off precisely when the patient did as they
 *   were told. It clears when staff clear it.
 */
export function IdleGuard() {
  const router = useRouter();
  const pathname = usePathname();
  const { t } = useLanguage();
  const { patient, reset } = usePatientSession();

  const exempt = pathname === ROUTES.start || pathname === ROUTES.priority;
  const enabled = Boolean(patient) && !exempt;

  const { warning, secondsLeft, stayActive } = useIdleTimeout({
    idleMs: IDLE_MS,
    warningMs: WARNING_MS,
    enabled,
    onTimeout: () => {
      reset();
      router.push(ROUTES.start);
    },
  });

  return (
    <Modal
      open={warning}
      title={t("idle.title")}
      onClose={stayActive}
      closeLabel={t("idle.continue")}
    >
      <div className="mk-stack">
        <div className="mk-row">
          <span className="mk-help-icon">
            <Icon name="clock" size={32} />
          </span>
          <p className="mk-lead">{t("idle.body")}</p>
        </div>

        <p className="mk-help mk-num" aria-live="polite">
          {t("idle.counting", { seconds: secondsLeft })}
        </p>

        <button
          type="button"
          className="mk-btn mk-btn--primary mk-btn--lg mk-btn--block"
          onClick={stayActive}
        >
          {t("idle.continue")}
        </button>
      </div>
    </Modal>
  );
}
