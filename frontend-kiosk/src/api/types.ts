/* ==========================================================================
   Frontend/API contracts.

   These are the shapes the KIOSK UI knows how to render. They are a frontend
   contract, not a mandated backend schema (build spec §9, §10). When the
   backend team finalises their payloads, adapt them to these types inside the
   api/ modules — do not reshape the components.
   ========================================================================== */

/* --- Session / patient ---------------------------------------------------- */

export type IdentityMethod = "abha" | "aadhaar" | "new";

/** The two cards a returning patient can be found by. */
export type IdentityCard = "abha" | "aadhaar";

/** What the kiosk knows about who is sitting in front of it.
 *  Deliberately minimal: the kiosk holds no clinical record of its own. */
export interface PatientSessionInfo {
  session_id: string;
  patient_ref: string;
  display_name: string;
  identity_method: IdentityMethod;
  /** Masked for display. The kiosk never holds a full ABHA/Aadhaar number. */
  masked_id?: string | null;
  age?: number;
  sex?: string;
  /** True when the patient was found by ID rather than newly registered. */
  returning?: boolean;
  /** YYYY-MM-DD of the previous visit, when there was one. */
  last_visit?: string | null;
}

/**
 * What came back from photographing an ABHA card or Aadhaar.
 *
 * Reading an identity card is OCR — the same class of work the document
 * service already owns, and emphatically not something the kiosk attempts.
 * The frontend photographs, uploads, and fills in whatever identifier it is
 * handed back; the patient can always correct it or type instead.
 */
export interface IdentityScanResult {
  identity_method: IdentityMethod;
  /** The number as read, or null when the card could not be read. Never
   *  presented as verified — nothing is verified. */
  identifier: string | null;
  name?: string | null;
  confidence?: number;
}

/** First-time registration. The ABHA/Aadhaar numbers are optional: attaching
 *  one now is what lets the patient be found by it on their next visit. */
export interface RegistrationRequest {
  identity_method: IdentityMethod;
  identifier?: string;
  language: LanguageCode;
  new_patient?: {
    name: string;
    age: string;
    sex: string;
    phone?: string;
  };
  abha_number?: string;
  aadhaar_number?: string;
}

/** Returning patient: find their record by the card they carry. */
export interface LookupRequest {
  identity_method: IdentityCard;
  identifier: string;
  language: LanguageCode;
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

/**
 * Result of mapping a spoken complaint onto the known complaint list.
 *
 * The complaint taxonomy belongs to the question service — it is the same
 * component that decides which line of questioning a complaint opens. The
 * kiosk sends words and renders the answer. A patient may name several
 * problems in one breath ("fever and a headache"), so every match comes back.
 * When nothing matches, the spoken text is carried through as a free-text
 * complaint rather than discarded.
 */
export interface ComplaintMatch {
  /** The first match, kept for older callers. */
  complaint: ChiefComplaintOption | null;
  complaints?: ChiefComplaintOption[];
  transcript: string;
}

/* --- Intake --------------------------------------------------------------- */

export type QuestionInputType =
  | "voice_or_touch"
  | "voice_or_text"
  | "single_select"
  | "multi_select"
  | "scale";

/**
 * Which way a scale's meaning runs — the engine must say, because the two
 * directions are opposites and the UI cannot guess.
 *
 * `severity`: last option is the worst (mild → worst pain). Warrants the
 * warning-to-emergency ramp.
 *
 * `grade`: last option is the best. The Dashavidha axes are ordered
 * avara → madhyama → pravara, least to optimum, matching the doctor console.
 * These get a neutral ramp: running severity colours over them would paint
 * "strong and glossy hair" red, and would also tell a patient their own
 * constitution is an alarm state, which it is not.
 */
export type ScaleTone = "severity" | "grade";

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

/**
 * Where this question sits in the interview.
 *
 * A General Medicine intake is short enough that a single "question 3 of 8"
 * carries it. A Dashavidha Pariksha interview is not — it runs to thirty-odd
 * questions across several unrelated topics, and a patient watching a bar
 * crawl from 3/30 to 4/30 has no idea whether they are nearly done or barely
 * started. Naming the part they are in is what makes the length bearable.
 */
export interface QuestionSection {
  id: string;
  /** Localised by the question service, like the question text itself. */
  label: string;
  index: number;
  total: number;
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
  /** Absent for short interviews that do not need sectioning. */
  section?: QuestionSection;
  /** Only meaningful when input_type is "scale". Defaults to severity. */
  scale_tone?: ScaleTone;
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
  /** Every complaint the patient chose — the interview covers all of them. */
  chief_complaints: string[];
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
  /** Links a spoken answer to the stored transcript it came from. */
  transcript_id?: string;
}

/** Matches the provenance vocabulary in tokens.css (.mk-chip-src). */
export type AnswerSource =
  | "patient_spoken"
  | "patient_touch"
  | "patient_typed"
  | "document"
  | "prior_encounter"
  | "clinician";

/** The patient's OPD token, counted live by the backend. */
export interface QueueInfo {
  token: number;
  /** YYYY-MM-DD, the hospital's (India) calendar day the token belongs to. */
  queue_date: string;
  /** ISO timestamp (UTC) when the token was issued. */
  issued_at: string;
  /** Same doctor, same day, earlier token, not yet seen. */
  patients_ahead: number;
  doctor_name?: string | null;
  department?: string | null;
  priority?: string;
}

/* --- Speech --------------------------------------------------------------- */

export interface TranscriptResult {
  /** Present when the speech service kept the transcript as evidence. */
  transcript_id?: string;
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
  /** The options a spoken answer was mapped onto, when it was. */
  values?: string[];
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
