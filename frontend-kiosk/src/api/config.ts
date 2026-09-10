/* ==========================================================================
   The one place endpoints are configured (build spec §8).

   Nothing else in the app may reference a URL. The paths below are the
   backend's kiosk routes (backend/app/api/integration.py); switching
   NEXT_PUBLIC_USE_MOCKS off points every screen at them with no other change.
   ========================================================================== */

/** Mock mode is the default. Set NEXT_PUBLIC_USE_MOCKS=false once the real
 *  backend is reachable. */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

/** Base URL of the team's backend. "/backend" goes through this app's own
 *  rewrite (next.config.ts), so the patient's phone reaches it too. */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/** Shows the "skip with sample answers" control on the question screen, so a
 *  live demo can jump straight to document upload. Never enable for patients. */
export const DEMO_SKIP = process.env.NEXT_PUBLIC_DEMO_SKIP === "true";

export const ENDPOINTS = {
  patient: {
    register: "/patient/register",
    lookup: "/patient/lookup",
    session: "/patient/session",
    consent: "/patient/consent",
    scanIdentity: "/patient/scan-identity",
  },
  intake: {
    start: "/intake/start",
    question: "/intake/question",
    answer: "/intake/answer",
    autofill: "/intake/autofill",
    queue: "/intake/queue",
    complaints: "/intake/complaints",
    matchComplaint: "/intake/match-complaint",
  },
  speech: {
    transcribe: "/speech/transcribe", // Whisper stays server-side
    synthesize: "/speech/synthesize",
  },
  document: {
    createSession: "/documents/upload-session",
    sessionStatus: "/documents/upload-session/", // + token
    upload: "/documents/upload-session/", // + token + /documents or /connect
  },
} as const;

/**
 * MOCK document service, served by this app's own route handlers.
 *
 * The QR flow is the one place the kiosk genuinely needs a second device to
 * talk to something, so the mock lives on the server instead of in memory.
 * It is a stand-in for the team's document service and is used only in mock
 * mode — it stores metadata only and never the file bytes.
 */
export const MOCK_DOCUMENT_API = "/api/mock/upload-sessions";

/** Public origin the patient's phone can reach. On a laptop this is the LAN
 *  address, so the QR is scannable — localhost is not. See README. */
export function publicOrigin(): string {
  const configured = process.env.NEXT_PUBLIC_KIOSK_PUBLIC_ORIGIN;
  if (configured) return configured.replace(/\/$/, "");
  if (typeof window !== "undefined") return window.location.origin;
  return "";
}

/** Simulated round-trip so the real loading, processing and error states get
 *  exercised during mock development instead of resolving instantly. */
export const MOCK_LATENCY = {
  fast: 260,
  normal: 550,
  slow: 1200,
} as const;

export function mockDelay(ms: number = MOCK_LATENCY.normal): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
