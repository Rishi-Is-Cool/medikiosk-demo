"""
MediKiosk — adaptive kiosk interview engine.

Replaces the fixed ten-question sequence for the kiosk integration path
(`/intake/*`). The legacy `/api/interview/*` routes keep using question_engine.

How it keeps the interview short
--------------------------------
- Every complaint the patient ticks contributes only its one or two most
  discriminating questions ("core"). Deeper questions ("focused") are asked
  only when a single complaint was chosen, and follow-ups ("conditional") only
  when an earlier answer makes them relevant.
- Symptoms that several complaints care about are asked ONCE, in a single
  combined "associated symptoms" question whose options are built from the
  complaints chosen, minus anything already known.
- The plan is recomputed after every answer, so the question count shrinks
  or grows with what the patient says — the estimated total is honest.

Safety
------
Red flags are structured rules over *findings* accumulated across the whole
encounter (e.g. chest pain AND pain spreading to the arm), not substring
matches on option codes. Chest pain alone, or "severe" pain alone, never fires
a rule. Free-text / spoken answers are scanned for a small set of specific
phrases (with a simple negation guard) that map onto the same findings.

This module is deterministic on purpose: the same answers always produce the
same questions and the same alerts, and it never generates clinical questions
with an LLM. Question wording is a demo script and must be reviewed by the
clinical members of the team before real patient use.

AYUSH question ids and answer codes are kept identical to question_engine's
AYUSH_STEPS because services/ayush_snapshot.py maps them onto the doctor
console's Dashavidha panel.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

L = Dict[str, str]  # {"en": ..., "hi": ..., "mr": ...}


def loc(value: Optional[L], language: str) -> str:
    if not value:
        return ""
    return value.get(language) or value.get("en") or ""


# ─── Data model ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Option:
    value: str
    label: L
    findings: Tuple[str, ...] = ()
    exclusive: bool = False


@dataclass(frozen=True)
class Question:
    id: str
    module: str  # complaint id | "shared" | "ayush" | "history"
    section: str  # "problem" | "ayush" | "history"
    text: L
    doctor_label: str
    input_type: str  # single_select | multi_select | scale | voice_or_text
    options: Tuple[Option, ...] = ()
    default: Tuple[str, ...] = ()
    default_text: Optional[str] = None
    helper: Optional[L] = None
    scale_tone: Optional[str] = None
    depth: str = "core"  # core | focused | conditional
    when: Optional[Callable[["Context"], bool]] = None
    text_fn: Optional[Callable[["Context"], L]] = None
    options_fn: Optional[Callable[["Context"], Tuple[Option, ...]]] = None

    def resolved_text(self, ctx: "Context") -> L:
        return self.text_fn(ctx) if self.text_fn else self.text

    def resolved_options(self, ctx: "Context") -> Tuple[Option, ...]:
        return self.options_fn(ctx) if self.options_fn else self.options


@dataclass
class Context:
    complaints: List[str]
    framework: str  # "general_medicine" | "ayush"
    answers: Dict[str, Dict[str, Any]]  # qid -> {"values": [...], "text": str | None}
    complaint_text: Optional[str] = None
    findings: Set[str] = field(default_factory=set)

    @property
    def single_complaint(self) -> bool:
        return len(self.complaints) == 1


# ─── Complaint taxonomy ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Complaint:
    id: str
    label: L
    icon: str
    findings: Tuple[str, ...]
    keywords: Tuple[str, ...]


COMPLAINTS: Tuple[Complaint, ...] = (
    Complaint("chest_pain", {"en": "Chest pain", "hi": "सीने में दर्द", "mr": "छातीत दुखणे"}, "heart",
              ("chest_pain",), ("chest", "heart pain", "सीने", "सीना", "छाती", "छातीत", "seene", "chhati")),
    Complaint("fever", {"en": "Fever", "hi": "बुखार", "mr": "ताप"}, "thermometer",
              ("fever",), ("fever", "temperature", "बुखार", "ताप", "bukhar", "taap")),
    Complaint("cough_cold", {"en": "Cough, cold or sore throat", "hi": "खांसी, जुकाम या गले में खराश",
                             "mr": "खोकला, सर्दी किंवा घसा दुखणे"}, "lungs",
              ("cough",), ("cough", "cold", "throat", "खांसी", "खाँसी", "जुकाम", "गला", "गले", "खोकला", "सर्दी", "घसा", "khansi")),
    Complaint("breathlessness", {"en": "Difficulty breathing", "hi": "सांस लेने में तकलीफ", "mr": "श्वास घेण्यास त्रास"},
              "wind", ("breathless",), ("breath", "breathing", "breathless", "सांस", "साँस", "श्वास", "दम", "saans")),
    Complaint("headache", {"en": "Headache", "hi": "सिरदर्द", "mr": "डोकेदुखी"}, "head",
              ("headache",), ("headache", "head", "सिर", "सिरदर्द", "डोके", "डोकं", "sir dard")),
    Complaint("abdominal_pain", {"en": "Stomach pain", "hi": "पेट दर्द", "mr": "पोटदुखी"}, "stomach",
              ("abdominal_pain",), ("stomach", "abdomen", "abdominal", "belly", "पेट", "पोट", "pet dard")),
    Complaint("vomiting_diarrhoea", {"en": "Vomiting or loose motions", "hi": "उल्टी या दस्त", "mr": "उलट्या किंवा जुलाब"},
              "droplet", ("gi_upset",), ("vomit", "loose motion", "diarrh", "उल्टी", "उलटी", "उलट्या", "दस्त", "जुलाब", "ulti")),
    Complaint("joint_back_pain", {"en": "Joint, back or body pain", "hi": "जोड़ों, कमर या बदन में दर्द",
                                  "mr": "सांधे, पाठ किंवा अंगदुखी"}, "bone",
              ("joint_back_pain",), ("joint", "knee", "back pain", "body pain", "जोड़", "घुटन", "कमर", "बदन", "सांधे", "गुडघ", "कंबर", "अंगदुखी")),
    Complaint("dizziness_weakness", {"en": "Dizziness or weakness", "hi": "चक्कर या कमज़ोरी", "mr": "चक्कर किंवा अशक्तपणा"},
              "dizzy", ("dizziness",), ("dizz", "weak", "tired", "चक्कर", "कमज़ोर", "कमजोर", "अशक्त", "थकवा", "थकान")),
    Complaint("skin_problem", {"en": "Skin rash or itching", "hi": "त्वचा पर दाने या खुजली", "mr": "त्वचेवर पुरळ किंवा खाज"},
              "skin", ("skin",), ("rash", "itch", "skin", "दाने", "खुजली", "त्वचा", "पुरळ", "खाज")),
    Complaint("other", {"en": "Something else", "hi": "कुछ और", "mr": "आणखी काही"}, "dots", (), ()),
)

COMPLAINTS_BY_ID: Dict[str, Complaint] = {c.id: c for c in COMPLAINTS}

# Ids older clients (and the existing integration test) still send.
_LEGACY_COMPLAINT_IDS = {
    "fever_cough": ["fever", "cough_cold"],
    "chest pain": ["chest_pain"],
    "stomach": ["abdominal_pain"],
    "breathing": ["breathlessness"],
    "joint_pain": ["joint_back_pain"],
    "weakness": ["dizziness_weakness"],
}


def _latin_word_match(keyword: str, text: str) -> bool:
    if re.search(r"[a-z]", keyword):
        return re.search(r"(?<![a-z])" + re.escape(keyword), text) is not None
    return keyword in text


def _option_word_match(word: str, text: str) -> bool:
    """Whole-word for Latin script (plural 's' allowed) so "ever" never matches
    "severe"; substring for Devanagari, where inflections attach to the stem."""
    if re.search(r"[a-z]", word):
        return re.search(r"(?<![a-z])" + re.escape(word) + r"s?(?![a-z])", text) is not None
    return word in text


def normalize_complaints(ids: Sequence[str]) -> List[str]:
    """Map incoming complaint ids (current or legacy) onto the taxonomy, keeping order."""
    out: List[str] = []
    for raw in ids:
        key = (raw or "").strip().lower()
        if not key:
            continue
        mapped = _LEGACY_COMPLAINT_IDS.get(key) or ([key] if key in COMPLAINTS_BY_ID else [key.replace(" ", "_")])
        for cid in mapped:
            cid = cid if cid in COMPLAINTS_BY_ID else "other"
            if cid not in out:
                out.append(cid)
    return out or ["other"]


def complaint_list(language: str) -> List[Dict[str, str]]:
    return [{"id": c.id, "label": loc(c.label, language), "icon": c.icon} for c in COMPLAINTS]


def complaint_label(cid: str, language: str = "en") -> str:
    complaint = COMPLAINTS_BY_ID.get(cid)
    return loc(complaint.label, language) if complaint else cid.replace("_", " ").capitalize()


def match_complaints(transcript: str) -> List[str]:
    text = (transcript or "").lower()
    found = [c.id for c in COMPLAINTS if c.keywords and any(_latin_word_match(k.lower(), text) for k in c.keywords)]
    return found


# ─── Shared questions ─────────────────────────────────────────────────────────

_DURATION_OPTIONS = (
    Option("today", {"en": "Since today (less than a day)", "hi": "आज से (एक दिन से कम)", "mr": "आजपासून (एका दिवसापेक्षा कमी)"}, ("onset_today",)),
    Option("d1_3", {"en": "1 to 3 days", "hi": "1 से 3 दिन", "mr": "1 ते 3 दिवस"}),
    Option("d4_7", {"en": "4 to 7 days", "hi": "4 से 7 दिन", "mr": "4 ते 7 दिवस"}),
    Option("w1_4", {"en": "1 to 4 weeks", "hi": "1 से 4 हफ़्ते", "mr": "1 ते 4 आठवडे"}, ("duration_weeks",)),
    Option("gt_month", {"en": "More than a month", "hi": "एक महीने से ज़्यादा", "mr": "एका महिन्यापेक्षा जास्त"}, ("chronic",)),
)


def _duration_text(ctx: Context) -> L:
    if ctx.single_complaint and ctx.complaints[0] != "other":
        return {"en": "How long have you had this problem?", "hi": "यह तकलीफ़ कब से है?",
                "mr": "हा त्रास किती दिवसांपासून आहे?"}
    return {"en": "How long have you been unwell?", "hi": "आप कब से बीमार महसूस कर रहे हैं?",
            "mr": "तुम्हाला कधीपासून बरे वाटत नाही?"}


SHARED_DURATION = Question(
    "duration", "shared", "problem", {}, "Duration", "single_select", _DURATION_OPTIONS,
    default=("d1_3",), text_fn=_duration_text,
)

SHARED_SEVERITY = Question(
    "severity", "shared", "problem",
    {"en": "How bad is it right now?", "hi": "अभी तकलीफ़ कितनी ज़्यादा है?", "mr": "आत्ता त्रास किती जास्त आहे?"},
    "Severity", "scale",
    (
        Option("mild", {"en": "Mild", "hi": "हल्की", "mr": "सौम्य"}),
        Option("moderate", {"en": "Moderate", "hi": "मध्यम", "mr": "मध्यम"}),
        Option("severe", {"en": "Severe", "hi": "तेज़", "mr": "तीव्र"}, ("severity_severe",)),
        Option("worst", {"en": "Worst ever", "hi": "सबसे ज़्यादा", "mr": "असह्य"}, ("severity_severe", "severity_worst")),
    ),
    default=("moderate",), scale_tone="severity",
)


# ─── Complaint modules ────────────────────────────────────────────────────────

def _q(qid, module, text, label, input_type, options, default, depth="core", when=None, helper=None):
    return Question(qid, module, "problem", text, label, input_type, tuple(options), default=tuple(default),
                    depth=depth, when=when, helper=helper)


MODULES: Dict[str, List[Question]] = {
    "chest_pain": [
        _q("cp_character", "chest_pain",
           {"en": "What does the chest pain feel like?", "hi": "सीने का दर्द कैसा महसूस होता है?", "mr": "छातीतील वेदना कशी जाणवते?"},
           "Chest pain — character", "single_select", [
               Option("pressing", {"en": "Heavy, tight or pressing", "hi": "भारी, जकड़न या दबाव जैसा", "mr": "जड, आवळल्यासारखी किंवा दाबल्यासारखी"}, ("cp_pressing",)),
               Option("sharp", {"en": "Sharp or stabbing", "hi": "तेज़ या चुभने वाला", "mr": "तीक्ष्ण किंवा टोचणारी"}, ("cp_sharp",)),
               Option("burning", {"en": "Burning", "hi": "जलन", "mr": "जळजळ"}, ("cp_burning",)),
               Option("dull", {"en": "Dull ache", "hi": "हल्का लगातार दर्द", "mr": "मंद सतत दुखणे"}),
           ], ("dull",)),
        _q("cp_radiation", "chest_pain",
           {"en": "Does the pain spread anywhere?", "hi": "क्या दर्द कहीं और फैलता है?", "mr": "वेदना इतर कुठे पसरते का?"},
           "Chest pain — radiation", "single_select", [
               Option("left_arm", {"en": "To the left arm or shoulder", "hi": "बाएँ हाथ या कंधे तक", "mr": "डाव्या हातापर्यंत किंवा खांद्यापर्यंत"}, ("cp_radiates",)),
               Option("jaw_neck", {"en": "To the jaw or neck", "hi": "जबड़े या गर्दन तक", "mr": "जबड्यापर्यंत किंवा मानेपर्यंत"}, ("cp_radiates",)),
               Option("back", {"en": "To the back", "hi": "पीठ तक", "mr": "पाठीपर्यंत"}, ("cp_back",)),
               Option("none", {"en": "It stays in one place", "hi": "एक ही जगह रहता है", "mr": "एकाच जागी राहते"}),
           ], ("none",)),
        _q("cp_trigger", "chest_pain",
           {"en": "When does the chest pain come?", "hi": "सीने में दर्द कब होता है?", "mr": "छातीत दुखणे कधी होते?"},
           "Chest pain — trigger", "single_select", [
               Option("exertion", {"en": "When I walk or climb stairs", "hi": "चलने या सीढ़ियाँ चढ़ने पर", "mr": "चालताना किंवा जिना चढताना"}, ("cp_exertional",)),
               Option("breathing", {"en": "When I breathe deeply or cough", "hi": "गहरी साँस लेने या खाँसने पर", "mr": "दीर्घ श्वास घेताना किंवा खोकताना"}, ("cp_pleuritic",)),
               Option("food", {"en": "After eating", "hi": "खाना खाने के बाद", "mr": "जेवणानंतर"}, ("cp_food",)),
               Option("rest", {"en": "Even at rest", "hi": "आराम करते समय भी", "mr": "विश्रांतीतही"}, ("cp_rest",)),
               Option("no_pattern", {"en": "No particular pattern", "hi": "कोई खास पैटर्न नहीं", "mr": "ठराविक असे काही नाही"}),
           ], ("no_pattern",), depth="focused"),
    ],
    "fever": [
        _q("fever_pattern", "fever",
           {"en": "How is the fever?", "hi": "बुखार कैसा है?", "mr": "ताप कसा आहे?"},
           "Fever — pattern", "single_select", [
               Option("continuous", {"en": "Stays all the time", "hi": "लगातार बना रहता है", "mr": "सतत असतो"}, ("fever_continuous",)),
               Option("chills", {"en": "Comes with shivering", "hi": "कँपकँपी के साथ आता है", "mr": "थंडी वाजून येतो"}, ("chills",)),
               Option("evening", {"en": "Mostly in the evening or night", "hi": "ज़्यादातर शाम या रात को", "mr": "बहुतेक संध्याकाळी किंवा रात्री"}, ("fever_evening",)),
               Option("on_off", {"en": "Comes and goes", "hi": "आता-जाता रहता है", "mr": "येतो-जातो"}),
           ], ("on_off",)),
        _q("fever_measured", "fever",
           {"en": "Did you check your temperature?", "hi": "क्या आपने तापमान नापा?", "mr": "तुम्ही तापमान मोजले का?"},
           "Fever — measured", "single_select", [
               Option("high", {"en": "Yes — above 102°F (38.9°C)", "hi": "हाँ — 102°F से ज़्यादा", "mr": "होय — 102°F पेक्षा जास्त"}, ("fever_high",)),
               Option("mild", {"en": "Yes — 99 to 102°F", "hi": "हाँ — 99 से 102°F", "mr": "होय — 99 ते 102°F"}),
               Option("no", {"en": "Not checked", "hi": "नहीं नापा", "mr": "मोजले नाही"}),
           ], ("no",), depth="focused"),
    ],
    "cough_cold": [
        _q("cough_type", "cough_cold",
           {"en": "What kind of cough do you have?", "hi": "आपकी खांसी कैसी है?", "mr": "तुमचा खोकला कसा आहे?"},
           "Cough — type", "single_select", [
               Option("dry", {"en": "Dry cough", "hi": "सूखी खांसी", "mr": "कोरडा खोकला"}),
               Option("phlegm", {"en": "Cough with phlegm", "hi": "बलगम वाली खांसी", "mr": "कफ असलेला खोकला"}, ("productive_cough",)),
               Option("blood", {"en": "Blood in the cough", "hi": "खांसी में खून", "mr": "खोकल्यात रक्त"}, ("haemoptysis",)),
               Option("no_cough", {"en": "No cough — only cold or sore throat", "hi": "खांसी नहीं — सिर्फ़ जुकाम या गले में खराश", "mr": "खोकला नाही — फक्त सर्दी किंवा घसा दुखणे"}),
           ], ("dry",)),
    ],
    "breathlessness": [
        _q("sob_when", "breathlessness",
           {"en": "When do you feel breathless?", "hi": "सांस फूलना कब होता है?", "mr": "धाप कधी लागते?"},
           "Breathlessness — when", "single_select", [
               Option("rest", {"en": "Even while sitting or resting", "hi": "बैठे-बैठे या आराम में भी", "mr": "बसलेले असतानाही किंवा विश्रांतीतही"}, ("sob_rest",)),
               Option("walking", {"en": "Only when walking or climbing stairs", "hi": "सिर्फ़ चलने या सीढ़ियाँ चढ़ने पर", "mr": "फक्त चालताना किंवा जिना चढताना"}, ("sob_exertion",)),
               Option("lying", {"en": "When lying flat", "hi": "सीधा लेटने पर", "mr": "सरळ झोपल्यावर"}, ("orthopnoea",)),
               Option("night", {"en": "It wakes me up at night", "hi": "रात को नींद से जगा देता है", "mr": "रात्री झोपेतून जाग येते"}, ("pnd",)),
           ], ("walking",)),
        _q("sob_speech", "breathlessness",
           {"en": "Right now, can you speak a full sentence without stopping for breath?",
            "hi": "क्या आप अभी बिना रुके पूरा वाक्य बोल पा रहे हैं?", "mr": "आत्ता तुम्ही न थांबता पूर्ण वाक्य बोलू शकता का?"},
           "Breathlessness — speech", "single_select", [
               Option("yes", {"en": "Yes", "hi": "हाँ", "mr": "होय"}),
               Option("no", {"en": "No, I have to stop for breath", "hi": "नहीं, साँस लेने के लिए रुकना पड़ता है", "mr": "नाही, श्वासासाठी थांबावे लागते"}, ("cannot_speak_full",)),
           ], ("yes",), depth="conditional", when=lambda ctx: "sob_rest" in ctx.findings),
    ],
    "headache": [
        _q("ha_onset", "headache",
           {"en": "How did the headache start?", "hi": "सिरदर्द कैसे शुरू हुआ?", "mr": "डोकेदुखी कशी सुरू झाली?"},
           "Headache — onset", "single_select", [
               Option("sudden", {"en": "Suddenly — the worst headache of my life", "hi": "अचानक — ज़िंदगी का सबसे तेज़ सिरदर्द", "mr": "अचानक — आयुष्यातील सर्वात तीव्र डोकेदुखी"}, ("thunderclap",)),
               Option("gradual", {"en": "Slowly, over hours or days", "hi": "धीरे-धीरे, घंटों या दिनों में", "mr": "हळूहळू, काही तासांत किंवा दिवसांत"}),
               Option("recurring", {"en": "I get such headaches often", "hi": "ऐसा सिरदर्द अक्सर होता है", "mr": "अशी डोकेदुखी वारंवार होते"}, ("ha_recurrent",)),
           ], ("gradual",)),
        _q("ha_site", "headache",
           {"en": "Where is the headache?", "hi": "सिरदर्द कहाँ है?", "mr": "डोके कुठे दुखते?"},
           "Headache — site", "single_select", [
               Option("one_side", {"en": "One side of the head", "hi": "सिर के एक तरफ़", "mr": "डोक्याच्या एका बाजूला"}),
               Option("whole", {"en": "The whole head", "hi": "पूरे सिर में", "mr": "संपूर्ण डोक्यात"}),
               Option("back", {"en": "Back of the head and neck", "hi": "सिर के पीछे और गर्दन में", "mr": "डोक्याच्या मागे आणि मानेत"}),
               Option("front", {"en": "Forehead or around the eyes", "hi": "माथे या आँखों के आसपास", "mr": "कपाळावर किंवा डोळ्यांभोवती"}),
           ], ("whole",), depth="focused"),
    ],
    "abdominal_pain": [
        _q("ab_site", "abdominal_pain",
           {"en": "Where is the stomach pain?", "hi": "पेट में दर्द कहाँ है?", "mr": "पोटात नेमके कुठे दुखते?"},
           "Abdominal pain — site", "single_select", [
               Option("upper_middle", {"en": "Upper middle (below the chest)", "hi": "ऊपर बीच में (छाती के नीचे)", "mr": "वरच्या मध्यभागी (छातीखाली)"}, ("epigastric",)),
               Option("right_upper", {"en": "Upper right side", "hi": "ऊपर दाईं तरफ़", "mr": "वरच्या उजव्या बाजूला"}, ("ruq_pain",)),
               Option("lower_right", {"en": "Lower right side", "hi": "नीचे दाईं तरफ़", "mr": "खालच्या उजव्या बाजूला"}, ("rlq_pain",)),
               Option("lower_left", {"en": "Lower left side", "hi": "नीचे बाईं तरफ़", "mr": "खालच्या डाव्या बाजूला"}),
               Option("navel", {"en": "Around the navel", "hi": "नाभि के आसपास", "mr": "बेंबीभोवती"}),
               Option("all_over", {"en": "All over the stomach", "hi": "पूरे पेट में", "mr": "संपूर्ण पोटात"}, ("ab_diffuse",)),
           ], ("upper_middle",)),
        _q("ab_character", "abdominal_pain",
           {"en": "What is the pain like?", "hi": "दर्द कैसा है?", "mr": "वेदना कशी आहे?"},
           "Abdominal pain — character", "single_select", [
               Option("cramping", {"en": "Cramping, comes in waves", "hi": "मरोड़ जैसा, रुक-रुक कर", "mr": "मुरडा येतो, थांबून थांबून"}, ("colicky",)),
               Option("constant", {"en": "Constant, does not go away", "hi": "लगातार, जाता नहीं", "mr": "सतत, जात नाही"}, ("ab_constant",)),
               Option("burning", {"en": "Burning", "hi": "जलन", "mr": "जळजळ"}, ("ab_burning",)),
               Option("after_food", {"en": "Worse after eating", "hi": "खाने के बाद बढ़ता है", "mr": "जेवणानंतर वाढते"}),
           ], ("cramping",), depth="focused"),
    ],
    "vomiting_diarrhoea": [
        _q("vd_type", "vomiting_diarrhoea",
           {"en": "What are you having?", "hi": "आपको क्या हो रहा है?", "mr": "तुम्हाला काय होत आहे?"},
           "Vomiting / loose motions", "single_select", [
               Option("vomiting", {"en": "Vomiting", "hi": "उल्टी", "mr": "उलट्या"}, ("vomiting",)),
               Option("loose", {"en": "Loose motions", "hi": "दस्त", "mr": "जुलाब"}, ("diarrhoea",)),
               Option("both", {"en": "Both", "hi": "दोनों", "mr": "दोन्ही"}, ("vomiting", "diarrhoea")),
           ], ("loose",)),
        _q("vd_frequency", "vomiting_diarrhoea",
           {"en": "How many times in the last 24 hours?", "hi": "पिछले 24 घंटों में कितनी बार?", "mr": "गेल्या 24 तासांत किती वेळा?"},
           "Episodes in 24 h", "single_select", [
               Option("1_3", {"en": "1 to 3 times", "hi": "1 से 3 बार", "mr": "1 ते 3 वेळा"}),
               Option("4_6", {"en": "4 to 6 times", "hi": "4 से 6 बार", "mr": "4 ते 6 वेळा"}),
               Option("gt_6", {"en": "More than 6 times", "hi": "6 से ज़्यादा बार", "mr": "6 पेक्षा जास्त वेळा"}, ("vd_frequent",)),
           ], ("1_3",), depth="focused"),
    ],
    "joint_back_pain": [
        _q("jb_site", "joint_back_pain",
           {"en": "Where is the pain?", "hi": "दर्द कहाँ है?", "mr": "कुठे दुखते?"},
           "Pain — site", "multi_select", [
               Option("knees", {"en": "Knees", "hi": "घुटने", "mr": "गुडघे"}),
               Option("back", {"en": "Lower back", "hi": "कमर", "mr": "कंबर"}, ("back_pain",)),
               Option("neck_shoulder", {"en": "Neck or shoulders", "hi": "गर्दन या कंधे", "mr": "मान किंवा खांदे"}),
               Option("hands", {"en": "Hands or fingers", "hi": "हाथ या उँगलियाँ", "mr": "हात किंवा बोटे"}),
               Option("many", {"en": "Many joints / whole body", "hi": "कई जोड़ / पूरा बदन", "mr": "अनेक सांधे / संपूर्ण अंग"}, ("polyarthralgia",)),
           ], ("knees",)),
        _q("jb_swelling", "joint_back_pain",
           {"en": "Is there swelling, redness or warmth at the painful place?", "hi": "क्या दर्द वाली जगह पर सूजन, लाली या गर्माहट है?",
            "mr": "दुखणाऱ्या जागी सूज, लाली किंवा गरमपणा आहे का?"},
           "Swelling / redness", "single_select", [
               Option("yes", {"en": "Yes", "hi": "हाँ", "mr": "होय"}, ("joint_swelling",)),
               Option("no", {"en": "No", "hi": "नहीं", "mr": "नाही"}),
           ], ("no",), depth="focused"),
    ],
    "dizziness_weakness": [
        _q("dz_type", "dizziness_weakness",
           {"en": "What exactly do you feel?", "hi": "आपको ठीक-ठीक क्या महसूस होता है?", "mr": "तुम्हाला नेमके काय जाणवते?"},
           "Dizziness / weakness — type", "single_select", [
               Option("spinning", {"en": "The room seems to spin", "hi": "चारों ओर सब घूमता लगता है", "mr": "सगळे गरगरल्यासारखे वाटते"}, ("vertigo",)),
               Option("faint", {"en": "I feel I might faint", "hi": "लगता है बेहोश हो जाऊँगा", "mr": "बेशुद्ध पडेन असे वाटते"}, ("presyncope",)),
               Option("weak", {"en": "Weak and tired all the time", "hi": "हर समय कमज़ोरी और थकान", "mr": "सतत अशक्तपणा आणि थकवा"}, ("fatigue",)),
           ], ("weak",)),
    ],
    "skin_problem": [
        _q("sk_type", "skin_problem",
           {"en": "What is the skin problem?", "hi": "त्वचा की क्या समस्या है?", "mr": "त्वचेची काय समस्या आहे?"},
           "Skin — type", "multi_select", [
               Option("rash", {"en": "Rash or red spots", "hi": "दाने या लाल चकत्ते", "mr": "पुरळ किंवा लाल चट्टे"}, ("rash",)),
               Option("itching", {"en": "Itching", "hi": "खुजली", "mr": "खाज"}),
               Option("boils", {"en": "Boils or a wound", "hi": "फोड़े या घाव", "mr": "फोड किंवा जखम"}),
               Option("patches", {"en": "Patches or change in skin colour", "hi": "धब्बे या त्वचा का रंग बदलना", "mr": "डाग किंवा त्वचेचा रंग बदलणे"}),
           ], ("itching",)),
    ],
    "other": [
        Question("other_describe", "other", "problem",
                 {"en": "Please tell us what is troubling you.", "hi": "कृपया बताइए आपको क्या तकलीफ़ है।", "mr": "कृपया तुम्हाला काय त्रास होतो ते सांगा."},
                 "Presenting complaint", "voice_or_text",
                 helper={"en": "Speak as you would to the doctor.", "hi": "जैसे डॉक्टर को बताते हैं वैसे बोलिए।", "mr": "डॉक्टरांना सांगाल तसे सांगा."},
                 default_text="Mild discomfort for a few days.",
                 when=lambda ctx: not (ctx.complaint_text or "").strip()),
    ],
}


# ─── Combined associated-symptoms question ────────────────────────────────────


@dataclass(frozen=True)
class _Assoc:
    rank: int
    option: Option
    complaints: Tuple[str, ...]


_ASSOCIATED: Tuple[_Assoc, ...] = (
    _Assoc(1, Option("one_side_weakness", {"en": "Weakness or numbness on one side of the body", "hi": "शरीर के एक तरफ़ कमज़ोरी या सुन्नपन", "mr": "शरीराच्या एका बाजूला अशक्तपणा किंवा बधिरपणा"}, ("one_side_weakness",)), ("headache", "dizziness_weakness")),
    _Assoc(2, Option("speech", {"en": "Difficulty speaking or slurred speech", "hi": "बोलने में दिक्कत या लड़खड़ाती ज़बान", "mr": "बोलण्यात अडचण किंवा अडखळणे"}, ("speech_difficulty",)), ("headache", "dizziness_weakness")),
    _Assoc(3, Option("sweating", {"en": "Cold sweat", "hi": "ठंडा पसीना", "mr": "थंड घाम"}, ("sweating",)), ("chest_pain", "dizziness_weakness")),
    _Assoc(4, Option("sob", {"en": "Difficulty breathing", "hi": "सांस लेने में तकलीफ", "mr": "श्वास घेण्यास त्रास"}, ("breathless",)), ("chest_pain", "fever", "cough_cold", "dizziness_weakness", "skin_problem", "other")),
    _Assoc(5, Option("fainting", {"en": "Fainting or nearly fainting", "hi": "बेहोशी या बेहोशी जैसा लगना", "mr": "बेशुद्ध पडणे किंवा तसे वाटणे"}, ("syncope",)), ("chest_pain", "dizziness_weakness", "vomiting_diarrhoea", "other")),
    _Assoc(6, Option("neck_stiffness", {"en": "Stiff neck — cannot bend the head forward", "hi": "गर्दन अकड़ना — सिर आगे नहीं झुकता", "mr": "मान ताठ — डोके पुढे वाकत नाही"}, ("neck_stiffness",)), ("fever", "headache")),
    _Assoc(7, Option("face_swelling", {"en": "Swelling of face, lips or tongue", "hi": "चेहरे, होंठ या जीभ में सूजन", "mr": "चेहरा, ओठ किंवा जिभेला सूज"}, ("angioedema",)), ("skin_problem",)),
    _Assoc(8, Option("blood_stool", {"en": "Blood in stool or black stool", "hi": "मल में खून या काला मल", "mr": "शौचात रक्त किंवा काळी शौच"}, ("gi_bleed",)), ("abdominal_pain", "vomiting_diarrhoea")),
    _Assoc(9, Option("vomit_blood", {"en": "Vomiting blood", "hi": "खून की उल्टी", "mr": "रक्ताची उलटी"}, ("gi_bleed",)), ("abdominal_pain", "vomiting_diarrhoea")),
    _Assoc(10, Option("bladder_bowel", {"en": "Loss of control over urine or stool", "hi": "पेशाब या मल पर नियंत्रण न रहना", "mr": "लघवी किंवा शौचावर नियंत्रण न राहणे"}, ("bladder_bowel_loss",)), ("joint_back_pain",)),
    _Assoc(11, Option("leg_numbness", {"en": "Numbness or weakness in the legs", "hi": "पैरों में सुन्नपन या कमज़ोरी", "mr": "पायांमध्ये बधिरपणा किंवा अशक्तपणा"}, ("leg_numbness",)), ("joint_back_pain",)),
    _Assoc(12, Option("confusion", {"en": "Confusion or unusual drowsiness", "hi": "उलझन या असामान्य नींद आना", "mr": "गोंधळ किंवा असामान्य गुंगी"}, ("confusion",)), ("headache", "fever", "dizziness_weakness")),
    _Assoc(13, Option("chest_pain", {"en": "Chest pain", "hi": "सीने में दर्द", "mr": "छातीत दुखणे"}, ("chest_pain",)), ("cough_cold", "breathlessness", "dizziness_weakness", "other")),
    _Assoc(14, Option("vision", {"en": "Blurred or double vision", "hi": "धुंधला या दोहरा दिखना", "mr": "अंधुक किंवा दोन-दोन दिसणे"}, ("vision_change",)), ("headache",)),
    _Assoc(15, Option("dehydration", {"en": "Very thirsty or passing very little urine", "hi": "बहुत प्यास या बहुत कम पेशाब", "mr": "खूप तहान किंवा खूप कमी लघवी"}, ("dehydration",)), ("vomiting_diarrhoea",)),
    _Assoc(16, Option("palpitations", {"en": "Racing or pounding heartbeat", "hi": "धड़कन तेज़ या ज़ोर से", "mr": "छातीत धडधड"}, ("palpitations",)), ("chest_pain", "dizziness_weakness", "breathlessness")),
    _Assoc(17, Option("leg_swelling", {"en": "Swelling of feet or legs", "hi": "पैरों या टखनों में सूजन", "mr": "पाय किंवा घोट्यांना सूज"}, ("leg_swelling",)), ("breathlessness",)),
    _Assoc(18, Option("wheeze", {"en": "Wheezing sound while breathing", "hi": "सांस लेते समय सीटी जैसी आवाज़", "mr": "श्वास घेताना शिट्टीसारखा आवाज"}, ("wheeze",)), ("breathlessness", "cough_cold")),
    _Assoc(19, Option("nausea", {"en": "Nausea or vomiting", "hi": "जी मिचलाना या उल्टी", "mr": "मळमळ किंवा उलटी"}, ("vomiting",)), ("chest_pain", "headache", "abdominal_pain", "fever", "other")),
    _Assoc(20, Option("burning_urine", {"en": "Burning while passing urine", "hi": "पेशाब में जलन", "mr": "लघवीला जळजळ"}, ("dysuria",)), ("fever", "abdominal_pain")),
    _Assoc(21, Option("loose_motions", {"en": "Loose motions", "hi": "दस्त", "mr": "जुलाब"}, ("diarrhoea",)), ("abdominal_pain", "fever")),
    _Assoc(22, Option("fever", {"en": "Fever", "hi": "बुखार", "mr": "ताप"}, ("fever",)), ("skin_problem", "joint_back_pain", "abdominal_pain", "vomiting_diarrhoea", "cough_cold", "headache", "other")),
    _Assoc(23, Option("rash", {"en": "Skin rash", "hi": "त्वचा पर दाने", "mr": "त्वचेवर पुरळ"}, ("rash",)), ("fever",)),
    _Assoc(24, Option("spreading", {"en": "Spreading quickly", "hi": "तेज़ी से फैल रहा है", "mr": "झपाट्याने पसरत आहे"}, ("rash_spreading",)), ("skin_problem",)),
    _Assoc(25, Option("blisters", {"en": "Blisters or peeling skin", "hi": "छाले या त्वचा उतरना", "mr": "फोड किंवा त्वचा सोलणे"}, ("blisters",)), ("skin_problem",)),
    _Assoc(26, Option("body_ache", {"en": "Body ache", "hi": "बदन दर्द", "mr": "अंगदुखी"}, ("body_ache",)), ("fever",)),
    _Assoc(27, Option("sore_throat", {"en": "Sore throat", "hi": "गले में खराश", "mr": "घसा दुखणे"}, ("sore_throat",)), ("cough_cold", "fever")),
    _Assoc(28, Option("runny_nose", {"en": "Runny or blocked nose", "hi": "नाक बहना या बंद होना", "mr": "नाक वाहणे किंवा बंद होणे"}, ("runny_nose",)), ("cough_cold",)),
)

_NONE_OPTION = Option("none", {"en": "None of these", "hi": "इनमें से कुछ नहीं", "mr": "यापैकी काहीही नाही"}, exclusive=True)
_ASSOCIATED_CAP = 9


def _associated_options(ctx: Context) -> Tuple[Option, ...]:
    chosen: List[Option] = []
    seen_values: Set[str] = set()
    for entry in sorted(_ASSOCIATED, key=lambda a: a.rank):
        if not any(c in ctx.complaints for c in entry.complaints):
            continue
        # Skip anything the patient has already told us (e.g. "Difficulty
        # breathing" when breathlessness is the complaint itself).
        if entry.option.findings and all(f in ctx.findings for f in entry.option.findings):
            continue
        if entry.option.value in seen_values:
            continue
        seen_values.add(entry.option.value)
        chosen.append(entry.option)
        if len(chosen) >= _ASSOCIATED_CAP:
            break
    return tuple(chosen) + ((_NONE_OPTION,) if chosen else ())


SHARED_ASSOCIATED = Question(
    "associated", "shared", "problem",
    {"en": "Along with this, do you have any of these?", "hi": "इसके साथ क्या इनमें से कुछ है?", "mr": "यासोबत यापैकी काही आहे का?"},
    "Associated symptoms", "multi_select", default=("none",), options_fn=_associated_options,
)


# ─── AYUSH — Dashavidha Pariksha (ids and codes match question_engine) ───────

def _ay(qid, text, label, options, default):
    return Question(qid, "ayush", "ayush", text, label, "single_select", tuple(options), default=(default,))


AYUSH_QUESTIONS: List[Question] = [
    _ay("ayush_q2_prakriti",
        {"en": "Which describes your natural body type best (as you have always been)?", "hi": "आप हमेशा से किस तरह के शरीर वाले रहे हैं?", "mr": "तुमची नैसर्गिक शरीरप्रकृती कशी आहे (नेहमीपासून)?"},
        "Prakriti", [
            Option("vata", {"en": "Thin, dry skin, feel cold, worry easily (Vata)", "hi": "दुबला, रूखी त्वचा, ठंड लगती है, जल्दी चिंता (वात)", "mr": "सडपातळ, कोरडी त्वचा, थंडी वाजते, पटकन काळजी (वात)"}),
            Option("pitta", {"en": "Medium build, feel hot, strong hunger, quick temper (Pitta)", "hi": "मध्यम शरीर, गर्मी लगती है, तेज़ भूख, जल्दी गुस्सा (पित्त)", "mr": "मध्यम शरीर, उष्णता जाणवते, तीव्र भूक, पटकन राग (पित्त)"}),
            Option("kapha", {"en": "Heavy build, calm, slow digestion, sleep a lot (Kapha)", "hi": "भारी शरीर, शांत, धीमा पाचन, ज़्यादा नींद (कफ)", "mr": "भरदार शरीर, शांत, मंद पचन, जास्त झोप (कफ)"}),
            Option("vata_pitta", {"en": "Mix of thin and hot (Vata-Pitta)", "hi": "दुबला और गर्म दोनों (वात-पित्त)", "mr": "सडपातळ आणि उष्ण दोन्ही (वात-पित्त)"}),
            Option("pitta_kapha", {"en": "Mix of hot and heavy (Pitta-Kapha)", "hi": "गर्म और भारी दोनों (पित्त-कफ)", "mr": "उष्ण आणि भरदार दोन्ही (पित्त-कफ)"}),
            Option("tridosha_sama", {"en": "Balanced — none of these stands out", "hi": "संतुलित — कोई खास नहीं", "mr": "संतुलित — विशेष काही नाही"}),
        ], "tridosha_sama"),
    _ay("ayush_q3_vikriti",
        {"en": "What has been disturbed in your body recently?", "hi": "हाल ही में आपके शरीर में क्या बिगड़ा है?", "mr": "अलीकडे तुमच्या शरीरात काय बिघडले आहे?"},
        "Vikriti", [
            Option("vata_vikriti", {"en": "Dryness, gas, body pain, anxiety", "hi": "रूखापन, गैस, बदन दर्द, घबराहट", "mr": "कोरडेपणा, गॅस, अंगदुखी, अस्वस्थता"}),
            Option("pitta_vikriti", {"en": "Acidity, burning, inflammation, anger", "hi": "एसिडिटी, जलन, सूजन, गुस्सा", "mr": "आम्लपित्त, जळजळ, सूज, राग"}),
            Option("kapha_vikriti", {"en": "Heaviness, cold or congestion, laziness", "hi": "भारीपन, सर्दी-जकड़न, आलस", "mr": "जडपणा, सर्दी-कफ, आळस"}),
            Option("sannipata", {"en": "All of these together", "hi": "ये सब एक साथ", "mr": "हे सर्व एकत्र"}),
            Option("unknown_vikriti", {"en": "Not sure", "hi": "पता नहीं", "mr": "माहीत नाही"}),
        ], "unknown_vikriti"),
    _ay("ayush_q4_sara",
        {"en": "How would you describe your skin, hair and body strength?", "hi": "आपकी त्वचा, बाल और शरीर की ताक़त कैसी है?", "mr": "तुमची त्वचा, केस आणि शरीराची ताकद कशी आहे?"},
        "Sara", [
            Option("rasa_sara", {"en": "Glowing, soft skin", "hi": "चमकदार, मुलायम त्वचा", "mr": "तेजस्वी, मऊ त्वचा"}),
            Option("rakta_sara", {"en": "Good colour, healthy blood", "hi": "अच्छा रंग, स्वस्थ खून", "mr": "चांगला रंग, निरोगी रक्त"}),
            Option("mamsa_sara", {"en": "Firm, strong muscles", "hi": "कसी हुई, मज़बूत मांसपेशियाँ", "mr": "घट्ट, मजबूत स्नायू"}),
            Option("majja_sara", {"en": "Sharp mind, good memory", "hi": "तेज़ दिमाग़, अच्छी याददाश्त", "mr": "तल्लख बुद्धी, चांगली स्मरणशक्ती"}),
            Option("shukra_sara", {"en": "Rarely fall ill, strong immunity", "hi": "कम बीमार पड़ते हैं, मज़बूत रोग-प्रतिरोध", "mr": "क्वचित आजारी पडता, मजबूत प्रतिकारशक्ती"}),
            Option("avasara", {"en": "Weak, dry, tire easily", "hi": "कमज़ोर, रूखा, जल्दी थकान", "mr": "अशक्त, कोरडे, पटकन थकवा"}),
        ], "mamsa_sara"),
    _ay("ayush_q5_samhanana",
        {"en": "How is your body frame?", "hi": "आपकी शारीरिक बनावट कैसी है?", "mr": "तुमची शरीरयष्टी कशी आहे?"},
        "Samhanana", [
            Option("pravara", {"en": "Well-built and strong", "hi": "गठीला और मज़बूत", "mr": "पिळदार आणि मजबूत"}),
            Option("madhyama", {"en": "Medium build", "hi": "मध्यम बनावट", "mr": "मध्यम बांधा"}),
            Option("avara", {"en": "Thin, lean build", "hi": "दुबला-पतला", "mr": "सडपातळ, कृश"}),
        ], "madhyama"),
    _ay("ayush_q6_agni_koshtha",
        {"en": "How are your digestion and bowel habits?", "hi": "आपका पाचन और मल-त्याग कैसा है?", "mr": "तुमचे पचन आणि शौच कसे आहे?"},
        "Agni & Koshtha", [
            Option("sama_madhyama", {"en": "Regular — digest well, normal motions", "hi": "नियमित — अच्छा पाचन, सामान्य मल", "mr": "नियमित — चांगले पचन, सामान्य शौच"}),
            Option("tikshna_mridu", {"en": "Very hungry, loose motions", "hi": "बहुत भूख, पतला मल", "mr": "खूप भूक, पातळ शौच"}),
            Option("manda_krura", {"en": "Slow digestion, constipation", "hi": "धीमा पाचन, कब्ज़", "mr": "मंद पचन, बद्धकोष्ठता"}),
            Option("vishma_vishama", {"en": "Irregular — keeps changing", "hi": "अनियमित — बदलता रहता है", "mr": "अनियमित — बदलत राहते"}),
        ], "sama_madhyama"),
    _ay("ayush_q7_satmya",
        {"en": "What suits your body?", "hi": "आपके शरीर को क्या सूट करता है?", "mr": "तुमच्या शरीराला काय मानवते?"},
        "Satmya", [
            Option("sarva_satmya", {"en": "All kinds of food and weather", "hi": "हर तरह का खाना और मौसम", "mr": "सर्व प्रकारचे अन्न आणि हवामान"}),
            Option("ekahara_satmya", {"en": "Only light, simple food", "hi": "सिर्फ़ हल्का, सादा खाना", "mr": "फक्त हलके, साधे अन्न"}),
            Option("cold_intolerant", {"en": "Cannot tolerate cold", "hi": "ठंड सहन नहीं होती", "mr": "थंडी सहन होत नाही"}),
            Option("heat_intolerant", {"en": "Cannot tolerate heat", "hi": "गर्मी सहन नहीं होती", "mr": "उष्णता सहन होत नाही"}),
        ], "sarva_satmya"),
    _ay("ayush_q8_sattva",
        {"en": "How do you handle stress and pain?", "hi": "आप तनाव और दर्द को कैसे झेलते हैं?", "mr": "तुम्ही ताण आणि वेदना कशा सहन करता?"},
        "Sattva", [
            Option("pravara_sattva", {"en": "Stay calm and steady", "hi": "शांत और स्थिर रहते हैं", "mr": "शांत आणि स्थिर राहता"}),
            Option("madhyama_sattva", {"en": "Manage with some effort", "hi": "थोड़ी कोशिश से संभाल लेते हैं", "mr": "थोड्या प्रयत्नाने सांभाळता"}),
            Option("avara_sattva", {"en": "Get anxious or upset quickly", "hi": "जल्दी घबरा या परेशान हो जाते हैं", "mr": "पटकन घाबरता किंवा अस्वस्थ होता"}),
        ], "madhyama_sattva"),
    _ay("ayush_q9_ahara_shakti",
        {"en": "How is your appetite, and how much can you eat?", "hi": "आपकी भूख कैसी है और आप कितना खा पाते हैं?", "mr": "तुमची भूक कशी आहे आणि तुम्ही किती खाऊ शकता?"},
        "Ahara Shakti", [
            Option("high_ahara_vyayama", {"en": "Good appetite, eat a full meal", "hi": "अच्छी भूख, भरपेट खाते हैं", "mr": "चांगली भूक, पोटभर जेवता"}),
            Option("moderate_ahara_vyayama", {"en": "Moderate appetite", "hi": "मध्यम भूख", "mr": "मध्यम भूक"}),
            Option("low_ahara_vyayama", {"en": "Poor appetite, eat very little", "hi": "कम भूख, बहुत थोड़ा खाते हैं", "mr": "कमी भूक, खूप थोडे खाता"}),
            Option("irregular_ahara", {"en": "Appetite keeps changing", "hi": "भूख बदलती रहती है", "mr": "भूक बदलत राहते"}),
        ], "moderate_ahara_vyayama"),
    _ay("ayush_q10_vyayama_shakti",
        {"en": "How much physical work or exercise can you do?", "hi": "आप कितना शारीरिक काम या व्यायाम कर पाते हैं?", "mr": "तुम्ही किती शारीरिक काम किंवा व्यायाम करू शकता?"},
        "Vyayama Shakti", [
            Option("high_vyayama", {"en": "A lot, without getting tired", "hi": "बहुत, बिना थके", "mr": "खूप, न थकता"}),
            Option("moderate_vyayama", {"en": "A moderate amount", "hi": "मध्यम", "mr": "मध्यम"}),
            Option("low_vyayama", {"en": "Very little, I tire quickly", "hi": "बहुत कम, जल्दी थक जाते हैं", "mr": "खूप कमी, पटकन थकता"}),
        ], "moderate_vyayama"),
    _ay("ayush_q11_vaya_ahara_vihara",
        {"en": "Which best matches your age and daily routine?", "hi": "आपकी उम्र और दिनचर्या के लिए कौन-सा सबसे सही है?", "mr": "तुमचे वय आणि दिनचर्या यासाठी काय सर्वात योग्य आहे?"},
        "Vaya & Ahara-Vihara", [
            Option("bala", {"en": "Under 16 years", "hi": "16 साल से कम", "mr": "16 वर्षांखालील"}),
            Option("madhyama_sattvic", {"en": "16–60 years, simple diet, regular routine", "hi": "16–60 साल, सादा खाना, नियमित दिनचर्या", "mr": "16–60 वर्षे, साधा आहार, नियमित दिनचर्या"}),
            Option("madhyama_guru_irregular", {"en": "16–60 years, heavy or oily food, late nights", "hi": "16–60 साल, भारी या तला खाना, देर रात", "mr": "16–60 वर्षे, जड किंवा तेलकट अन्न, रात्री उशिरा"}),
            Option("vriddha_laghu", {"en": "Over 60 years, light diet", "hi": "60 साल से ज़्यादा, हल्का खाना", "mr": "60 वर्षांवरील, हलका आहार"}),
        ], "madhyama_sattvic"),
]


# ─── History tail ─────────────────────────────────────────────────────────────

_YES = {"en": "Yes", "hi": "हाँ", "mr": "होय"}
_NO = {"en": "No", "hi": "नहीं", "mr": "नाही"}

HISTORY_QUESTIONS: List[Question] = [
    Question("hx_conditions", "history", "history",
             {"en": "Do you have any of these long-term illnesses?", "hi": "क्या आपको इनमें से कोई पुरानी बीमारी है?", "mr": "तुम्हाला यापैकी कोणता जुनाट आजार आहे का?"},
             "Known conditions", "multi_select", (
                 Option("diabetes", {"en": "Diabetes (sugar)", "hi": "मधुमेह (शुगर)", "mr": "मधुमेह (साखर)"}, ("diabetes",)),
                 Option("hypertension", {"en": "High blood pressure", "hi": "हाई ब्लड प्रेशर", "mr": "उच्च रक्तदाब"}, ("hypertension",)),
                 Option("heart", {"en": "Heart disease", "hi": "दिल की बीमारी", "mr": "हृदयविकार"}, ("heart_disease",)),
                 Option("asthma", {"en": "Asthma or lung disease", "hi": "दमा या फेफड़ों की बीमारी", "mr": "दमा किंवा फुफ्फुसाचा आजार"}, ("asthma",)),
                 Option("thyroid", {"en": "Thyroid problem", "hi": "थायरॉइड की समस्या", "mr": "थायरॉइडची समस्या"}),
                 Option("kidney", {"en": "Kidney disease", "hi": "गुर्दे की बीमारी", "mr": "मूत्रपिंडाचा आजार"}, ("kidney_disease",)),
                 _NONE_OPTION,
             ), default=("none",)),
    Question("hx_medicines", "history", "history",
             {"en": "Do you take any medicines regularly?", "hi": "क्या आप कोई दवा नियमित रूप से लेते हैं?", "mr": "तुम्ही नियमितपणे कोणतेही औषध घेता का?"},
             "Regular medicines", "single_select", (Option("yes", _YES, ("on_meds",)), Option("no", _NO)), default=("no",)),
    Question("hx_medicines_list", "history", "history",
             {"en": "Which medicines do you take?", "hi": "आप कौन-सी दवाएँ लेते हैं?", "mr": "तुम्ही कोणती औषधे घेता?"},
             "Medicines", "voice_or_text",
             helper={"en": "Say the names you remember — you can also scan the prescription in the next step.",
                     "hi": "जो नाम याद हों बताइए — अगले चरण में पर्चा भी स्कैन कर सकते हैं।",
                     "mr": "आठवणारी नावे सांगा — पुढच्या टप्प्यात चिठ्ठीही स्कॅन करू शकता."},
             default_text="Not recalled", depth="conditional", when=lambda ctx: "on_meds" in ctx.findings),
    Question("hx_allergy", "history", "history",
             {"en": "Are you allergic to any medicine or food?", "hi": "क्या आपको किसी दवा या खाने से एलर्जी है?", "mr": "तुम्हाला कोणत्या औषधाची किंवा अन्नाची ॲलर्जी आहे का?"},
             "Allergies", "single_select",
             (Option("yes", _YES, ("allergy",)), Option("no", _NO), Option("not_sure", {"en": "Not sure", "hi": "पता नहीं", "mr": "माहीत नाही"})),
             default=("no",)),
    Question("hx_allergy_list", "history", "history",
             {"en": "What are you allergic to?", "hi": "आपको किस चीज़ से एलर्जी है?", "mr": "तुम्हाला कशाची ॲलर्जी आहे?"},
             "Allergy details", "voice_or_text", default_text="Not recalled",
             depth="conditional", when=lambda ctx: "allergy" in ctx.findings),
]

SECTION_LABELS: Dict[str, L] = {
    "problem": {"en": "About your problem", "hi": "आपकी तकलीफ़ के बारे में", "mr": "तुमच्या त्रासाविषयी"},
    "ayush": {"en": "Body constitution (Dashavidha)", "hi": "शरीर प्रकृति (दशविध परीक्षा)", "mr": "शरीर प्रकृती (दशविध परीक्षा)"},
    "history": {"en": "Your medical history", "hi": "आपका पिछला इलाज", "mr": "तुमचा वैद्यकीय इतिहास"},
}

ALL_QUESTIONS: Dict[str, Question] = {
    q.id: q for q in [SHARED_DURATION, SHARED_SEVERITY, SHARED_ASSOCIATED, *AYUSH_QUESTIONS, *HISTORY_QUESTIONS,
                      *(q for module in MODULES.values() for q in module)]
}


# ─── Findings ─────────────────────────────────────────────────────────────────

_NEGATORS = ("no", "not", "never", "without", "नहीं", "नही", "ना", "नाही", "न")

# Phrases in free-text / spoken answers that map onto findings. Deliberately
# short and specific: a broad list turns every "no pain" into an alert.
_TEXT_FINDINGS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("cp_radiates", ("left arm", "left shoulder", "jaw", "बाएँ हाथ", "बाएं हाथ", "बाये हाथ", "जबड़", "जबड", "डाव्या हात")),
    ("sweating", ("sweat", "पसीना", "पसीने", "घाम")),
    ("breathless", ("breathless", "short of breath", "difficulty breathing", "सांस फूल", "साँस फूल", "सांस लेने में", "साँस लेने में", "दम लाग", "धाप")),
    ("syncope", ("fainted", "faint", "blacked out", "बेहोश", "बेशुद्ध")),
    ("one_side_weakness", ("one side", "paralys", "लकवा", "एक तरफ", "एका बाजू")),
    ("speech_difficulty", ("slurred", "can't speak", "cannot speak", "बोलने में दिक्कत", "बोलता नहीं", "बोलता येत नाही")),
    ("neck_stiffness", ("stiff neck", "neck stiff", "गर्दन अकड़", "गर्दन अकड", "मान ताठ")),
    ("thunderclap", ("worst headache", "sudden severe headache", "अचानक तेज सिरदर्द", "अचानक तेज़ सिरदर्द")),
    ("cannot_speak_full", ("cannot breathe", "can't breathe", "not able to breathe", "सांस नहीं आ", "साँस नहीं आ", "श्वास घेता येत नाही")),
    ("angioedema", ("lip swell", "lips swell", "throat swell", "tongue swell", "swollen lips", "होंठ सूज", "होठ सूज", "गला सूज", "ओठ सूज", "जीभ सूज")),
    ("gi_bleed", ("vomiting blood", "blood in vomit", "black stool", "blood in stool", "खून की उल्टी", "काला मल", "रक्ताची उलटी")),
    ("haemoptysis", ("coughing blood", "cough blood", "blood in cough", "खांसी में खून", "खोकल्यात रक्त")),
    ("bladder_bowel_loss", ("no control of urine", "can't control urine", "cannot control urine", "पेशाब पर नियंत्रण")),
    ("confusion", ("confused", "confusion", "भ्रम", "गोंधळ")),
)


def _negated(text: str, start: int) -> bool:
    window = text[max(0, start - 24):start].split()[-3:]
    return any(w.strip(".,!?") in _NEGATORS for w in window)


def text_findings(text: str) -> Set[str]:
    found: Set[str] = set()
    lowered = (text or "").lower()
    if not lowered:
        return found
    for finding, phrases in _TEXT_FINDINGS:
        for phrase in phrases:
            idx = lowered.find(phrase.lower())
            if idx >= 0 and not _negated(lowered, idx):
                found.add(finding)
                break
    return found


def build_context(complaints: Sequence[str], framework: str, answers: Dict[str, Dict[str, Any]],
                  complaint_text: Optional[str] = None) -> Context:
    ctx = Context(list(complaints), framework, answers, complaint_text)
    findings: Set[str] = set()
    for cid in ctx.complaints:
        complaint = COMPLAINTS_BY_ID.get(cid)
        if complaint:
            findings.update(complaint.findings)
    if complaint_text:
        findings |= text_findings(complaint_text)
    ctx.findings = findings
    # Option findings are resolved against the options that were on offer, which
    # for the associated question depend on the findings known so far.
    for qid, answer in answers.items():
        question = ALL_QUESTIONS.get(qid)
        values = set(answer.get("values") or [])
        if question and values:
            for option in question.resolved_options(ctx) or question.options:
                if option.value in values:
                    findings.update(option.findings)
            if qid == "associated":
                for entry in _ASSOCIATED:
                    if entry.option.value in values:
                        findings.update(entry.option.findings)
        if answer.get("text"):
            findings |= text_findings(answer["text"])
    ctx.findings = findings
    return ctx


# ─── Planning ─────────────────────────────────────────────────────────────────


def plan(ctx: Context) -> List[Question]:
    """The full ordered interview for the current state of the encounter."""
    ordered: List[Question] = [SHARED_DURATION]
    for cid in ctx.complaints:
        ordered += [q for q in MODULES.get(cid, []) if q.depth == "core"]
    ordered.append(SHARED_SEVERITY)
    ordered.append(SHARED_ASSOCIATED)
    if ctx.single_complaint:
        for cid in ctx.complaints:
            ordered += [q for q in MODULES.get(cid, []) if q.depth == "focused"]
    for cid in ctx.complaints:
        ordered += [q for q in MODULES.get(cid, []) if q.depth == "conditional"]
    if ctx.framework == "ayush":
        ordered += AYUSH_QUESTIONS
    ordered += HISTORY_QUESTIONS

    out: List[Question] = []
    for q in ordered:
        if q.id in {x.id for x in out}:
            continue
        if q.id in ctx.answers:
            out.append(q)
            continue
        if q.when and not q.when(ctx):
            continue
        if q.options_fn and not q.resolved_options(ctx):
            continue
        out.append(q)
    return out


def next_question(ctx: Context) -> Tuple[Optional[Question], List[Question]]:
    steps = plan(ctx)
    for q in steps:
        if q.id not in ctx.answers:
            return q, steps
    return None, steps


def render(question: Question, ctx: Context, steps: List[Question], language: str) -> Dict[str, Any]:
    """The kiosk's IntakeQuestion shape (frontend-kiosk/src/api/types.ts)."""
    options = question.resolved_options(ctx)
    sections = [s for s in ("problem", "ayush", "history") if any(q.section == s for q in steps)]
    current = next((i for i, q in enumerate(steps) if q.id == question.id), len(steps) - 1) + 1
    payload: Dict[str, Any] = {
        "question_id": question.id,
        "text": loc(question.resolved_text(ctx), language),
        "input_type": question.input_type,
        "options": [{"value": o.value, "label": loc(o.label, language), "exclusive": o.exclusive} for o in options],
        "allow_voice": True,
        "allow_text": question.input_type == "voice_or_text",
        "progress": {"current": current, "estimated_total": len(steps)},
        "section": {"id": question.section, "label": loc(SECTION_LABELS[question.section], language),
                    "index": sections.index(question.section) + 1, "total": len(sections)},
    }
    if question.helper:
        payload["helper"] = loc(question.helper, language)
    if question.scale_tone:
        payload["scale_tone"] = question.scale_tone
    return payload


