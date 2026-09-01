/* ==========================================================================
   MOCK transcripts — a stand-in for Whisper behind the backend.

   ⚠ INTEGRATION POINT. The kiosk records audio and posts it; it never
   transcribes (build spec §7, §19). These canned utterances exist so the
   recording → processing → transcript → confirm states can be built and
   demoed before the speech service is reachable. Replace by pointing
   speechApi at the real endpoint; nothing else changes.

   Utterances are written the way a patient actually answers — not as a tidy
   restatement of the question — so the confirm step is exercised honestly.
   ========================================================================== */

import type { LanguageCode } from "@/api/types";
import { resolveLocalized, type Localized } from "@/i18n";

const TRANSCRIPTS: Record<string, Localized> = {
  cp_site: {
    en: "It is here in the middle of my chest, like something is sitting on it.",
    hi: "यहाँ छाती के बीच में है, जैसे कुछ रखा हुआ हो।",
  },
  cp_onset: {
    en: "It started this morning while I was walking to the bus stop.",
    hi: "आज सुबह बस स्टॉप तक जाते समय शुरू हुआ था।",
  },
  cp_character: {
    en: "It feels heavy, like a weight pressing down.",
    hi: "भारी लगता है, जैसे कोई वज़न दबा रहा हो।",
  },
  cp_radiation: {
    en: "Yes, it goes down my left arm sometimes.",
    hi: "हाँ, कभी-कभी बाएँ हाथ तक जाता है।",
  },
  cp_associated: {
    en: "I was sweating a lot and could not breathe properly.",
    hi: "बहुत पसीना आ रहा था और ठीक से साँस नहीं ले पा रहा था।",
  },
  cp_severity: {
    en: "It is very bad, I had to sit down.",
    hi: "बहुत तेज़ है, मुझे बैठना पड़ा।",
  },
  cp_relief: {
    en: "It gets worse when I walk. When I sit quietly it becomes a little less.",
    hi: "चलने पर बढ़ जाता है। चुपचाप बैठने पर थोड़ा कम हो जाता है।",
  },

  fc_duration: {
    en: "I have had fever for about three days now.",
    hi: "मुझे लगभग तीन दिन से बुखार है।",
  },
  fc_pattern: {
    en: "It comes in the evening and goes down by morning.",
    hi: "शाम को आता है और सुबह तक उतर जाता है।",
  },
  fc_measured: {
    en: "We checked with the thermometer at home, it was one hundred and two.",
    hi: "घर पर थर्मामीटर से देखा था, एक सौ दो था।",
  },
  fc_cough: {
    en: "Yes there is cough, and some phlegm comes out.",
    hi: "हाँ खाँसी है, और थोड़ा बलगम भी आता है।",
  },
  fc_sputum: {
    en: "It is yellowish in colour.",
    hi: "रंग पीला सा है।",
  },
  fc_associated: {
    en: "My whole body is aching and I have a headache also.",
    hi: "पूरे बदन में दर्द है और सिरदर्द भी है।",
  },

  gen_describe: {
    en: "There is pain in my right knee since about one month. It is more when I climb stairs.",
    hi: "लगभग एक महीने से दाहिने घुटने में दर्द है। सीढ़ी चढ़ने पर ज़्यादा होता है।",
  },
  gen_duration: {
    en: "It has been about a month now.",
    hi: "लगभग एक महीना हो गया है।",
  },
  gen_severity: {
    en: "I can walk but I cannot do heavy work.",
    hi: "चल लेता हूँ पर भारी काम नहीं कर पाता।",
  },

  hx_conditions: {
    en: "I have sugar since eight years and blood pressure also.",
    hi: "आठ साल से शुगर है और ब्लड प्रेशर भी है।",
  },
  hx_medications: {
    en: "Yes, I take tablets every morning.",
    hi: "हाँ, रोज़ सुबह गोली लेता हूँ।",
  },
  hx_medications_list: {
    en: "Metformin in the morning, and one tablet for blood pressure. I forget the name.",
    hi: "सुबह मेटफॉर्मिन, और ब्लड प्रेशर की एक गोली। नाम याद नहीं है।",
  },
  hx_allergies: {
    en: "Yes, one injection gave me rashes once.",
    hi: "हाँ, एक इंजेक्शन से एक बार चकत्ते हो गए थे।",
  },
  hx_allergies_list: {
    en: "It was a penicillin injection, my skin came out in red patches.",
    hi: "पेनिसिलिन का इंजेक्शन था, त्वचा पर लाल चकत्ते निकल आए थे।",
  },
};

const FALLBACK: Localized = {
  en: "Yes, that is what I wanted to say.",
  hi: "हाँ, मैं यही कहना चाहता था।",
};

export function mockTranscript(questionId: string, language: LanguageCode): string {
  return resolveLocalized(TRANSCRIPTS[questionId] ?? FALLBACK, language);
}

/** Forces the speech path to fail so the error and "Type instead" states can
 *  be exercised on demand. Random failures during a live demo are worse than
 *  no failures at all, so this is a switch, not a dice roll. */
export const FORCE_SPEECH_FAILURE = process.env.NEXT_PUBLIC_MOCK_SPEECH_FAILS === "true";
