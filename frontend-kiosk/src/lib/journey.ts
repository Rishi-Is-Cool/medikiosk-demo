/* The patient journey, in one place (build spec §5).

   Screens read the order from here instead of hardcoding "next page", so the
   flow can be reordered without hunting through nine components. */

export const ROUTES = {
  start: "/",
  language: "/language",
  register: "/register",
  consent: "/consent",
  mode: "/mode",
  complaint: "/complaint",
  intake: "/intake",
  priority: "/priority",
  documents: "/documents",
  complete: "/complete",
} as const;

export type StepId = "language" | "identity" | "consent" | "complaint" | "intake" | "documents" | "done";

/** The dots in the top bar. Coarser than the route list on purpose — a
 *  patient should see about six milestones, not every screen. */
export const STEPS: StepId[] = [
  "language",
  "identity",
  "consent",
  "complaint",
  "intake",
  "documents",
  "done",
];

export function stepIndex(step: StepId): number {
  return STEPS.indexOf(step);
}