# ─── Answers: readable text and voice → option mapping ────────────────────────

_STOPWORDS = {"the", "and", "or", "of", "to", "a", "an", "in", "my", "i", "it", "is", "when", "with", "only",
              "even", "all", "time", "more", "than", "less", "day", "days", "yes", "no", "not", "have", "has",
              "at", "on", "for", "me", "am", "this", "that", "side", "very", "like", "feel", "से", "में", "और",
              "या", "का", "की", "के", "है", "हैं", "नहीं", "आणि", "किंवा", "आहे", "नाही"}

_DURATION_PATTERN = re.compile(r"(\d+)\s*(hour|hr|day|week|month|घंट|दिन|हफ़्त|हफ्त|सप्ताह|महीन|तास|दिवस|आठवड|महिन)")

# Whisper writes small numbers as words as often as digits.
_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1, "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6, "सात": 7,
    "आठ": 8, "नौ": 9, "दस": 10, "दोन": 2, "पाच": 5, "सहा": 6, "नऊ": 9, "दहा": 10,
}


def _words_to_digits(text: str) -> str:
    return " ".join(str(_NUMBER_WORDS[w]) if w in _NUMBER_WORDS else w for w in text.split())


def _duration_from_text(text: str) -> Optional[str]:
    lowered = _words_to_digits((text or "").lower())
    match = _DURATION_PATTERN.search(lowered)
    if not match:
        if any(w in lowered for w in ("today", "आज", "आजपासून")):
            return "today"
        return None
    n, unit = int(match.group(1)), match.group(2)
    if unit.startswith(("hour", "hr", "घंट", "तास")):
        return "today"
    if unit.startswith(("day", "दिन", "दिवस")):
        return "today" if n < 1 else "d1_3" if n <= 3 else "d4_7" if n <= 7 else "w1_4" if n <= 30 else "gt_month"
    if unit.startswith(("week", "हफ़्त", "हफ्त", "सप्ताह", "आठवड")):
        return "d4_7" if n <= 1 else "w1_4" if n <= 4 else "gt_month"
    return "gt_month" if n >= 1 else "w1_4"


