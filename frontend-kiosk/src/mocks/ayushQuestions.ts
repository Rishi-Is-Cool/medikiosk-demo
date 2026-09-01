/* ==========================================================================
   MOCK AYUSH intake — Dashavidha Pariksha and Ahara-Vihara.

   ⚠ INTEGRATION POINT, and the one that most needs a real reviewer.

   The problem statement names ten Dashavidha axes: Prakriti, Vikriti, Sara,
   Samhanana, Pramana, Satmya, Sattva, Ahara Shakti, Vyayama Shakti and Vaya.
   `shared/snapshot-contract.json` already fixes how the doctor console
   receives them — Prakriti as vata/pitta/kapha proportions, and six of the
   axes as a pravara / madhyama / avara grade.

   WHAT THIS FILE IS NOT: it does not produce those grades. A patient cannot
   self-report "Sara: pravara" — that is a practitioner's synthesis. What a
   patient *can* answer is the proxy question underneath it: what their hair
   and skin are like, how much they can eat, whether they tire quickly. So
   this bank asks the proxies, and the raw answers go out through intakeApi
   exactly like every other answer. Turning them into doshas and grades is
   AI/backend work — the same boundary the kiosk keeps for red-flag priority,
   for the same reason.

   ⚠ CLINICAL REVIEW REQUIRED. These proxies are drafted from the standard
   published descriptions of each axis and are shaped to be answerable by a
   patient with no Ayurvedic vocabulary. A real Prakriti questionnaire runs
   to twenty or forty items; this is six. Nothing here has been reviewed by an
   Ayurveda practitioner and it must be before any of it is shown at AIIA.
   ========================================================================== */

import type { MockQuestion, MockSection } from "./questionTypes";

/* --- Dashavidha Pariksha -------------------------------------------------- */

