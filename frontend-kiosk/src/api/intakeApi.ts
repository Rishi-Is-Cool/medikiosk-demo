/* Start intake, fetch questions, submit answers, receive priority state
   (build spec §8). The kiosk asks what to show next; it never decides. */

import { ENDPOINTS, MOCK_LATENCY, USE_MOCKS, mockDelay } from "./config";
import { request } from "./http";
import { mockExtraction } from "@/mocks/extraction";
import { mockComplaints, mockMatchComplaint, mockNextQuestion } from "@/mocks/questions";
import {
  ApiError,
  type AnswerPayload,
  type ChiefComplaintOption,
  type ComplaintMatch,
  type ExtractionResult,
  type HistoryMode,
  type IntakeResponse,
  type LanguageCode,
  type QueueInfo,
  type StartIntakeRequest,
  type SubmitAnswerRequest,
} from "./types";

/* --- Mock interview memory ------------------------------------------------
   Stands in for server-side session state. Keyed by session id so a restarted
   session starts clean, exactly as the real service would behave.          */

interface MockInterview {
  complaint: string;
  historyMode: HistoryMode;
  answers: Record<string, AnswerPayload>;
}

const mockInterviews = new Map<string, MockInterview>();

/** The mock bank scripts one line of questioning; pick the most specific. */
function mockComplaintFor(ids: string[]): string {
  if (ids.includes("chest_pain")) return "chest_pain";
  if (ids.some((id) => id === "fever" || id === "cough_cold" || id === "fever_cough")) return "fever_cough";
  return ids[0] ?? "other";
}

const COMPLETE: IntakeResponse = {
  question: null,
  priority: { priority: "normal", red_flag: false, action: "continue" },
  complete: true,
};

export const intakeApi = {
  async getComplaints(language: LanguageCode): Promise<ChiefComplaintOption[]> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.fast);
      return mockComplaints(language);
    }

    return request<ChiefComplaintOption[]>(
      `${ENDPOINTS.intake.complaints}?language=${language}`,
    );
  },

  /**
   * Map a spoken complaint onto the known complaint list.
   *
   * The problem statement's own example opens with the patient *saying* their
   * complaint — "on stating 'chest pain', it probes onset, character..." — so
   * the complaint screen needs a voice path like every other question. Which
   * words mean which complaint is the question service's business, because it
   * is the same component that decides what line of questioning to open. An
   * empty match is a valid answer, not a failure: the words are carried
   * through as a free-text complaint rather than thrown away.
   */
  async matchComplaint(transcript: string, language: LanguageCode): Promise<ComplaintMatch> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.fast);
      return mockMatchComplaint(transcript, language);
    }

    return request<ComplaintMatch>(ENDPOINTS.intake.matchComplaint, {
      method: "POST",
      body: JSON.stringify({ transcript, language }),
    });
  },

  async startIntake(payload: StartIntakeRequest): Promise<IntakeResponse> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.normal);
      const complaint = mockComplaintFor(payload.chief_complaints);
      mockInterviews.set(payload.session_id, {
        complaint,
        historyMode: payload.history_mode,
        answers: {},
      });
      return mockNextQuestion(complaint, payload.history_mode, {}, payload.language);
    }

    return request<IntakeResponse>(ENDPOINTS.intake.start, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Re-fetch the question the interview is currently sitting on.
   *
   * Needed because language is changeable at any moment from the top bar: the
   * chrome re-renders from the dictionary, but question text is localised by
   * the engine, so it has to be asked for again. Without this a patient who
   * switches language mid-interview keeps reading the old one.
   */
  async getCurrentQuestion(sessionId: string, language: LanguageCode): Promise<IntakeResponse> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.fast);
      const interview = mockInterviews.get(sessionId);
      if (!interview) {
        throw new ApiError("unknown_session", `No mock interview for ${sessionId}`, false);
      }
      return mockNextQuestion(
        interview.complaint,
        interview.historyMode,
        interview.answers,
        language,
      );
    }

    return request<IntakeResponse>(
      `${ENDPOINTS.intake.question}?session_id=${encodeURIComponent(sessionId)}&language=${language}`,
    );
  },

  /**
   * Structure a raw answer into clinical fields.
   *
   * Backend/AI work (build spec §6.8). Called before submitAnswer so the
   * patient can confirm what was understood from a spoken answer. Touch and
   * typed answers skip this — there is nothing to interpret, and an extra
   * confirmation tap on every question is a real cost to a slow, tired user.
   */
  async extractAnswer(payload: SubmitAnswerRequest): Promise<ExtractionResult> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.normal);
      return mockExtraction(payload.question_id, payload.answer, payload.language);
    }

    return request<ExtractionResult>(ENDPOINTS.intake.answer, {
      method: "POST",
      body: JSON.stringify({ ...payload, mode: "extract" }),
    });
  },

  /** Records the answer and returns the next question plus priority state. */
  async submitAnswer(payload: SubmitAnswerRequest): Promise<IntakeResponse> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.normal);
      const interview = mockInterviews.get(payload.session_id);
      if (!interview) {
        // The real service would 404 an unknown session; behave the same way
        // so the screen's error path is exercised.
        return COMPLETE;
      }
      interview.answers[payload.question_id] = payload.answer;
      return mockNextQuestion(
        interview.complaint,
        interview.historyMode,
        interview.answers,
        payload.language,
      );
    }

    return request<IntakeResponse>(ENDPOINTS.intake.answer, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * DEMO ONLY: answer every remaining question with the engine's default and
   * finish the interview. The backend records these as sample answers, never
   * as something the patient said. Shown only when NEXT_PUBLIC_DEMO_SKIP=true.
   */
  async autofill(sessionId: string, language: LanguageCode): Promise<IntakeResponse> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.normal);
      mockInterviews.delete(sessionId);
      return COMPLETE;
    }

    return request<IntakeResponse>(ENDPOINTS.intake.autofill, {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, language }),
      timeoutMs: 30000,
    });
  },

  /** The patient's OPD token and how many patients are ahead of them. */
  async getQueue(sessionId: string): Promise<QueueInfo> {
    if (USE_MOCKS) {
      await mockDelay(MOCK_LATENCY.fast);
      const issued = new Date();
      return {
        token: 7,
        queue_date: issued.toISOString().slice(0, 10),
        issued_at: issued.toISOString(),
        patients_ahead: 3,
        doctor_name: "Dr. S. Nair",
        department: "General Medicine OPD",
      };
    }

    return request<QueueInfo>(`${ENDPOINTS.intake.queue}?session_id=${encodeURIComponent(sessionId)}`);
  },

  /** Kiosk session ended — drop anything held for it (build spec §6.14). */
  clearMockSession(sessionId: string): void {
    mockInterviews.delete(sessionId);
  },
};
