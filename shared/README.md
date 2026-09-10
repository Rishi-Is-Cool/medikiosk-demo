# shared/

Three files both frontends read. Changing any of them changes both apps, which
is the point — there is no second copy to keep in step.

## `tokens.css` — colour, type, spacing

The ten roles from `MediKiosk_Colour_Scheme.docx` turned into real values, plus
what a dense dashboard needs that a kiosk does not (borders, sunken surfaces,
provenance chips, the Dashavidha grading scale).

Import once at the root of each app, then set the density on `<html>`:

```html
<html data-density="kiosk">      <!-- patient kiosk -->
<html data-density="dashboard">  <!-- doctor console -->
```

Colour, type family and alert language are **shared**. Only scale is forked —
kiosk gets 20–24px text and 56px touch targets, the console gets 14–16px and
32px. Nothing else should differ.

Three rules worth keeping:

1. **Exactly three alert severities** — critical, warning, info. A fourth means
   nobody trusts the first three.
2. **The four provenance chips are identical in both apps.** `.mk-chip-src` is
   in this file; use it rather than rolling your own.
3. **Every contrast pair passes WCAG AA.** All 40 foreground/background
   combinations the UI renders were checked; eight failed and were corrected.
   If you change a value, re-check it — muted text on a washed-out hospital
   monitor is the case that fails first.

## `snapshot-contract.json` — the API shape

The response the doctor console builds against, populated with the demo patient
so it doubles as a fixture.

**One rule matters:** no clinical value is ever a bare string. Every one is an
object carrying `source`, `status` and `fact_id`. A bare string is a fact with
no provenance, and provenance is the differentiator.

Backend needs three columns for this to work:

- `facts.source_type` — `patient_spoken | document | prior_encounter | clinician`
- `facts.status` — `ai_extracted | doctor_edited | doctor_confirmed`
- `encounters.intake_framework` — `allopathic | ayush`

Note the snapshot is **viewer-dependent**: the Ayurvedic block is suppressed
server-side based on the requesting doctor's practitioner type, so any cache
must key on doctor as well as encounter.

## `terminology.json` — NAMASTE, ICD-11 TM2, WHO-SAT codes

Real codes for the diagnoses and frameworks used in the demo. Dual-coded rows
in the source read `TM2CODE (NAMC_CODE)` — e.g. Madhumeha is NAMASTE `EF-2.4.4`
with TM2 `SP60`.

**Read the flagged entries before quoting anything at AIIA.** Two are
deliberately not answered:

- **Hypertension** has no clean NAMASTE-to-TM2 mapping. The nearest concept is
  related but not equivalent, so it carries the biomedicine code alone.
- **Sara and Sattva** as Dashavidha axes are homonyms of unrelated concepts in
  the terminology list. Left uncoded on purpose — a wrong code in front of an
  Ayurveda panel is worse than no code.

Provenance is a public mirror, not the official portal. Verify against
namaste.ayush.gov.in before any demonstration.
