/* Demo fixtures shaped exactly like shared/snapshot-contract.json.
   Two patients on purpose: Rahul is Ayurveda OPD (ayush block present),
   Anjali is General Medicine (ayush block null). Switching between them
   demonstrates the framework-agnostic claim without a toggle. */

export const QUEUE = {
  department: "Ayurveda OPD · Ground floor",
  doctor: { name: "Dr. S. Nair", hpr: "71-4402-9915", practitioner_type: "ayurveda" },
  stats: { seen_today: 34, in_queue: 17, median_wait_min: 22, intake_complete: 15 },
  patients: [
    {
      encounter_id: "enc_20260831_0451",
      token: "A-51",
      name: "Anjali Deshmukh",
      age_years: 58,
      sex: "female",
      complaint: "Chest pain, 40 minutes",
      department: "General med",
      intake_framework: "allopathic",
      intake_state: "ready",
      wait_min: 4,
      priority: true,
      priority_reason: "Chest pain + breathlessness + diaphoresis",
    },
    {
      encounter_id: "enc_20260831_0412",
      token: "A-12",
      name: "Rahul Verma",
      age_years: 42,
      sex: "male",
      complaint: "Fever with cough, 3 days",
      department: "Ayurveda",
      intake_framework: "ayush",
      intake_state: "ready",
      wait_min: null,
      in_consultation: true,
    },
    {
      encounter_id: "enc_20260831_0413",
      token: "A-13",
      name: "Meera Krishnan",
      age_years: 31,
      sex: "female",
      complaint: "Joint pain, both knees, 6 weeks",
      department: "Ayurveda",
      intake_framework: "ayush",
      intake_state: "ready",
      wait_min: 19,
    },
    {
      encounter_id: "enc_20260831_0414",
      token: "A-14",
      name: "Iqbal Ansari",
      age_years: 64,
      sex: "male",
      complaint: "Follow-up, diabetes review",
      department: "Ayurveda",
      intake_framework: "ayush",
      intake_state: "documents_processing",
      wait_min: 16,
    },
    {
      encounter_id: "enc_20260831_0415",
      token: "A-15",
      name: "Sunita Rao",
      age_years: 47,
      sex: "female",
      complaint: "Acidity, bloating after meals",
      department: "Ayurveda",
      intake_framework: "ayush",
      intake_state: "intake_in_progress",
      wait_min: 11,
    },
    {
      encounter_id: "enc_20260831_0416",
      token: "A-16",
      name: "Devendra Patil",
      age_years: 29,
      sex: "male",
      complaint: null,
      department: "Ayurveda",
      intake_framework: "ayush",
      intake_state: "not_started",
      wait_min: 3,
    },
  ],
};

const src = (type, id, locator = null) => ({ type, id, locator });

