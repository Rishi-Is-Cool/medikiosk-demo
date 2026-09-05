"""
MediKiosk Backend — Clinical History Extractor
Transforms raw kiosk interview answers into standardized clinical history domains.
Supports both Allopathy (SOCRATES) and AYUSH (Dashavidha Pariksha) interview schemas.
"""
import json
from typing import Dict, Any, Optional, List


class HistoryExtractor:
    """
    Structures interview answers from the adaptive question engine into
    physician-readable clinical history sections:
    Chief Complaint → HPI → Past History → Surgical → Medications/Allergies
    → Family History → Personal/Social History → Review of Systems
    """

    def extract_history(
        self,
        answers: Dict[str, Any],
        department_mode: str = "Allopathy"
    ) -> Dict[str, Any]:
        """
        Convert raw interview answer dict into structured clinical history domains.

        Args:
            answers: Dict mapping question_id → answer (str, list, or selected value)
            department_mode: "Allopathy" or "AYUSH"

        Returns:
            Dict with all standard clinical history keys + optional ayush_data
        """
        is_ayush = department_mode.strip().upper() == "AYUSH"

        if is_ayush:
            return self._extract_ayush_history(answers)
        else:
            return self._extract_allopathy_history(answers)

    # ──────────────────────────────────────────────────────────────────────────
    # Allopathy (SOCRATES Framework) Extraction
    # ──────────────────────────────────────────────────────────────────────────
    def _extract_allopathy_history(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        # Step 1 — Chief Complaint
        chief_raw = answers.get("q1_chief_complaint", "Not specified")
        chief_complaint = self._humanize(chief_raw)

        # Step 2 — Duration / Onset
        duration_raw = answers.get("q2_duration_onset", "duration unknown")
        duration_map = {
            "acute_1h": "less than 1 hour (acute onset)",
            "acute_24h": "within the last 24 hours",
            "1_3_days": "1 to 3 days",
            "1_2_weeks": "1 to 2 weeks",
            "gt_1_month": "more than 1 month (chronic)",
            "recurrent": "recurring / episodic problem"
        }
        duration = duration_map.get(str(duration_raw), str(duration_raw))

        # Step 3 — Severity
        severity_raw = answers.get("q3_severity_scale", "")
        severity_map = {
            "mild_1_3": "Mild (1-3/10)",
            "moderate_4_6": "Moderate (4-6/10)",
            "severe_7_9": "Severe (7-9/10)",
            "unbearable_10": "Unbearable (10/10)"
        }
        severity = severity_map.get(str(severity_raw), str(severity_raw) or "Not rated")

        # Step 4 — Character / Radiation (SOCRATES C + R)
        character_raw = answers.get("q4_character_radiation", "")
        character_map = {
            "sharp": "Sharp / stabbing in quality",
            "dull_aching": "Dull, aching pain",
            "burning": "Burning sensation",
            "pressing": "Pressing / squeezing quality",
            "throbbing": "Throbbing / pulsating",
            "radiates_arm_jaw": "Radiating to arm, jaw, or left side"
        }
        character = character_map.get(str(character_raw), str(character_raw) or "Not described")

        # Step 5 — Associated symptoms
        assoc_raw = answers.get("q5_associated_symptoms", [])
        assoc_list = assoc_raw if isinstance(assoc_raw, list) else [assoc_raw]
        assoc_display = {
            "shortness_of_breath": "Shortness of breath",
            "nausea_vomiting": "Nausea / Vomiting",
            "cold_sweats": "Cold sweats / diaphoresis",
            "high_fever": "High fever (> 101°F)",
            "dizziness_syncope": "Dizziness / near-syncope",
            "limb_swelling": "Swelling of limbs",
            "palpitations": "Palpitations",
            "none": "None"
        }
        assoc_str = ", ".join(
            [assoc_display.get(a, a) for a in assoc_list if a != "none"]
        ) or "None reported"

        # Step 6 — Aggravating / Relieving factors
        aggrav_raw = answers.get("q6_aggravating_relieving", [])
        aggrav_list = aggrav_raw if isinstance(aggrav_raw, list) else [aggrav_raw]
        aggrav_display = {
            "worse_exertion": "worsened by exertion",
            "worse_supine": "worsened on lying flat",
            "relieved_rest": "relieved by rest",
            "worse_eating": "worsened after eating",
            "relieved_medication": "partially relieved by medication",
            "no_pattern": "no clear aggravating/relieving pattern"
        }
        aggrav_str = "; ".join(
            [aggrav_display.get(a, a) for a in aggrav_list]
        ) or "Not specified"

        # Build SOCRATES-structured HPI
        hpi = (
            f"Patient presents with {chief_complaint} for {duration}. "
            f"Pain/discomfort is rated {severity}, described as {character}. "
            f"Associated symptoms include: {assoc_str}. "
            f"Factors: {aggrav_str}."
        )

        # Step 7 — Past Medical History
        past_raw = answers.get("q7_past_medical_history", [])
        past_list = past_raw if isinstance(past_raw, list) else [past_raw]
        past_display = {
            "diabetes": "Type 2 Diabetes Mellitus",
            "hypertension": "Essential Hypertension",
            "heart_disease": "Ischaemic Heart Disease",
            "asthma_thyroid": "Asthma / Hypothyroidism",
            "kidney_disease": "Chronic Kidney Disease",
            "cancer": "Malignancy (type not specified)",
            "prior_surgery": "Prior surgical procedure",
            "none": "No significant past medical history"
        }
        past_conditions = [past_display.get(p, p) for p in past_list]
        surgical = "Previous surgery reported — details not specified." if "prior_surgery" in past_list else "No major surgical history reported."
        past_str = ", ".join([p for p in past_conditions if p != past_display["none"]]) or "No significant past history"

        # Step 8 — Medications & Allergies
        meds_raw = answers.get("q8_medications_allergies", "")
        meds_map = {
            "chronic_meds": "Currently on chronic medications for BP / Diabetes / Heart condition",
            "penicillin_sulfa_allergy": "Known allergy to Penicillin / Sulpha drugs — PLEASE FLAG",
            "nsaid_allergy": "Known allergy to NSAIDs (Aspirin / Ibuprofen) — PLEASE FLAG",
            "anticoagulants": "Currently on anticoagulant therapy (blood thinners)",
            "nkda_no_meds": "No known drug allergies (NKDA). No regular medications."
        }
        meds_str = meds_map.get(str(meds_raw), str(meds_raw) or "Not specified")
        allergies = "Penicillin / Sulpha" if "penicillin" in str(meds_raw).lower() else (
            "NSAIDs (Aspirin / Ibuprofen)" if "nsaid" in str(meds_raw).lower() else "NKDA"
        )

        # Step 9 — Family History
        fam_raw = answers.get("q9_family_personal_history", [])
        fam_list = fam_raw if isinstance(fam_raw, list) else [fam_raw]
        fam_display = {
            "fh_diabetes": "Diabetes",
            "fh_cardiac_stroke": "Cardiac disease / Stroke",
            "fh_hypertension": "Hypertension",
            "fh_cancer": "Malignancy",
            "fh_none": "No significant family history"
        }
        fam_conditions = [fam_display.get(f, f) for f in fam_list]
        fam_str = ", ".join(fam_conditions) or "Not reported"

        # Step 10 — Personal / Social History
        social_raw = answers.get("q10_personal_social_history", [])
        social_list = social_raw if isinstance(social_raw, list) else [social_raw]
        social_display = {
            "smoker": "Smoker",
            "alcohol": "Alcohol use",
            "tobacco_gutkha": "Tobacco / Gutkha use",
            "sedentary": "Sedentary lifestyle",
            "active": "Physically active",
            "vegetarian": "Vegetarian",
            "none": "Non-smoker, no alcohol, no tobacco"
        }
        social_str = ", ".join(
            [social_display.get(s, s) for s in social_list if s != "none"]
        ) or "No significant social history"

        # Review of Systems (generated from associated symptoms)
        ros_lines = []
        if assoc_str and "None" not in assoc_str:
            ros_lines.append(f"Relevant associated: {assoc_str}")
        if "shortness_of_breath" in str(assoc_list):
            ros_lines.append("Respiratory: Dyspnoea reported")
        if "palpitations" in str(assoc_list):
            ros_lines.append("Cardiovascular: Palpitations noted")
        if "nausea_vomiting" in str(assoc_list):
            ros_lines.append("GI: Nausea / vomiting")
        ros = " | ".join(ros_lines) if ros_lines else "No significant additional systems review."

        return {
            "chief_complaint": chief_complaint,
            "hpi": hpi,
            "past_history": f"Known case of: {past_str}",
            "surgical_history": surgical,
            "allergies": allergies,
            "medications": meds_str,
            "family_history": fam_str,
            "personal_history": social_str,
            "ros": ros,
            "ayush_data": None
        }

    # ──────────────────────────────────────────────────────────────────────────
    # AYUSH Dashavidha Pariksha Extraction
    # ──────────────────────────────────────────────────────────────────────────
    def _extract_ayush_history(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        chief_raw = answers.get("ayush_q1_chief_complaint", "General AYUSH consultation")
        chief_complaint = self._humanize(chief_raw)

        prakriti_map = {
            "vata": "Vata Pradhana (Light, Dry, Cold, Mobile)",
            "pitta": "Pitta Pradhana (Warm, Sharp, Acidic, Intense)",
            "kapha": "Kapha Pradhana (Heavy, Moist, Calm, Stable)",
            "vata_pitta": "Vata-Pitta Dwandwaja",
            "pitta_kapha": "Pitta-Kapha Dwandwaja",
            "tridosha_sama": "Tridosha Sama (Balanced Constitution)"
        }

        vikriti_map = {
            "vata_vikriti": "Vata Vikriti (Dryness, Gas, Constipation, Anxiety)",
            "pitta_vikriti": "Pitta Vikriti (Inflammation, Acidity, Rashes)",
            "kapha_vikriti": "Kapha Vikriti (Congestion, Weight gain, Lethargy)",
            "sannipata": "Sannipata Vikriti (All three Doshas disturbed)",
            "unknown_vikriti": "Vikriti undetermined — requires clinical examination"
        }

        sara_map = {
            "rasa_sara": "Rasa Sara (Excellent skin, moisture, complexion)",
            "rakta_sara": "Rakta Sara (Healthy blood, good colour, vitality)",
            "mamsa_sara": "Mamsa Sara (Well-developed musculature)",
            "majja_sara": "Majja Sara (Clear intellect, good memory, creativity)",
            "shukra_sara": "Shukra Sara (Excellent immunity, reproductive strength)",
            "avasara": "Avasara (Depleted tissue quality)"
        }

        agni_map = {
            "sama_madhyama": "Sama Agni / Madhyama Koshtha (Balanced digestion and bowel)",
            "tikshna_mridu": "Tikshna Agni / Mridu Koshtha (High appetite, loose stools)",
            "manda_krura": "Manda Agni / Krura Koshtha (Slow digestion, constipation)",
            "vishma_vishama": "Vishma Agni / Vishama Koshtha (Irregular digestion and bowel)"
        }

        sattva_map = {
            "pravara_sattva": "Pravara Sattva (Strong, fearless, resilient mind)",
            "madhyama_sattva": "Madhyama Sattva (Moderate mental resilience)",
            "avara_sattva": "Avara Sattva (Fearful, anxious, low pain tolerance)"
        }

        samhanana_map = {
            "pravara": "Pravara Samhanana (Well-built, strong, compact frame)",
            "madhyama": "Madhyama Samhanana (Medium body build)",
            "avara": "Avara Samhanana (Lean / thin / underdeveloped frame)"
        }

        satmya_map = {
            "sarva_satmya": "Sarva Satmya (Tolerates all foods and environments)",
            "ekahara_satmya": "Ekahara Satmya (Only tolerates light, single foods)",
            "cold_intolerant": "Cold Asatmya (Intolerance to cold climate/foods)",
            "heat_intolerant": "Ushna Asatmya (Intolerance to heat/spicy/pungent)"
        }

        ahara_map = {
            "high_ahara_vyayama": "High Ahara Shakti & Vyayama Shakti (Good appetite and exercise tolerance)",
            "moderate_ahara_vyayama": "Madhyama Ahara & Vyayama Shakti (Moderate capacity)",
            "low_ahara_vyayama": "Low Ahara & Vyayama Shakti (Poor appetite, fatigues easily)",
            "irregular_ahara": "Vishama Ahara Shakti (Irregular, unpredictable appetite)"
        }

        vaya_map = {
            "bala": "Bala Avastha (Childhood / Adolescence)",
            "madhyama_sattvic": "Madhyama Avastha (Adult, balanced Sattvic lifestyle)",
            "madhyama_guru_irregular": "Madhyama Avastha with Guru Ahara (Heavy diet, irregular routine)",
            "vriddha_laghu": "Vriddha Avastha (Senior, light diet recommended)"
        }

        ayush_data = {
            "Prakriti": prakriti_map.get(
                answers.get("ayush_q2_prakriti", ""), answers.get("ayush_q2_prakriti", "Not assessed")
            ),
            "Vikriti": vikriti_map.get(
                answers.get("ayush_q3_vikriti", ""), answers.get("ayush_q3_vikriti", "Not assessed")
            ),
            "Sara": sara_map.get(
                answers.get("ayush_q4_sara", ""), answers.get("ayush_q4_sara", "Not assessed")
            ),
            "Samhanana": samhanana_map.get(
                answers.get("ayush_q5_samhanana", ""), answers.get("ayush_q5_samhanana", "Not assessed")
            ),
            "Agni_Koshtha": agni_map.get(
                answers.get("ayush_q6_agni_koshtha", ""), answers.get("ayush_q6_agni_koshtha", "Not assessed")
            ),
            "Satmya": satmya_map.get(
                answers.get("ayush_q7_satmya", ""), answers.get("ayush_q7_satmya", "Not assessed")
            ),
            "Sattva": sattva_map.get(
                answers.get("ayush_q8_sattva", ""), answers.get("ayush_q8_sattva", "Not assessed")
            ),
            "Ahara_Vyayama_Shakti": ahara_map.get(
                answers.get("ayush_q9_ahara_shakti", ""), answers.get("ayush_q9_ahara_shakti", "Not assessed")
            ),
            "Vaya_Ahara_Vihara": vaya_map.get(
                answers.get("ayush_q10_vaya_ahara_vihara", ""), answers.get("ayush_q10_vaya_ahara_vihara", "Not assessed")
            )
        }

        hpi = (
            f"Patient presents for Ayurvedic consultation with chief complaint: {chief_complaint}. "
            f"Prakriti (constitution): {ayush_data['Prakriti']}. "
            f"Vikriti (current imbalance): {ayush_data['Vikriti']}. "
            f"Agni & Koshtha: {ayush_data['Agni_Koshtha']}."
        )

        return {
            "chief_complaint": chief_complaint,
            "hpi": hpi,
            "past_history": "As per AYUSH assessment — details in Dashavidha Pariksha section.",
            "surgical_history": "Not separately assessed in AYUSH intake (see clinical record).",
            "allergies": "Not separately elicited in AYUSH intake.",
            "medications": "Current Ayurvedic / Allopathic medications not separately listed.",
            "family_history": "Not separately elicited in AYUSH intake.",
            "personal_history": f"Ahara-Vihara & Lifestyle: {ayush_data['Vaya_Ahara_Vihara']}",
            "ros": (
                f"Sara: {ayush_data['Sara']} | Samhanana: {ayush_data['Samhanana']} | "
                f"Satmya: {ayush_data['Satmya']} | Sattva: {ayush_data['Sattva']} | "
                f"Ahara-Vyayama Shakti: {ayush_data['Ahara_Vyayama_Shakti']}"
            ),
            "ayush_data": json.dumps(ayush_data)
        }

    @staticmethod
    def _humanize(raw: Any) -> str:
        """Convert underscored option values to human-readable strings."""
        if isinstance(raw, str):
            return raw.replace("_", " ").replace("-", " ").title()
        if isinstance(raw, list):
            return ", ".join([str(r).replace("_", " ").title() for r in raw])
        return str(raw)


history_extractor = HistoryExtractor()
