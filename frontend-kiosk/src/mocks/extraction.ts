/* ==========================================================================
   MOCK clinical extraction.

   ⚠ INTEGRATION POINT. Turning a sentence into structured clinical fields is
   the backend/AI's job — build spec §6.8 is explicit that no extraction logic
   lives in React. This file fakes the *result* so the kiosk can render the
   confirmation step ("you said … is this right?") during mock development.

   The kiosk shows the patient a plain restatement. It never shows model
   reasoning, confidence internals or clinical interpretation (§6.11).
   ========================================================================== */

import type { AnswerPayload, ExtractionResult, LanguageCode } from "@/api/types";
import { resolveLocalized, type Localized } from "@/i18n";
import { mockOptionLabel } from "./questions";

/** Field label the doctor's summary would carry this answer under. */
const FIELD_LABEL: Record<string, Localized> = {
  cp_site: { en: "Site", hi: "जगह" },
  cp_onset: { en: "Onset", hi: "शुरुआत" },
  cp_character: { en: "Character", hi: "कैसा दर्द" },
  cp_radiation: { en: "Radiation", hi: "फैलाव" },
  cp_associated: { en: "Associated symptoms", hi: "साथ के लक्षण" },
  cp_severity: { en: "Severity", hi: "तीव्रता" },
  cp_relief: { en: "Aggravating and relieving factors", hi: "बढ़ाने/घटाने वाली बातें" },
  fc_duration: { en: "Duration", hi: "अवधि" },
  fc_pattern: { en: "Pattern", hi: "प्रकार" },
  fc_measured: { en: "Recorded temperature", hi: "नापा गया तापमान" },
  fc_cough: { en: "Cough", hi: "खाँसी" },
  fc_sputum: { en: "Sputum", hi: "बलगम" },
  fc_associated: { en: "Associated symptoms", hi: "साथ के लक्षण" },
  gen_describe: { en: "Presenting complaint", hi: "मुख्य तकलीफ़" },
  gen_duration: { en: "Duration", hi: "अवधि" },
  gen_severity: { en: "Functional impact", hi: "रोज़मर्रा पर असर" },
  hx_conditions: { en: "Past medical history", hi: "पुरानी बीमारियाँ" },
  hx_medications: { en: "Current medication", hi: "चल रही दवाएँ" },
  hx_medications_list: { en: "Medicines", hi: "दवाएँ" },
  hx_allergies: { en: "Allergy history", hi: "एलर्जी" },
  hx_allergies_list: { en: "Allergen", hi: "किससे एलर्जी" },
};

/** What the extractor pulls out of the canned spoken answers in
 *  mocks/transcripts.ts. Keyed the same way. */
const SPOKEN_VALUE: Record<string, Localized> = {
  cp_site: { en: "Central chest", hi: "छाती के बीच में" },
  cp_onset: { en: "This morning, on exertion", hi: "आज सुबह, चलते समय" },
  cp_character: { en: "Heavy, pressing", hi: "भारी, दबाव जैसा" },
  cp_radiation: { en: "To the left arm", hi: "बाएँ हाथ तक" },
  cp_associated: { en: "Sweating, breathlessness", hi: "पसीना, साँस फूलना" },
  cp_severity: { en: "Severe", hi: "तेज़" },
  cp_relief: { en: "Worse on walking, better on rest", hi: "चलने पर बढ़े, आराम पर कम" },
  fc_duration: { en: "3 days", hi: "3 दिन" },
  fc_pattern: { en: "Evening rise, settles by morning", hi: "शाम को चढ़े, सुबह उतरे" },
  fc_measured: { en: "102 °F at home", hi: "घर पर 102 °F" },
  fc_cough: { en: "Productive cough", hi: "बलगम वाली खाँसी" },
  fc_sputum: { en: "Yellow", hi: "पीला" },
  fc_associated: { en: "Body ache, headache", hi: "बदन दर्द, सिरदर्द" },
  gen_describe: { en: "Right knee pain, 1 month, worse on stairs", hi: "दाहिने घुटने में दर्द, 1 महीना, सीढ़ी पर ज़्यादा" },
  gen_duration: { en: "About 1 month", hi: "लगभग 1 महीना" },
  gen_severity: { en: "Limits heavy work", hi: "भारी काम नहीं कर पाते" },
  hx_conditions: { en: "Diabetes (8 years), hypertension", hi: "मधुमेह (8 साल), हाई ब्लड प्रेशर" },
  hx_medications: { en: "Yes, daily", hi: "हाँ, रोज़" },
  hx_medications_list: { en: "Metformin, one antihypertensive (name not recalled)", hi: "मेटफॉर्मिन, ब्लड प्रेशर की एक दवा (नाम याद नहीं)" },
  hx_allergies: { en: "Yes", hi: "हाँ" },
  hx_allergies_list: { en: "Penicillin — rash", hi: "पेनिसिलिन — चकत्ते" },
};

function label(questionId: string, language: LanguageCode): string {
  const l = FIELD_LABEL[questionId];
  return l ? resolveLocalized(l, language) : questionId;
}

export function mockExtraction(
  questionId: string,
  answer: AnswerPayload,
  language: LanguageCode,
): ExtractionResult {
  // Touch and typed answers need no interpretation — the patient already
  // said exactly what they meant. The "extraction" is just a readback.
  if (answer.source === "patient_touch") {
    const chosen = (answer.values ?? []).map((v) => mockOptionLabel(questionId, v, language));
    const summary = chosen.join(", ");
    return {
      question_id: questionId,
      summary,
      fields: [{ label: label(questionId, language), value: summary }],
      source: "patient_touch",
    };
  }

  if (answer.source === "patient_typed") {
    const text = answer.text ?? "";
    return {
      question_id: questionId,
      summary: text,
      fields: [{ label: label(questionId, language), value: text }],
      source: "patient_typed",
    };
  }

  const spoken = SPOKEN_VALUE[questionId];
  const value = spoken ? resolveLocalized(spoken, language) : (answer.text ?? "");

  return {
    question_id: questionId,
    summary: value,
    fields: [{ label: label(questionId, language), value }],
    source: "patient_spoken",
  };
}
