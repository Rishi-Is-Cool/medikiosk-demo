/* ==========================================================================
   Frontend/API contracts.

   These are the shapes the KIOSK UI knows how to render. They are a frontend
   contract, not a mandated backend schema (build spec §9, §10). When the
   backend team finalises their payloads, adapt them to these types inside the
   api/ modules — do not reshape the components.
   ========================================================================== */

/* --- Session / patient ---------------------------------------------------- */

export type IdentityMethod = "abha" | "aadhaar" | "new";

/** What the kiosk knows about who is sitting in front of it.
 *  Deliberately minimal: the kiosk holds no clinical record of its own. */
export interface PatientSessionInfo {
  session_id: string;
  patient_ref: string;
  display_name: string;
  identity_method: IdentityMethod;
  /** Masked for display. The kiosk never holds a full ABHA/Aadhaar number. */
  masked_id?: string;
  age?: number;
  sex?: string;
}

export interface RegistrationRequest {
  identity_method: IdentityMethod;
  /** ABHA address / Aadhaar last digits / typed name, per method. */
  identifier?: string;
  language: LanguageCode;
  new_patient?: {
    name: string;
    age: string;
    sex: string;
    phone?: string;
  };
}

/* --- Language ------------------------------------------------------------- */

export type LanguageCode = "en" | "hi" | "mr" | "bn" | "ta" | "te";

/* --- Consent -------------------------------------------------------------- */

export interface ConsentItem {
  id: string;
  /** Required items block progress (build spec §15). */
  required: boolean;
}

export interface ConsentSubmission {
  session_id: string;
  granted: string[];
  declined: string[];
  language: LanguageCode;
  /** Set when the patient played the audio explanation at least once. */
  audio_explanation_played: boolean;
}

export interface ConsentReceipt {
  consent_id: string;
  accepted_at: string;
}

/* --- History mode / complaint --------------------------------------------- */

export type HistoryMode = "general_medicine" | "ayush";

export interface ChiefComplaintOption {
  id: string;
  /** Localised by the question service, not by the kiosk. */
  label: string;
  icon: string;
}

/* --- Intake --------------------------------------------------------------- */

export type QuestionInputType =
  | "voice_or_touch"
  | "voice_or_text"
  | "single_select"
  | "multi_select"
  | "scale";

export interface QuestionOption {
  value: string;
  label: string;
  icon?: string;
  /** Renders the option on its own row, e.g. a "none of these" escape. */
  exclusive?: boolean;
}

export interface QuestionProgress {
  current: number;
  /** An estimate. The engine may branch and change it (build spec §6.10). */
  estimated_total: number;
}

export interface IntakeQuestion {
  question_id: string;
  text: string;
  helper?: string;
  input_type: QuestionInputType;
  options: QuestionOption[];
  allow_voice: boolean;
  allow_text: boolean;
  progress: QuestionProgress;
}

/** Build spec §10. The kiosk consumes this; it never computes it. */
export interface PriorityState {
  priority: "normal" | "priority" | "urgent";
  red_flag: boolean;
  action: "continue" | "staff_assistance" | "immediate_assistance";
  reason_code?: string;
}

export interface IntakeResponse {
  /** null when the interview is finished. */
  question: IntakeQuestion | null;
  priority: PriorityState;
  complete: boolean;
}

export interface StartIntakeRequest {
  session_id: string;
  history_mode: HistoryMode;
  chief_complaint: string;
  chief_complaint_text?: string;
  language: LanguageCode;
}

export interface SubmitAnswerRequest {
  session_id: string;
  question_id: string;
  answer: AnswerPayload;
  language: LanguageCode;
}

export interface AnswerPayload {
  /** How the patient gave this answer — drives the provenance chip. */
  source: AnswerSource;
  /** Option values for select types. */
  values?: string[];
  /** Free text, or the accepted transcript for a spoken answer. */
  text?: string;
}

/** Matches the provenance vocabulary in tokens.css (.mk-chip-src). */
export type AnswerSource =
  | "patient_spoken"
  | "patient_touch"
  | "patient_typed"
  | "document"
  | "prior_encounter"
  | "clinician";

/* --- Speech --------------------------------------------------------------- */

export interface TranscriptResult {
  transcript: string;
  language: LanguageCode;
  /** 0..1. The kiosk uses this only to decide how firmly to ask for
   *  confirmation — never to make a clinical judgement. */
  confidence: number;
  duration_ms: number;
}

/** Structured extraction is produced by the backend/AI, never in React
 *  (build spec §6.8). The kiosk only displays what it is handed. */
export interface ExtractionResult {
  question_id: string;
  /** Short, patient-readable restatement of what was understood. */
  summary: string;
  fields: ExtractedField[];
  source: AnswerSource;
}

export interface ExtractedField {
  label: string;
  value: string;
}

/* --- Text to speech ------------------------------------------------------- */

export interface SpeechRequest {
  text: string;
  language: LanguageCode;
}

/* --- Documents ------------------------------------------------------------ */

export type UploadSessionStatus =
  | "waiting"
  | "connected"
  | "uploading"
  | "complete"
  | "expired";

export type DocumentStatus = "received" | "processing" | "processed" | "failed";

export interface UploadedDocument {
  document_id: string;
  file_name: string;
  size_bytes: number;
  status: DocumentStatus;
  /** Assigned by the document service, not guessed by the kiosk. */
  doc_type?: string;
  received_at: string;
}

export interface UploadSession {
  /** Opaque, short-lived. Carries no patient medical information (§11). */
  token: string;
  upload_url: string;
  status: UploadSessionStatus;
  documents: UploadedDocument[];
  expires_at: string;
}

/* --- Errors --------------------------------------------------------------- */

/** Every api module rejects with this. Screens map `code` to a patient-safe
 *  message; raw errors are never shown (build spec §15). */
export class ApiError extends Error {
  code: string;
  retryable: boolean;

  constructor(code: string, message: string, retryable = true) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.retryable = retryable;
  }
}