export const SNAPSHOTS = {
  /* ---------------------------------------------------------------- Rahul */
  enc_20260831_0412: {
    encounter_id: "enc_20260831_0412",
    generated_at: "2026-08-31T10:14:22+05:30",
    status: "draft",
    intake_framework: "ayush",
    patient: {
      patient_id: "pat_00731",
      name: "Rahul Verma",
      age_years: 42,
      sex: "male",
      abha_id: "91-2847-5563-0192",
      preferred_language: "hi",
      department: "Ayurveda OPD",
    },
    alerts: [
      {
        alert_id: "alr_01",
        severity: "critical",
        rule: "allergy_conflict",
        headline: "Penicillin allergy on record",
        detail:
          "Documented 14 Mar 2026 discharge summary; patient stated “no known allergies” at intake today.",
        conflicting_sources: [
          src("document", "doc_0091", { field: "drug_allergy", page: 1 }),
          src("patient_spoken", "utt_0034", { question_id: "allergy_known" }),
        ],
      },
      {
        alert_id: "alr_02",
        severity: "warning",
        rule: "abnormal_lab_value",
        headline: "HbA1c 8.2% — above reference range",
        detail: "Reference 4.0–5.6%. Rising from 7.4% in March.",
        conflicting_sources: [],
      },
    ],
    sections: {
      chief_complaint: {
        label: "Chief complaint",
        text: {
          value: "Fever with cough",
          duration: "3 days",
          source: src("patient_spoken", "utt_0002"),
          status: "ai_extracted",
        },
      },
      hpi: {
        label: "History of present illness",
        framework: "SOCRATES",
        items: [
          { key: "site", label: "Site", value: "Chest, retrosternal", source: src("patient_spoken", "utt_0007"), status: "ai_extracted" },
          { key: "onset", label: "Onset", value: "Gradual, 3 days", source: src("patient_spoken", "utt_0008"), status: "ai_extracted" },
          { key: "character", label: "Character", value: "Dry, non-productive", source: src("patient_spoken", "utt_0009"), status: "ai_extracted" },
          { key: "radiation", label: "Radiation", value: "None reported", source: src("patient_spoken", "utt_0010"), status: "ai_extracted" },
          { key: "associations", label: "Associations", value: "Fever, myalgia", source: src("patient_spoken", "utt_0011"), status: "ai_extracted" },
          { key: "timing", label: "Timing", value: "Worse at night", source: src("patient_spoken", "utt_0012"), status: "ai_extracted" },
          { key: "exacerbating", label: "Exacerbating", value: "Cold exposure", source: src("patient_spoken", "utt_0013"), status: "ai_extracted" },
          { key: "severity", label: "Severity", value: "6/10", source: src("patient_spoken", "utt_0014"), status: "ai_extracted" },
        ],
      },
      past_medical_surgical: {
        label: "Past medical and surgical",
        items: [
          { fact_id: "fct_0201", value: "Diabetes mellitus type 2", normalized: { system: "NAMASTE", display: "Madhumeha", code: "TODO", icd11_bio: "5A11" }, source: src("document", "doc_0091", { field: "diagnosis", page: 1 }), status: "ai_extracted" },
          { fact_id: "fct_0202", value: "Hypertension", normalized: { system: "NAMASTE", display: "Raktagata Vata", code: "TODO", icd11_bio: "BA00" }, source: src("document", "doc_0091", { field: "diagnosis", page: 1 }), status: "ai_extracted" },
          { fact_id: "fct_0203", value: "Community-acquired pneumonia, Mar 2026", normalized: null, source: src("document", "doc_0091", { field: "diagnosis", page: 1 }), status: "ai_extracted" },
        ],
      },
      drug_and_allergy: {
        label: "Drug and allergy",
        medications: [
          { fact_id: "fct_0301", value: "Metformin 500mg PO BD", source: src("document", "doc_0091", { field: "discharge_meds", page: 1 }), status: "ai_extracted" },
          { fact_id: "fct_0302", value: "Amlodipine 5mg PO OD", source: src("prior_encounter", "enc_20260314_0088"), status: "ai_extracted" },
        ],
        allergies: [
          { fact_id: "fct_0401", value: "Penicillin", reaction: "Urticarial rash", source: src("document", "doc_0091", { field: "drug_allergy", page: 1 }), status: "ai_extracted", alert_ids: ["alr_01"] },
          { fact_id: null, value: "Patient reported no known allergies", reaction: null, source: src("patient_spoken", "utt_0034"), status: "ai_extracted", alert_ids: ["alr_01"] },
        ],
      },
      family_history: { label: "Family history", collapsed_by_default: true, count: 2, items: [] },
      personal_history: { label: "Personal history", collapsed_by_default: true, count: 5, items: [] },
      review_of_systems: { label: "Review of systems", collapsed_by_default: true, systems_reviewed: 14, positive_count: 2, items: [] },
    },
    trend: {
      label: "Trend — one column per visit",
      dates: ["14 Mar", "02 Aug", "31 Aug"],
      groups: [
        {
          label: "Biomedical",
          rows: [
            { key: "hba1c", label: "HbA1c", values: ["7.4", "8.2", null], flags: [null, "high", null], ref: "4.0–5.6 %", source: src("document", "doc_0092", { field: "hba1c", page: 1 }) },
            { key: "fbs", label: "Fasting glucose", values: ["148", "164", null], flags: [null, "high", null], ref: "70–100 mg/dL", source: src("document", "doc_0092", { field: "fbs", page: 1 }) },
            { key: "hb", label: "Haemoglobin", values: ["13.1", "13.4", null], flags: [null, null, null], ref: "13.0–17.0 g/dL", source: src("document", "doc_0092", { field: "hb", page: 1 }) },
            { key: "weight", label: "Weight", values: ["81", "78", "77"], flags: [null, null, null], ref: "kg", source: src("patient_spoken", "utt_0042") },
          ],
        },
        {
          label: "Ayurvedic measures",
          ayush_only: true,
          rows: [
            { key: "agni", label: "Agni", values: ["Sama", "Manda", "Manda"], flags: [null, "low", "low"], ref: "—", source: src("patient_spoken", "utt_0049") },
            { key: "koshtha", label: "Koshtha", values: ["Madhyama", "Madhyama", "Krura"], flags: [null, null, "low"], ref: "—", source: src("patient_spoken", "utt_0050") },
            { key: "nidra", label: "Nidra", values: ["Prakrita", "Alpa", "Alpa"], flags: [null, "low", "low"], ref: "—", source: src("patient_spoken", "utt_0051") },
          ],
        },
      ],
    },
    ayush: {
      captured: true,
      prakriti: { value: "Pitta-Kapha", components: { vata: 20, pitta: 45, kapha: 35 }, source: src("patient_spoken", "utt_0040"), status: "ai_extracted" },
      vikriti: { value: "Pitta-Kapha vriddhi, Amavastha", source: src("patient_spoken", "utt_0041"), status: "ai_extracted" },
      vaya: { value: "Madhya", age_years: 42, source: src("patient_spoken", "utt_0001"), status: "ai_extracted" },
      pramana: { value: "172 cm · 78 kg · BMI 26.4", source: src("patient_spoken", "utt_0042"), status: "ai_extracted" },
      graded: [
        { key: "sara", label: "Sara", grade: "madhyama", source: src("patient_spoken", "utt_0043"), status: "ai_extracted" },
        { key: "samhanana", label: "Samhanana", grade: "madhyama", source: src("patient_spoken", "utt_0044"), status: "ai_extracted" },
        { key: "satmya", label: "Satmya", grade: "pravara", source: src("patient_spoken", "utt_0045"), status: "ai_extracted" },
        { key: "sattva", label: "Sattva", grade: "madhyama", source: src("patient_spoken", "utt_0046"), status: "ai_extracted" },
        { key: "ahara_shakti", label: "Ahara shakti", grade: "avara", source: src("patient_spoken", "utt_0047"), status: "ai_extracted" },
        { key: "vyayama_shakti", label: "Vyayama shakti", grade: "avara", source: src("patient_spoken", "utt_0048"), status: "ai_extracted" },
      ],
    },
    ayush_status: "present",
    last_visit: {
      encounter_id: "enc_20260314_0088",
      date: "2026-03-14",
      summary:
        "Discharged after community-acquired pneumonia. Metformin and amlodipine continued. Review advised in 4 weeks.",
      source: src("prior_encounter", "enc_20260314_0088"),
    },
    documents: [
      { document_id: "doc_0091", doc_type: "discharge_summary", dated: "2026-03-14", title: "City General Hospital — Discharge summary", page_count: 1 },
      { document_id: "doc_0092", doc_type: "lab_report", dated: "2026-08-02", title: "Pathology report", page_count: 1 },
    ],
  },

  /* --------------------------------------------------------------- Anjali */
  enc_20260831_0451: {
    encounter_id: "enc_20260831_0451",
    generated_at: "2026-08-31T10:16:02+05:30",
    status: "draft",
    intake_framework: "allopathic",
    patient: {
      patient_id: "pat_00982",
      name: "Anjali Deshmukh",
      age_years: 58,
      sex: "female",
      abha_id: "91-5510-2284-7731",
      preferred_language: "mr",
      department: "General Medicine OPD",
    },
    alerts: [
      {
        alert_id: "alr_11",
        severity: "critical",
        rule: "red_flag_combination",
        headline: "Possible acute coronary syndrome — priority triage",
        detail:
          "Chest pain with breathlessness and diaphoresis, onset 40 minutes. Flagged at intake and moved ahead of the queue.",
        conflicting_sources: [],
      },
    ],
    sections: {
      chief_complaint: {
        label: "Chief complaint",
        text: { value: "Central chest pain", duration: "40 minutes", source: src("patient_spoken", "utt_1002"), status: "ai_extracted" },
      },
      hpi: {
        label: "History of present illness",
        framework: "SOCRATES",
        items: [
          { key: "site", label: "Site", value: "Central chest", source: src("patient_spoken", "utt_1007"), status: "ai_extracted" },
          { key: "onset", label: "Onset", value: "Sudden, at rest", source: src("patient_spoken", "utt_1008"), status: "ai_extracted" },
          { key: "character", label: "Character", value: "Heavy, pressing", source: src("patient_spoken", "utt_1009"), status: "ai_extracted" },
          { key: "radiation", label: "Radiation", value: "Left arm, jaw", source: src("patient_spoken", "utt_1010"), status: "ai_extracted" },
          { key: "associations", label: "Associations", value: "Breathlessness, sweating, nausea", source: src("patient_spoken", "utt_1011"), status: "ai_extracted" },
          { key: "timing", label: "Timing", value: "Constant since onset", source: src("patient_spoken", "utt_1012"), status: "ai_extracted" },
          { key: "exacerbating", label: "Exacerbating", value: "Exertion", source: src("patient_spoken", "utt_1013"), status: "ai_extracted" },
          { key: "severity", label: "Severity", value: "8/10", source: src("patient_spoken", "utt_1014"), status: "ai_extracted" },
        ],
      },
      past_medical_surgical: {
        label: "Past medical and surgical",
        items: [
          { fact_id: "fct_1201", value: "Hypertension", normalized: { system: "ICD-11", display: "Essential hypertension", icd11_bio: "BA00" }, source: src("prior_encounter", "enc_20251102_0455"), status: "ai_extracted" },
        ],
      },
      drug_and_allergy: {
        label: "Drug and allergy",
        medications: [
          { fact_id: "fct_1301", value: "Telmisartan 40mg PO OD", source: src("prior_encounter", "enc_20251102_0455"), status: "ai_extracted" },
        ],
        allergies: [
          { fact_id: null, value: "No known drug allergies", reaction: null, source: src("patient_spoken", "utt_1034"), status: "ai_extracted", alert_ids: [] },
        ],
      },
      family_history: { label: "Family history", collapsed_by_default: true, count: 1, items: [] },
      personal_history: { label: "Personal history", collapsed_by_default: true, count: 3, items: [] },
      review_of_systems: { label: "Review of systems", collapsed_by_default: true, systems_reviewed: 9, positive_count: 3, items: [] },
    },
    trend: {
      label: "Trend — one column per visit",
      dates: ["02 Nov", "31 Aug"],
      groups: [
        {
          label: "Biomedical",
          rows: [
            { key: "sbp", label: "Systolic BP", values: ["148", "162"], flags: [null, "high"], ref: "90–130 mmHg", source: src("clinician", "obs_2201") },
            { key: "dbp", label: "Diastolic BP", values: ["92", "98"], flags: [null, "high"], ref: "60–85 mmHg", source: src("clinician", "obs_2202") },
            { key: "pulse", label: "Pulse", values: ["78", "104"], flags: [null, "high"], ref: "60–100 /min", source: src("clinician", "obs_2203") },
          ],
        },
      ],
    },
    ayush: null,
    ayush_status: "not_captured",
    last_visit: {
      encounter_id: "enc_20251102_0455",
      date: "2025-11-02",
      summary: "Routine hypertension review. Telmisartan 40mg continued. BP 148/92.",
      source: src("prior_encounter", "enc_20251102_0455"),
    },
    documents: [],
  },
};

