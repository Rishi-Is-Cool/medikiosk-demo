/* Upload sessions and document status (build spec §8, §11).

   The kiosk never receives, stores or interprets a document. It creates a
   short-lived upload session, shows the QR, and polls for status. The phone
   posts the file; the document service stores the bytes in object storage and
   owns all OCR and extraction. */

import { ENDPOINTS, MOCK_DOCUMENT_API, USE_MOCKS, publicOrigin } from "./config";
import { request } from "./http";
import { ApiError, type UploadSession, type UploadedDocument } from "./types";

/** Where the phone should land. Encodes only the opaque session token — no
 *  patient identity and no medical information (build spec §11). */
export function uploadUrlFor(token: string): string {
  return `${publicOrigin()}/upload/${token}`;
}

export const documentApi = {
  async createUploadSession(sessionId: string, forceNew = false): Promise<UploadSession> {
    if (USE_MOCKS) {
      const session = await request<UploadSession>(MOCK_DOCUMENT_API, {
        method: "POST",
        body: JSON.stringify({ session_id: sessionId, force_new: forceNew }),
      });
      return { ...session, upload_url: uploadUrlFor(session.token) };
    }

    return request<UploadSession>(ENDPOINTS.document.createSession, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  async getUploadSession(token: string): Promise<UploadSession> {
    const path = USE_MOCKS
      ? `${MOCK_DOCUMENT_API}/${token}`
      : `${ENDPOINTS.document.sessionStatus}${token}`;

    const session = await request<UploadSession>(path);
    return { ...session, upload_url: uploadUrlFor(session.token) };
  },

  /** Called from the patient's phone, not the kiosk. */
  async uploadDocument(token: string, file: File): Promise<UploadedDocument> {
    const form = new FormData();
    form.append("file", file, file.name);

    const path = USE_MOCKS
      ? `${MOCK_DOCUMENT_API}/${token}/documents`
      : `${ENDPOINTS.document.upload}${token}/documents`;

    try {
      return await request<UploadedDocument>(path, {
        method: "POST",
        body: form,
        timeoutMs: 45000,
      });
    } catch (error) {
      if (error instanceof ApiError && error.code === "http_410") {
        throw new ApiError("session_expired", "Upload session expired", false);
      }
      throw error;
    }
  },

  /** The phone announcing itself, so the kiosk can stop saying "waiting". */
  async markConnected(token: string): Promise<void> {
    if (!USE_MOCKS) return;
    await request(`${MOCK_DOCUMENT_API}/${token}/connect`, { method: "POST" });
  },
};
