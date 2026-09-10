/* ==========================================================================
   MOCK question engine — a stand-in for a backend service.

   ⚠ INTEGRATION POINT. Everything in this file is logic the frontend does not
   own (build spec §6.6, §10, §19): which question comes next, how the
   interview branches, and whether an answer combination warrants priority.
   It lives here, behind intakeApi, so that the UI can be built and demoed
   before the backend exists — and so that deleting this file and pointing
   intakeApi at the real service changes no screen and no component.

   The question order below follows SOCRATES for pain and a conventional
   fever/cough line of questioning. It is a demo script, NOT a clinical
   protocol, and it must be reviewed by the clinical members of the team
   before it is shown to a real patient. The AYUSH bank in ayushQuestions.ts
   carries the same warning, more loudly.
   ========================================================================== */

import type {
  AnswerPayload,
  ChiefComplaintOption,
  ComplaintMatch,
  HistoryMode,
  IntakeQuestion,
  LanguageCode,
  PriorityState,
} from "@/api/types";
import { resolveLocalized, type Localized } from "@/i18n";
import { AYUSH_BANK, AYUSH_SECTIONS } from "./ayushQuestions";
import type { MockQuestion, MockSection } from "./questionTypes";

/* --- Chief complaints ----------------------------------------------------- */

const COMPLAINTS: Array<{ id: string; label: Localized; icon: string; keywords: Localized }> = [
  {
    id: "fever_cough",
    label: { en: "Fever or cough", hi: "बुखार या खाँसी", mr: "ताप किंवा खोकला" },
    icon: "thermometer",
    keywords: { en: "fever cough temperature cold flu", hi: "बुखार खाँसी ताप सर्दी जुकाम", mr: "ताप खोकला सर्दी" },
  },
  {
    id: "chest_pain",
    label: { en: "Chest pain", hi: "छाती में दर्द", mr: "छातीत दुखणे" },
    icon: "heart",
    keywords: { en: "chest pain heart tightness pressure", hi: "छाती सीना दर्द दिल जकड़न", mr: "छाती दुखणे हृदय" },
  },
  {
    id: "stomach",
    label: { en: "Stomach pain", hi: "पेट में दर्द", mr: "पोटात दुखणे" },
    icon: "stomach",
    keywords: { en: "stomach abdomen belly pain vomit", hi: "पेट दर्द उल्टी", mr: "पोट दुखणे उलटी" },
  },
  {
    id: "headache",
    label: { en: "Headache", hi: "सिरदर्द", mr: "डोकेदुखी" },
    icon: "head",
    keywords: { en: "head headache migraine", hi: "सिर सिरदर्द", mr: "डोके डोकेदुखी" },
  },
  {
    id: "breathing",
    label: { en: "Breathing difficulty", hi: "साँस लेने में तकलीफ़", mr: "श्वास घेण्यास त्रास" },
    icon: "lungs",
    keywords: { en: "breath breathing breathless asthma wheeze", hi: "साँस दमा साँस फूलना", mr: "श्वास दमा" },
  },
];

export function mockComplaints(language: LanguageCode): ChiefComplaintOption[] {
  return COMPLAINTS.map((c) => ({
    id: c.id,
    label: resolveLocalized(c.label, language),
    icon: c.icon,
  }));
}

/**
 * Naive keyword match, standing in for whatever the question service really
 * does. Deliberately unclever: a wrong confident match sends the patient down
 * the wrong line of questioning, so anything ambiguous returns null and the
 * spoken words are carried through as a free-text complaint instead.
 */
export function mockMatchComplaint(transcript: string, language: LanguageCode): ComplaintMatch {
  const text = transcript.toLowerCase();

  const complaints = COMPLAINTS.filter((c) =>
    resolveLocalized(c.keywords, language)
      .split(/\s+/)
      .some((word) => word.length > 2 && text.includes(word.toLowerCase())),
  ).map((hit) => ({ id: hit.id, label: resolveLocalized(hit.label, language), icon: hit.icon }));

  return { complaint: complaints[0] ?? null, complaints, transcript };
}

/* --- General Medicine question bank --------------------------------------- */

