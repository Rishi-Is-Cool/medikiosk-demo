"""
MediKiosk Backend — Conversational Multimodal History Engine: Question Engine
Implements SOCRATES framework for Allopathy and full Dashavidha Pariksha for AYUSH mode.
Dynamically branches follow-up questions based on chief complaint.
"""
from typing import Dict, Any, List, Optional
from app.ai.red_flag_detector import red_flag_detector

# ─── Allopathy — Core Steps (SOCRATES Framework) ──────────────────────────────
ALLOPATHY_STEPS = [
    {
        "id": "q1_chief_complaint",
        "step": 1,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "What brings you to the hospital today? Please describe your main health concern.",
            "hi": "आज आप अस्पताल किस मुख्य स्वास्थ्य समस्या के लिए आए हैं? कृपया अपनी परेशानी बताएं।",
            "mr": "आज आपण रुग्णालयात कोणत्या मुख्य आरोग्याच्या समस्येसाठी आला आहात? कृपया तुमची अडचण सांगा."
        },
        "options": [
            {"label": "Chest Pain / छाती में दर्द", "value": "chest_pain"},
            {"label": "Fever & Cough / बुखार और खांसी", "value": "fever_cough"},
            {"label": "Abdominal Pain / पेट दर्द", "value": "abdominal_pain"},
            {"label": "Joint Pain / जोड़ों में दर्द", "value": "joint_pain"},
            {"label": "Headache & Dizziness / सिरदर्द और चक्कर", "value": "headache"},
            {"label": "Difficulty Breathing / सांस लेने में तकलीफ", "value": "breathlessness"},
            {"label": "Weakness / Fatigue / कमजोरी", "value": "weakness"},
            {"label": "Other / अन्य", "value": "other"}
        ]
    },
    {
        "id": "q2_duration_onset",
        "step": 2,
        "input_type": "options",
        "question_text": {
            "en": "When did this problem start? How long have you been experiencing it?",
            "hi": "यह समस्या कब से शुरू हुई? आपको यह तकलीफ कितने समय से हो रही है?",
            "mr": "हा त्रास कधी सुरू झाला? तुम्हाला किती दिवसांपासून होत आहे?"
        },
        "options": [
            {"label": "Just started (< 1 hour) / अभी शुरू हुई", "value": "acute_1h"},
            {"label": "Today (< 24 hours) / आज", "value": "acute_24h"},
            {"label": "1 to 3 days / 1 से 3 दिन", "value": "1_3_days"},
            {"label": "1 to 2 weeks / 1 से 2 सप्ताह", "value": "1_2_weeks"},
            {"label": "More than 1 month / 1 महीने से अधिक", "value": "gt_1_month"},
            {"label": "Recurring problem / बार-बार होने वाली समस्या", "value": "recurrent"}
        ]
    },
    {
        "id": "q3_severity_scale",
        "step": 3,
        "input_type": "options",
        "question_text": {
            "en": "On a scale of 1 to 10, how severe is your discomfort right now? (1 = mild, 10 = unbearable)",
            "hi": "1 से 10 के पैमाने पर, अभी आपकी तकलीफ कितनी तेज है? (1 = हल्का, 10 = असहनीय)",
            "mr": "1 ते 10 च्या स्केलवर, तुमचा त्रास किती तीव्र आहे? (1 = सौम्य, 10 = असह्य)"
        },
        "options": [
            {"label": "Mild — 1 to 3 / हल्का", "value": "mild_1_3"},
            {"label": "Moderate — 4 to 6 / मध्यम", "value": "moderate_4_6"},
            {"label": "Severe — 7 to 9 / अत्यधिक तेज", "value": "severe_7_9"},
            {"label": "Unbearable — 10 / असहनीय", "value": "unbearable_10"}
        ]
    },
    {
        "id": "q4_character_radiation",
        "step": 4,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "How would you describe the quality of pain/discomfort? Does it spread anywhere else?",
            "hi": "दर्द या तकलीफ की प्रकृति कैसी है? क्या यह किसी और जगह फैलती है?",
            "mr": "वेदना किंवा त्रासाचे स्वरूप कसे आहे? ते इतर कुठे पसरते का?"
        },
        "options": [
            {"label": "Sharp / stabbing / तेज़ / चुभने वाला", "value": "sharp"},
            {"label": "Dull / aching / हल्का दर्द", "value": "dull_aching"},
            {"label": "Burning / जलन", "value": "burning"},
            {"label": "Pressing / squeezing / दबाने वाला", "value": "pressing"},
            {"label": "Throbbing / pulsating / धड़कता हुआ", "value": "throbbing"},
            {"label": "Radiates to arm / jaw / left side / हाथ, जबड़े, बाईं ओर फैलता है", "value": "radiates_arm_jaw"}
        ]
    },
    {
        "id": "q5_associated_symptoms",
        "step": 5,
        "input_type": "multi_select",
        "question_text": {
            "en": "Are you experiencing any of these associated symptoms alongside your main complaint?",
            "hi": "क्या आपको मुख्य तकलीफ के साथ इनमें से कोई अतिरिक्त लक्षण भी हैं?",
            "mr": "तुमच्या मुख्य त्रासाबरोबर खालीलपैकी कोणतीही लक्षणे जाणवत आहेत का?"
        },
        "options": [
            {"label": "Shortness of breath / सांस लेने में तकलीफ", "value": "shortness_of_breath"},
            {"label": "Nausea / Vomiting / जी मिचलाना या उल्टी", "value": "nausea_vomiting"},
            {"label": "Cold sweats / diaphoresis / ठंडा पसीना", "value": "cold_sweats"},
            {"label": "High fever (> 101°F) / तेज बुखार", "value": "high_fever"},
            {"label": "Dizziness / fainting / चक्कर आना", "value": "dizziness_syncope"},
            {"label": "Swelling of limbs / पैरों में सूजन", "value": "limb_swelling"},
            {"label": "Palpitations / दिल की धड़कन तेज होना", "value": "palpitations"},
            {"label": "None / कोई नहीं", "value": "none"}
        ]
    },
    {
        "id": "q6_aggravating_relieving",
        "step": 6,
        "input_type": "multi_select",
        "question_text": {
            "en": "What makes your symptoms worse or better?",
            "hi": "किस से आपकी तकलीफ और बढ़ती है या कम होती है?",
            "mr": "कशामुळे तुमचा त्रास वाढतो किंवा कमी होतो?"
        },
        "options": [
            {"label": "Worse with exertion / exercise / परिश्रम से बढ़ता है", "value": "worse_exertion"},
            {"label": "Worse on lying flat / लेटने पर बढ़ता है", "value": "worse_supine"},
            {"label": "Relieved with rest / आराम से कम होता है", "value": "relieved_rest"},
            {"label": "Worse after eating / खाने के बाद बढ़ता है", "value": "worse_eating"},
            {"label": "Better with medication already taken / दवा से राहत मिली", "value": "relieved_medication"},
            {"label": "No clear pattern / कोई स्पष्ट कारण नहीं", "value": "no_pattern"}
        ]
    },
    {
        "id": "q7_past_medical_history",
        "step": 7,
        "input_type": "multi_select",
        "question_text": {
            "en": "Do you have any pre-existing diagnosed medical conditions?",
            "hi": "क्या आपको पहले से कोई पुरानी बीमारी है जिसका निदान हुआ हो?",
            "mr": "तुम्हाला आधीपासून कोणतेही निदान झालेले आजार आहेत का?"
        },
        "options": [
            {"label": "Diabetes (Sugar) / मधुमेह", "value": "diabetes"},
            {"label": "Hypertension (High BP) / उच्च रक्तचाप", "value": "hypertension"},
            {"label": "Heart Disease / हृदय रोग", "value": "heart_disease"},
            {"label": "Asthma / COPD / Thyroid / अस्थमा / थायरॉइड", "value": "asthma_thyroid"},
            {"label": "Kidney Disease / गुर्दे की बीमारी", "value": "kidney_disease"},
            {"label": "Cancer (any type) / कैंसर", "value": "cancer"},
            {"label": "Previous surgery / पहले कोई ऑपरेशन", "value": "prior_surgery"},
            {"label": "None / कोई पुरानी बीमारी नहीं", "value": "none"}
        ]
    },
    {
        "id": "q8_medications_allergies",
        "step": 8,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "Please list any regular medications you are currently taking and any known drug allergies.",
            "hi": "कृपया वे दवाएं बताएं जो आप नियमित रूप से लेते हैं और किसी दवा से एलर्जी हो तो वह भी बताएं।",
            "mr": "तुम्ही नियमितपणे घेत असलेल्या औषधांची आणि कोणत्याही औषधांच्या अॅलर्जीची माहिती द्या."
        },
        "options": [
            {"label": "Taking BP / Diabetes / Heart medications / BP या मधुमेह की दवाएं", "value": "chronic_meds"},
            {"label": "Allergic to Penicillin / Sulfa drugs / पेनिसिलिन से एलर्जी", "value": "penicillin_sulfa_allergy"},
            {"label": "Allergic to NSAIDs (e.g., Aspirin, Ibuprofen)", "value": "nsaid_allergy"},
            {"label": "Taking blood thinners / खून पतला करने वाली दवा", "value": "anticoagulants"},
            {"label": "No regular medicines / No known allergies (NKDA)", "value": "nkda_no_meds"}
        ]
    },
    {
        "id": "q9_family_personal_history",
        "step": 9,
        "input_type": "multi_select",
        "question_text": {
            "en": "Does anyone in your immediate family (parents, siblings) have any of these conditions?",
            "hi": "क्या आपके परिवार में (माता-पिता, भाई-बहन) किसी को ये बीमारियाँ हैं?",
            "mr": "तुमच्या कुटुंबातील (आई-वडील, भाऊ-बहीण) कुणाला हे आजार आहेत का?"
        },
        "options": [
            {"label": "Diabetes in family / परिवार में मधुमेह", "value": "fh_diabetes"},
            {"label": "Heart attack or stroke / हृदय रोग या लकवा", "value": "fh_cardiac_stroke"},
            {"label": "Hypertension / उच्च रक्तचाप", "value": "fh_hypertension"},
            {"label": "Cancer / कैंसर", "value": "fh_cancer"},
            {"label": "No known family history / कोई पारिवारिक इतिहास नहीं", "value": "fh_none"}
        ]
    },
    {
        "id": "q10_personal_social_history",
        "step": 10,
        "input_type": "multi_select",
        "question_text": {
            "en": "Tell us about your lifestyle habits (select all that apply).",
            "hi": "अपनी जीवनशैली की आदतों के बारे में बताएं।",
            "mr": "तुमच्या जीवनशैलीतील सवयींबद्दल सांगा."
        },
        "options": [
            {"label": "Smoker / धूम्रपान करते हैं", "value": "smoker"},
            {"label": "Alcohol use / शराब पीते हैं", "value": "alcohol"},
            {"label": "Tobacco / Gutkha / तम्बाकू / गुटखा", "value": "tobacco_gutkha"},
            {"label": "Sedentary lifestyle / बैठे रहने का काम", "value": "sedentary"},
            {"label": "Physically active (exercise regularly) / नियमित व्यायाम", "value": "active"},
            {"label": "Vegetarian diet / शाकाहारी", "value": "vegetarian"},
            {"label": "None of the above / उपरोक्त में से कोई नहीं", "value": "none"}
        ]
    }
]