def match_options(question: Question, ctx: Context, text: str) -> List[str]:
    """Best-effort mapping of a spoken/typed answer onto a select question's options."""
    if question.input_type == "voice_or_text" or not text:
        return []
    if question.id == "duration":
        value = _duration_from_text(text)
        return [value] if value else []
    lowered = text.lower()
    # (score, -position, value): highest score wins, ties go to the option the
    # patient saw first rather than whichever sorts last alphabetically.
    scores: List[Tuple[int, int, str]] = []
    for position, option in enumerate(question.resolved_options(ctx)):
        words: Set[str] = set()
        for label in option.label.values():
            for word in re.split(r"[\s,/()\-—–.]+", label.lower()):
                if len(word) >= 3 and word not in _STOPWORDS:
                    words.add(word)
        # Whole-word matching for Latin script ("ever" must not match "severe");
        # substring for Devanagari, where inflection attaches to the stem.
        score = sum(1 for w in words if _option_word_match(w, lowered))
        if score:
            scores.append((score, -position, option.value))
    if not scores:
        return []
    scores.sort(reverse=True)
    if question.input_type in ("single_select", "scale"):
        return [scores[0][2]]
    return [value for _, _, value in scores if value != "none"] or [scores[0][2]]


def readable_answer(question: Optional[Question], ctx: Context, values: Sequence[str], text: Optional[str],
                    language: str = "en") -> str:
    """The value the doctor sees: option labels in English, the patient's words verbatim."""
    labels: List[str] = []
    if question and values:
        by_value = {o.value: o for o in question.resolved_options(ctx)}
        if question.id == "associated":
            by_value.update({e.option.value: e.option for e in _ASSOCIATED})
        labels = [loc(by_value[v].label, language) if v in by_value else v.replace("_", " ") for v in values]
    joined = "; ".join(labels)
    if text and joined:
        return f"{joined} — “{text.strip()}”"
    return joined or (text or "").strip()


