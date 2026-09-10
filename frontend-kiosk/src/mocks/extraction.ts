/* ==========================================================================
   MOCK clinical extraction.

   ⚠ INTEGRATION POINT. Turning a sentence into structured clinical fields is
   the backend/AI's job — build spec §6.8 is explicit that no extraction logic
   lives in React. This file fakes the *result* so the kiosk can render the
   confirmation step ("you said … is this right?") during mock development.

   The kiosk shows the patient a plain restatement. It never shows model
   reasoning, confidence internals or clinical interpretation (§6.11) — and
   for the AYUSH questions it deliberately never shows the classical axis
   name either. A patient confirming what they said should read "Body build",
   not "Prakriti"; the axis mapping is the practitioner's vocabulary and
   belongs on the doctor's console, not here.
   ========================================================================== */

import type { AnswerPayload, ExtractionResult, LanguageCode } from "@/api/types";
import { resolveLocalized, type Localized } from "@/i18n";
import { mockOptionLabel } from "./questions";

/** Field label the doctor's summary would carry this answer under. */
const FIELD_LABEL: Record<string, Localized> = {
  cp_site: { en: "Site", hi: "जगह", mr: "जागा" },
  cp_onset: { en: "Onset", hi: "शुरुआत", mr: "सुरुवात" },
  cp_character: { en: "Character", hi: "कैसा दर्द", mr: "वेदनेचा प्रकार" },
  cp_radiation: { en: "Radiation", hi: "फैलाव", mr: "प्रसार" },
  cp_associated: { en: "Associated symptoms", hi: "साथ के लक्षण", mr: "सोबतची लक्षणे" },
  cp_severity: { en: "Severity", hi: "तीव्रता", mr: "तीव्रता" },
  cp_relief: { en: "Aggravating and relieving factors", hi: "बढ़ाने/घटाने वाली बातें", mr: "वाढवणारे/कमी करणारे घटक" },
  fc_duration: { en: "Duration", hi: "अवधि", mr: "कालावधी" },
  fc_pattern: { en: "Pattern", hi: "प्रकार", mr: "स्वरूप" },
  fc_measured: { en: "Recorded temperature", hi: "नापा गया तापमान", mr: "मोजलेले तापमान" },
  fc_cough: { en: "Cough", hi: "खाँसी", mr: "खोकला" },
  fc_sputum: { en: "Sputum", hi: "बलगम", mr: "कफ" },
  fc_associated: { en: "Associated symptoms", hi: "साथ के लक्षण", mr: "सोबतची लक्षणे" },
  gen_describe: { en: "Presenting complaint", hi: "मुख्य तकलीफ़", mr: "मुख्य त्रास" },
  gen_duration: { en: "Duration", hi: "अवधि", mr: "कालावधी" },
  gen_severity: { en: "Functional impact", hi: "रोज़मर्रा पर असर", mr: "रोजच्या कामावर परिणाम" },
  hx_conditions: { en: "Past medical history", hi: "पुरानी बीमारियाँ", mr: "जुने आजार" },
  hx_medications: { en: "Current medication", hi: "चल रही दवाएँ", mr: "सुरू असलेली औषधे" },
  hx_medications_list: { en: "Medicines", hi: "दवाएँ", mr: "औषधे" },
  hx_allergies: { en: "Allergy history", hi: "एलर्जी", mr: "ॲलर्जी" },
  hx_allergies_list: { en: "Allergen", hi: "किससे एलर्जी", mr: "कशाची ॲलर्जी" },

  /* AYUSH — patient-facing wording, not the classical axis names. */
  ay_vaya: { en: "Age", hi: "उम्र", mr: "वय" },
  ay_pk_build: { en: "Body build", hi: "शरीर की बनावट", mr: "शरीरयष्टी" },
  ay_pk_skin: { en: "Skin", hi: "त्वचा", mr: "त्वचा" },
  ay_pk_appetite: { en: "Usual appetite", hi: "आम भूख", mr: "नेहमीची भूक" },
  ay_pk_sleep: { en: "Sleep", hi: "नींद", mr: "झोप" },
  ay_pk_stress: { en: "Response to stress", hi: "परेशानी में प्रतिक्रिया", mr: "त्रासातील प्रतिक्रिया" },
  ay_pk_weather: { en: "Weather tolerance", hi: "मौसम सहनशीलता", mr: "हवामान सहनशीलता" },
  ay_vk_change: { en: "What has changed", hi: "क्या बदला है", mr: "काय बदलले आहे" },
  ay_vk_since: { en: "Changed since", hi: "कब से बदला", mr: "कधीपासून बदलले" },
  ay_sara: { en: "Hair, skin and nails", hi: "बाल, त्वचा और नाखून", mr: "केस, त्वचा आणि नखे" },
  ay_samhanana: { en: "Body firmness", hi: "शरीर की कसावट", mr: "शरीराची घट्टता" },
  ay_pramana: { en: "Height and weight", hi: "लंबाई और वज़न", mr: "उंची आणि वजन" },
  ay_satmya: { en: "Adaptability", hi: "अनुकूलन", mr: "जुळवून घेण्याची क्षमता" },
  ay_sattva: { en: "Coping with difficulty", hi: "मुश्किल में सहनशक्ति", mr: "अडचणीत टिकाव" },
  ay_ahara_shakti: { en: "Digestive capacity", hi: "पाचन क्षमता", mr: "पचनशक्ती" },
  ay_vyayama_shakti: { en: "Capacity for exertion", hi: "मेहनत की क्षमता", mr: "श्रमक्षमता" },
  ay_av_diet: { en: "Diet", hi: "आहार", mr: "आहार" },
  ay_av_meal_time: { en: "Meal timing", hi: "खाने का समय", mr: "जेवणाची वेळ" },
  ay_av_meal_count: { en: "Meals per day", hi: "दिन में भोजन", mr: "दिवसातील जेवणे" },
  ay_av_taste: { en: "Preferred tastes", hi: "पसंदीदा स्वाद", mr: "आवडत्या चवी" },
  ay_av_sleep_time: { en: "Sleep timing", hi: "सोने का समय", mr: "झोपण्याची वेळ" },
  ay_av_activity: { en: "Daily activity", hi: "रोज़ की गतिविधि", mr: "रोजची हालचाल" },
  ay_av_habits: { en: "Habits", hi: "आदतें", mr: "सवयी" },
};

