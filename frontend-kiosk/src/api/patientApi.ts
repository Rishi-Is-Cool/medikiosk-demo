/* Registration, returning-patient lookup, session creation and consent
   submission (build spec §8). */

import { ENDPOINTS, MOCK_LATENCY, USE_MOCKS, mockDelay } from "./config";
import { request } from "./http";
import { mockLookup, mockRegister, mockScanIdentity } from "@/mocks/patients";
import type {
  ConsentReceipt,
  ConsentSubmission,
  IdentityMethod,
  IdentityScanResult,
  LookupRequest,
  PatientSessionInfo,
  RegistrationRequest,
} from "./types";

export const patientApi = {
  /**
   * Registers a first-time patient and opens the kiosk session.
   * Rejects with `http_409` when an attached ABHA/Aadhaar is already on file —
   * that patient has been here before and should be looked up instead.
   * Identity is NOT verified against any national database.
   */
  async register(payload: RegistrationRequest): Promise<PatientSessionInfo> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.slow);
      return mockRegister(payload);
    }

    return request<PatientSessionInfo>(ENDPOINTS.patient.register, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Finds a returning patient by the card they carry and opens a session.
   * Rejects with `http_404` when nobody is registered with that number and
   * `http_422` when it is not a well-formed ABHA/Aadhaar number.
   */
  async lookup(payload: LookupRequest): Promise<PatientSessionInfo> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.slow);
      return mockLookup(payload);
    }

    return request<PatientSessionInfo>(ENDPOINTS.patient.lookup, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Photograph of an ABHA card or Aadhaar in, identifier out.
   *
   * The problem statement's patient journey says the patient "enters/scans"
   * their ID, so scanning has to be offered — but reading the card is OCR,
   * which belongs to the document/AI layer, not to React. The kiosk uploads
   * the image and fills in whatever comes back, and the patient can correct
   * it. Nothing here verifies an identity against anything (build spec §19).
   */
  async scanIdentity(method: IdentityMethod, image: File): Promise<IdentityScanResult> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.slow);
      return mockScanIdentity(method);
    }

    const form = new FormData();
    form.append("image", image, image.name);
    form.append("identity_method", method);

    return request<IdentityScanResult>(ENDPOINTS.patient.scanIdentity, {
      method: "POST",
      body: form,
      timeoutMs: 30000,
    });
  },

  /**
   * Records what the patient agreed to.
   *
   * The kiosk captures and transmits consent. It does not, by itself,
   * constitute DPDP 2023 or ABDM consent-framework compliance — that lives in
   * the backend's consent artefact and audit trail (build spec §6.3).
   */
  async submitConsent(payload: ConsentSubmission): Promise<ConsentReceipt> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.normal);
      return {
        consent_id: `consent_${Math.random().toString(36).slice(2, 10)}`,
        accepted_at: new Date().toISOString(),
      };
    }

    return request<ConsentReceipt>(ENDPOINTS.patient.consent, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
