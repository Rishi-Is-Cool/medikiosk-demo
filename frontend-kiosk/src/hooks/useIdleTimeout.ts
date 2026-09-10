"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Watches for a patient who has walked away.
 *
 * A kiosk is a shared public device. The completion screen already clears
 * itself, but a patient can abandon a session anywhere — after consent, in
 * the middle of the interview, waiting for a QR scan — and until now the next
 * person would have walked up to the previous person's half-finished
 * session, on screen, with their answers in it.
 *
 * Two stages on purpose: a warning the patient can dismiss, then the clear.
 * Going straight to a reset would wipe the session of anyone who paused to
 * find their reading glasses or read a question twice.
 */

/** Activity that counts as "still here". Deliberately broad — a hovering
 *  finger or a scroll is as much a sign of presence as a tap. */
const ACTIVITY_EVENTS = ["pointerdown", "keydown", "touchstart", "scroll", "wheel"] as const;

export function useIdleTimeout({
  idleMs,
  warningMs,
  onTimeout,
  enabled = true,
}: {
  /** Quiet time before the warning appears. */
  idleMs: number;
  /** How long the warning stays up before the session is cleared. */
  warningMs: number;
  onTimeout: () => void;
  enabled?: boolean;
}) {
  const [warning, setWarning] = useState(false);
  const [remainingMs, setRemainingMs] = useState(warningMs);

  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const countdown = useRef<ReturnType<typeof setInterval> | null>(null);
  // Held in a ref so changing the callback does not restart the timers.
  const onTimeoutRef = useRef(onTimeout);
  onTimeoutRef.current = onTimeout;

  const clearTimers = useCallback(() => {
    if (idleTimer.current) clearTimeout(idleTimer.current);
    if (countdown.current) clearInterval(countdown.current);
    idleTimer.current = null;
    countdown.current = null;
  }, []);

  /** Called by real activity, and by the patient answering the warning. */
  const reset = useCallback(() => {
    clearTimers();
    setWarning(false);
    setRemainingMs(warningMs);

    if (!enabled) return;

    idleTimer.current = setTimeout(() => {
      setWarning(true);
      const deadline = Date.now() + warningMs;

      countdown.current = setInterval(() => {
        const left = deadline - Date.now();
        setRemainingMs(Math.max(0, left));
        if (left <= 0) {
          clearTimers();
          setWarning(false);
          onTimeoutRef.current();
        }
      }, 250);
    }, idleMs);
  }, [clearTimers, enabled, idleMs, warningMs]);

  useEffect(() => {
    if (!enabled) {
      clearTimers();
      setWarning(false);
      return;
    }

    reset();

    // While the warning is up, background activity must not silently dismiss
    // it — the patient has to answer. Otherwise a passing trolley bumping the
    // screen would cancel a reset that should have happened.
    const onActivity = () => {
      if (!warningRef.current) reset();
    };

    for (const event of ACTIVITY_EVENTS) {
      window.addEventListener(event, onActivity, { passive: true });
    }

    return () => {
      for (const event of ACTIVITY_EVENTS) {
        window.removeEventListener(event, onActivity);
      }
      clearTimers();
    };
  }, [enabled, reset, clearTimers]);

  // Mirror of `warning` for the listener above, which closes over a stale
  // value otherwise.
  const warningRef = useRef(warning);
  warningRef.current = warning;

  return {
    warning,
    secondsLeft: Math.ceil(remainingMs / 1000),
    /** "I am still here" — dismisses the warning and restarts the clock. */
    stayActive: reset,
  };
}