/* Stand-in for the scanned page the evidence panel renders. In the real build
   this is documents.file_path; here it is transcribed text with the extracted
   field marked so click-to-source is demonstrable without binary assets. */
export const DOCUMENT_BODIES = {
  doc_0091: {
    title: "City General Hospital — Discharge summary",
    dated: "14 Mar 2026",
    lines: [
      { text: "Admitted 11 Mar 2026 · Discharged 14 Mar 2026" },
      { text: "Diagnosis: Community-acquired pneumonia", field: "diagnosis" },
      { text: "Known conditions: T2DM, Hypertension", field: "diagnosis" },
      { text: "Drug allergy: PENICILLIN — urticarial rash", field: "drug_allergy" },
      { text: "Discharge meds: Metformin 500mg BD, Amlodipine 5mg OD", field: "discharge_meds" },
      { text: "Advice: Review in 4 weeks" },
    ],
  },
  doc_0092: {
    title: "Pathology report",
    dated: "02 Aug 2026",
    lines: [
      { text: "Sample collected 02 Aug 2026, fasting" },
      { text: "HbA1c ................ 8.2 %   (4.0–5.6)", field: "hba1c" },
      { text: "Fasting glucose ...... 164 mg/dL (70–100)", field: "fbs" },
      { text: "Haemoglobin .......... 13.4 g/dL (13.0–17.0)", field: "hb" },
    ],
  },
};

