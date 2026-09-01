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
  /* ---- Chief complaint, spoken before any list is shown ---- */
  chief_complaint: {
    en: "I have had fever and a cough for the last three days.",
    hi: "मुझे पिछले तीन दिन से बुखार और खाँसी है।",
    mr: "मला गेल्या तीन दिवसांपासून ताप आणि खोकला आहे.",
  },

  /* ---- Chest pain ---- */
  cp_site: {
    en: "It is here in the middle of my chest, like something is sitting on it.",
    hi: "यहाँ छाती के बीच में है, जैसे कुछ रखा हुआ हो।",
    mr: "इथे छातीच्या मध्यभागी आहे, जणू काहीतरी ठेवले आहे.",
  },
  cp_onset: {
    en: "It started this morning while I was walking to the bus stop.",
    hi: "आज सुबह बस स्टॉप तक जाते समय शुरू हुआ था।",
    mr: "आज सकाळी बस स्टॉपकडे जाताना सुरू झाले.",
  },
  cp_character: {
    en: "It feels heavy, like a weight pressing down.",
    hi: "भारी लगता है, जैसे कोई वज़न दबा रहा हो।",
    mr: "जड वाटते, जणू काहीतरी दाबते आहे.",
  },
  cp_radiation: {
    en: "Yes, it goes down my left arm sometimes.",
    hi: "हाँ, कभी-कभी बाएँ हाथ तक जाता है।",
    mr: "होय, कधीकधी डाव्या हातापर्यंत जाते.",
  },
  cp_associated: {
    en: "I was sweating a lot and could not breathe properly.",
    hi: "बहुत पसीना आ रहा था और ठीक से साँस नहीं ले पा रहा था।",
    mr: "खूप घाम येत होता आणि नीट श्वास घेता येत नव्हता.",
  },
  cp_severity: {
    en: "It is very bad, I had to sit down.",
    hi: "बहुत तेज़ है, मुझे बैठना पड़ा।",
    mr: "खूप तीव्र आहे, मला बसावे लागले.",
  },
  cp_relief: {
    en: "It gets worse when I walk. When I sit quietly it becomes a little less.",
    hi: "चलने पर बढ़ जाता है। चुपचाप बैठने पर थोड़ा कम हो जाता है।",
    mr: "चालल्यावर वाढते. शांत बसल्यावर थोडे कमी होते.",
  },

  /* ---- Fever and cough ---- */
  fc_duration: {
    en: "I have had fever for about three days now.",
    hi: "मुझे लगभग तीन दिन से बुखार है।",
    mr: "मला सुमारे तीन दिवसांपासून ताप आहे.",
  },
  fc_pattern: {
    en: "It comes in the evening and goes down by morning.",
    hi: "शाम को आता है और सुबह तक उतर जाता है।",
    mr: "संध्याकाळी येतो आणि सकाळपर्यंत उतरतो.",
  },
  fc_measured: {
    en: "We checked with the thermometer at home, it was one hundred and two.",
    hi: "घर पर थर्मामीटर से देखा था, एक सौ दो था।",
    mr: "घरी थर्मामीटरने पाहिले होते, एकशे दोन होता.",
  },
  fc_cough: {
    en: "Yes there is cough, and some phlegm comes out.",
    hi: "हाँ खाँसी है, और थोड़ा बलगम भी आता है।",
    mr: "होय खोकला आहे, आणि थोडा कफही येतो.",
  },
  fc_sputum: { en: "It is yellowish in colour.", hi: "रंग पीला सा है।", mr: "रंग पिवळसर आहे." },
  fc_associated: {
    en: "My whole body is aching and I have a headache also.",
    hi: "पूरे बदन में दर्द है और सिरदर्द भी है।",
    mr: "संपूर्ण अंग दुखते आहे आणि डोकेही दुखते.",
  },

  /* ---- Generic ---- */
  gen_describe: {
    en: "There is pain in my right knee since about one month. It is more when I climb stairs.",
    hi: "लगभग एक महीने से दाहिने घुटने में दर्द है। सीढ़ी चढ़ने पर ज़्यादा होता है।",
    mr: "सुमारे एका महिन्यापासून उजवा गुडघा दुखतो. जिना चढताना जास्त दुखतो.",
  },
  gen_duration: { en: "It has been about a month now.", hi: "लगभग एक महीना हो गया है।", mr: "सुमारे एक महिना झाला आहे." },
  gen_severity: {
    en: "I can walk but I cannot do heavy work.",
    hi: "चल लेता हूँ पर भारी काम नहीं कर पाता।",
    mr: "चालू शकतो पण जड काम करू शकत नाही.",
  },

  /* ---- History tail ---- */
  hx_conditions: {
    en: "I have sugar since eight years and blood pressure also.",
    hi: "आठ साल से शुगर है और ब्लड प्रेशर भी है।",
    mr: "आठ वर्षांपासून साखर आहे आणि रक्तदाबही आहे.",
  },
  hx_medications: { en: "Yes, I take tablets every morning.", hi: "हाँ, रोज़ सुबह गोली लेता हूँ।", mr: "होय, रोज सकाळी गोळी घेतो." },
  hx_medications_list: {
    en: "Metformin in the morning, and one tablet for blood pressure. I forget the name.",
    hi: "सुबह मेटफॉर्मिन, और ब्लड प्रेशर की एक गोली। नाम याद नहीं है।",
    mr: "सकाळी मेटफॉर्मिन, आणि रक्तदाबाची एक गोळी. नाव आठवत नाही.",
  },
  hx_allergies: {
    en: "Yes, one injection gave me rashes once.",
    hi: "हाँ, एक इंजेक्शन से एक बार चकत्ते हो गए थे।",
    mr: "होय, एका इंजेक्शनने एकदा पुरळ आले होते.",
  },
  hx_allergies_list: {
    en: "It was a penicillin injection, my skin came out in red patches.",
    hi: "पेनिसिलिन का इंजेक्शन था, त्वचा पर लाल चकत्ते निकल आए थे।",
    mr: "पेनिसिलिनचे इंजेक्शन होते, त्वचेवर लाल पुरळ आले होते.",
  },

  /* ---- AYUSH — Dashavidha Pariksha ---- */
  ay_vaya: { en: "I am forty-two years old.", hi: "मैं बयालीस साल का हूँ।", mr: "मी बेचाळीस वर्षांचा आहे." },
  ay_pk_build: {
    en: "I have always been on the heavier side, I put on weight easily.",
    hi: "मैं हमेशा से भारी रहा हूँ, वज़न जल्दी बढ़ जाता है।",
    mr: "मी नेहमीच भरदार राहिलो आहे, वजन लवकर वाढते.",
  },
  ay_pk_skin: {
    en: "My skin is soft, a little oily.",
    hi: "मेरी त्वचा मुलायम है, थोड़ी तैलीय।",
    mr: "माझी त्वचा मऊ आहे, थोडी तेलकट.",
  },
  ay_pk_appetite: {
    en: "I get very hungry, I cannot skip a meal.",
    hi: "मुझे बहुत भूख लगती है, खाना छोड़ नहीं सकता।",
    mr: "मला खूप भूक लागते, जेवण टाळू शकत नाही.",
  },
  ay_pk_sleep: { en: "I sleep deeply and for long.", hi: "मेरी नींद गहरी और लंबी होती है।", mr: "माझी झोप गाढ आणि दीर्घ असते." },
  ay_pk_stress: {
    en: "I get irritated quickly when something goes wrong.",
    hi: "कुछ गड़बड़ हो तो जल्दी चिढ़ जाता हूँ।",
    mr: "काही बिघडले की मला लवकर चिडचिड होते.",
  },
  ay_pk_weather: { en: "I cannot bear the heat.", hi: "मुझसे गर्मी बर्दाश्त नहीं होती।", mr: "मला उष्णता सहन होत नाही." },
  ay_vk_change: {
    en: "My digestion has been off, and I am not sleeping well.",
    hi: "पाचन ठीक नहीं चल रहा, और नींद भी ठीक नहीं आ रही।",
    mr: "पचन नीट होत नाही, आणि झोपही नीट लागत नाही.",
  },
  ay_vk_since: { en: "About two weeks now.", hi: "लगभग दो हफ़्ते से।", mr: "सुमारे दोन आठवड्यांपासून." },
  ay_sara: {
    en: "My hair has been falling and my skin is dry these days.",
    hi: "आजकल बाल झड़ रहे हैं और त्वचा रूखी है।",
    mr: "हल्ली केस गळत आहेत आणि त्वचा कोरडी आहे.",
  },
  ay_samhanana: { en: "My body is medium built.", hi: "मेरा शरीर मध्यम है।", mr: "माझी शरीरयष्टी मध्यम आहे." },
  ay_pramana: {
    en: "About five feet seven inches, and around seventy-eight kilos.",
    hi: "लगभग पाँच फुट सात इंच, और करीब अठहत्तर किलो।",
    mr: "सुमारे पाच फूट सात इंच, आणि अठ्ठ्याहत्तर किलोच्या आसपास.",
  },
  ay_satmya: {
    en: "New food and water usually suit me.",
    hi: "नया खाना-पानी आमतौर पर सह लेता हूँ।",
    mr: "नवीन अन्न-पाणी सहसा मानवते.",
  },
  ay_sattva: {
    en: "I manage, but it takes effort.",
    hi: "संभाल लेता हूँ, पर मेहनत लगती है।",
    mr: "सांभाळतो, पण प्रयत्न करावे लागतात.",
  },
  ay_ahara_shakti: {
    en: "I eat a full meal but it feels heavy afterwards.",
    hi: "भरपेट खाता हूँ पर बाद में भारी लगता है।",
    mr: "पोटभर जेवतो पण नंतर जड वाटते.",
  },
  ay_vyayama_shakti: {
    en: "I tire quickly these days, even walking up stairs.",
    hi: "आजकल जल्दी थक जाता हूँ, सीढ़ी चढ़ने पर भी।",
    mr: "हल्ली लवकर थकतो, जिना चढतानाही.",
  },

  /* ---- AYUSH — Ahara-Vihara ---- */
  ay_av_diet: { en: "I am vegetarian.", hi: "मैं शाकाहारी हूँ।", mr: "मी शाकाहारी आहे." },
  ay_av_meal_time: {
    en: "No, my meal times keep changing because of work.",
    hi: "नहीं, काम की वजह से खाने का समय बदलता रहता है।",
    mr: "नाही, कामामुळे जेवणाची वेळ बदलत राहते.",
  },
  ay_av_meal_count: { en: "Three times a day.", hi: "दिन में तीन बार।", mr: "दिवसातून तीन वेळा." },
  ay_av_taste: {
    en: "I like sweet and salty food the most.",
    hi: "मुझे मीठा और नमकीन सबसे अच्छा लगता है।",
    mr: "मला गोड आणि खारट सर्वात आवडते.",
  },
  ay_av_sleep_time: {
    en: "Usually after midnight.",
    hi: "आमतौर पर आधी रात के बाद।",
    mr: "सहसा मध्यरात्रीनंतर.",
  },
  ay_av_activity: {
    en: "I sit at work most of the day.",
    hi: "काम पर दिन भर ज़्यादातर बैठा रहता हूँ।",
    mr: "कामावर दिवसभर बहुतेक बसून असतो.",
  },
  ay_av_habits: {
    en: "I chew tobacco sometimes. Nothing else.",
    hi: "कभी-कभी तंबाकू खाता हूँ। और कुछ नहीं।",
    mr: "कधीकधी तंबाखू खातो. बाकी काही नाही.",
  },
};

const FALLBACK: Localized = {
  en: "Yes, that is what I wanted to say.",
  hi: "हाँ, मैं यही कहना चाहता था।",
  mr: "होय, मला हेच सांगायचे होते.",
};

export function mockTranscript(questionId: string, language: LanguageCode): string {
  return resolveLocalized(TRANSCRIPTS[questionId] ?? FALLBACK, language);
}

/** Forces the speech path to fail so the error and "Type instead" states can
 *  be exercised on demand. Random failures during a live demo are worse than
 *  no failures at all, so this is a switch, not a dice roll. */
export const FORCE_SPEECH_FAILURE = process.env.NEXT_PUBLIC_MOCK_SPEECH_FAILS === "true";
