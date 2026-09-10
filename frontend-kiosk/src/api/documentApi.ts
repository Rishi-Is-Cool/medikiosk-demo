/* Upload sessions and document status (build spec §8, §11).

   The kiosk never receives, stores or interprets a document. It creates a
   short-lived upload session, shows the QR, and polls for status. The phone
   posts the file; the document service stores it and owns all OCR and
   extraction. */

import { ENDPOINTS, MOCK_DOCUMENT_API, USE_MOCKS, publicOrigin } from "./config";
import { request } from "./http";
import { ApiError, type UploadSession, type UploadedDocument } from "./types";

/** Where the phone should land. Encodes only the opaque session token — no
 *  patient identity and no medical information (build spec §11). */
export function uploadUrlFor(token: string): string {
  return `${publicOrigin()}/upload/${token}`;
}

/** The backend answers with a path relative to itself; the QR needs the
 *  kiosk's own public address, which only the kiosk knows. */
function withPublicUrl(session: UploadSession): UploadSession {
  return { ...session, upload_url: uploadUrlFor(session.token) };
}

export const documentApi = {
  async createUploadSession(sessionId: string, forceNew = false): Promise<UploadSession> {
    const path = USE_MOCKS ? MOCK_DOCUMENT_API : ENDPOINTS.document.createSession;
    const session = await request<UploadSession>(path, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, force_new: forceNew }),
    });
    return withPublicUrl(session);
  },

  async getUploadSession(token: string): Promise<UploadSession> {
    const path = USE_MOCKS
      ? `${MOCK_DOCUMENT_API}/${token}`
      : `${ENDPOINTS.document.sessionStatus}${token}`;

    return withPublicUrl(await request<UploadSession>(path));
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
    const path = USE_MOCKS
      ? `${MOCK_DOCUMENT_API}/${token}/connect`
      : `${ENDPOINTS.document.upload}${token}/connect`;
    await request(path, { method: "POST" });
  },
};
