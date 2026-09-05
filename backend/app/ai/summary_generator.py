"""
MediKiosk Backend — Physician-Ready Clinical Summary Generator
Synthesizes conversational history, AYUSH Dashavidha Pariksha, red flags,
and extracted OCR lab data into a single structured physician-ready summary.
Supports Gemini LLM enhancement when GEMINI_API_KEY is configured.
"""
import os
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Priority badge formatting for red flags
_PRIORITY_BADGE = {
    "P1_CRITICAL": "🚨 P1-CRITICAL",
    "P2_URGENT": "⚠️ P2-URGENT",
    "P3_ROUTINE": "ℹ️ P3-ROUTINE"
}


class SummaryGenerator:
    """
    Synthesizes conversational history data, AYUSH assessment, red flag alerts,
    and extracted OCR lab/document data into a single physician-ready clinical
    summary formatted in Markdown.
    
    Optional: Gemini LLM can refine and professionally structure the HPI narrative.
    """

    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.use_gemini_summary = bool(self.gemini_api_key)

    def generate_physician_summary(
        self,
        patient_info: Dict[str, Any],
        history_data: Dict[str, Any],
        lab_results: List[Dict[str, Any]],
        red_flags: List[Dict[str, Any]],
        department_mode: str = "Allopathy"
    ) -> Dict[str, Any]:
        """
        Generate the complete physician-facing clinical intake summary.

        Args:
            patient_info: Patient demographics dict (name, age, gender, abha_id, language)
            history_data: Structured history from HistoryExtractor
            lab_results: List of extracted lab result dicts from OCR pipeline
            red_flags: List of detected emergency alert dicts
            department_mode: "Allopathy" or "AYUSH"

        Returns:
            Dict with:
              - formatted_summary_markdown: Full Markdown clinical summary for physician screen
              - audio_summary_text: Patient-facing audio confirmation in their language
              - ayush_dashavidha_summary: Parsed AYUSH Dashavidha dict (or None)
              - red_flags: Passed-through red flag list
        """
        name = patient_info.get("name", "Patient")
        age = patient_info.get("age", "—")
        gender = patient_info.get("gender", "—")
        abha_id = patient_info.get("abha_id") or "Not Linked"
        lang = patient_info.get("language", "en")

        # ── Red Flag Section ──────────────────────────────────────────────────
        red_flag_section = ""
        if red_flags:
            red_flag_section = "## 🚨 EMERGENCY RED FLAG ALERTS\n\n"
            red_flag_section += "> [!CAUTION]\n"
            for rf in red_flags:
                badge = _PRIORITY_BADGE.get(rf.get("priority", ""), rf.get("priority", ""))
                red_flag_section += (
                    f"> **{badge}** — {rf.get('title', '')}\n"
                    f"> {rf.get('message', '')}\n"
                    f"> **Recommended Action:** {rf.get('recommended_action', '')}\n\n"
                )
            red_flag_section += "---\n\n"

        # ── AYUSH Dashavidha Section ──────────────────────────────────────────
        ayush_section = ""
        ayush_dict = None
        ayush_raw = history_data.get("ayush_data")
        if ayush_raw:
            try:
                ayush_dict = json.loads(ayush_raw) if isinstance(ayush_raw, str) else ayush_raw
                ayush_lines = [
                    f"| **Prakriti (Constitution)** | {ayush_dict.get('Prakriti', '—')} |",
                    f"| **Vikriti (Current Imbalance)** | {ayush_dict.get('Vikriti', '—')} |",
                    f"| **Sara (Tissue Quality)** | {ayush_dict.get('Sara', '—')} |",
                    f"| **Samhanana (Body Build)** | {ayush_dict.get('Samhanana', '—')} |",
                    f"| **Agni & Koshtha** | {ayush_dict.get('Agni_Koshtha', '—')} |",
                    f"| **Satmya (Suitability)** | {ayush_dict.get('Satmya', '—')} |",
                    f"| **Sattva (Mental Strength)** | {ayush_dict.get('Sattva', '—')} |",
                    f"| **Ahara & Vyayama Shakti** | {ayush_dict.get('Ahara_Vyayama_Shakti', '—')} |",
                    f"| **Vaya & Ahara-Vihara** | {ayush_dict.get('Vaya_Ahara_Vihara', '—')} |",
                ]
                ayush_section = (
                    "## 🌿 AYUSH DASHAVIDHA PARIKSHA\n\n"
                    "| Parameter | Assessment |\n"
                    "|-----------|------------|\n"
                    + "\n".join(ayush_lines)
                    + "\n\n---\n\n"
                )
            except Exception as ex:
                logger.warning(f"Failed to parse AYUSH data: {ex}")

        # ── Lab Results Section ───────────────────────────────────────────────
        labs_section = "## 🔬 PRIOR INVESTIGATIONS & DIGITIZED LAB TIMELINE\n\n"
        if lab_results:
            labs_section += "| Test Name | Result | Unit | Reference Range | Status |\n"
            labs_section += "|-----------|--------|------|-----------------|--------|\n"
            for lab in lab_results:
                status_icon = "⚠️ **ABNORMAL**" if lab.get("abnormal") else "✅ Normal"
                labs_section += (
                    f"| {lab.get('test_name', '—')} "
                    f"| {lab.get('value', '—')} "
                    f"| {lab.get('unit', '—')} "
                    f"| {lab.get('reference_range', '—')} "
                    f"| {status_icon} |\n"
                )
        else:
            labs_section += "_No prior physical lab reports scanned._\n"

        labs_section += "\n---\n\n"

        # ── HPI — optionally LLM-enhanced ────────────────────────────────────
        hpi_text = history_data.get("hpi", "History not elicited.")
        if self.use_gemini_summary:
            hpi_text = self._enhance_hpi_with_gemini(hpi_text, history_data)

        # ── Compose Full Markdown Summary ─────────────────────────────────────
        markdown_summary = f"""# 🩺 MEDIKIOSK CLINICAL INTAKE SUMMARY

| Field | Details |
|-------|---------|
| **Patient** | {name} |
| **Age / Gender** | {age} yrs / {gender} |
| **ABHA ID** | {abha_id} |
| **Department Mode** | {department_mode} |
| **Intake Language** | {lang.upper()} |

---

{red_flag_section}## 📋 CLINICAL HISTORY

### Chief Complaint
{history_data.get('chief_complaint', 'Not specified')}

### History of Present Illness (HPI)
{hpi_text}

### Past Medical History
{history_data.get('past_history', 'Not reported')}

### Surgical History
{history_data.get('surgical_history', 'None')}

### Active Medications
{history_data.get('medications', 'None')}

### Drug Allergies
{history_data.get('allergies', 'NKDA')}

### Family History
{history_data.get('family_history', 'Not reported')}

### Personal & Social History
{history_data.get('personal_history', 'Not reported')}

### Review of Systems
{history_data.get('ros', 'Not performed')}

---

{ayush_section}{labs_section}> [!NOTE]
> Generated by **MediKiosk AI Clinical Intake Platform** v1.0  
> This is a draft summary from patient self-reporting. Physician review, examination, and confirmation required before clinical use.  
> Data handled under DPDPA 2023 & ABDM Consent Framework.
"""

        # ── Patient-Facing Audio Summary ──────────────────────────────────────
        audio_text = self._build_audio_summary(name, lang)

        return {
            "formatted_summary_markdown": markdown_summary,
            "audio_summary_text": audio_text,
            "ayush_dashavidha_summary": ayush_dict,
            "red_flags": red_flags
        }

    def _enhance_hpi_with_gemini(
        self,
        raw_hpi: str,
        history_data: Dict[str, Any]
    ) -> str:
        """
        Use Gemini to professionally rephrase the auto-generated HPI into
        a concise, physician-readable narrative paragraph.
        """
        try:
            from google import genai

            client = genai.Client(api_key=self.gemini_api_key)
            prompt = (
                "You are a clinical documentation AI for an Indian hospital OPD. "
                "Rewrite the following auto-generated History of Present Illness (HPI) "
                "into a concise, professional, physician-readable narrative in SOAP style. "
                "Do NOT diagnose. Do NOT add information not present. Keep it factual.\n\n"
                f"Raw HPI: {raw_hpi}\n\n"
                "Refined HPI:"
            )
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            refined = response.text.strip() if response.text else raw_hpi
            return refined if len(refined) > 30 else raw_hpi

        except Exception as ex:
            logger.warning(f"Gemini HPI refinement failed: {ex}. Using raw HPI.")
            return raw_hpi

    def _build_audio_summary(self, name: str, lang: str) -> str:
        """Build patient-facing audio confirmation text in their preferred language."""
        audio_map = {
            "hi": (
                f"नमस्कार {name}। आपकी स्वास्थ्य जानकारी सफलतापूर्वक दर्ज कर ली गई है। "
                "आपकी पुरानी जाँच रिपोर्ट और मुख्य शिकायत डॉक्टर की स्क्रीन पर भेज दी गई है। "
                "कृपया अपने नंबर का इंतजार करें।"
            ),
            "mr": (
                f"नमस्कार {name}। तुमची आरोग्य माहिती यशस्वीरित्या नोंदवली गेली आहे. "
                "तुमचे अहवाल आणि तक्रारी डॉक्टरांच्या स्क्रीनवर पाठवण्यात आल्या आहेत. "
                "कृपया तुमच्या नंबरची वाट पहा."
            ),
            "ta": (
                f"வணக்கம் {name}. உங்கள் மருத்துவ வரலாறு பதிவு செய்யப்பட்டது. "
                "உங்கள் அறிக்கைகள் மருத்துவர் திரைக்கு அனுப்பப்பட்டன. "
                "தயவுசெய்து காத்திருங்கள்."
            ),
            "te": (
                f"నమస్కారం {name}. మీ ఆరోగ్య వివరాలు విజయవంతంగా నమోదు చేయబడ్డాయి. "
                "మీ నివేదికలు వైద్యుని స్క్రీన్‌కు పంపించబడ్డాయి. "
                "దయచేసి వేచి ఉండండి."
            ),
            "en": (
                f"Hello {name}. Your clinical history and prior lab reports have been "
                "successfully recorded and sent to the doctor's consultation screen. "
                "Please wait for your token number to be called."
            )
        }
        return audio_map.get(lang, audio_map["en"])


summary_generator = SummaryGenerator()
