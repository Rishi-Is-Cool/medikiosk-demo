/* ==========================================================================
   MOCK question engine — a stand-in for a backend service.

   ⚠ INTEGRATION POINT. Everything in this file is logic the frontend does not
   own (build spec §6.6, §10, §19): which question comes next, how the
   interview branches, and whether an answer combination warrants priority.
   It lives here, behind intakeApi, so that the UI can be built and demoed
   before the backend exists — and so that deleting this file and pointing
   intakeApi at the real service changes no screen and no component.

   The question order below follows SOCRATES for pain and a conventional
   fever/cough line of questioning, per the team's MVP scope. It is a
   demo script, NOT a clinical protocol, and it must be reviewed by the
   clinical members of the team before it is shown to a real patient.
   ========================================================================== */

import type {
  AnswerPayload,
  ChiefComplaintOption,
  IntakeQuestion,
  LanguageCode,
  PriorityState,
  QuestionInputType,
} from "@/api/types";
import { resolveLocalized, type Localized } from "@/i18n";

interface MockOption {
  value: string;
  label: Localized;
  /** "None of these" — selecting it clears every other choice. */
  exclusive?: boolean;
}

interface MockQuestion {
  id: string;
  text: Localized;
  helper?: Localized;
  input_type: QuestionInputType;
  options?: MockOption[];
  allow_voice?: boolean;
  allow_text?: boolean;
}

/* --- Chief complaints ----------------------------------------------------- */

const COMPLAINTS: Array<{ id: string; label: Localized; icon: string }> = [
  { id: "fever_cough", label: { en: "Fever or cough", hi: "बुखार या खाँसी" }, icon: "thermometer" },
  { id: "chest_pain", label: { en: "Chest pain", hi: "छाती में दर्द" }, icon: "heart" },
  { id: "stomach", label: { en: "Stomach pain", hi: "पेट में दर्द" }, icon: "stomach" },
  { id: "headache", label: { en: "Headache", hi: "सिरदर्द" }, icon: "head" },
  { id: "breathing", label: { en: "Breathing difficulty", hi: "साँस लेने में तकलीफ़" }, icon: "lungs" },
];

export function mockComplaints(language: LanguageCode): ChiefComplaintOption[] {
  return COMPLAINTS.map((c) => ({
    id: c.id,
    label: resolveLocalized(c.label, language),
    icon: c.icon,
  }));
}

/* --- Question bank -------------------------------------------------------- */