export const DEVIATION_REASONS = [
  "Treatment failure",
  "Adverse reaction to previous drug",
  "Patient preference",
  "Cost or availability",
  "Comorbidity interaction",
  "Protocol update",
  "Other — specify",
];

/* ---------------------------------------------------------------------------
   Docon #07 — follow-up carry-forward.
   What the previous encounter left behind, offered for reuse rather than
   retyping. This is longitudinal patient memory made visible in one dialog.
   --------------------------------------------------------------------------- */

export const CARRY_FORWARD = {
  enc_20260831_0412: {
    from_encounter: "enc_20260314_0088",
    from_date: "14 Mar 2026",
    groups: [
      { key: "symptoms", label: "Symptoms and findings", value: "Productive cough, fever, reduced breath sounds left base" },
      { key: "diagnosis", label: "Diagnosis", value: "Community-acquired pneumonia; T2DM; Hypertension" },
      { key: "medicines", label: "Medicines", value: "Metformin 500mg BD · Amlodipine 5mg OD" },
      { key: "investigations", label: "Investigations", value: "HbA1c, Fasting glucose, Chest radiograph" },
      { key: "advice", label: "Advice", value: "Warm water only · Avoid curd at night · Review in 4 weeks" },
    ],
  },
  enc_20260831_0451: {
    from_encounter: "enc_20251102_0455",
    from_date: "02 Nov 2025",
    groups: [
      { key: "symptoms", label: "Symptoms and findings", value: "Asymptomatic; routine review" },
      { key: "diagnosis", label: "Diagnosis", value: "Essential hypertension" },
      { key: "medicines", label: "Medicines", value: "Telmisartan 40mg OD" },
      { key: "investigations", label: "Investigations", value: "Serum creatinine, Lipid profile" },
      { key: "advice", label: "Advice", value: "Reduce added salt · Walk 30 minutes daily" },
    ],
  },
};

