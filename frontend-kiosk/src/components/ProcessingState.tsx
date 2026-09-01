"use client";

/** Never leave a patient looking at a frozen screen. Every wait says what is
 *  happening, in their language (build spec §14: clear current state). */
export function ProcessingState({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="mk-processing" role="status" aria-live="polite">
      <span className="mk-spinner" />
      <span className="mk-stack mk-stack--tight">
        <span className="mk-processing__label">{label}</span>
        {hint && <span className="mk-help">{hint}</span>}
      </span>
    </div>
  );
}
