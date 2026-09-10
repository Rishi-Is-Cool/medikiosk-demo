/* Registration, session creation and consent submission (build spec §8). */

import { ENDPOINTS, MOCK_LATENCY, USE_MOCKS, mockDelay } from "./config";
import { request } from "./http";
import { mockRegister, mockScanIdentity } from "@/mocks/patients";
import type {
  ConsentReceipt,
  ConsentSubmission,
  IdentityMethod,
  IdentityScanResult,
  PatientSessionInfo,
  RegistrationRequest,
} from "./types";

export const patientApi = {
  /** Creates the kiosk session. Identity is NOT verified — see mocks/patients. */
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
