/* Provenance chip.

   tokens.css owns this primitive (.mk-chip-src) and says the four sources
   "MUST be identical in both apps" — the kiosk shows the patient what it
   captured, the doctor's console shows where it came from. So this component
   only ever emits those four values and reuses the shared class rather than
   restyling it.

   Touch and typed answers deliberately carry no chip: they are the patient's
   own words with nothing interpreted in between, and labelling them MIC would
   be wrong. */

export type ChipSource = "patient_spoken" | "document" | "prior_encounter" | "clinician";

const LABELS: Record<ChipSource, string> = {
  patient_spoken: "MIC",
  document: "DOC",
  prior_encounter: "HX",
  clinician: "MD",
};

const TITLES: Record<ChipSource, string> = {
  patient_spoken: "Stated by the patient, not yet verified",
  document: "Extracted from an uploaded record",
  prior_encounter: "Carried from a previous visit",
  clinician: "Entered by a clinician",
};

export function SourceChip({ source }: { source: ChipSource }) {
  return (
    <span className="mk-chip-src" data-src={source} title={TITLES[source]}>
      {LABELS[source]}
    </span>
  );
}
