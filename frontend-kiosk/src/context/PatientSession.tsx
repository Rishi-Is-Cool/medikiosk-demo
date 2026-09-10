"use client";

/* ==========================================================================
   The kiosk's whole state model (build spec §12).

   Deliberately in memory only. Nothing is written to localStorage or a
   cookie: a kiosk is a shared device in a public foyer, and the next patient
   must not be able to reach the previous patient's answers by pressing Back.
   Reload is a reset, and that is the correct behaviour here.
   ========================================================================== */

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
  type Dispatch,
  type ReactNode,
} from "react";
import { LanguageProvider } from "@/i18n/LanguageProvider";
import { DEFAULT_LANGUAGE } from "@/i18n/languages";
import type {
  AnswerPayload,
  ExtractionResult,
  HistoryMode,
  IntakeQuestion,
  LanguageCode,
  PatientSessionInfo,
  PriorityState,
  UploadSession,
} from "@/api/types";

export interface StoredAnswer {
  question_id: string;
  question_text: string;
  payload: AnswerPayload;
  extraction?: ExtractionResult;
}

export interface ChiefComplaint {
  /** Every complaint the patient chose — they may have more than one. */
  ids: string[];
  /** The chosen labels, joined for display. */
  label: string;
  /** The patient's own words, spoken or typed, when they gave any. */
  text?: string;
}

interface State {
  language: LanguageCode;
  patient: PatientSessionInfo | null;
  consentGranted: string[];
  consentId: string | null;
  historyMode: HistoryMode | null;
  complaint: ChiefComplaint | null;
  question: IntakeQuestion | null;
  answers: Record<string, StoredAnswer>;
  priority: PriorityState | null;
  intakeComplete: boolean;
  documentSession: UploadSession | null;
  documentsSkipped: boolean;
}

const initialState: State = {
  language: DEFAULT_LANGUAGE,
  patient: null,
  consentGranted: [],
  consentId: null,
  historyMode: null,
  complaint: null,
  question: null,
  answers: {},
  priority: null,
  intakeComplete: false,
  documentSession: null,
  documentsSkipped: false,
};

type Action =
  | { type: "setLanguage"; language: LanguageCode }
  | { type: "setPatient"; patient: PatientSessionInfo }
  | { type: "setConsent"; granted: string[]; consentId: string }
  | { type: "setHistoryMode"; mode: HistoryMode }
  | { type: "setComplaint"; complaint: ChiefComplaint }
  | { type: "setQuestion"; question: IntakeQuestion | null }
  | { type: "recordAnswer"; answer: StoredAnswer }
  | { type: "setPriority"; priority: PriorityState }
  | { type: "setIntakeComplete"; complete: boolean }
  | { type: "setDocumentSession"; session: UploadSession | null }
  | { type: "skipDocuments" }
  | { type: "reset" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "setLanguage":
      return { ...state, language: action.language };
    case "setPatient":
      return { ...state, patient: action.patient };
    case "setConsent":
      return { ...state, consentGranted: action.granted, consentId: action.consentId };
    case "setHistoryMode":
      return { ...state, historyMode: action.mode };
    case "setComplaint":
      // A new complaint invalidates any interview already in progress.
      return { ...state, complaint: action.complaint, answers: {}, question: null, priority: null, intakeComplete: false };
    case "setQuestion":
      return { ...state, question: action.question };
    case "recordAnswer":
      return {
        ...state,
        answers: { ...state.answers, [action.answer.question_id]: action.answer },
      };
    case "setPriority":
      return { ...state, priority: action.priority };
    case "setIntakeComplete":
      return { ...state, intakeComplete: action.complete };
    case "setDocumentSession":
      return { ...state, documentSession: action.session };
    case "skipDocuments":
      return { ...state, documentsSkipped: true };
    case "reset":
      // Keep the language: the next patient sees the language screen anyway,
      // and resetting it mid-flow would flip the UI to English under them.
      return { ...initialState, language: state.language };
  }
}

interface ContextValue extends State {
  dispatch: Dispatch<Action>;
  /** Clears everything the kiosk holds about this patient (build spec §6.14). */
  reset: () => void;
  answeredCount: number;
}

const PatientSessionContext = createContext<ContextValue | null>(null);

export function PatientSessionProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  const reset = useCallback(() => dispatch({ type: "reset" }), []);

  const value = useMemo<ContextValue>(
    () => ({
      ...state,
      dispatch,
      reset,
      answeredCount: Object.keys(state.answers).length,
    }),
    [state, reset],
  );

  return (
    <PatientSessionContext.Provider value={value}>
      <LanguageProvider language={state.language}>{children}</LanguageProvider>
    </PatientSessionContext.Provider>
  );
}

export function usePatientSession(): ContextValue {
  const ctx = useContext(PatientSessionContext);
  if (!ctx) throw new Error("usePatientSession must be used inside a PatientSessionProvider");
  return ctx;
}