/** What the extractor pulls out of the canned spoken answers in
 *  mocks/transcripts.ts. Keyed the same way. */
const SPOKEN_VALUE: Record<string, Localized> = {
  cp_site: { en: "Central chest", hi: "छाती के बीच में", mr: "छातीच्या मध्यभागी" },
  cp_onset: { en: "This morning, on exertion", hi: "आज सुबह, चलते समय", mr: "आज सकाळी, चालताना" },
  cp_character: { en: "Heavy, pressing", hi: "भारी, दबाव जैसा", mr: "जड, दाबल्यासारखे" },
  cp_radiation: { en: "To the left arm", hi: "बाएँ हाथ तक", mr: "डाव्या हातापर्यंत" },
  cp_associated: { en: "Sweating, breathlessness", hi: "पसीना, साँस फूलना", mr: "घाम, दम लागणे" },
  cp_severity: { en: "Severe", hi: "तेज़", mr: "तीव्र" },
  cp_relief: { en: "Worse on walking, better on rest", hi: "चलने पर बढ़े, आराम पर कम", mr: "चालल्याने वाढते, विश्रांतीने कमी" },
  fc_duration: { en: "3 days", hi: "3 दिन", mr: "3 दिवस" },
  fc_pattern: { en: "Evening rise, settles by morning", hi: "शाम को चढ़े, सुबह उतरे", mr: "संध्याकाळी चढतो, सकाळी उतरतो" },
  fc_measured: { en: "102 °F at home", hi: "घर पर 102 °F", mr: "घरी 102 °F" },
  fc_cough: { en: "Productive cough", hi: "बलगम वाली खाँसी", mr: "कफयुक्त खोकला" },
  fc_sputum: { en: "Yellow", hi: "पीला", mr: "पिवळा" },
  fc_associated: { en: "Body ache, headache", hi: "बदन दर्द, सिरदर्द", mr: "अंगदुखी, डोकेदुखी" },
  gen_describe: {
    en: "Right knee pain, 1 month, worse on stairs",
    hi: "दाहिने घुटने में दर्द, 1 महीना, सीढ़ी पर ज़्यादा",
    mr: "उजवा गुडघा दुखणे, 1 महिना, जिन्यावर जास्त",
  },
  gen_duration: { en: "About 1 month", hi: "लगभग 1 महीना", mr: "सुमारे 1 महिना" },
  gen_severity: { en: "Limits heavy work", hi: "भारी काम नहीं कर पाते", mr: "जड काम करता येत नाही" },
  hx_conditions: {
    en: "Diabetes (8 years), hypertension",
    hi: "मधुमेह (8 साल), हाई ब्लड प्रेशर",
    mr: "मधुमेह (8 वर्षे), उच्च रक्तदाब",
  },
  hx_medications: { en: "Yes, daily", hi: "हाँ, रोज़", mr: "होय, रोज" },
  hx_medications_list: {
    en: "Metformin, one antihypertensive (name not recalled)",
    hi: "मेटफॉर्मिन, ब्लड प्रेशर की एक दवा (नाम याद नहीं)",
    mr: "मेटफॉर्मिन, रक्तदाबाचे एक औषध (नाव आठवत नाही)",
  },
  hx_allergies: { en: "Yes", hi: "हाँ", mr: "होय" },
  hx_allergies_list: { en: "Penicillin — rash", hi: "पेनिसिलिन — चकत्ते", mr: "पेनिसिलिन — पुरळ" },

  /* AYUSH */
  ay_vaya: { en: "42 years", hi: "42 साल", mr: "42 वर्षे" },
  ay_pk_build: { en: "Heavy build, gains weight easily", hi: "भारी शरीर, वज़न जल्दी बढ़े", mr: "भरदार शरीर, वजन लवकर वाढते" },
  ay_pk_skin: { en: "Soft, slightly oily", hi: "मुलायम, थोड़ी तैलीय", mr: "मऊ, थोडी तेलकट" },
  ay_pk_appetite: { en: "Strong, cannot skip meals", hi: "तेज़, खाना छोड़ नहीं सकते", mr: "तीव्र, जेवण टाळू शकत नाही" },
  ay_pk_sleep: { en: "Deep and long", hi: "गहरी और लंबी", mr: "गाढ आणि दीर्घ" },
  ay_pk_stress: { en: "Becomes irritated", hi: "चिढ़ जाते हैं", mr: "चिडचिड होते" },
  ay_pk_weather: { en: "Cannot tolerate heat", hi: "गर्मी सहन नहीं", mr: "उष्णता सहन होत नाही" },
  ay_vk_change: { en: "Digestion and sleep", hi: "पाचन और नींद", mr: "पचन आणि झोप" },
  ay_vk_since: { en: "About 2 weeks", hi: "लगभग 2 हफ़्ते", mr: "सुमारे 2 आठवडे" },
  ay_sara: { en: "Hair fall, dry skin", hi: "बाल झड़ना, रूखी त्वचा", mr: "केस गळणे, कोरडी त्वचा" },
  ay_samhanana: { en: "Medium build", hi: "मध्यम शरीर", mr: "मध्यम शरीरयष्टी" },
  ay_pramana: { en: "170 cm, 78 kg", hi: "170 सेमी, 78 किलो", mr: "170 सेमी, 78 किलो" },
  ay_satmya: { en: "Adapts to most things", hi: "ज़्यादातर चीज़ें सह लेते हैं", mr: "बहुतेक गोष्टी मानवतात" },
  ay_sattva: { en: "Copes with effort", hi: "कोशिश से संभाल लेते हैं", mr: "प्रयत्नाने सांभाळतात" },
  ay_ahara_shakti: { en: "Full meal, feels heavy after", hi: "भरपेट, बाद में भारी", mr: "पोटभर, नंतर जड" },
  ay_vyayama_shakti: { en: "Tires quickly", hi: "जल्दी थक जाते हैं", mr: "लवकर थकतात" },
  ay_av_diet: { en: "Vegetarian", hi: "शाकाहारी", mr: "शाकाहारी" },
  ay_av_meal_time: { en: "Irregular, work-dependent", hi: "अनियमित, काम पर निर्भर", mr: "अनियमित, कामावर अवलंबून" },
  ay_av_meal_count: { en: "Three times a day", hi: "दिन में तीन बार", mr: "दिवसातून तीन वेळा" },
  ay_av_taste: { en: "Sweet, salty", hi: "मीठा, नमकीन", mr: "गोड, खारट" },
  ay_av_sleep_time: { en: "After midnight", hi: "आधी रात के बाद", mr: "मध्यरात्रीनंतर" },
  ay_av_activity: { en: "Mostly seated", hi: "ज़्यादातर बैठे हुए", mr: "बहुतेक बसून" },
  ay_av_habits: { en: "Tobacco, occasional", hi: "तंबाकू, कभी-कभी", mr: "तंबाखू, कधीकधी" },
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
