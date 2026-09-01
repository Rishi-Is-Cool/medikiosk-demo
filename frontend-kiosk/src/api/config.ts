/* ==========================================================================
   The one place endpoints are configured (build spec §8).

   Nothing else in the app may reference a URL. When the backend team hands
   over real routes, they are filled in here and MOCKS is switched off — no
   screen or component changes.
   ========================================================================== */

/** Mock mode is the default. Set NEXT_PUBLIC_USE_MOCKS=false once the real
 *  backend is reachable, then flip endpoints on one at a time. */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";

/** Base URL of the team's backend. Empty until they publish one. */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

/**
 * PLACEHOLDER PATHS — not agreed with the backend team yet.
 * Build spec §8: "Do not invent final endpoint URLs." These exist so the
 * request code has a shape to compile against; every one of them is an
 * integration point to confirm before switching USE_MOCKS off.
 */
export const ENDPOINTS = {
  patient: {
    register: "/patient/register", // TODO(backend): confirm path + payload
    session: "/patient/session", // TODO(backend): confirm path + payload
    consent: "/patient/consent", // TODO(backend): confirm path + payload
  },
  intake: {
    start: "/intake/start", // TODO(backend): confirm path + payload
    question: "/intake/question", // TODO(backend): confirm path + payload
    answer: "/intake/answer", // TODO(backend): confirm path + payload
    complaints: "/intake/complaints", // TODO(backend): confirm path + payload
  },
  speech: {
    transcribe: "/speech/transcribe", // TODO(backend): Whisper stays server-side
    synthesize: "/speech/synthesize", // TODO(backend): TTS service, if any
  },
  document: {
    createSession: "/documents/upload-session", // TODO(backend): confirm
    sessionStatus: "/documents/upload-session/", // + token
    upload: "/documents/upload-session/", // + token + /documents
  },
} as const;

/**
 * MOCK document service, served by this app's own route handlers.
 *
 * The QR flow is the one place the kiosk genuinely needs a second device to
 * talk to something, so the mock lives on the server instead of in memory.
 * It is a stand-in for the team's document service and is deleted the day
 * that service exists — it stores metadata only and never the file bytes.
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