export const AYUSH_BANK: Record<string, MockQuestion> = {
  /* ---- Vaya (life stage) — the console derives this from age ---- */

  ay_vaya: {
    id: "ay_vaya",
    text: { en: "How old are you?", hi: "आपकी उम्र कितनी है?", mr: "तुमचे वय किती आहे?" },
    helper: {
      en: "Say the number of years, or tap the group you belong to.",
      hi: "साल में उम्र बोलिए, या अपना समूह चुनिए।",
      mr: "वर्षांमध्ये वय सांगा, किंवा तुमचा गट निवडा.",
    },
    input_type: "voice_or_touch",
    allow_text: true,
    options: [
      { value: "bala", label: { en: "Under 16 years", hi: "16 साल से कम", mr: "16 वर्षांखालील" } },
      { value: "madhya_young", label: { en: "16 to 30 years", hi: "16 से 30 साल", mr: "16 ते 30 वर्षे" } },
      { value: "madhya", label: { en: "31 to 60 years", hi: "31 से 60 साल", mr: "31 ते 60 वर्षे" } },
      { value: "vriddha", label: { en: "Over 60 years", hi: "60 साल से ज़्यादा", mr: "60 वर्षांवरील" } },
    ],
  },

  /* ---- Prakriti (constitution) — six proxies, one per classical marker ---- */

  ay_pk_build: {
    id: "ay_pk_build",
    text: {
      en: "Which best describes your body build, through your life?",
      hi: "आपका शरीर हमेशा से कैसा रहा है?",
      mr: "तुमची शरीरयष्टी आयुष्यभर कशी राहिली आहे?",
    },
    helper: {
      en: "Think of how you have usually been, not just now.",
      hi: "अभी नहीं, हमेशा से कैसा रहा है यह सोचिए।",
      mr: "फक्त आत्ताचे नाही, नेहमी कसे होते ते आठवा.",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "vata", label: { en: "Thin — I find it hard to gain weight", hi: "पतला — वज़न बढ़ाना मुश्किल लगता है", mr: "बारीक — वजन वाढवणे कठीण जाते" } },
      { value: "pitta", label: { en: "Medium and muscular", hi: "मध्यम और गठीला", mr: "मध्यम आणि पिळदार" } },
      { value: "kapha", label: { en: "Broad — I gain weight easily", hi: "भारी — वज़न आसानी से बढ़ता है", mr: "भरदार — वजन सहज वाढते" } },
    ],
  },

  ay_pk_skin: {
    id: "ay_pk_skin",
    text: {
      en: "How is your skin, usually?",
      hi: "आपकी त्वचा आमतौर पर कैसी रहती है?",
      mr: "तुमची त्वचा सहसा कशी असते?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "vata", label: { en: "Dry and rough", hi: "रूखी और खुरदरी", mr: "कोरडी आणि खरखरीत" } },
      { value: "pitta", label: { en: "Warm, and marks or reddens easily", hi: "गर्म, जल्दी लाल हो जाती है", mr: "उष्ण, लवकर लाल होते" } },
      { value: "kapha", label: { en: "Soft, smooth, somewhat oily", hi: "मुलायम, चिकनी, कुछ तैलीय", mr: "मऊ, गुळगुळीत, थोडी तेलकट" } },
    ],
  },

  ay_pk_appetite: {
    id: "ay_pk_appetite",
    text: {
      en: "How is your hunger, usually?",
      hi: "आपकी भूख आमतौर पर कैसी रहती है?",
      mr: "तुमची भूक सहसा कशी असते?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "vata", label: { en: "Irregular — sometimes a lot, sometimes none", hi: "अनियमित — कभी ज़्यादा, कभी बिलकुल नहीं", mr: "अनियमित — कधी खूप, कधी अजिबात नाही" } },
      { value: "pitta", label: { en: "Strong — I cannot skip a meal", hi: "तेज़ — मैं खाना छोड़ नहीं सकता", mr: "तीव्र — मी जेवण टाळू शकत नाही" } },
      { value: "kapha", label: { en: "Steady but small", hi: "एक जैसी पर कम", mr: "स्थिर पण कमी" } },
    ],
  },

  ay_pk_sleep: {
    id: "ay_pk_sleep",
    text: { en: "How do you sleep, usually?", hi: "आपकी नींद आमतौर पर कैसी होती है?", mr: "तुमची झोप सहसा कशी असते?" },
    input_type: "voice_or_touch",
    options: [
      { value: "vata", label: { en: "Light — I wake up often", hi: "कच्ची — बार-बार खुल जाती है", mr: "हलकी — वारंवार जाग येते" } },
      { value: "pitta", label: { en: "Moderate — I sleep through mostly", hi: "ठीक-ठाक — ज़्यादातर पूरी होती है", mr: "मध्यम — बहुतेकदा पूर्ण होते" } },
      { value: "kapha", label: { en: "Deep and long", hi: "गहरी और लंबी", mr: "गाढ आणि दीर्घ" } },
    ],
  },

  ay_pk_stress: {
    id: "ay_pk_stress",
    text: {
      en: "When something troubles you, how do you usually react?",
      hi: "जब कोई परेशानी होती है तो आप आमतौर पर कैसे रहते हैं?",
      mr: "काही त्रास झाल्यावर तुमची सहसा कशी प्रतिक्रिया असते?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "vata", label: { en: "I worry and feel restless", hi: "चिंता होती है, बेचैनी लगती है", mr: "काळजी वाटते, अस्वस्थ होतो" } },
      { value: "pitta", label: { en: "I become irritated or angry", hi: "चिढ़ या ग़ुस्सा आता है", mr: "चिडचिड किंवा राग येतो" } },
      { value: "kapha", label: { en: "I become quiet and withdraw", hi: "चुप हो जाता हूँ, अलग रहता हूँ", mr: "शांत होतो, बाजूला राहतो" } },
    ],
  },

  ay_pk_weather: {
    id: "ay_pk_weather",
    text: {
      en: "Which weather suits you least?",
      hi: "कौन सा मौसम आपको सबसे कम भाता है?",
      mr: "कोणते हवामान तुम्हाला सर्वात कमी मानवते?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "vata", label: { en: "Cold and dry weather", hi: "ठंडा और सूखा मौसम", mr: "थंड आणि कोरडे हवामान" } },
      { value: "pitta", label: { en: "Hot weather", hi: "गर्मी", mr: "उष्ण हवामान" } },
      { value: "kapha", label: { en: "Cold and damp weather", hi: "ठंडा और सीलनभरा मौसम", mr: "थंड आणि दमट हवामान" } },
    ],
  },

  /* ---- Vikriti (present imbalance) — what has changed from the above ---- */

  ay_vk_change: {
    id: "ay_vk_change",
    text: {
      en: "Compared with your usual self, what feels different now?",
      hi: "आम दिनों के मुक़ाबले अभी क्या अलग लग रहा है?",
      mr: "नेहमीच्या तुलनेत आता काय वेगळे वाटते आहे?",
    },
    input_type: "multi_select",
    options: [
      { value: "digestion", label: { en: "My digestion", hi: "पाचन", mr: "पचन" } },
      { value: "sleep", label: { en: "My sleep", hi: "नींद", mr: "झोप" } },
      { value: "energy", label: { en: "My energy", hi: "ताक़त", mr: "ऊर्जा" } },
      { value: "mood", label: { en: "My mood", hi: "मन की स्थिति", mr: "मनःस्थिती" } },
      { value: "bowel", label: { en: "My bowel habit", hi: "शौच की आदत", mr: "शौचाची सवय" } },
      { value: "none", label: { en: "Nothing feels different", hi: "कुछ अलग नहीं लग रहा", mr: "काहीही वेगळे वाटत नाही" }, exclusive: true },
    ],
  },

  ay_vk_since: {
    id: "ay_vk_since",
    text: {
      en: "How long has it felt this way?",
      hi: "यह कब से ऐसा लग रहा है?",
      mr: "हे किती काळापासून असे वाटते आहे?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "days", label: { en: "A few days", hi: "कुछ दिनों से", mr: "काही दिवसांपासून" } },
      { value: "weeks", label: { en: "A few weeks", hi: "कुछ हफ़्तों से", mr: "काही आठवड्यांपासून" } },
      { value: "months", label: { en: "A few months", hi: "कुछ महीनों से", mr: "काही महिन्यांपासून" } },
      { value: "longer", label: { en: "Longer than that", hi: "उससे भी ज़्यादा", mr: "त्याहूनही अधिक" } },
    ],
  },

  /* ---- Sara (tissue quality) ---- */

  ay_sara: {
    id: "ay_sara",
    text: {
      en: "How are your hair, skin and nails?",
      hi: "आपके बाल, त्वचा और नाखून कैसे हैं?",
      mr: "तुमचे केस, त्वचा आणि नखे कशी आहेत?",
    },
    input_type: "scale",
    scale_tone: "grade",
    options: [
      { value: "avara", label: { en: "Dry, brittle, thinning", hi: "रूखे, कमज़ोर, झड़ते हुए", mr: "कोरडे, ठिसूळ, गळणारे" } },
      { value: "madhyama", label: { en: "Average", hi: "ठीक-ठाक", mr: "साधारण" } },
      { value: "pravara", label: { en: "Strong and glossy", hi: "मज़बूत और चमकदार", mr: "मजबूत आणि चमकदार" } },
    ],
  },

  /* ---- Samhanana (compactness of build) ---- */

  ay_samhanana: {
    id: "ay_samhanana",
    text: {
      en: "How would you describe your body's firmness?",
      hi: "आपका शरीर कितना कसा हुआ है?",
      mr: "तुमचे शरीर किती घट्ट आहे?",
    },
    input_type: "scale",
    scale_tone: "grade",
    options: [
      { value: "avara", label: { en: "Loose and weak", hi: "ढीला और कमज़ोर", mr: "सैल आणि कमजोर" } },
      { value: "madhyama", label: { en: "Moderate", hi: "मध्यम", mr: "मध्यम" } },
      { value: "pravara", label: { en: "Firm and well-built", hi: "कसा हुआ और मज़बूत", mr: "घट्ट आणि सुदृढ" } },
    ],
  },

  /* ---- Pramana (body measurement) ---- */

  ay_pramana: {
    id: "ay_pramana",
    text: {
      en: "What is your height and weight?",
      hi: "आपकी लंबाई और वज़न कितना है?",
      mr: "तुमची उंची आणि वजन किती आहे?",
    },
    helper: {
      en: "If you do not know exactly, say roughly. Staff can measure you later.",
      hi: "ठीक-ठीक न पता हो तो अंदाज़ा बता दीजिए। कर्मचारी बाद में नाप लेंगे।",
      mr: "नक्की माहीत नसेल तर अंदाजे सांगा. कर्मचारी नंतर मोजतील.",
    },
    input_type: "voice_or_text",
    allow_text: true,
  },

  /* ---- Satmya (adaptability / habituation) ---- */

  ay_satmya: {
    id: "ay_satmya",
    text: {
      en: "How well do you handle new food, water or a change of place?",
      hi: "नया खाना, पानी या जगह बदलना आपको कितना सहता है?",
      mr: "नवीन अन्न, पाणी किंवा ठिकाण बदलणे तुम्हाला किती मानवते?",
    },
    input_type: "scale",
    scale_tone: "grade",
    options: [
      { value: "avara", label: { en: "It upsets me easily", hi: "जल्दी तकलीफ़ हो जाती है", mr: "लवकर त्रास होतो" } },
      { value: "madhyama", label: { en: "Most things suit me", hi: "ज़्यादातर चीज़ें सह लेता हूँ", mr: "बहुतेक गोष्टी मानवतात" } },
      { value: "pravara", label: { en: "Everything suits me", hi: "सब कुछ सह लेता हूँ", mr: "सर्व काही मानवते" } },
    ],
  },

  /* ---- Sattva (mental resilience) ---- */

  ay_sattva: {
    id: "ay_sattva",
    text: {
      en: "When you are in pain or difficulty, how do you hold up?",
      hi: "दर्द या मुश्किल में आप कितना सह लेते हैं?",
      mr: "वेदना किंवा अडचणीत तुम्ही किती टिकून राहता?",
    },
    input_type: "scale",
    scale_tone: "grade",
    options: [
      { value: "avara", label: { en: "I get disturbed quickly", hi: "जल्दी घबरा जाता हूँ", mr: "लवकर अस्वस्थ होतो" } },
      { value: "madhyama", label: { en: "I manage, with effort", hi: "कोशिश करके संभाल लेता हूँ", mr: "प्रयत्नाने सांभाळतो" } },
      { value: "pravara", label: { en: "I stay steady", hi: "शांत बना रहता हूँ", mr: "स्थिर राहतो" } },
    ],
  },

  /* ---- Ahara Shakti (digestive capacity) ---- */

  ay_ahara_shakti: {
    id: "ay_ahara_shakti",
    text: {
      en: "How much can you eat at one meal, and does it digest well?",
      hi: "एक बार में कितना खा लेते हैं, और क्या वह ठीक से पचता है?",
      mr: "एका जेवणात किती खाऊ शकता, आणि ते नीट पचते का?",
    },
    input_type: "scale",
    scale_tone: "grade",
    options: [
      { value: "avara", label: { en: "Only a little, and it sits heavy", hi: "थोड़ा ही, और भारी लगता है", mr: "थोडेच, आणि जड वाटते" } },
      { value: "madhyama", label: { en: "A normal meal, digests alright", hi: "सामान्य भोजन, ठीक पच जाता है", mr: "साधारण जेवण, ठीक पचते" } },
      { value: "pravara", label: { en: "A full meal, digests easily", hi: "भरपेट, आसानी से पच जाता है", mr: "पोटभर, सहज पचते" } },
    ],
  },

  /* ---- Vyayama Shakti (capacity for exertion) ---- */

  ay_vyayama_shakti: {
    id: "ay_vyayama_shakti",
    text: {
      en: "How much physical work can you do before you tire?",
      hi: "थकने से पहले आप कितना शारीरिक काम कर लेते हैं?",
      mr: "थकण्यापूर्वी तुम्ही किती शारीरिक काम करू शकता?",
    },
    input_type: "scale",
    scale_tone: "grade",
    options: [
      { value: "avara", label: { en: "I tire very quickly", hi: "बहुत जल्दी थक जाता हूँ", mr: "खूप लवकर थकतो" } },
      { value: "madhyama", label: { en: "Ordinary work is fine", hi: "आम काम कर लेता हूँ", mr: "सामान्य काम जमते" } },
      { value: "pravara", label: { en: "I can do heavy work without tiring", hi: "भारी काम भी बिना थके कर लेता हूँ", mr: "जड कामही न थकता करतो" } },
    ],
  },

  /* --- Ahara-Vihara — diet and daily conduct ------------------------------
     ⚠ NO AGREED CONTRACT. Unlike the Dashavidha axes, nothing anywhere in
     the project — not ai/intake/schemas.py, not shared/snapshot-contract.json,
     not the doctor console — models Ahara-Vihara yet. These questions capture
     what the classical assessment covers, but the shape they should be
     delivered in has to be agreed with whoever owns AI synthesis before this
     is anything more than a demo.                                          */

  ay_av_diet: {
    id: "ay_av_diet",
    text: { en: "What do you usually eat?", hi: "आप आमतौर पर क्या खाते हैं?", mr: "तुम्ही सहसा काय खाता?" },
    input_type: "voice_or_touch",
    options: [
      { value: "vegetarian", label: { en: "Vegetarian", hi: "शाकाहारी", mr: "शाकाहारी" } },
      { value: "eggetarian", label: { en: "Vegetarian, with eggs", hi: "शाकाहारी, अंडे के साथ", mr: "शाकाहारी, अंड्यांसह" } },
      { value: "nonveg_some", label: { en: "Non-vegetarian sometimes", hi: "कभी-कभी मांसाहारी", mr: "कधीकधी मांसाहारी" } },
      { value: "nonveg_regular", label: { en: "Non-vegetarian regularly", hi: "नियमित मांसाहारी", mr: "नियमित मांसाहारी" } },
    ],
  },

  ay_av_meal_time: {
    id: "ay_av_meal_time",
    text: {
      en: "Do you eat your meals at the same times each day?",
      hi: "क्या आप रोज़ एक ही समय पर खाना खाते हैं?",
      mr: "तुम्ही दररोज एकाच वेळी जेवता का?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "regular", label: { en: "Yes, at fixed times", hi: "हाँ, तय समय पर", mr: "होय, ठरलेल्या वेळी" } },
      { value: "mostly", label: { en: "Mostly", hi: "ज़्यादातर", mr: "बहुतेकदा" } },
      { value: "irregular", label: { en: "No, it changes every day", hi: "नहीं, रोज़ बदलता रहता है", mr: "नाही, रोज बदलते" } },
    ],
  },

  ay_av_meal_count: {
    id: "ay_av_meal_count",
    text: {
      en: "How many times a day do you eat?",
      hi: "दिन में कितनी बार खाते हैं?",
      mr: "दिवसातून किती वेळा खाता?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "one_two", label: { en: "Once or twice", hi: "एक या दो बार", mr: "एकदा किंवा दोनदा" } },
      { value: "three", label: { en: "Three times", hi: "तीन बार", mr: "तीन वेळा" } },
      { value: "frequent", label: { en: "More than three, with snacks", hi: "तीन से ज़्यादा, बीच में नाश्ता भी", mr: "तीनहून अधिक, मधे खाणेही" } },
    ],
  },

  ay_av_taste: {
    id: "ay_av_taste",
    text: {
      en: "Which tastes do you like most in your food?",
      hi: "खाने में आपको कौन से स्वाद सबसे अच्छे लगते हैं?",
      mr: "जेवणात तुम्हाला कोणत्या चवी सर्वात आवडतात?",
    },
    helper: {
      en: "Choose as many as you like.",
      hi: "जितने चाहें उतने चुन सकते हैं।",
      mr: "तुम्हाला हवे तितके निवडा.",
    },
    input_type: "multi_select",
    options: [
      { value: "madhura", label: { en: "Sweet", hi: "मीठा", mr: "गोड" } },
      { value: "amla", label: { en: "Sour", hi: "खट्टा", mr: "आंबट" } },
      { value: "lavana", label: { en: "Salty", hi: "नमकीन", mr: "खारट" } },
      { value: "katu", label: { en: "Spicy or pungent", hi: "तीखा", mr: "तिखट" } },
      { value: "tikta", label: { en: "Bitter", hi: "कड़वा", mr: "कडू" } },
      { value: "kashaya", label: { en: "Astringent", hi: "कसैला", mr: "तुरट" } },
    ],
  },

  ay_av_sleep_time: {
    id: "ay_av_sleep_time",
    text: {
      en: "What time do you usually go to sleep?",
      hi: "आप आमतौर पर कितने बजे सोते हैं?",
      mr: "तुम्ही सहसा किती वाजता झोपता?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "early", label: { en: "Before 10 at night", hi: "रात 10 बजे से पहले", mr: "रात्री 10 च्या आधी" } },
      { value: "normal", label: { en: "Between 10 and midnight", hi: "10 से 12 बजे के बीच", mr: "10 ते 12 च्या दरम्यान" } },
      { value: "late", label: { en: "After midnight", hi: "आधी रात के बाद", mr: "मध्यरात्रीनंतर" } },
      { value: "irregular", label: { en: "It changes every day", hi: "रोज़ बदलता रहता है", mr: "रोज बदलते" } },
    ],
  },

  ay_av_activity: {
    id: "ay_av_activity",
    text: {
      en: "How much do you move about in a normal day?",
      hi: "आम दिन में आप कितना चलते-फिरते हैं?",
      mr: "सामान्य दिवसात तुम्ही किती हालचाल करता?",
    },
    input_type: "voice_or_touch",
    options: [
      { value: "exercise", label: { en: "I exercise daily", hi: "रोज़ व्यायाम करता हूँ", mr: "रोज व्यायाम करतो" } },
      { value: "walking", label: { en: "I walk, but do not exercise", hi: "चलता हूँ, पर व्यायाम नहीं करता", mr: "चालतो, पण व्यायाम करत नाही" } },
      { value: "sedentary", label: { en: "I sit for most of the day", hi: "दिन भर ज़्यादातर बैठा रहता हूँ", mr: "दिवसभर बहुतेक बसून असतो" } },
      { value: "labour", label: { en: "I do heavy physical work", hi: "भारी शारीरिक काम करता हूँ", mr: "जड शारीरिक काम करतो" } },
    ],
  },

  ay_av_habits: {
    id: "ay_av_habits",
    text: {
      en: "Do you use any of these?",
      hi: "क्या आप इनमें से कुछ लेते हैं?",
      mr: "तुम्ही यापैकी काही घेता का?",
    },
    helper: {
      en: "This stays between you and your doctor.",
      hi: "यह बात आपके और डॉक्टर के बीच रहेगी।",
      mr: "ही गोष्ट तुमच्या आणि डॉक्टरांमध्येच राहील.",
    },
    input_type: "multi_select",
    options: [
      { value: "tobacco", label: { en: "Tobacco or gutka", hi: "तंबाकू या गुटखा", mr: "तंबाखू किंवा गुटखा" } },
      { value: "smoking", label: { en: "Smoking", hi: "धूम्रपान", mr: "धूम्रपान" } },
      { value: "alcohol", label: { en: "Alcohol", hi: "शराब", mr: "मद्य" } },
      { value: "none", label: { en: "None of these", hi: "इनमें से कुछ नहीं", mr: "यापैकी काहीही नाही" }, exclusive: true },
    ],
  },
};

