# MediKiosk

**Smart India Hackathon 2026 — SIH26047, for the All India Institute of Ayurveda (AIIA).**

An AI-assisted clinical intake system for high-volume Indian hospital OPDs: a
patient answers questions on a kiosk (by voice or touch, in their own
language) and uploads their old prescriptions from their phone — all before
they ever see the doctor. The doctor opens a patient and finds a structured,
source-linked snapshot already waiting: chief complaint, history, prior
documents, lab values, red flags, and — for Ayurveda encounters — a full
Dashavidha Pariksha assessment. Nothing is auto-confirmed; every AI-drafted
field is something the doctor accepts, edits, or rejects.

This repo is the integrated build: patient kiosk, doctor console, hospital
admin dashboard, and the FastAPI backend that ties them together, all in one
tree so the whole loop can be run and demoed from a single checkout.

---

## What's in the system

**Patient kiosk** (`frontend-kiosk/`) — language select (English, Hindi,
Marathi, with Bengali/Tamil/Telugu voices already wired for when those
languages ship); new-patient registration or returning-patient lookup by
ABHA/Aadhaar; department selection (General Medicine / Ayurveda); multi-select
chief complaints (one spoken sentence can tick several); an adaptive
AI-driven interview — SOCRATES for a general complaint, the fuller Dashavidha
Pariksha for an Ayurveda encounter — that shares questions across complaints
instead of asking twice; a QR code the patient scans with their own phone to
upload old prescriptions and lab reports (JPEG/PNG/WEBP/HEIC/PDF); an OPD
token with live queue position; and read-aloud in a real Indian-accented
voice (English/Hindi/Marathi), not whatever generic voice the browser
happens to ship.

