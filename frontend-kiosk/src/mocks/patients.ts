/* ==========================================================================
   MOCK patient identity.

   ⚠ INTEGRATION POINT. There is no ABHA or Aadhaar verification here and
   there must not be (build spec §6.2, §19). This returns a plausible session
   so the rest of the journey has something to hang on. Nothing it produces
   may be described as verified identity.
   ========================================================================== */

import {
  ApiError,
  type IdentityMethod,
  type IdentityScanResult,
  type LookupRequest,
  type PatientSessionInfo,
  type RegistrationRequest,
} from "@/api/types";

/** A couple of fixtures so a demo can show the "returning patient" case,
 *  keyed by the ID's digits. Any other number is "not found". */
const KNOWN: Record<string, Omit<PatientSessionInfo, "session_id" | "identity_method">> = {
  "12345678901234": {
    patient_ref: "PT-10482",
    display_name: "Sunita Deshmukh",
    masked_id: "XX-XXXX-XXXX-1234",
    age: 54,
    sex: "female",
    returning: true,
    last_visit: "2026-06-12",
  },
  "234567899876": {
    patient_ref: "PT-10517",
    display_name: "Ramesh Kumar",
    masked_id: "XXXX XXXX 9876",
    age: 61,
    sex: "male",
    returning: true,
    last_visit: "2026-08-02",
  },
};

function digits(raw: string | undefined): string {
  return (raw ?? "").replace(/\D/g, "");
}

function newSessionId(): string {
  return `sess_${Math.random().toString(36).slice(2, 10)}`;
}

function maskIdentifier(method: IdentityMethod, raw: string): string {
  const tail = digits(raw).slice(-4);
  if (!tail) return "";
  return method === "aadhaar" ? `XXXX XXXX ${tail}` : `XX-XXXX-XXXX-${tail}`;
}

/**
 * MOCK card OCR.
 *
 * Returns the known fixture so a scan demo lands on the "returning patient"
 * path. No image is inspected — the real service reads the card.
 */
export function mockScanIdentity(method: IdentityMethod): IdentityScanResult {
  return {
    identity_method: method,
    identifier: method === "aadhaar" ? "234567899876" : "12345678901234",
    confidence: 0.96,
  };
}

export function mockLookup(request: LookupRequest): PatientSessionInfo {
  const known = KNOWN[digits(request.identifier)];
  if (!known) {
    throw new ApiError("http_404", "No mock patient with that ID", false);
  }
  return { session_id: newSessionId(), identity_method: request.identity_method, ...known };
}

export function mockRegister(request: RegistrationRequest): PatientSessionInfo {
  const id = digits(request.abha_number) || digits(request.aadhaar_number);
  if (id && KNOWN[id]) {
    throw new ApiError("http_409", "That ID is already registered", false);
  }

  const method: IdentityMethod = request.abha_number ? "abha" : request.aadhaar_number ? "aadhaar" : "new";
  const details = request.new_patient;
  return {
    session_id: newSessionId(),
    patient_ref: `PT-${Math.floor(10000 + Math.random() * 89999)}`,
    display_name: details?.name?.trim() || "New patient",
    identity_method: method,
    masked_id: id ? maskIdentifier(method, id) : null,
    age: details?.age ? Number(details.age) : undefined,
    sex: details?.sex,
    returning: false,
    last_visit: null,
  };
}