/* --- Sections ------------------------------------------------------------
   Four named parts. The complaint line and the shared history tail are added
   around these by the plan builder in questions.ts.                        */

export const AYUSH_SECTIONS: MockSection[] = [
  {
    id: "ayush_body",
    label: { en: "About your body", hi: "आपके शरीर के बारे में", mr: "तुमच्या शरीराविषयी" },
    questions: [
      "ay_vaya",
      "ay_pk_build",
      "ay_pk_skin",
      "ay_pk_appetite",
      "ay_pk_sleep",
      "ay_pk_stress",
      "ay_pk_weather",
      "ay_pramana",
    ],
  },
  {
    id: "ayush_present",
    label: { en: "How you feel now", hi: "अभी आप कैसा महसूस कर रहे हैं", mr: "आता तुम्हाला कसे वाटते" },
    questions: ["ay_vk_change", "ay_vk_since"],
  },
  {
    id: "ayush_strength",
    label: { en: "Your strength and digestion", hi: "आपकी ताक़त और पाचन", mr: "तुमची ताकद आणि पचन" },
    questions: [
      "ay_sara",
      "ay_samhanana",
      "ay_satmya",
      "ay_sattva",
      "ay_ahara_shakti",
      "ay_vyayama_shakti",
    ],
  },
  {
    id: "ayush_ahara_vihara",
    label: { en: "Food and daily routine", hi: "खान-पान और दिनचर्या", mr: "आहार आणि दिनचर्या" },
    questions: [
      "ay_av_diet",
      "ay_av_meal_time",
      "ay_av_meal_count",
      "ay_av_taste",
      "ay_av_sleep_time",
      "ay_av_activity",
      "ay_av_habits",
    ],
  },
];