const BANK: Record<string, MockQuestion> = {
  /* ---- Chest pain — SOCRATES ---- */

  cp_site: {
    id: "cp_site",
    text: { en: "Where exactly do you feel the pain?", hi: "दर्द ठीक कहाँ महसूस होता है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "centre", label: { en: "In the centre of the chest", hi: "छाती के बीच में" } },
      { value: "left", label: { en: "On the left side", hi: "बाईं ओर" } },
      { value: "right", label: { en: "On the right side", hi: "दाईं ओर" } },
      { value: "upper_abdomen", label: { en: "In the upper stomach", hi: "पेट के ऊपरी हिस्से में" } },
      { value: "whole", label: { en: "All over the chest", hi: "पूरी छाती में" } },
    ],
  },

  cp_onset: {
    id: "cp_onset",
    text: { en: "When did the pain start?", hi: "दर्द कब शुरू हुआ?" },
    input_type: "voice_or_touch",
    options: [
      { value: "minutes", label: { en: "In the last few minutes", hi: "पिछले कुछ मिनटों में" } },
      { value: "hours", label: { en: "Today, a few hours ago", hi: "आज, कुछ घंटे पहले" } },
      { value: "days", label: { en: "A few days ago", hi: "कुछ दिन पहले" } },
      { value: "weeks", label: { en: "More than a week ago", hi: "एक हफ़्ते से ज़्यादा पहले" } },
    ],
  },

  cp_character: {
    id: "cp_character",
    text: { en: "What does the pain feel like?", hi: "दर्द कैसा महसूस होता है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "pressing", label: { en: "Heavy, like pressure", hi: "भारीपन या दबाव जैसा" } },
      { value: "burning", label: { en: "Burning", hi: "जलन जैसा" } },
      { value: "sharp", label: { en: "Sharp, like a needle", hi: "तेज़, सुई चुभने जैसा" } },
      { value: "dull", label: { en: "A dull ache", hi: "हल्का लगातार दर्द" } },
    ],
  },

  cp_radiation: {
    id: "cp_radiation",
    text: { en: "Does the pain travel anywhere else?", hi: "क्या दर्द कहीं और फैलता है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "left_arm", label: { en: "To the left arm or shoulder", hi: "बाएँ हाथ या कंधे तक" } },
      { value: "jaw_neck", label: { en: "To the jaw or neck", hi: "जबड़े या गर्दन तक" } },
      { value: "back", label: { en: "To the back", hi: "पीठ तक" } },
      { value: "none", label: { en: "It stays in one place", hi: "यह एक ही जगह रहता है" }, exclusive: true },
    ],
  },

  cp_associated: {
    id: "cp_associated",
    text: {
      en: "Along with the pain, do you have any of these?",
      hi: "दर्द के साथ क्या इनमें से कुछ है?",
    },
    input_type: "multi_select",
    options: [
      { value: "breathless", label: { en: "Difficulty breathing", hi: "साँस लेने में तकलीफ़" } },
      { value: "sweating", label: { en: "Cold sweating", hi: "ठंडा पसीना" } },
      { value: "nausea", label: { en: "Feeling sick or vomiting", hi: "जी मिचलाना या उल्टी" } },
      { value: "dizzy", label: { en: "Dizziness or fainting", hi: "चक्कर आना या बेहोशी" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कुछ नहीं" }, exclusive: true },
    ],
  },

  cp_severity: {
    id: "cp_severity",
    text: { en: "How bad is the pain right now?", hi: "अभी दर्द कितना तेज़ है?" },
    input_type: "scale",
    options: [
      { value: "mild", label: { en: "Mild", hi: "हल्का" } },
      { value: "moderate", label: { en: "Moderate", hi: "मध्यम" } },
      { value: "severe", label: { en: "Severe", hi: "तेज़" } },
      { value: "worst", label: { en: "The worst I have felt", hi: "सबसे तेज़ जो कभी हुआ" } },
    ],
  },

  cp_relief: {
    id: "cp_relief",
    text: {
      en: "Does anything make the pain better or worse?",
      hi: "क्या किसी चीज़ से दर्द कम या ज़्यादा होता है?",
    },
    helper: {
      en: "For example: walking, resting, eating, lying down.",
      hi: "जैसे: चलने से, आराम करने से, खाने से, लेटने से।",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  /* ---- Fever and cough ---- */

  fc_duration: {
    id: "fc_duration",
    text: { en: "How many days have you had the fever?", hi: "आपको बुखार कितने दिनों से है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "today", label: { en: "Since today", hi: "आज से" } },
      { value: "d2_3", label: { en: "2 to 3 days", hi: "2 से 3 दिन" } },
      { value: "d4_7", label: { en: "4 to 7 days", hi: "4 से 7 दिन" } },
      { value: "gt_week", label: { en: "More than a week", hi: "एक हफ़्ते से ज़्यादा" } },
    ],
  },

  fc_pattern: {
    id: "fc_pattern",
    text: { en: "How does the fever behave?", hi: "बुखार कैसा रहता है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "continuous", label: { en: "It stays all the time", hi: "हर समय रहता है" } },
      { value: "intermittent", label: { en: "It comes and goes", hi: "आता-जाता रहता है" } },
      { value: "night", label: { en: "Mostly at night", hi: "ज़्यादातर रात में" } },
      { value: "unsure", label: { en: "I am not sure", hi: "मुझे ठीक से पता नहीं" } },
    ],
  },

  fc_measured: {
    id: "fc_measured",
    text: { en: "Have you measured your temperature?", hi: "क्या आपने बुखार नापा है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "high", label: { en: "Yes, it was high", hi: "हाँ, तेज़ था" } },
      { value: "mild", label: { en: "Yes, it was mild", hi: "हाँ, हल्का था" } },
      { value: "no", label: { en: "No, I have not measured it", hi: "नहीं, नापा नहीं है" } },
    ],
  },

  fc_cough: {
    id: "fc_cough",
    text: { en: "Do you have a cough?", hi: "क्या आपको खाँसी है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "dry", label: { en: "Yes, a dry cough", hi: "हाँ, सूखी खाँसी" } },
      { value: "productive", label: { en: "Yes, with phlegm", hi: "हाँ, बलगम के साथ" } },
      { value: "none", label: { en: "No cough", hi: "खाँसी नहीं है" } },
    ],
  },

  /* Branch: only asked when the cough is productive. */
  fc_sputum: {
    id: "fc_sputum",
    text: { en: "What colour is the phlegm?", hi: "बलगम का रंग कैसा है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "clear", label: { en: "Clear or white", hi: "साफ़ या सफ़ेद" } },
      { value: "yellow", label: { en: "Yellow or green", hi: "पीला या हरा" } },
      { value: "blood", label: { en: "There is blood in it", hi: "इसमें खून आता है" } },
      { value: "unsure", label: { en: "I am not sure", hi: "मुझे पता नहीं" } },
    ],
  },

  fc_associated: {
    id: "fc_associated",
    text: {
      en: "Along with the fever, do you have any of these?",
      hi: "बुखार के साथ क्या इनमें से कुछ है?",
    },
    input_type: "multi_select",
    options: [
      { value: "breathless", label: { en: "Difficulty breathing", hi: "साँस लेने में तकलीफ़" } },
      { value: "chest_pain", label: { en: "Chest pain", hi: "छाती में दर्द" } },
      { value: "sore_throat", label: { en: "Sore throat", hi: "गले में खराश" } },
      { value: "body_ache", label: { en: "Body ache", hi: "बदन दर्द" } },
      { value: "headache", label: { en: "Headache", hi: "सिरदर्द" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कुछ नहीं" }, exclusive: true },
    ],
  },

  /* ---- Generic complaint line ---- */

  gen_describe: {
    id: "gen_describe",
    text: {
      en: "Please describe the problem in your own words.",
      hi: "अपनी तकलीफ़ अपने शब्दों में बताइए।",
    },
    helper: {
      en: "Speak as you would to the doctor. Take your time.",
      hi: "जैसे डॉक्टर को बताते हैं वैसे ही बोलिए। आराम से बताइए।",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  gen_duration: {
    id: "gen_duration",
    text: { en: "How long have you had this problem?", hi: "यह तकलीफ़ आपको कब से है?" },
    input_type: "voice_or_touch",
    options: [
      { value: "today", label: { en: "Since today", hi: "आज से" } },
      { value: "days", label: { en: "A few days", hi: "कुछ दिनों से" } },
      { value: "weeks", label: { en: "A few weeks", hi: "कुछ हफ़्तों से" } },
      { value: "months", label: { en: "Months or longer", hi: "महीनों या उससे ज़्यादा" } },
    ],
  },

  gen_severity: {
    id: "gen_severity",
    text: {
      en: "How much does this trouble you day to day?",
      hi: "यह रोज़मर्रा के कामों में कितनी परेशानी देती है?",
    },
    input_type: "scale",
    options: [
      { value: "mild", label: { en: "A little", hi: "थोड़ी" } },
      { value: "moderate", label: { en: "Somewhat", hi: "कुछ हद तक" } },
      { value: "severe", label: { en: "A lot", hi: "बहुत" } },
      { value: "worst", label: { en: "I cannot do my work", hi: "मैं अपना काम नहीं कर पाता" } },
    ],
  },

  /* ---- Common tail, asked for every complaint ---- */

  hx_conditions: {
    id: "hx_conditions",
    text: {
      en: "Do you have any of these long-term illnesses?",
      hi: "क्या आपको इनमें से कोई पुरानी बीमारी है?",
    },
    input_type: "multi_select",
    options: [
      { value: "diabetes", label: { en: "Diabetes (sugar)", hi: "मधुमेह (शुगर)" } },
      { value: "hypertension", label: { en: "High blood pressure", hi: "हाई ब्लड प्रेशर" } },
      { value: "heart", label: { en: "Heart disease", hi: "दिल की बीमारी" } },
      { value: "asthma", label: { en: "Asthma or breathing illness", hi: "दमा या साँस की बीमारी" } },
      { value: "thyroid", label: { en: "Thyroid problem", hi: "थायरॉइड की समस्या" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कोई नहीं" }, exclusive: true },
    ],
  },

  hx_medications: {
    id: "hx_medications",
    text: { en: "Are you taking any medicines at present?", hi: "क्या आप इस समय कोई दवा ले रहे हैं?" },
    input_type: "voice_or_touch",
    options: [
      { value: "yes", label: { en: "Yes", hi: "हाँ" } },
      { value: "no", label: { en: "No", hi: "नहीं" } },
    ],
  },

  /* Branch: only asked when the patient takes medicines. */
  hx_medications_list: {
    id: "hx_medications_list",
    text: { en: "Which medicines are you taking?", hi: "आप कौन सी दवाएँ ले रही/रहे हैं?" },
    helper: {
      en: "Say the names you remember. You can also send a photo of the prescription in the next step.",
      hi: "जो नाम याद हैं वे बोल दीजिए। अगले चरण में पर्चे की फ़ोटो भी भेज सकते हैं।",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  hx_allergies: {
    id: "hx_allergies",
    text: {
      en: "Does any medicine or food disagree with you?",
      hi: "क्या कोई दवा या खाना आपको नुक़सान करता है?",
    },
    helper: {
      en: "For example: a rash, swelling or breathlessness after taking something.",
      hi: "जैसे: कुछ लेने के बाद चकत्ते, सूजन या साँस फूलना।",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "yes", label: { en: "Yes", hi: "हाँ" } },
      { value: "no", label: { en: "No", hi: "नहीं" } },
      { value: "unsure", label: { en: "I am not sure", hi: "मुझे पता नहीं" } },
    ],
  },

  /* Branch: only asked when an allergy is reported. */
  hx_allergies_list: {
    id: "hx_allergies_list",
    text: { en: "What disagrees with you?", hi: "किस चीज़ से आपको दिक़्क़त होती है?" },
    input_type: "voice_or_text",
    allow_text: true,
  },
};

/* --- The plan ------------------------------------------------------------
   Recomputed after every answer. Branches appear and disappear, so the
   estimated total legitimately moves — which is exactly why the kiosk must
   not assume a fixed question count (build spec §6.10).                     */

const COMPLAINT_LINES: Record<string, string[]> = {
  chest_pain: ["cp_site", "cp_onset", "cp_character", "cp_radiation", "cp_associated", "cp_severity", "cp_relief"],
  fever_cough: ["fc_duration", "fc_pattern", "fc_measured", "fc_cough", "fc_associated"],
};

const TAIL = ["hx_conditions", "hx_medications", "hx_allergies"];

function values(answers: Record<string, AnswerPayload>, id: string): string[] {
  return answers[id]?.values ?? [];
}

function planFor(complaint: string, answers: Record<string, AnswerPayload>): string[] {
  const line = COMPLAINT_LINES[complaint] ?? ["gen_describe", "gen_duration", "gen_severity"];
  const plan = [...line];

  if (values(answers, "fc_cough").includes("productive")) {
    plan.splice(plan.indexOf("fc_cough") + 1, 0, "fc_sputum");
  }

  plan.push(...TAIL);

  if (values(answers, "hx_medications").includes("yes")) {
    plan.splice(plan.indexOf("hx_medications") + 1, 0, "hx_medications_list");
  }
  if (values(answers, "hx_allergies").includes("yes")) {
    plan.splice(plan.indexOf("hx_allergies") + 1, 0, "hx_allergies_list");
  }

  return plan;
}

/* --- Priority ------------------------------------------------------------
   ⚠ BACKEND-OWNED. The project plan keeps red-flag detection rule-based and
   deliberately separate from the LLM. These are placeholder rules so the
   kiosk's priority screen can be built and tested; they are not a triage
   protocol and carry no clinical authority. The real rules replace this
   function wholesale when the safety layer exists.                          */

const NORMAL: PriorityState = { priority: "normal", red_flag: false, action: "continue" };

function evaluatePriority(complaint: string, answers: Record<string, AnswerPayload>): PriorityState {
  const associated = values(answers, "cp_associated");
  const radiation = values(answers, "cp_radiation");

  if (complaint === "chest_pain") {
    const cardiacPattern =
      associated.includes("breathless") ||
      associated.includes("sweating") ||
      associated.includes("dizzy") ||
      radiation.includes("left_arm") ||
      radiation.includes("jaw_neck");

    if (cardiacPattern) {
      return {
        priority: "urgent",
        red_flag: true,
        action: "immediate_assistance",
        reason_code: "MOCK_CHEST_PAIN_WITH_ASSOCIATED_FEATURES",
      };
    }
  }

  if (values(answers, "fc_associated").includes("breathless")) {
    return {
      priority: "priority",
      red_flag: true,
      action: "staff_assistance",
      reason_code: "MOCK_FEVER_WITH_BREATHLESSNESS",
    };
  }

  if (values(answers, "fc_sputum").includes("blood")) {
    return {
      priority: "priority",
      red_flag: true,
      action: "staff_assistance",
      reason_code: "MOCK_HAEMOPTYSIS",
    };
  }

  return NORMAL;
}

/* --- Rendering ------------------------------------------------------------ */

function toQuestion(
  def: MockQuestion,
  language: LanguageCode,
  current: number,
  estimatedTotal: number,
): IntakeQuestion {
  return {
    question_id: def.id,
    text: resolveLocalized(def.text, language),
    helper: def.helper ? resolveLocalized(def.helper, language) : undefined,
    input_type: def.input_type,
    options: (def.options ?? []).map((o) => ({
      value: o.value,
      label: resolveLocalized(o.label, language),
      exclusive: o.exclusive,
    })),
    allow_voice: def.allow_voice ?? true,
    allow_text: def.allow_text ?? false,
    progress: { current, estimated_total: estimatedTotal },
  };
}

/** What the mock service returns for a given interview state. */
export function mockNextQuestion(
  complaint: string,
  answers: Record<string, AnswerPayload>,
  language: LanguageCode,
): { question: IntakeQuestion | null; priority: PriorityState; complete: boolean } {
  const priority = evaluatePriority(complaint, answers);

  // A red flag halts the interview. The kiosk is told to stop; it does not
  // decide to.
  if (priority.red_flag) {
    return { question: null, priority, complete: false };
  }

  const plan = planFor(complaint, answers);
  const nextId = plan.find((id) => !(id in answers));

  if (!nextId) {
    return { question: null, priority, complete: true };
  }

  return {
    question: toQuestion(BANK[nextId], language, plan.indexOf(nextId) + 1, plan.length),
    priority,
    complete: false,
  };
}

export function mockQuestionText(questionId: string, language: LanguageCode): string {
  const def = BANK[questionId];
  return def ? resolveLocalized(def.text, language) : "";
}

export function mockOptionLabel(
  questionId: string,
  value: string,
  language: LanguageCode,
): string {
  const opt = BANK[questionId]?.options?.find((o) => o.value === value);
  return opt ? resolveLocalized(opt.label, language) : value;
}