# ─── AYUSH — Full Dashavidha Pariksha (10 Examination Parameters) ──────────────
AYUSH_STEPS = [
    {
        "id": "ayush_q1_chief_complaint",
        "step": 1,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "AYUSH Intake: What is your main health concern today? Please describe in your own words.",
            "hi": "आयुष परीक्षण: आज आपकी मुख्य स्वास्थ्य समस्या क्या है? कृपया अपने शब्दों में बताएं।",
            "mr": "आयुष तपासणी: आज तुमची मुख्य आरोग्याची तक्रार काय आहे?"
        },
        "options": [
            {"label": "Digestive / Gut issues / पाचन समस्या", "value": "digestive"},
            {"label": "Joint / Muscle pain / सांधे या मांसपेशियों का दर्द", "value": "joint_muscle"},
            {"label": "Skin disorders / त्वचा रोग", "value": "skin"},
            {"label": "Stress / Sleep / Mental health / तनाव या नींद की समस्या", "value": "stress_sleep"},
            {"label": "Respiratory / श्वसन समस्या", "value": "respiratory"},
            {"label": "General weakness / Fatigue / सामान्य कमज़ोरी", "value": "general_weakness"}
        ]
    },
    {
        "id": "ayush_q2_prakriti",
        "step": 2,
        "input_type": "options",
        "question_text": {
            "en": "Dashavidha Pariksha (1/10) — Prakriti: What best describes your dominant body constitution?",
            "hi": "दशविध परीक्षा (1/10) — प्रकृति: आपकी शारीरिक प्रकृति (वात, पित्त, कफ) का चयन करें।",
            "mr": "दशविध परीक्षा (1/10) — प्रकृती: तुमची शारीरिक प्रकृती (वात, पित्त, कफ) निवडा."
        },
        "options": [
            {"label": "Vata Pradhana — Thin, Dry, Cold, Anxious / वात प्रधान", "value": "vata"},
            {"label": "Pitta Pradhana — Warm, Sharp, Acidic, Ambitious / पित्त प्रधान", "value": "pitta"},
            {"label": "Kapha Pradhana — Heavy, Moist, Calm, Stable / कफ प्रधान", "value": "kapha"},
            {"label": "Vata-Pitta (Mixed) / वात-पित्त", "value": "vata_pitta"},
            {"label": "Pitta-Kapha (Mixed) / पित्त-कफ", "value": "pitta_kapha"},
            {"label": "Tridosha Sama (Balanced) / त्रिदोष सम", "value": "tridosha_sama"}
        ]
    },
    {
        "id": "ayush_q3_vikriti",
        "step": 3,
        "input_type": "options",
        "question_text": {
            "en": "Dashavidha Pariksha (2/10) — Vikriti: What imbalance (Dosha disturbance) are you currently experiencing?",
            "hi": "दशविध परीक्षा (2/10) — विकृति: अभी आपका कौन सा दोष असंतुलित है?",
            "mr": "दशविध परीक्षा (2/10) — विकृती: सध्या कोणता दोष असंतुलित आहे?"
        },
        "options": [
            {"label": "Vata Vikriti — Dryness, Gas, Anxiety / वात विकृति", "value": "vata_vikriti"},
            {"label": "Pitta Vikriti — Inflammation, Acidity, Anger / पित्त विकृति", "value": "pitta_vikriti"},
            {"label": "Kapha Vikriti — Heaviness, Congestion, Lethargy / कफ विकृति", "value": "kapha_vikriti"},
            {"label": "Sannipata (All three disturbed) / सन्निपात", "value": "sannipata"},
            {"label": "Uncertain / Unknown / अनिश्चित", "value": "unknown_vikriti"}
        ]
    },
    {
        "id": "ayush_q4_sara",
        "step": 4,
        "input_type": "options",
        "question_text": {
            "en": "Dashavidha Pariksha (3/10) — Sara (Tissue Quality): Which best describes your tissue/bodily excellence?",
            "hi": "दशविध परीक्षा (3/10) — सार: आपके शरीर की धातु सार की स्थिति कैसी है?",
            "mr": "दशविध परीक्षा (3/10) — सार: तुमच्या शरीरातील धातू सार कसे आहे?"
        },
        "options": [
            {"label": "Rasa Sara — Good complexion, moisturized skin / रस सार", "value": "rasa_sara"},
            {"label": "Rakta Sara — Healthy blood, good color / रक्त सार", "value": "rakta_sara"},
            {"label": "Mamsa Sara — Good muscle mass / मांस सार", "value": "mamsa_sara"},
            {"label": "Majja Sara — Clear mind, good memory / मज्जा सार", "value": "majja_sara"},
            {"label": "Shukra Sara — Strong immunity, good health / शुक्र सार", "value": "shukra_sara"},
            {"label": "Avasara (Poor tissue quality) / अवसार", "value": "avasara"}
        ]
    },
    {
        "id": "ayush_q5_samhanana",
        "step": 5,
        "input_type": "options",
        "question_text": {
            "en": "Dashavidha Pariksha (4/10) — Samhanana (Body Build): How would you describe your physical frame?",
            "hi": "दशविध परीक्षा (4/10) — संहनन: आपकी शारीरिक बनावट कैसी है?",
            "mr": "दशविध परीक्षा (4/10) — संहनन: तुमची शारीरिक ठेवण कशी आहे?"
        },
        "options": [
            {"label": "Pravara Samhanana — Well-built, compact, strong / प्रवर संहनन", "value": "pravara"},
            {"label": "Madhyama Samhanana — Medium build / मध्यम संहनन", "value": "madhyama"},
            {"label": "Avara Samhanana — Lean / thin / under-built / अवर संहनन", "value": "avara"}
        ]
    },
    {
        "id": "ayush_q6_agni_koshtha",
        "step": 6,
        "input_type": "options",
        "question_text": {
            "en": "Dashavidha Pariksha (5/10) — Agni & Koshtha: Describe your digestive fire and bowel nature.",
            "hi": "दशविध परीक्षा (5/10) — अग्नि एवं कोष्ठ: पाचन क्षमता और मल त्याग की स्थिति।",
            "mr": "दशविध परीक्षा (5/10) — अग्नी आणि कोष्ठ: पचन क्षमता आणि मलाचा स्वभाव."
        },
        "options": [
            {"label": "Sama Agni / Madhyama Koshtha — Balanced digestion & bowel / समाग्नि", "value": "sama_madhyama"},
            {"label": "Tikshna Agni / Mridu Koshtha — High appetite, loose stools / तीक्ष्णाग्नि", "value": "tikshna_mridu"},
            {"label": "Manda Agni / Krura Koshtha — Slow digestion, constipation / मंदाग्नि", "value": "manda_krura"},
            {"label": "Vishma Agni / Vishama Koshtha — Irregular digestion & bowel / विषमाग्नि", "value": "vishma_vishama"}
        ]
    },
    {
        "id": "ayush_q7_satmya",
        "step": 7,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "Dashavidha Pariksha (6/10) — Satmya (Suitability): What foods, climates, or substances does your body tolerate well or poorly?",
            "hi": "दशविध परीक्षा (6/10) — सात्म्य: आपका शरीर किन आहार, मौसम या चीजों के प्रति अनुकूल या प्रतिकूल है?",
            "mr": "दशविध परीक्षा (6/10) — सात्म्य: तुमचे शरीर कोणत्या आहार, वातावरण किंवा गोष्टींना चांगले किंवा वाईट प्रतिसाद देते?"
        },
        "options": [
            {"label": "Tolerates all foods (Sarva Satmya) / सर्व सात्म्य", "value": "sarva_satmya"},
            {"label": "Only tolerates light diet (Ekahara Satmya) / एकाहार सात्म्य", "value": "ekahara_satmya"},
            {"label": "Cold intolerant / शीत असहनीय", "value": "cold_intolerant"},
            {"label": "Heat intolerant / गर्मी असहनीय", "value": "heat_intolerant"}
        ]
    },
    {
        "id": "ayush_q8_sattva",
        "step": 8,
        "input_type": "options",
        "question_text": {
            "en": "Dashavidha Pariksha (7/10) — Sattva (Mental Strength): How would you describe your mental resilience?",
            "hi": "दशविध परीक्षा (7/10) — सत्त्व: आपकी मानसिक शक्ति / दृढ़ता कैसी है?",
            "mr": "दशविध परीक्षा (7/10) — सत्त्व: तुमची मानसिक शक्ती / दृढता कशी आहे?"
        },
        "options": [
            {"label": "Pravara Sattva — Strong, fearless, clear mind / प्रवर सत्त्व", "value": "pravara_sattva"},
            {"label": "Madhyama Sattva — Moderate resilience / मध्यम सत्त्व", "value": "madhyama_sattva"},
            {"label": "Avara Sattva — Fearful, anxious, low tolerance / अवर सत्त्व", "value": "avara_sattva"}
        ]
    },
    {
        "id": "ayush_q9_ahara_shakti",
        "step": 9,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "Dashavidha Pariksha (8 & 9/10) — Ahara Shakti & Vyayama Shakti: Describe your appetite, food quantity, and exercise capacity.",
            "hi": "दशविध परीक्षा (8 और 9/10) — आहार शक्ति एवं व्यायाम शक्ति: अपनी भूख, भोजन मात्रा और व्यायाम क्षमता बताएं।",
            "mr": "दशविध परीक्षा (8 आणि 9/10) — आहार शक्ती आणि व्यायाम शक्ती: भूक, खाण्याचे प्रमाण आणि व्यायामाची क्षमता सांगा."
        },
        "options": [
            {"label": "Good appetite, high food intake, high exercise tolerance", "value": "high_ahara_vyayama"},
            {"label": "Moderate appetite, moderate exercise / मध्यम क्षमता", "value": "moderate_ahara_vyayama"},
            {"label": "Poor appetite, small portions, low exercise tolerance", "value": "low_ahara_vyayama"},
            {"label": "Variable appetite (irregular) / अनियमित भूख", "value": "irregular_ahara"}
        ]
    },
    {
        "id": "ayush_q10_vaya_ahara_vihara",
        "step": 10,
        "input_type": "voice_or_text",
        "question_text": {
            "en": "Dashavidha Pariksha (10/10) — Vaya & Ahara-Vihara: Your age group and daily diet/lifestyle routine.",
            "hi": "दशविध परीक्षा (10/10) — वय एवं आहार-विहार: आयु वर्ग और दैनिक आहार एवं जीवनशैली।",
            "mr": "दशविध परीक्षा (10/10) — वय आणि आहार-विहार: वयोगट आणि दैनंदिन आहार व जीवनशैली."
        },
        "options": [
            {"label": "Bala (Child/Youth < 16) / बाल अवस्था", "value": "bala"},
            {"label": "Madhyama (Adult 16–60) + Balanced Sattvic diet / मध्य अवस्था", "value": "madhyama_sattvic"},
            {"label": "Madhyama + Heavy/Oily diet + Late sleep / Irregular lifestyle", "value": "madhyama_guru_irregular"},
            {"label": "Vriddha (Senior > 60) + Light simple diet / वृद्ध अवस्था", "value": "vriddha_laghu"}
        ]
    }
]


