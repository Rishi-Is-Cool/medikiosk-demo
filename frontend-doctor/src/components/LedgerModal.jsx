/* The Clinical Accountability Ledger. No AI anywhere in this component by
   design — the rationale is always doctor-authored, never generated. That is
   the whole point of the differentiator, and it is enforced here by there
   being no model call to make.

   Deviation reasons are frequency-ranked (Docon #05): the ones actually used
   sit above the divider so the common case is one click. */

import { useEffect, useRef, useState } from "react";
import { DEVIATION_REASONS } from "../api/mock.js";
import VoiceInput from "./VoiceInput.jsx";

export default function LedgerModal({ patientName, onCancel, onSave, saving }) {
  const [treatmentChanged, setTreatmentChanged] = useState(true);
  const [reason, setReason] = useState("");
  const [rationale, setRationale] = useState("");
  const [notes, setNotes] = useState("");
  const [followUp, setFollowUp] = useState(true);
  const [timeframe, setTimeframe] = useState("7 days");
  const [error, setError] = useState("");
  const firstField = useRef(null);

  useEffect(() => {
    firstField.current?.focus();
    const onKey = (e) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  function submit(e) {
    e.preventDefault();
    if (treatmentChanged && !reason) {
      setError("Select a deviation reason before confirming.");
      return;
    }
    if (treatmentChanged && !rationale.trim()) {
      setError("A short rationale is required when treatment changes.");
      return;
    }
    setError("");
    onSave({
      treatment_change: treatmentChanged,
      deviation_reason: treatmentChanged ? reason : null,
      doctor_rationale: treatmentChanged ? rationale.trim() : null,
      notes: notes.trim() || null,
      follow_up_required: followUp,
      follow_up_timeframe: followUp ? timeframe : null,
      doctor_confirmed: true,
    });
  }

  return (
    <div className="scrim" role="presentation">
      <form
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="ledger-h"
        onSubmit={submit}
      >
        <h2 id="ledger-h">Finalise encounter — {patientName}</h2>
        <p className="modal-sub">
          Treatment differs from the previous plan. Documenting why is what makes this record
          auditable; nothing on this form is generated.
        </p>

        <fieldset className="fs">
          <legend>Treatment</legend>
          <label className="check">
            <input
              ref={firstField}
              type="checkbox"
              checked={treatmentChanged}
              onChange={(e) => {
                setTreatmentChanged(e.target.checked);
                setError("");
              }}
            />
            Treatment changed from the previous plan
          </label>
        </fieldset>

        {treatmentChanged ? (
          <>
            <fieldset className="fs">
              <legend>Deviation reason</legend>
              <div className="reasons">
                {DEVIATION_REASONS.map((r, i) => (
                  <label key={r} className={`reason ${i === 3 ? "after-common" : ""}`}>
                    <input
                      type="radio"
                      name="reason"
                      value={r}
                      checked={reason === r}
                      onChange={() => {
                        setReason(r);
                        setError("");
                      }}
                    />
                    {r}
                  </label>
                ))}
              </div>
            </fieldset>

            <fieldset className="fs">
              <legend>
                Rationale <span className="req">required</span>
              </legend>
              <textarea
                rows={3}
                value={rationale}
                placeholder="Metformin alone no longer controlling HbA1c; adding second agent."
                onChange={(e) => {
                  setRationale(e.target.value);
                  setError("");
                }}
              />
            </fieldset>
          </>
        ) : null}

        <fieldset className="fs">
          <legend>Note for the patient summary</legend>
          <textarea
            rows={2}
            value={notes}
            placeholder="Anything the printed sheet should say in your own words — optional."
            onChange={(e) => setNotes(e.target.value)}
          />
          <VoiceInput onInsert={(text) => setNotes((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text))} />
        </fieldset>

        <fieldset className="fs">
          <legend>Follow-up</legend>
          <label className="check">
            <input
              type="checkbox"
              checked={followUp}
              onChange={(e) => setFollowUp(e.target.checked)}
            />
            Requires follow-up
          </label>
          {followUp ? (
            <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
              {["3 days", "7 days", "2 weeks", "1 month", "3 months"].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          ) : null}
        </fieldset>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        {/* Nothing destructive sits next to the confirm action — Docon puts
            Delete directly beneath Print Preview and it is a trap. */}
        <div className="modal-actions">
          <button type="button" className="btn" onClick={onCancel}>
            Back
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Saving…" : "Confirm and finalise"}
          </button>
        </div>
      </form>
    </div>
  );
}
