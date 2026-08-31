/* C3 — the persistent patient rail from Docon's clinic shell (S2).

   In Docon this list never leaves the screen: you move between patients
   without going back to a queue. That guarantee is worth keeping even though
   the density is not — a doctor mid-clinic should never navigate away to
   reach the next person.

   Priority patients stay pinned at the top, for the same reason the queue
   uses a band rather than a sort: a re-order is easy to miss. */

import { useMemo, useState } from "react";

const STATE_TONE = {
  ready: "ready",
  documents_processing: "part",
  intake_in_progress: "part",
  not_started: "none",
};

export default function PatientRail({ patients, activeId, onSelect, collapsed, onToggle }) {
  const [q, setQ] = useState("");

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const match = (p) =>
      !needle ||
      p.name.toLowerCase().includes(needle) ||
      p.token.toLowerCase().includes(needle) ||
      (p.complaint ?? "").toLowerCase().includes(needle);
    const list = patients.filter(match);
    return [...list].sort((a, b) => Number(!!b.priority) - Number(!!a.priority));
  }, [patients, q]);

  if (collapsed) {
    return (
      <div className="rail rail-collapsed">
        <button type="button" className="rail-toggle" onClick={onToggle} aria-label="Show patient list" title="Show patient list">
          ›
        </button>
        {shown.slice(0, 12).map((p) => (
          <button
            key={p.encounter_id}
            type="button"
            className={`rail-mini ${p.encounter_id === activeId ? "on" : ""} ${p.priority ? "p" : ""}`}
            onClick={() => onSelect(p.encounter_id)}
            title={`${p.token} · ${p.name}`}
          >
            {p.token.replace(/^A-/, "")}
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="rail">
      <div className="rail-head">
        <input
          className="rail-search"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name, token or complaint"
          aria-label="Search patients"
        />
        <button type="button" className="rail-toggle" onClick={onToggle} aria-label="Collapse patient list" title="Collapse">
          ‹
        </button>
      </div>

      <div className="rail-list">
        {!shown.length ? <p className="rail-empty">No patient matches “{q}”.</p> : null}
        {shown.map((p) => (
          <button
            key={p.encounter_id}
            type="button"
            className={`rail-row ${p.encounter_id === activeId ? "on" : ""} ${p.priority ? "p" : ""}`}
            aria-current={p.encounter_id === activeId ? "true" : undefined}
            onClick={() => onSelect(p.encounter_id)}
            disabled={p.intake_state === "not_started"}
          >
            <span className="rail-tok mk-num">{p.token}</span>
            <span className="rail-body">
              <span className="rail-name">{p.name}</span>
              <span className="rail-meta">
                {p.age_years} y · {p.sex === "female" ? "F" : "M"}
              </span>
              <span className="rail-complaint">{p.complaint ?? "Intake not started"}</span>
              {p.priority_reason ? <span className="rail-flag">{p.priority_reason}</span> : null}
            </span>
            <span className={`rail-dot ${STATE_TONE[p.intake_state] ?? "none"}`} aria-hidden="true" />
          </button>
        ))}
      </div>
    </div>
  );
}
