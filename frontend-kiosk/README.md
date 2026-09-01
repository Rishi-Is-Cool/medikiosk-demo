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
- Only two languages are enabled (English, Hindi). The other four appear
  disabled rather than silently rendering English — a patient who cannot read
  English would have no way back. Adding one is a dictionary file in
  `src/i18n/dictionaries` plus `translated: true` in `src/i18n/languages.ts`.
- Language is changeable from any screen, and the current question is re-fetched
  in the new language rather than left behind.

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

## Known gaps

- **No automated tests.** Verified by walking the journey in a browser.
- **No ESLint config** — scaffolded with `--no-eslint`; `next lint` is removed
  in Next 16, so add the ESLint CLI directly if the team wants it.
- **Going back during the interview restarts the complaint.** Rewinding an
  adaptive interview one question at a time needs a backend contract that does
  not exist yet; the screen asks for confirmation rather than dropping answers
  silently.
- **AYUSH is a disabled stub**, per the project plan. The question components
  are framework-agnostic, so a Dashavidha Pariksha set plugs in server-side.
- Consent is captured and transmitted, but consent *compliance* (DPDP 2023,
  the ABDM consent framework) lives in the backend's consent artefact and audit
  trail. Nothing here should be described as compliant.
