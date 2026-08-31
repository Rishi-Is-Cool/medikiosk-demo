/* The provenance affordance. Four kinds, deliberately — the difference between
   what a patient said and what a document proves is the subjective/objective
   split clinicians already think in, and it costs nothing to render.
   Styling lives in shared/tokens.css as .mk-chip-src so the kiosk renders
   these identically. */

const LABEL = {
  patient_spoken: "MIC",
  document: "DOC",
  prior_encounter: "HX",
  clinician: "MD",
};

const TITLE = {
  patient_spoken: "Patient stated at the kiosk — unverified",
  document: "Extracted from an uploaded record — click to view source",
  prior_encounter: "Carried from a previous encounter",
  clinician: "Entered or edited by a clinician",
};

export default function SourceChip({ source, onOpen }) {
  if (!source) return null;
  const clickable = typeof onOpen === "function";

  return (
    <button
      type="button"
      className="mk-chip-src chip-btn"
      data-src={source.type}
      title={TITLE[source.type] ?? source.type}
      aria-label={TITLE[source.type] ?? source.type}
      disabled={!clickable}
      onClick={clickable ? () => onOpen(source) : undefined}
    >
      {LABEL[source.type] ?? "?"}
    </button>
  );
}