const BANK: Record<string, MockQuestion> = {
  /* ---- Chest pain — SOCRATES ---- */

  cp_site: {
    id: "cp_site",
    text: { en: "Where exactly do you feel the pain?", hi: "दर्द ठीक कहाँ महसूस होता है?", mr: "वेदना नेमकी कुठे जाणवते?" },
    input_type: "voice_or_touch",
    options: [
      { value: "centre", label: { en: "In the centre of the chest", hi: "छाती के बीच में", mr: "छातीच्या मध्यभागी" } },
      { value: "left", label: { en: "On the left side", hi: "बाईं ओर", mr: "डाव्या बाजूला" } },
      { value: "right", label: { en: "On the right side", hi: "दाईं ओर", mr: "उजव्या बाजूला" } },
      { value: "upper_abdomen", label: { en: "In the upper stomach", hi: "पेट के ऊपरी हिस्से में", mr: "पोटाच्या वरच्या भागात" } },
      { value: "whole", label: { en: "All over the chest", hi: "पूरी छाती में", mr: "संपूर्ण छातीत" } },
    ],
  },

  cp_onset: {
    id: "cp_onset",
    text: { en: "When did the pain start?", hi: "दर्द कब शुरू हुआ?", mr: "वेदना कधी सुरू झाली?" },
    input_type: "voice_or_touch",
    options: [
      { value: "minutes", label: { en: "In the last few minutes", hi: "पिछले कुछ मिनटों में", mr: "गेल्या काही मिनिटांत" } },
      { value: "hours", label: { en: "Today, a few hours ago", hi: "आज, कुछ घंटे पहले", mr: "आज, काही तासांपूर्वी" } },
      { value: "days", label: { en: "A few days ago", hi: "कुछ दिन पहले", mr: "काही दिवसांपूर्वी" } },
      { value: "weeks", label: { en: "More than a week ago", hi: "एक हफ़्ते से ज़्यादा पहले", mr: "एका आठवड्याहून अधिक काळापूर्वी" } },
    ],
  },

  cp_character: {
    id: "cp_character",
    text: { en: "What does the pain feel like?", hi: "दर्द कैसा महसूस होता है?", mr: "वेदना कशी जाणवते?" },
    input_type: "voice_or_touch",
    options: [
      { value: "pressing", label: { en: "Heavy, like pressure", hi: "भारीपन या दबाव जैसा", mr: "जडपणा किंवा दाबल्यासारखे" } },
      { value: "burning", label: { en: "Burning", hi: "जलन जैसा", mr: "जळजळल्यासारखे" } },
      { value: "sharp", label: { en: "Sharp, like a needle", hi: "तेज़, सुई चुभने जैसा", mr: "तीव्र, सुई टोचल्यासारखे" } },
      { value: "dull", label: { en: "A dull ache", hi: "हल्का लगातार दर्द", mr: "मंद सततची वेदना" } },
    ],
  },

  cp_radiation: {
    id: "cp_radiation",
    text: { en: "Does the pain travel anywhere else?", hi: "क्या दर्द कहीं और फैलता है?", mr: "वेदना इतरत्र पसरते का?" },
    input_type: "voice_or_touch",
    options: [
      { value: "left_arm", label: { en: "To the left arm or shoulder", hi: "बाएँ हाथ या कंधे तक", mr: "डाव्या हातापर्यंत किंवा खांद्यापर्यंत" } },
      { value: "jaw_neck", label: { en: "To the jaw or neck", hi: "जबड़े या गर्दन तक", mr: "जबडा किंवा मानेपर्यंत" } },
      { value: "back", label: { en: "To the back", hi: "पीठ तक", mr: "पाठीपर्यंत" } },
      { value: "none", label: { en: "It stays in one place", hi: "यह एक ही जगह रहता है", mr: "ती एकाच जागी राहते" }, exclusive: true },
    ],
  },

  cp_associated: {
    id: "cp_associated",
    text: {
      en: "Along with the pain, do you have any of these?",
      hi: "दर्द के साथ क्या इनमें से कुछ है?",
      mr: "वेदनेसोबत यापैकी काही आहे का?",
    },
    input_type: "multi_select",
    options: [
      { value: "breathless", label: { en: "Difficulty breathing", hi: "साँस लेने में तकलीफ़", mr: "श्वास घेण्यास त्रास" } },
      { value: "sweating", label: { en: "Cold sweating", hi: "ठंडा पसीना", mr: "थंड घाम" } },
      { value: "nausea", label: { en: "Feeling sick or vomiting", hi: "जी मिचलाना या उल्टी", mr: "मळमळ किंवा उलटी" } },
      { value: "dizzy", label: { en: "Dizziness or fainting", hi: "चक्कर आना या बेहोशी", mr: "चक्कर येणे किंवा बेशुद्धी" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कुछ नहीं", mr: "यापैकी काहीही नाही" }, exclusive: true },
    ],
  },

  cp_severity: {
    id: "cp_severity",
    text: { en: "How bad is the pain right now?", hi: "अभी दर्द कितना तेज़ है?", mr: "आत्ता वेदना किती तीव्र आहे?" },
    input_type: "scale",
    scale_tone: "severity",
    options: [
      { value: "mild", label: { en: "Mild", hi: "हल्का", mr: "सौम्य" } },
      { value: "moderate", label: { en: "Moderate", hi: "मध्यम", mr: "मध्यम" } },
      { value: "severe", label: { en: "Severe", hi: "तेज़", mr: "तीव्र" } },
      { value: "worst", label: { en: "The worst I have felt", hi: "सबसे तेज़ जो कभी हुआ", mr: "आजवरची सर्वात तीव्र" } },
    ],
  },

  cp_relief: {
    id: "cp_relief",
    text: {
      en: "Does anything make the pain better or worse?",
      hi: "क्या किसी चीज़ से दर्द कम या ज़्यादा होता है?",
      mr: "कशामुळे वेदना कमी किंवा जास्त होते का?",
    },
    helper: {
      en: "For example: walking, resting, eating, lying down.",
      hi: "जैसे: चलने से, आराम करने से, खाने से, लेटने से।",
      mr: "उदा.: चालल्याने, विश्रांतीने, खाल्ल्याने, झोपल्याने.",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  /* ---- Fever and cough ---- */

  fc_duration: {
    id: "fc_duration",
    text: { en: "How many days have you had the fever?", hi: "आपको बुखार कितने दिनों से है?", mr: "तुम्हाला किती दिवसांपासून ताप आहे?" },
    input_type: "voice_or_touch",
    options: [
      { value: "today", label: { en: "Since today", hi: "आज से", mr: "आजपासून" } },
      { value: "d2_3", label: { en: "2 to 3 days", hi: "2 से 3 दिन", mr: "2 ते 3 दिवस" } },
      { value: "d4_7", label: { en: "4 to 7 days", hi: "4 से 7 दिन", mr: "4 ते 7 दिवस" } },
      { value: "gt_week", label: { en: "More than a week", hi: "एक हफ़्ते से ज़्यादा", mr: "एका आठवड्याहून अधिक" } },
    ],
  },

  fc_pattern: {
    id: "fc_pattern",
    text: { en: "How does the fever behave?", hi: "बुखार कैसा रहता है?", mr: "ताप कसा राहतो?" },
    input_type: "voice_or_touch",
    options: [
      { value: "continuous", label: { en: "It stays all the time", hi: "हर समय रहता है", mr: "सतत राहतो" } },
      { value: "intermittent", label: { en: "It comes and goes", hi: "आता-जाता रहता है", mr: "येतो-जातो" } },
      { value: "night", label: { en: "Mostly at night", hi: "ज़्यादातर रात में", mr: "बहुतेक रात्री" } },
      { value: "unsure", label: { en: "I am not sure", hi: "मुझे ठीक से पता नहीं", mr: "मला नक्की माहीत नाही" } },
    ],
  },

  fc_measured: {
    id: "fc_measured",
    text: { en: "Have you measured your temperature?", hi: "क्या आपने बुखार नापा है?", mr: "तुम्ही ताप मोजला आहे का?" },
    input_type: "voice_or_touch",
    options: [
      { value: "high", label: { en: "Yes, it was high", hi: "हाँ, तेज़ था", mr: "होय, जास्त होता" } },
      { value: "mild", label: { en: "Yes, it was mild", hi: "हाँ, हल्का था", mr: "होय, सौम्य होता" } },
      { value: "no", label: { en: "No, I have not measured it", hi: "नहीं, नापा नहीं है", mr: "नाही, मोजलेला नाही" } },
    ],
  },

  fc_cough: {
    id: "fc_cough",
    text: { en: "Do you have a cough?", hi: "क्या आपको खाँसी है?", mr: "तुम्हाला खोकला आहे का?" },
    input_type: "voice_or_touch",
    options: [
      { value: "dry", label: { en: "Yes, a dry cough", hi: "हाँ, सूखी खाँसी", mr: "होय, कोरडा खोकला" } },
      { value: "productive", label: { en: "Yes, with phlegm", hi: "हाँ, बलगम के साथ", mr: "होय, कफासह" } },
      { value: "none", label: { en: "No cough", hi: "खाँसी नहीं है", mr: "खोकला नाही" } },
    ],
  },

  fc_sputum: {
    id: "fc_sputum",
    text: { en: "What colour is the phlegm?", hi: "बलगम का रंग कैसा है?", mr: "कफाचा रंग कसा आहे?" },
    input_type: "voice_or_touch",
    options: [
      { value: "clear", label: { en: "Clear or white", hi: "साफ़ या सफ़ेद", mr: "स्वच्छ किंवा पांढरा" } },
      { value: "yellow", label: { en: "Yellow or green", hi: "पीला या हरा", mr: "पिवळा किंवा हिरवा" } },
      { value: "blood", label: { en: "There is blood in it", hi: "इसमें खून आता है", mr: "त्यात रक्त येते" } },
      { value: "unsure", label: { en: "I am not sure", hi: "मुझे पता नहीं", mr: "मला माहीत नाही" } },
    ],
  },

  fc_associated: {
    id: "fc_associated",
    text: {
      en: "Along with the fever, do you have any of these?",
      hi: "बुखार के साथ क्या इनमें से कुछ है?",
      mr: "तापासोबत यापैकी काही आहे का?",
    },
    input_type: "multi_select",
    options: [
      { value: "breathless", label: { en: "Difficulty breathing", hi: "साँस लेने में तकलीफ़", mr: "श्वास घेण्यास त्रास" } },
      { value: "chest_pain", label: { en: "Chest pain", hi: "छाती में दर्द", mr: "छातीत दुखणे" } },
      { value: "sore_throat", label: { en: "Sore throat", hi: "गले में खराश", mr: "घसा खवखवणे" } },
      { value: "body_ache", label: { en: "Body ache", hi: "बदन दर्द", mr: "अंगदुखी" } },
      { value: "headache", label: { en: "Headache", hi: "सिरदर्द", mr: "डोकेदुखी" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कुछ नहीं", mr: "यापैकी काहीही नाही" }, exclusive: true },
    ],
  },

  /* ---- Generic complaint line ---- */

  gen_describe: {
    id: "gen_describe",
    text: {
      en: "Please describe the problem in your own words.",
      hi: "अपनी तकलीफ़ अपने शब्दों में बताइए।",
      mr: "तुमचा त्रास तुमच्या शब्दांत सांगा.",
    },
    helper: {
      en: "Speak as you would to the doctor. Take your time.",
      hi: "जैसे डॉक्टर को बताते हैं वैसे ही बोलिए। आराम से बताइए।",
      mr: "डॉक्टरांना सांगाल तसे सांगा. सावकाश सांगा.",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  gen_duration: {
    id: "gen_duration",
    text: { en: "How long have you had this problem?", hi: "यह तकलीफ़ आपको कब से है?", mr: "हा त्रास तुम्हाला किती काळापासून आहे?" },
    input_type: "voice_or_touch",
    options: [
      { value: "today", label: { en: "Since today", hi: "आज से", mr: "आजपासून" } },
      { value: "days", label: { en: "A few days", hi: "कुछ दिनों से", mr: "काही दिवसांपासून" } },
      { value: "weeks", label: { en: "A few weeks", hi: "कुछ हफ़्तों से", mr: "काही आठवड्यांपासून" } },
      { value: "months", label: { en: "Months or longer", hi: "महीनों या उससे ज़्यादा", mr: "महिने किंवा त्याहून अधिक" } },
    ],
  },

  gen_severity: {
    id: "gen_severity",
    text: {
      en: "How much does this trouble you day to day?",
      hi: "यह रोज़मर्रा के कामों में कितनी परेशानी देती है?",
      mr: "याचा रोजच्या कामात किती त्रास होतो?",
    },
    input_type: "scale",
    scale_tone: "severity",
    options: [
      { value: "mild", label: { en: "A little", hi: "थोड़ी", mr: "थोडा" } },
      { value: "moderate", label: { en: "Somewhat", hi: "कुछ हद तक", mr: "काही प्रमाणात" } },
      { value: "severe", label: { en: "A lot", hi: "बहुत", mr: "खूप" } },
      { value: "worst", label: { en: "I cannot do my work", hi: "मैं अपना काम नहीं कर पाता", mr: "मी माझे काम करू शकत नाही" } },
    ],
  },

  /* ---- Common tail, asked for every complaint ---- */

  hx_conditions: {
    id: "hx_conditions",
    text: {
      en: "Do you have any of these long-term illnesses?",
      hi: "क्या आपको इनमें से कोई पुरानी बीमारी है?",
      mr: "तुम्हाला यापैकी कोणता जुनाट आजार आहे का?",
    },
    input_type: "multi_select",
    options: [
      { value: "diabetes", label: { en: "Diabetes (sugar)", hi: "मधुमेह (शुगर)", mr: "मधुमेह (साखर)" } },
      { value: "hypertension", label: { en: "High blood pressure", hi: "हाई ब्लड प्रेशर", mr: "उच्च रक्तदाब" } },
      { value: "heart", label: { en: "Heart disease", hi: "दिल की बीमारी", mr: "हृदयविकार" } },
      { value: "asthma", label: { en: "Asthma or breathing illness", hi: "दमा या साँस की बीमारी", mr: "दमा किंवा श्वसनाचा आजार" } },
      { value: "thyroid", label: { en: "Thyroid problem", hi: "थायरॉइड की समस्या", mr: "थायरॉइडची समस्या" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कोई नहीं", mr: "यापैकी काहीही नाही" }, exclusive: true },
    ],
  },

  hx_medications: {
    id: "hx_medications",
    text: { en: "Are you taking any medicines at present?", hi: "क्या आप इस समय कोई दवा ले रहे हैं?", mr: "तुम्ही सध्या काही औषधे घेत आहात का?" },
    input_type: "voice_or_touch",
    options: [
      { value: "yes", label: { en: "Yes", hi: "हाँ", mr: "होय" } },
      { value: "no", label: { en: "No", hi: "नहीं", mr: "नाही" } },
    ],
  },

  hx_medications_list: {
    id: "hx_medications_list",
    text: { en: "Which medicines are you taking?", hi: "आप कौन सी दवाएँ ले रही/रहे हैं?", mr: "तुम्ही कोणती औषधे घेत आहात?" },
    helper: {
      en: "Say the names you remember. You can also send a photo of the prescription in the next step.",
      hi: "जो नाम याद हैं वे बोल दीजिए। अगले चरण में पर्चे की फ़ोटो भी भेज सकते हैं।",
      mr: "आठवणारी नावे सांगा. पुढील टप्प्यात चिठ्ठीचा फोटोही पाठवू शकता.",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  hx_allergies: {
    id: "hx_allergies",
    text: {
      en: "Does any medicine or food disagree with you?",
      hi: "क्या कोई दवा या खाना आपको नुक़सान करता है?",
      mr: "एखादे औषध किंवा अन्न तुम्हाला त्रासदायक ठरते का?",
    },
    helper: {
      en: "For example: a rash, swelling or breathlessness after taking something.",
      hi: "जैसे: कुछ लेने के बाद चकत्ते, सूजन या साँस फूलना।",
      mr: "उदा.: काही घेतल्यावर पुरळ, सूज किंवा दम लागणे.",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "yes", label: { en: "Yes", hi: "हाँ", mr: "होय" } },
      { value: "no", label: { en: "No", hi: "नहीं", mr: "नाही" } },
      { value: "unsure", label: { en: "I am not sure", hi: "मुझे पता नहीं", mr: "मला माहीत नाही" } },
    ],
  },

  hx_allergies_list: {
    id: "hx_allergies_list",
    text: { en: "What disagrees with you?", hi: "किस चीज़ से आपको दिक़्क़त होती है?", mr: "कशाचा तुम्हाला त्रास होतो?" },
    input_type: "voice_or_text",
    allow_text: true,
  },
};

/** Both banks, so lookup does not care which framework a question came from. */
const ALL_QUESTIONS: Record<string, MockQuestion> = { ...BANK, ...AYUSH_BANK };

/* --- Section labels shared by both frameworks ----------------------------- */

const SECTION_COMPLAINT: Localized = {
  en: "About your problem",
  hi: "आपकी तकलीफ़ के बारे में",
  mr: "तुमच्या त्रासाविषयी",
};

const SECTION_HISTORY: Localized = {
  en: "Your medical history",
  hi: "आपका पिछला इलाज",
  mr: "तुमचा वैद्यकीय इतिहास",
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

function complaintSection(complaint: string, answers: Record<string, AnswerPayload>): MockSection {
  const line = [...(COMPLAINT_LINES[complaint] ?? ["gen_describe", "gen_duration", "gen_severity"])];

  if (values(answers, "fc_cough").includes("productive")) {
    line.splice(line.indexOf("fc_cough") + 1, 0, "fc_sputum");
  }

  return { id: "complaint", label: SECTION_COMPLAINT, questions: line };
}

function historySection(answers: Record<string, AnswerPayload>): MockSection {
  const tail = [...TAIL];

  if (values(answers, "hx_medications").includes("yes")) {
    tail.splice(tail.indexOf("hx_medications") + 1, 0, "hx_medications_list");
  }
  if (values(answers, "hx_allergies").includes("yes")) {
    tail.splice(tail.indexOf("hx_allergies") + 1, 0, "hx_allergies_list");
  }

  return { id: "history", label: SECTION_HISTORY, questions: tail };
}

/**
 * The ordered interview.
 *
 * General Medicine is complaint then history. AYUSH keeps both and inserts
 * the Dashavidha Pariksha and Ahara-Vihara sections between them — the
 * presenting complaint still comes first, because a patient who came in with
 * chest pain should not answer thirty constitution questions before anyone
 * asks what brought them in.
 */
function planFor(
  complaint: string,
  historyMode: HistoryMode,
  answers: Record<string, AnswerPayload>,
): MockSection[] {
  const sections = [complaintSection(complaint, answers)];

  if (historyMode === "ayush") {
    sections.push(...AYUSH_SECTIONS);
  }

  sections.push(historySection(answers));
  return sections;
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
  section: { def: MockSection; index: number; total: number },
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
    scale_tone: def.scale_tone,
    progress: { current, estimated_total: estimatedTotal },
    section: {
      id: section.def.id,
      label: resolveLocalized(section.def.label, language),
      index: section.index,
      total: section.total,
    },
  };
}

/** What the mock service returns for a given interview state. */
export function mockNextQuestion(
  complaint: string,
  historyMode: HistoryMode,
  answers: Record<string, AnswerPayload>,
  language: LanguageCode,
): { question: IntakeQuestion | null; priority: PriorityState; complete: boolean } {
  const priority = evaluatePriority(complaint, answers);

  // A red flag halts the interview. The kiosk is told to stop; it does not
  // decide to.
  if (priority.red_flag) {
    return { question: null, priority, complete: false };
  }

  const sections = planFor(complaint, historyMode, answers);
  const flat = sections.flatMap((s) => s.questions);
  const nextId = flat.find((id) => !(id in answers));

  if (!nextId) {
    return { question: null, priority, complete: true };
  }

  const sectionIndex = sections.findIndex((s) => s.questions.includes(nextId));

  return {
    question: toQuestion(ALL_QUESTIONS[nextId], language, flat.indexOf(nextId) + 1, flat.length, {
      def: sections[sectionIndex],
      index: sectionIndex + 1,
      total: sections.length,
    }),
    priority,
    complete: false,
  };
}

export function mockQuestionText(questionId: string, language: LanguageCode): string {
  const def = ALL_QUESTIONS[questionId];
  return def ? resolveLocalized(def.text, language) : "";
}

export function mockOptionLabel(
  questionId: string,
  value: string,
  language: LanguageCode,
): string {
  const opt = ALL_QUESTIONS[questionId]?.options?.find((o) => o.value === value);
  return opt ? resolveLocalized(opt.label, language) : value;
}