def default_answer(question: Question, ctx: Context) -> Dict[str, Any]:
    if question.input_type == "voice_or_text":
        return {"values": [], "text": question.default_text or "Not recorded"}
    valid = {o.value for o in question.resolved_options(ctx)}
    values = [v for v in question.default if v in valid] or ([next(iter(valid))] if valid else [])
    return {"values": values, "text": None}


# ─── Red flags ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RedFlagRule:
    id: str
    priority: str  # P1_CRITICAL | P2_URGENT
    headline: str
    action: str
    test: Callable[[Set[str]], bool]
    evidence: Tuple[str, ...] = ()


FINDING_LABELS = {
    "chest_pain": "chest pain", "cp_radiates": "pain spreading to arm/jaw", "sweating": "cold sweat",
    "breathless": "breathlessness", "syncope": "fainting", "cp_pressing": "pressing character",
    "severity_severe": "severe intensity", "cp_rest": "pain at rest", "cp_exertional": "pain on exertion",
    "one_side_weakness": "one-sided weakness", "speech_difficulty": "speech difficulty", "thunderclap": "sudden worst-ever headache",
    "neck_stiffness": "neck stiffness", "fever": "fever", "headache": "headache", "cannot_speak_full": "cannot complete sentences",
    "sob_rest": "breathless at rest", "angioedema": "face/lip/tongue swelling", "rash": "rash", "wheeze": "wheeze",
    "gi_bleed": "blood in vomit/stool", "haemoptysis": "blood in cough", "dehydration": "dehydration signs",
    "vd_frequent": "frequent vomiting/loose motions", "bladder_bowel_loss": "loss of bladder/bowel control",
    "back_pain": "back pain", "joint_back_pain": "back/joint pain", "leg_numbness": "leg numbness",
    "diabetes": "diabetes", "confusion": "confusion", "orthopnoea": "breathless lying flat", "pnd": "waking breathless at night",
    "fever_high": "fever above 102°F", "vomiting": "vomiting", "diarrhoea": "loose motions",
}