/* ---------------------------------------------------------------------------
   Docon #10 — reusable advice library, read as pathya / apathya.
   Dietary and conduct guidance is a far larger share of an Ayurvedic
   consultation than of a GP's, and it is the part most often lost to
   handwriting. Entries are coded so they can be printed in the patient's
   language and counted in aggregate reporting.
   Frequency ranking is Docon #05 — used_count drives the "most used" block.
   --------------------------------------------------------------------------- */

export const ADVICE_LIBRARY = [
  { id: "adv_001", kind: "pathya", text: "Drink lukewarm water through the day", hi: "दिनभर गुनगुना पानी पिएँ", used_count: 412 },
  { id: "adv_002", kind: "apathya", text: "Avoid curd at night", hi: "रात में दही से परहेज़ करें", used_count: 388 },
  { id: "adv_003", kind: "pathya", text: "Steam inhalation twice daily", hi: "दिन में दो बार भाप लें", used_count: 341 },
  { id: "adv_004", kind: "apathya", text: "Avoid cold and refrigerated foods", hi: "ठंडे और फ्रिज़ के भोजन से बचें", used_count: 297 },
  { id: "adv_005", kind: "pathya", text: "Light, warm, freshly cooked meals", hi: "हल्का, गर्म, ताज़ा बना भोजन लें", used_count: 264 },
  { id: "adv_006", kind: "apathya", text: "Avoid daytime sleep", hi: "दिन में सोने से बचें", used_count: 233 },
  { id: "adv_007", kind: "pathya", text: "Walk 30 minutes daily", hi: "रोज़ 30 मिनट टहलें", used_count: 201 },
  { id: "adv_008", kind: "apathya", text: "Avoid spicy and fermented food", hi: "मसालेदार और खमीरी भोजन से बचें", used_count: 187 },
  { id: "adv_009", kind: "pathya", text: "Sleep by 10 pm", hi: "रात 10 बजे तक सो जाएँ", used_count: 154 },
  { id: "adv_010", kind: "pathya", text: "Pranayama for 10 minutes each morning", hi: "हर सुबह 10 मिनट प्राणायाम करें", used_count: 142 },
  { id: "adv_011", kind: "apathya", text: "Avoid suppressing natural urges", hi: "प्राकृतिक वेगों को न रोकें", used_count: 96 },
  { id: "adv_012", kind: "pathya", text: "Reduce added salt", hi: "नमक की मात्रा कम करें", used_count: 88 },
  { id: "adv_013", kind: "apathya", text: "Avoid exertion until fever settles", hi: "बुखार उतरने तक परिश्रम न करें", used_count: 74 },
  { id: "adv_014", kind: "pathya", text: "Buttermilk with roasted cumin after lunch", hi: "दोपहर के भोजन के बाद भुने जीरे के साथ छाछ", used_count: 61 },
];

