# MediKiosk — patient kiosk frontend

The patient-facing half of MediKiosk: the screen a patient walks up to in an OPD
foyer, answers questions on by speaking or tapping, and sends their old
prescriptions to from their own phone — all before they see the doctor.

Built against `MediKiosk_Frontend_Master_Build_Specification.docx`. Section
references in the code (`build spec §6.7`) point at that document.

## Run it

```bash
npm install && npm run dev
```

Open <http://localhost:3000>. No backend, no API keys, no database — the whole
journey runs on mocks out of the box.

## What this app is, and is not

It owns the patient UI: touch and voice interaction, language switching,
browser microphone capture, and the QR-to-phone upload page.

It owns none of the intelligence. There is no Whisper call, no LLM prompt, no
clinical reasoning, no red-flag rule and no ABHA verification anywhere in this
codebase, and there must not be. Every one of those sits behind the API layer
so the same UI works against mocks today and the team's real services later.

Concretely, the frontend never decides that a symptom is urgent. It asks, and
renders the `priority` state it is handed.

## How the boundary is drawn

```
src/api/         the only place that talks to a backend
  config.ts        every endpoint + the USE_MOCKS switch (nothing else has URLs)
  patientApi       registration, session, consent
  intakeApi        start intake, get question, extract answer, submit answer
  speechApi        audio → transcript, text → audio
  documentApi      upload sessions and document status

src/mocks/       ⚠ stand-ins for services that do not exist yet
  questions.ts       question order, branching AND the placeholder red-flag rules
  transcripts.ts     canned ASR output
  extraction.ts      canned clinical structuring
  patients.ts        fake identity — verifies nothing
  uploadSessionStore.ts  in-memory document service (server-side)
```

Everything in `src/mocks/` is marked `⚠ INTEGRATION POINT` and is meant to be
deleted. Swapping in the real backend is: fill in `ENDPOINTS`, set
`NEXT_PUBLIC_USE_MOCKS=false`, delete the mock. No screen or component changes.

The placeholder question order in `mocks/questions.ts` follows SOCRATES for
pain and a conventional fever/cough line. **It is a demo script, not a clinical
protocol, and the clinical members of the team should review it before it is
shown to a real patient.**

## Screens

`/` start · `/language` · `/register` · `/consent` · `/mode` · `/complaint` ·
`/intake` · `/priority` · `/documents` · `/complete`, plus `/upload/[token]` —
the page the QR opens on the patient's phone, deliberately outside the kiosk
session so that device can never read it.

`src/screens/` holds the screens; the files under `src/app/` are thin routes.

## Two intake frameworks

`history_mode` is chosen on `/mode` and travels to the question service. The
kiosk does not know what either framework contains.

- **General Medicine** — SOCRATES for pain, a conventional fever/cough line,
  then the shared history tail. Around 10 questions.
- **AYUSH** — the same complaint line, plus Dashavidha Pariksha and
  Ahara-Vihara, then the same tail. Around 31.

Because the AYUSH interview is three times longer, the engine also sends a
**section** with each question, and the UI leads with it: "Part 4 of 6 · Your
strength and digestion". A bar crawling from 16/31 tells a patient nothing;
the part name tells them where they are.

### What the kiosk does and does not capture for Dashavidha

`shared/snapshot-contract.json` fixes how the doctor console *receives* the
ten axes — Prakriti as vata/pitta/kapha proportions, six axes as a
pravara / madhyama / avara grade. **The kiosk does not produce those.** A
patient cannot self-report "Sara: pravara"; that is a practitioner's
synthesis. `mocks/ayushQuestions.ts` asks the patient-answerable proxy
underneath each axis — what their hair and skin are like, how much they can
eat, whether they tire quickly — and the raw answers go out through
`intakeApi` like any other answer. Converting them to doshas and grades is
AI/backend work, the same boundary the kiosk keeps for red-flag priority.

**Ahara-Vihara has no agreed contract anywhere in the project** — not in
`ai/intake/schemas.py`, not in the shared snapshot, not in the doctor
console. The questions here capture what the classical assessment covers, but
the shape they should be delivered in still has to be agreed.

⚠ **The AYUSH question set has not been reviewed by an Ayurveda
practitioner.** A real Prakriti questionnaire runs to twenty or forty items;
this is six. Treat it as a demo script until someone qualified has read it.

### Scale direction is part of the contract

A `scale` question carries `scale_tone`, and it matters: `severity` climbs
toward alarm (mild → worst pain) and gets the warning ramp; `grade` climbs
toward *optimum* (avara → pravara) and gets a neutral one. Running the
severity ramp over a grading axis paints "strong and glossy hair" red and
tells a patient their own constitution is an emergency.

## Design tokens

