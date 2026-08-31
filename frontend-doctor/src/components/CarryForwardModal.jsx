/* Docon #07 — follow-up carry-forward.
   The teardown calls this the highest-value flow in the app for a repeat-visit
   Ayush OPD, and it is the clearest possible demonstration of what
   "longitudinal patient memory" actually buys a doctor: last visit's work,
   offered for reuse, in one dialog.

   Each row shows its current value — Docon's version does this and it is the
   part that matters. A checkbox labelled only "Medicines" makes you open the
   record to find out what you are agreeing to. */

import { useEffect, useState } from "react";

export default function CarryForwardModal({ data, onCancel, onApply }) {
  const [picked, setPicked] = useState(() => new Set(data.groups.map((g) => g.key)));
  const [error, setError] = useState("");

  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  function toggle(key) {
    setPicked((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
    setError("");
  }

  function submit(e) {
    e.preventDefault();
    if (picked.size === 0) {
      setError("Select at least one item to carry forward.");
      return;
    }
    onApply(data.groups.filter((g) => picked.has(g.key)));
  }

  return (
    <div className="scrim" role="presentation">
      <form className="modal" role="dialog" aria-modal="true" aria-labelledby="cf-h" onSubmit={submit}>
        <h2 id="cf-h">Carry forward from {data.from_date}</h2>
        <p className="modal-sub">
          Select what to bring into today's encounter. Everything carried forward stays editable and
          is marked as coming from the previous visit.
        </p>

        <div className="cf-list">
          {data.groups.map((g) => (
            <label className="cf-row" key={g.key}>
              <input type="checkbox" checked={picked.has(g.key)} onChange={() => toggle(g.key)} />
              <span className="cf-body">
                <span className="cf-label">{g.label}</span>
                <span className="cf-value">{g.value}</span>
              </span>
            </label>
          ))}
        </div>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary">
            Carry forward {picked.size} {picked.size === 1 ? "item" : "items"}
          </button>
        </div>
      </form>
    </div>
  );
}
