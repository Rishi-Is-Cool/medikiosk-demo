/* ==========================================================================
   MOCK document service — server-side, in-memory.

   ⚠ INTEGRATION POINT. Stands in for the team's document service so the
   QR → phone → kiosk loop is genuinely demoable across two devices before
   that service exists. Delete this file and the /api/mock routes the day it
   does, and point documentApi at the real endpoints.

   It deliberately does NOT keep file bytes. Build spec §11: documents belong
   in object storage, metadata in PostgreSQL. Holding images in a Node process
   would model the wrong architecture, so the bytes are measured and dropped.
   ========================================================================== */

import type {
  DocumentStatus,
  UploadSession,
  UploadSessionStatus,
  UploadedDocument,
} from "@/api/types";

const SESSION_TTL_MS = 10 * 60 * 1000;
/** How long a document "takes to process" before the kiosk sees it done. */
const PROCESSING_MS = 2500;

interface StoredDocument {
  document_id: string;
  file_name: string;
  size_bytes: number;
  received_at: number;
  failed: boolean;
}

interface StoredSession {
  token: string;
  kiosk_session_id: string;
  created_at: number;
  connected: boolean;
  documents: StoredDocument[];
}

/* Survives hot reload in dev, where module state is otherwise discarded. */
const store: Map<string, StoredSession> = (globalThis as { __mkUploadSessions?: Map<string, StoredSession> })
  .__mkUploadSessions ??= new Map();

function token(): string {
  return Math.random().toString(36).slice(2, 8) + Math.random().toString(36).slice(2, 8);
}

function expired(session: StoredSession): boolean {
  return Date.now() - session.created_at > SESSION_TTL_MS;
}

function documentStatus(doc: StoredDocument): DocumentStatus {
  if (doc.failed) return "failed";
  return Date.now() - doc.received_at > PROCESSING_MS ? "processed" : "processing";
}

function sessionStatus(session: StoredSession): UploadSessionStatus {
  if (expired(session)) return "expired";
  if (session.documents.length === 0) return session.connected ? "connected" : "waiting";
  return session.documents.some((d) => documentStatus(d) === "processing") ? "uploading" : "complete";
}

function toPublic(session: StoredSession): UploadSession {
  return {
    token: session.token,
    // Filled in by documentApi, which knows the browser's origin.
    upload_url: "",
    status: sessionStatus(session),
    expires_at: new Date(session.created_at + SESSION_TTL_MS).toISOString(),
    documents: session.documents.map<UploadedDocument>((d) => ({
      document_id: d.document_id,
      file_name: d.file_name,
      size_bytes: d.size_bytes,
      status: documentStatus(d),
      received_at: new Date(d.received_at).toISOString(),
    })),
  };
}

/* Drop sessions nobody is going to poll again, so a long-running dev server
   does not accumulate them. */
function sweep(): void {
  const cutoff = Date.now() - SESSION_TTL_MS * 2;
  for (const [key, session] of store) {
    if (session.created_at < cutoff) store.delete(key);
  }
}

export const uploadSessions = {
  create(kioskSessionId: string): UploadSession {
    sweep();
    const session: StoredSession = {
      token: token(),
      kiosk_session_id: kioskSessionId,
      created_at: Date.now(),
      connected: false,
      documents: [],
    };
    store.set(session.token, session);
    return toPublic(session);
  },

  get(tokenValue: string): UploadSession | null {
    const session = store.get(tokenValue);
    return session ? toPublic(session) : null;
  },

  connect(tokenValue: string): UploadSession | null {
    const session = store.get(tokenValue);
    if (!session || expired(session)) return null;
    session.connected = true;
    return toPublic(session);
  },

  addDocument(
    tokenValue: string,
    file: { name: string; size: number },
  ): UploadedDocument | "expired" | "unknown" {
    const session = store.get(tokenValue);
    if (!session) return "unknown";
    if (expired(session)) return "expired";

    const doc: StoredDocument = {
      document_id: `doc_${Math.random().toString(36).slice(2, 10)}`,
      file_name: file.name,
      size_bytes: file.size,
      received_at: Date.now(),
      failed: false,
    };
    session.connected = true;
    session.documents.push(doc);

    return {
      document_id: doc.document_id,
      file_name: doc.file_name,
      size_bytes: doc.size_bytes,
      status: "received",
      received_at: new Date(doc.received_at).toISOString(),
    };
  },
};
