"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePatientSession } from "@/context/PatientSession";
import { ROUTES } from "@/lib/journey";

export type Requirement = "patient" | "consent" | "complaint" | "intakeDone";

/**
 * Sends a patient back to the start if they land mid-journey without the
 * state that screen needs — a refresh, a bookmarked URL, or the back button
 * after a session reset.
 *
 * State is in memory by design (see context/PatientSession), so this is a
 * routine path, not an edge case.
 */
export function useJourneyGuard(requirement: Requirement): boolean {
  const router = useRouter();
  const session = usePatientSession();

  const satisfied =
    requirement === "patient"
      ? session.patient !== null
      : requirement === "consent"
        ? session.patient !== null && session.consentId !== null
        : requirement === "complaint"
          ? session.complaint !== null
          : session.intakeComplete || session.priority?.red_flag === true;

  useEffect(() => {
    if (!satisfied) router.replace(ROUTES.start);
  }, [satisfied, router]);

  return satisfied;
}
