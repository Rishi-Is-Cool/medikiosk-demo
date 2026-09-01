/* ==========================================================================
   MOCK patient identity.

   ⚠ INTEGRATION POINT. There is no ABHA or Aadhaar verification here and
   there must not be (build spec §6.2, §19). This returns a plausible session
   so the rest of the journey has something to hang on. Nothing it produces
   may be described as verified identity.
   ========================================================================== */

import type { PatientSessionInfo, RegistrationRequest } from "@/api/types";

/** A couple of fixtures so a demo can show the "returning patient" case.
 *  Any other identifier registers as a first-time visitor. */
const KNOWN: Record<string, Omit<PatientSessionInfo, "session_id" | "identity_method">> = {
  "12-3456-7890-1234": {
    patient_ref: "PT-10482",
    display_name: "Sunita Deshmukh",
    masked_id: "••-••••-••••-1234",
    age: 54,
    sex: "F",
  },
  "9876": {
    patient_ref: "PT-10517",
    display_name: "Ramesh Kumar",
    masked_id: "•••• •••• 9876",
    age: 61,
    sex: "M",
  },
};

function newSessionId(): string {
  return `sess_${Math.random().toString(36).slice(2, 10)}`;
}

function maskIdentifier(method: RegistrationRequest["identity_method"], raw: string): string {
  const tail = raw.replace(/\D/g, "").slice(-4);
  if (!tail) return "";
  return method === "aadhaar" ? `•••• •••• ${tail}` : `••-••••-••••-${tail}`;
}

export function mockRegister(request: RegistrationRequest): PatientSessionInfo {
  const session_id = newSessionId();

  if (request.identity_method === "new") {
    const details = request.new_patient;
    return {
      session_id,
      patient_ref: `PT-${Math.floor(10000 + Math.random() * 89999)}`,
      display_name: details?.name?.trim() || "New patient",
      identity_method: "new",
      age: details?.age ? Number(details.age) : undefined,
      sex: details?.sex,
    };
  }

  const key = (request.identifier ?? "").trim();
  const known = KNOWN[key];

  if (known) {
    return { session_id, identity_method: request.identity_method, ...known };
  }

  return {
    session_id,
    patient_ref: `PT-${Math.floor(10000 + Math.random() * 89999)}`,
    display_name: "Patient",
    identity_method: request.identity_method,
    masked_id: maskIdentifier(request.identity_method, key),
  };
}