class QuestionEngine:
    """
    Adaptive clinical history interview engine.
    Dynamically branches based on chief complaint (e.g., chest_pain → SOCRATES follow-up).
    Supports Allopathy (SOCRATES) and AYUSH (Dashavidha Pariksha) modes.
    Performs red-flag screening on every answer submission.
    """

    def get_next_question(
        self,
        current_step: int,
        answers: Dict[str, Any],
        department_mode: str = "Allopathy"
    ) -> Dict[str, Any]:
        """Return the next structured question for the patient kiosk."""

        steps = AYUSH_STEPS if department_mode.strip().upper() == "AYUSH" else ALLOPATHY_STEPS
        total_steps = len(steps)

        # ── Real-time red flag evaluation on all collected answers so far ──
        text_corpus = " ".join([str(v) for v in answers.values()])
        red_flags = red_flag_detector.check_red_flags(text_corpus)
        red_flag_alert = red_flags[0] if red_flags else None

        # ── Interview complete ──────────────────────────────────────────────
        if current_step > total_steps:
            return {
                "question_id": "completed",
                "step": total_steps,
                "total_steps": total_steps,
                "question_text": {
                    "en": "Thank you! Your health history is now complete. Please wait for the doctor's consultation.",
                    "hi": "धन्यवाद! आपका स्वास्थ्य विवरण दर्ज हो चुका है। कृपया डॉक्टर के पास जाएं।",
                    "mr": "धन्यवाद! तुमची आरोग्य नोंदणी पूर्ण झाली आहे. कृपया डॉक्टरकडे जा."
                },
                "input_type": "none",
                "options": [],
                "is_complete": True,
                "red_flag_alert": red_flag_alert
            }

        target_index = max(0, min(current_step - 1, total_steps - 1))
        question_data = steps[target_index]

        return {
            "question_id": question_data["id"],
            "step": question_data["step"],
            "total_steps": total_steps,
            "question_text": question_data["question_text"],
            "audio_prompt_url": f"/api/interview/audio-prompt/{question_data['id']}",
            "input_type": question_data["input_type"],
            "options": question_data.get("options", []),
            "is_complete": False,
            "red_flag_alert": red_flag_alert
        }

    def get_all_steps(self, department_mode: str = "Allopathy") -> List[Dict[str, Any]]:
        """Returns all question steps (useful for kiosk pre-loading)."""
        return AYUSH_STEPS if department_mode.strip().upper() == "AYUSH" else ALLOPATHY_STEPS


question_engine = QuestionEngine()