RED_FLAG_RULES: Tuple[RedFlagRule, ...] = (
    RedFlagRule("ACS_SUSPECTED", "P1_CRITICAL", "Possible acute coronary syndrome",
                "Immediate ECG and physician review.",
                lambda F: "chest_pain" in F and (bool(F & {"cp_radiates", "sweating", "breathless", "syncope"})
                                                 or ("cp_pressing" in F and bool(F & {"severity_severe", "cp_rest"}))),
                ("chest_pain", "cp_radiates", "sweating", "breathless", "syncope", "cp_pressing", "severity_severe", "cp_rest")),
    RedFlagRule("STROKE_SUSPECTED", "P1_CRITICAL", "Possible stroke (FAST signs)",
                "Activate stroke pathway; note time of onset.",
                lambda F: bool(F & {"one_side_weakness", "speech_difficulty"}), ("one_side_weakness", "speech_difficulty")),
    RedFlagRule("THUNDERCLAP_HEADACHE", "P1_CRITICAL", "Sudden worst-ever headache",
                "Urgent physician review — exclude subarachnoid haemorrhage.",
                lambda F: "thunderclap" in F, ("thunderclap",)),
    RedFlagRule("MENINGITIS_SUSPECTED", "P1_CRITICAL", "Possible meningitis",
                "Isolate and review immediately.",
                lambda F: "neck_stiffness" in F and bool(F & {"fever", "headache", "fever_high"}),
                ("neck_stiffness", "fever", "headache", "fever_high")),
    RedFlagRule("RESPIRATORY_DISTRESS", "P1_CRITICAL", "Severe breathing difficulty",
                "Oxygen saturation check and immediate review.",
                lambda F: "cannot_speak_full" in F, ("cannot_speak_full", "sob_rest")),
    RedFlagRule("ANAPHYLAXIS_SUSPECTED", "P1_CRITICAL", "Possible anaphylaxis",
                "Immediate review; adrenaline protocol available.",
                lambda F: "angioedema" in F and bool(F & {"breathless", "wheeze", "rash"}),
                ("angioedema", "breathless", "wheeze", "rash")),
    RedFlagRule("GI_BLEED", "P1_CRITICAL", "Possible gastrointestinal bleeding",
                "Check vitals and haemoglobin urgently.",
                lambda F: "gi_bleed" in F, ("gi_bleed",)),
    RedFlagRule("CAUDA_EQUINA", "P1_CRITICAL", "Back pain with loss of bladder/bowel control",
                "Urgent neurological review.",
                lambda F: "bladder_bowel_loss" in F, ("bladder_bowel_loss", "back_pain", "leg_numbness")),
    RedFlagRule("ANGIOEDEMA", "P2_URGENT", "Swelling of face, lips or tongue",
                "Prompt review for airway involvement.",
                lambda F: "angioedema" in F and not (F & {"breathless", "wheeze", "rash"}), ("angioedema",)),
    RedFlagRule("EXERTIONAL_CHEST_PAIN", "P2_URGENT", "Chest pain on exertion",
                "Prioritise physician review and ECG.",
                lambda F: "chest_pain" in F and "cp_exertional" in F, ("chest_pain", "cp_exertional")),
    RedFlagRule("HAEMOPTYSIS", "P2_URGENT", "Blood in cough", "Prioritise chest assessment.",
                lambda F: "haemoptysis" in F, ("haemoptysis",)),
    RedFlagRule("FEVER_WITH_BREATHLESSNESS", "P2_URGENT", "Fever with breathlessness",
                "Check oxygen saturation; prioritise review.",
                lambda F: "fever" in F and "breathless" in F, ("fever", "breathless")),
    RedFlagRule("SEVERE_DEHYDRATION", "P2_URGENT", "Possible dehydration",
                "Assess hydration; consider ORS/IV fluids.",
                lambda F: "dehydration" in F or ("vd_frequent" in F and bool(F & {"vomiting", "diarrhoea"})),
                ("dehydration", "vd_frequent", "vomiting", "diarrhoea")),
    RedFlagRule("SYNCOPE", "P2_URGENT", "Fainting episode", "Check vitals and blood glucose.",
                lambda F: "syncope" in F and "chest_pain" not in F, ("syncope",)),
    RedFlagRule("HYPOGLYCAEMIA_RISK", "P2_URGENT", "Diabetic with confusion or fainting",
                "Check blood glucose now.",
                lambda F: "diabetes" in F and bool(F & {"confusion", "syncope"}), ("diabetes", "confusion", "syncope")),
    RedFlagRule("HEART_FAILURE_SIGNS", "P2_URGENT", "Breathless lying flat or at night",
                "Prioritise cardiac review.",
                lambda F: "breathless" in F and bool(F & {"orthopnoea", "pnd"}), ("breathless", "orthopnoea", "pnd")),
    RedFlagRule("FEVER_WITH_CONFUSION", "P2_URGENT", "Fever with confusion",
                "Urgent review for sepsis.",
                lambda F: "fever" in F and "confusion" in F, ("fever", "confusion")),
)

RULE_IDS = {r.id for r in RED_FLAG_RULES}


def evaluate_red_flags(findings: Set[str]) -> List[Dict[str, Any]]:
    flags = []
    for rule in RED_FLAG_RULES:
        if rule.test(findings):
            matched = [FINDING_LABELS.get(f, f.replace("_", " ")) for f in rule.evidence if f in findings]
            flags.append({"rule": rule.id, "priority": rule.priority, "title": rule.headline,
                          "message": f"{rule.headline}: {', '.join(matched)}. {rule.action}"})
    flags.sort(key=lambda f: f["priority"])  # P1 before P2
    return flags