/* ---------------------------------------------------------------------------
   Docon #16 — who is due back, as a report rather than a memory.
   Panchakarma and most classical protocols run for weeks, so adherence is
   the outcome that decides whether the treatment worked. Populated from
   ledger follow-up entries, which closes the loop from the finalise form.
   --------------------------------------------------------------------------- */

export const DUE_BACK = [
  { patient_id: "pat_00512", name: "Kavita Joshi", age_years: 52, sex: "female", due_on: "2026-08-29", days_overdue: 2, reason: "Panchakarma review — Virechana follow-up", last_seen: "01 Aug 2026", contact: "ABHA-linked app" },
  { patient_id: "pat_00644", name: "Ramesh Gupta", age_years: 67, sex: "male", due_on: "2026-08-31", days_overdue: 0, reason: "Hypertension review", last_seen: "03 Aug 2026", contact: "ABHA-linked app" },
  { patient_id: "pat_00731", name: "Rahul Verma", age_years: 42, sex: "male", due_on: "2026-09-07", days_overdue: -7, reason: "Fever review, 7 days", last_seen: "31 Aug 2026", contact: "ABHA-linked app" },
  { patient_id: "pat_00889", name: "Farida Sheikh", age_years: 38, sex: "female", due_on: "2026-09-14", days_overdue: -14, reason: "Amavata protocol, week 4", last_seen: "17 Aug 2026", contact: "ABHA-linked app" },
  { patient_id: "pat_00301", name: "Suresh Nair", age_years: 59, sex: "male", due_on: "2026-08-24", days_overdue: 7, reason: "Madhumeha review", last_seen: "27 Jul 2026", contact: "ABHA-linked app" },
];