**Doctor console** (`frontend-doctor/`) — specialty-locked login (a doctor
signs up once as General Medicine or Ayurveda and only ever sees that
queue); the day's patients with red-flag priority surfaced separately; an
encounter view built around a single ten-second read (chief complaint,
conditions, medications, allergies) with history, the patient's visit
timeline, and — for AYUSH encounters — Dashavidha Pariksha underneath;
medicine prescribing from a specialty-scoped catalog with saveable
templates; an advice library (diet/lifestyle guidance, shown as
"Pathya/Apathya" for Ayurveda doctors and in plain language for General
Medicine); click-to-speak for the finalize note; a printable, QR-bearing
patient summary in the patient's own language; and an Evidence panel that
lets a doctor click any AI-sourced claim to see exactly which line of which
uploaded document it came from — including the original scanned image
itself, not just the OCR transcription. The Clinical Accountability Ledger
(deviation reason + doctor's own rationale, whenever treatment changes) has
no AI in it anywhere, by design — it exists specifically to be
doctor-authored.

**Hospital admin / reception** (`frontend-doctor/src/screens/admin/`) — a
separate five-tab view for a reception/admin account, not tied to any one
doctor's specialty: **Home** (a dashboard — stats, a 7-day patients-seen
chart, queue-by-specialty split, red flags); **Rooms** (every doctor as a
card, grouped by specialty, showing who they're currently with); **Waiting
Room** (every waiting patient hospital-wide, flattened and sorted by wait
time); **Patients** (the full hospital directory with search); **Settings**
(dashboard refresh interval). This is the one place in the system that
crosses specialties and doctors — everywhere else, a General Medicine
account can never see an Ayurveda patient's chart or vice versa.

**Backend** (`backend/`, FastAPI + PostgreSQL) — the adaptive interview
engine; a vision pipeline (Gemini) that extracts diagnoses, medications, and
lab values from an uploaded document image and tags each one with exactly
which line of the document it came from; `faster-whisper` for voice-answer
transcription; `edge-tts` for the Indian-voice read-aloud; least-busy-doctor
patient routing scoped to specialty; the OPD token sequence; the Clinical
Accountability Ledger; and the admin endpoints the Hospital Overview screens
read from. `ai/` and `ml_backend/` sit alongside it as the document-intelligence
library backend imports rather than calls over the network.

---

## Architecture

```
                    ┌─────────────────────┐        ┌──────────────────────┐
                    │   Patient's phone    │        │   frontend-kiosk     │
                    │ (QR document upload) │◄──────►│   (Next.js)          │
                    └───────────┬───────────┘        └──────────┬───────────┘
                                │                                │
                                └────────────────┬───────────────┘
                                                  ▼
                                       ┌─────────────────────┐
                                       │      backend/        │
                                       │  FastAPI + Postgres   │
                                       │                       │
                                       │  adaptive interview   │
                                       │  vision pipeline ─────┼──► ai/ + ml_backend/
                                       │  (Gemini OCR)         │    (imported directly,
                                       │  faster-whisper STT   │     not a separate service)
                                       │  edge-tts (Indian     │
                                       │    voices, EN/HI/MR)  │
                                       │  doctor + patient     │
                                       │    routing, ledger    │
                                       └──────────┬────────────┘
                                                  │ /api
                        ┌─────────────────────────┼─────────────────────────┐
                        ▼                                                   ▼
              ┌──────────────────┐                              ┌──────────────────────┐
              │  frontend-doctor  │                              │  frontend-doctor      │
              │  doctor console   │                              │  hospital admin panel │
              │  (React + Vite)   │                              │  (same app, admin     │
              │                   │                              │   role → 5 tabs)      │
              └───────────────────┘                              └───────────────────────┘
```

`shared/` holds the three files (`tokens.css`, and two more) both frontends
read, so a color or spacing change is made once, not twice.

---

## Repository layout

```
medikiosk-integration/
├── backend/            FastAPI app — the only service that talks to Postgres
│   ├── app/
│   │   ├── api/          route modules (integration.py is the kiosk+doctor+admin core)
│   │   ├── ai/            thin adapters into ai/ and ml_backend/
│   │   ├── database/      SQLAlchemy models, seed data, migrations helper
│   │   ├── services/      routing, ledger, timeline, fact-provenance logic
│   │   └── utils/         auth, identity hashing
│   ├── tests/            pytest — 139 tests, hermetic (own SQLite DB, no live keys)
│   └── README.md
├── frontend-doctor/    Doctor console + Hospital Admin panel (React + Vite)
│   ├── src/screens/       Home, Queue, Encounter, Patients, Settings…
│   ├── src/screens/admin/ AdminHome, AdminRooms, AdminWaitingRoom, AdminPatients, AdminSettings
│   └── README.md
├── frontend-kiosk/     Patient kiosk (Next.js)
│   └── README.md
├── ai/                  Interview engine, extraction schemas shared across the backend
│   └── README.md
├── ml_backend/          Document-intelligence library (vision extraction, lab
│   │                     validation, snapshot synthesis) — imported by backend/,
│   │                     not run as its own service in the integrated system
│   └── README.md
├── shared/              tokens.css + two more files both frontends read
│   └── README.md
├── DEMO_PATIENTS.md     20 fictional demo patients (real-shaped data, fake IDs)
└── requirements.txt      ai/ML module dependencies (backend/ has its own)
```

Each directory's own README has the real depth — this file is the map.

---

## Getting started

### Prerequisites
- Python 3.11+ and a virtualenv tool
- Node.js 18+
- A PostgreSQL database (or leave `DATABASE_URL` unset for a local SQLite
  file — fine for a demo, not for anything real)

### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
```

Create `backend/.env` (this is the one that matters — it's resolved by an
absolute path anchored to `backend/` regardless of where you launch uvicorn
from):

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=some-long-random-value
GEMINI_API_KEY=your-gemini-key          # optional — falls back to a deterministic mock without one
WHISPER_MODEL=base
```

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

On first run this seeds: a demo General Medicine doctor
(`doctor_opd_101` / `doc@MediK2026`), a demo Ayurveda doctor
(`vaidya_opd_201` / `vaidya@MediK2026`, only if no Ayurveda doctor exists
yet), an admin/reception account (`reception_admin_01` /
`admin@MediK2026`), the advice library, and a starter medicine catalog per
specialty. Seed 20 realistic demo patients (fake IDs, real-shaped history)
separately with:

```bash
python -m app.database.demo_patients
```

### 2. Doctor console + Hospital Admin panel

```bash
cd frontend-doctor
npm install
echo VITE_USE_MOCKS=0 > .env
npm run dev
```

Opens on **http://localhost:5174** (Vite proxies `/api` to `localhost:8000`).
Log in as a doctor account for the clinic view, or the admin account above
for the Hospital Overview dashboard — same login screen, the app branches on
the account's role.

### 3. Patient kiosk

```bash
cd frontend-kiosk
npm install
```

Create `frontend-kiosk/.env.local`:

```env
NEXT_PUBLIC_USE_MOCKS=false
NEXT_PUBLIC_API_BASE_URL=/backend
KIOSK_BACKEND_ORIGIN=http://127.0.0.1:8000
```

```bash
npm run dev
```

Opens on **http://localhost:3000** — the kiosk proxies `/backend/*` to the
FastAPI server itself, which is also how the patient's phone reaches the API
through the kiosk's own address after scanning the upload QR.

### Running the whole loop together

All three (`uvicorn`, `frontend-doctor`, `frontend-kiosk`) need to be running
at once to see a patient go from kiosk intake to a doctor's snapshot to the
hospital admin dashboard. `.claude/launch.json` at the parent project root
has preview configs for exactly this if you're using Claude Code.

---

## Tests

```bash
cd backend
pytest tests/ -q
```

139 tests, none of which touch a live network or the real database — a
fresh SQLite file per test session, `GEMINI_API_KEY`/`VISION_LLM_API_KEY`
blanked before the app is even imported, and TTS/vision calls that would hit
a real external service are mocked at the test layer.

---

## Tech stack

| Layer | Stack |
|---|---|
| Patient kiosk | Next.js, TypeScript |
| Doctor console + admin panel | React, Vite (no router, no component library, two runtime dependencies) |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| AI / document intelligence | Gemini (vision extraction), faster-whisper (speech-to-text), edge-tts (Indian-voice speech synthesis) |
| Auth | JWT (python-jose), bcrypt |

---

## Known gaps

Being upfront about what's demo-shaped rather than production-shaped:

- **No schema migration tool.** `Base.metadata.create_all()` only creates
  tables that don't exist yet — it never alters an existing table. A new or
  renamed column needs a manual `ALTER TABLE` against the real database.
- **"Currently with a patient" (Rooms tab) is a heuristic**, not a real
  event — there's no explicit consultation-start/end action anywhere in the
  system. It's inferred from the most recently opened chart, within a short
  window. Documented as exactly that in the code.
- **FHIR/ABDM export is a stub for demo purposes** (mock consent, mock HIS
  push) — the shape is real HL7 FHIR R4, the plumbing behind it isn't wired
  to a real ABDM sandbox.
- **`ml_backend/` also has its own standalone-service mode** (see its
  README) left over from before integration; the real system only ever runs
  it as a library import from `backend/`, never as a second process.
- **edge-tts is an unofficial, unauthenticated API** (it's what Microsoft
  Edge's browser uses internally) — free and reliable in practice, but not
  something with an SLA. Synthesis failures fall back to the browser's own
  `speechSynthesis`, which is how the app behaved before this was wired up.