`src/styles/tokens.css` is a **verbatim copy** of `About/tokens.css`. Do not
edit it here — change the shared file and re-copy, so the kiosk and the doctor
console cannot drift:

```bash
cp ../About/tokens.css src/styles/tokens.css
```

Its rule holds everywhere: **no component hardcodes a colour.** A hex value
outside `tokens.css` is a bug. Stylesheets load in one order —
`tokens.css` → `base.css` → `components.css` — set in `app/globals.css`.

Density is set once, on `<html data-density="kiosk">`: 20px base text, 56px
minimum tap targets. The kiosk stays light; the dark token set exists for the
doctor console.

## Accessibility, and why some things look the way they do

- Every question is answerable by speaking **or** tapping. Neither is a fallback.
- Single-choice questions commit on tap — no answer-then-confirm double step.
- Multi-select waits for an explicit Next, because nothing else can tell when
  the patient is finished.
- The touch list collapses while a spoken answer is being confirmed, so the
  transcript and its confirm buttons fit on a 768px panel without scrolling.
- The action bar is sticky. A primary action a patient cannot see is a trap.
- Three languages are enabled (English, Hindi, Marathi) across both the UI and
  every question. Bengali, Tamil and Telugu appear **disabled** rather than
  silently rendering English — a patient who cannot read English would have no
  way back, so a half-translated language is worse than an honest "coming
  soon". Adding one is a dictionary file in `src/i18n/dictionaries`, the `mr`
  keys in the two question banks, and `translated: true` in
  `src/i18n/languages.ts`.
- Language is changeable from any screen, and the current question is re-fetched
  in the new language rather than left behind.
- An abandoned session clears itself. After two minutes of silence on any
  screen the kiosk asks "are you still there?", then resets after twenty
  seconds. Two screens are exempt: the start screen (nothing to abandon) and
  the priority screen — that one told the patient to sit still and wait for
  staff, and timing out on a patient who did as they were asked would erase an
  urgent hand-off.

## The QR upload flow

The kiosk creates a short-lived upload session and shows a QR. The patient's
phone opens `/upload/<token>`, photographs their documents, and posts them; the
kiosk polls and updates. The token is opaque and carries no patient or medical
information.

**On a dev machine the QR will not work until you make the server reachable from
the phone** — `localhost` means the phone, not the kiosk:

```bash
npm run dev -- -H 0.0.0.0
```

and set `NEXT_PUBLIC_KIOSK_PUBLIC_ORIGIN` to your LAN address (see
`.env.local.example`). In development the documents screen also prints a
`dev: open the phone page` link so the flow can be demoed in a second tab.

The mock document service records filename, size and status and **discards the
bytes on purpose** — real documents belong in object storage with metadata in
PostgreSQL, and holding images in a Node process would model that wrongly.

## Testing the states that are hard to reach

- `NEXT_PUBLIC_MOCK_SPEECH_FAILS=true` — forces the speech error and
  "Type instead" path.
- Deny the microphone in the browser — the mic-unavailable state.
- Chest pain → "To the left arm or shoulder" → the urgent priority screen.
- Fever → "Difficulty breathing" → the staff-assistance priority screen.
- Fever → "Yes, with phlegm" — watch the estimated total move from 8 to 9. The
  interview branches, so the total is an estimate and the UI treats it as one.
- Ayurveda → any complaint → a 31-question interview across six named parts.
- Stop touching the screen for two minutes — the abandonment warning.
- ABHA or Aadhaar → "Scan my card" — fills the field from a photo, then asks
  the patient to check it.

## Known gaps

- **No automated tests.** Verified by walking the journey in a browser.
- **No ESLint config** — scaffolded with `--no-eslint`; `next lint` is removed
  in Next 16, so add the ESLint CLI directly if the team wants it.
- **Going back during the interview restarts the complaint.** Rewinding an
  adaptive interview one question at a time needs a backend contract that does
  not exist yet; the screen asks for confirmation rather than dropping answers
  silently.
- **The AYUSH question set is unreviewed** — see above. The Ahara-Vihara
  section has no agreed output contract at all.
- **Bengali, Tamil and Telugu are untranslated** and shown disabled.
- **No screen-reader, keyboard-only, real-touchscreen or cross-browser
  testing.** Safari/iOS in particular has different `MediaRecorder` codec
  support that the fallback logic has never actually run against.
- **No custom favicon** — still the Next.js default.
- Consent is captured and transmitted, but consent *compliance* (DPDP 2023,
  the ABDM consent framework) lives in the backend's consent artefact and audit
  trail. Nothing here should be described as compliant.
- `src/styles/tokens.css` duplicates `shared/tokens.css` on the
  `feat/doctor-console` branch. Identical today; should be reconciled into one
  shared file before the branches merge.
