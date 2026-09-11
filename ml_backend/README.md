# MediKiosk — AI/ML Document Intelligence & Clinical Synthesis Backend

AI-assisted clinical document perception, terminology normalization, deterministic validation, timeline construction, and physician snapshot synthesis for high-volume Indian hospital OPD kiosks (**Smart India Hackathon 2026**).

> **Note:** this document describes `ml_backend/` as it was originally built — a
> standalone FastAPI service with its own `/ml/*` routes. In the integrated
> system (see the [project root README](../README.md)), `ml_backend` is
> imported as a library by `backend/` (`app/ai/vision_pipeline.py` calls
> `ml_backend.services.vision_extract` directly) rather than run as its own
> process — the `uvicorn ml_backend.app:app` instructions below still work
> for developing this module in isolation, just not as part of the real
> kiosk → backend → doctor console loop, which only ever runs `backend/`.

---

## Architecture Overview

```
MEDICAL DOCUMENT (Prescription / Lab / Discharge Summary)
       │
       ▼
VISION LLM API (Gemini / OpenAI / Deterministic Mock)
       │
       ▼
DOCUMENT CLASSIFICATION & STRUCTURED EXTRACTION
       │
       ├─────────────────────────┬─────────────────────────┐
       ▼                         ▼                         ▼
MEDICAL NORMALIZATION    LAB RANGE VALIDATOR      CONFLICT DETECTOR
(Raw + Canonical Term)   (Deterministic Rules)    (Current vs Past Data)
       └─────────────────────────┼─────────────────────────┘
                                 ▼
                     CHRONOLOGICAL TIMELINE
                                 ▼
                        PATIENT FACTS MEMORY
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
      PHYSICIAN SNAPSHOT SYNTHESIS       DOCTOR Q&A ASSISTANT
      (12 Structured Sections)           (5 Predefined Patterns + Sources)
                 └───────────────┬───────────────┘
                                 ▼
                      SOURCE-LINKED EVIDENCE
                 (Every claim links to DOC_ID)
```

---

## Key Features

1. **Vision LLM Integration with Provider Abstraction**:
   - Swappable providers (`gemini`, `openai`, `mock`) configured via environment variables.
   - Outputs strict, validated Pydantic JSON schemas.
2. **Medical Terminology Normalization Dictionary**:
   - 40+ common Indian OPD abbreviations (`DM` → `Diabetes Mellitus`, `HTN` / `high BP` → `Hypertension`, `pcm` → `Paracetamol`, `BD` → `Twice daily`, etc.).
   - **Crucial**: Never overwrites raw data; preserves both `raw_value` and `normalized_value`.
3. **Deterministic Lab Result Validator**:
   - Parses complex reference intervals (`<5.7%`, `70 - 99 mg/dL`, `>60 mL/min`, qualitative tests).
   - Python logic deterministically marks `abnormal: true / false / null`. Never guesses.
4. **Chronological Medical Timeline**:
   - Sorts past diagnoses, hospitalizations, investigations, and prescriptions.
   - Missing dates are safely preserved as `null` (never hallucinated).
5. **Clinical Conflict & Contradiction Detector**:
   - Flags discrepancies (e.g. Current intake: "No known allergies" vs Past records: "Penicillin allergy").
6. **Physician Clinical Snapshot Generator**:
   - Generates a concise 12-section summary with explicit source citations (`source_document_ids`).
7. **Doctor Q&A Engine**:
   - Structured retrieval + LLM synthesis answering clinical inquiries with citations.

---

## Project Structure

```
medikiosk/
├── ml_backend/
│   ├── app.py                      # FastAPI API server
│   ├── config.py                   # Environment & settings
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Example environment file
│   ├── services/
│   │   ├── llm_client.py           # LLM Provider abstraction & mock fallback
│   │   ├── vision_extract.py       # Vision extraction coordinator
│   │   ├── normalization.py        # Terminology normalization service
│   │   ├── lab_validator.py        # Deterministic lab range validation
│   │   ├── timeline.py             # Chronological timeline engine
│   │   ├── snapshot_generator.py   # Physician snapshot synthesis
│   │   ├── doctor_qa.py            # Doctor clinical inquiry engine
│   │   └── conflict_detector.py    # Discrepancy & alert detector
│   ├── schemas/
│   │   ├── document.py             # Document extraction schemas
│   │   ├── medical_fact.py         # Patient fact & normalization schemas
│   │   ├── timeline.py             # Timeline event schemas
│   │   ├── snapshot.py             # Clinical history & snapshot schemas
│   │   └── qa.py                   # Doctor Q&A schemas
│   ├── prompts/
│   │   ├── document_extraction.txt # Perception prompt template
│   │   ├── snapshot_generation.txt # Snapshot synthesis prompt template
│   │   └── doctor_qa.txt           # Q&A prompt template
│   ├── data/
│   │   ├── normalization_dictionary.json
│   │   ├── lab_reference_ranges.json
│   │   └── sample_outputs/
│   ├── sample_documents/
│   │   ├── prescription_01.jpg
│   │   ├── lab_report_01.jpg
│   │   └── discharge_summary_01.jpg
│   └── tests/
│       ├── test_normalization.py
│       ├── test_lab_validator.py
│       ├── test_timeline.py
│       ├── test_conflicts.py
│       ├── test_snapshot.py
│       ├── test_doctor_qa.py
│       ├── test_api_endpoints.py
│       └── test_end_to_end.py
└── test_document.py                # Root CLI test script & demo runner
```

---

## Quick Start

### 1. Configure Environment
```bash
cp ml_backend/.env.example ml_backend/.env
# Edit .env to set VISION_LLM_PROVIDER and API key (or leave empty for Mock provider)
```

### 2. Run Test Suite (All 29 Tests)
```bash
python3 -m unittest discover -s ml_backend/tests -p "test_*.py" -v
```

### 3. Run Demo Scenario via CLI
```bash
python3 test_document.py --demo
```

### 4. Test an Individual Document Image
```bash
python3 test_document.py --file ml_backend/sample_documents/prescription_01.jpg
python3 test_document.py --file ml_backend/sample_documents/lab_report_01.jpg
python3 test_document.py --file ml_backend/sample_documents/discharge_summary_01.jpg
```

### 5. Start the FastAPI Service
```bash
uvicorn ml_backend.app:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI documentation will be available at: `http://localhost:8000/docs`.

---

## API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health status and active LLM provider |
| `POST` | `/ml/documents/extract` | Extract structured entities & labs from image/PDF |
| `POST` | `/ml/documents/normalize` | Normalize raw medical abbreviations / terms |
| `POST` | `/ml/validate/labs` | Deterministic lab value validation against reference ranges |
| `POST` | `/ml/documents/timeline` | Aggregate and chronologically sort events |
| `POST` | `/ml/validate/conflicts` | Detect inconsistencies between current intake & past files |
| `POST` | `/ml/snapshot` | Generate 12-section physician snapshot with source citations |
| `POST` | `/ml/doctor/qa` | Evidence-based doctor Q&A with source references |
| `POST` | `/ml/pipeline/full` | End-to-end kiosk ingestion and synthesis pipeline |
