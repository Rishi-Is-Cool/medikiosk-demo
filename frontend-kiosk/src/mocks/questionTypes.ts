/* Shapes shared by the two mock question banks (General Medicine and AYUSH).

   ⚠ Part of the MOCK question engine — see mocks/questions.ts for what that
   means and why it is temporary. */

import type { QuestionInputType, ScaleTone } from "@/api/types";
import type { Localized } from "@/i18n";

export interface MockOption {
  value: string;
  label: Localized;
  /** "None of these" — selecting it clears every other choice. */
  exclusive?: boolean;
}

export interface MockQuestion {
  id: string;
  text: Localized;
  helper?: Localized;
  input_type: QuestionInputType;
  options?: MockOption[];
  allow_voice?: boolean;
  allow_text?: boolean;
  /** Scale questions only. Dashavidha axes are "grade"; pain is "severity". */
  scale_tone?: ScaleTone;
}

/** A named run of questions. Sections exist so a thirty-question Dashavidha
 *  interview reads as four understandable parts rather than one long climb. */
export interface MockSection {
  id: string;
  label: Localized;
  questions: string[];
}
