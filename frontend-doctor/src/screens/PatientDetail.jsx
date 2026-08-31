/* The patient page — everything about this person, across visits.

   Deliberately not the encounter screen. The encounter answers "what is
   happening today"; this answers "who is this and what has happened". Docon
   splits them the same way and it is the right split: a doctor opening a
   record between clinics wants history, not a live consultation surface. */

import { useEffect, useState } from "react";
import { fetchPatientRecord } from "../api/client.js";
import { initials, fmt } from "./Patients.jsx";
import PrintSheet from "../components/PrintSheet.jsx";

export default function PatientDetail({ patientId, onOpenEncounter, onBack }) {
  const [p, setP] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("history");
  const [printing, setPrinting] = useState(false);

  useEffect(() => {
    let alive = true;
    setP(null);
    setError("");
    fetchPatientRecord(patientId)
      .then((d) => alive && setP(d))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [patientId]);

  if (error) return <p className="screen-msg">Could not load this record — {error}</p>;
  if (!p) return <p className="screen-msg">Loading record…</p>;

  return (
    <div className="pd">
      <header className="pd-head">
        <span className="avatar avatar-lg" aria-hidden="true">{initials(p.name)}</span>
        <div className="pd-id">
          <h1>{p.name}</h1>
          <p className="pd-meta mk-num">
            {p.age_years} y · {p.sex === "female" ? "Female" : "Male"} · ABHA {p.abha_id}
          </p>
          <p className="pd-dept">
            <span className={`pill ${p.department === "Ayurveda" || p.department === "Panchakarma" ? "ayu" : ""}`}>
              {p.department}
            </span>
            <span className="pd-visits">{p.visits} {p.visits === 1 ? "visit" : "visits"} on file</span>
          </p>
        </div>
        <div className="pd-actions">
          {p.encounter_id ? (
            <button type="button" className="btn btn-primary" onClick={() => onOpenEncounter(p.encounter_id)}>
              Open today's encounter
            </button>
          ) : null}
          <button type="button" className="btn" onClick={() => setPrinting(true)}>
            Print patient sheet
          </button>
        </div>
      </header>

      {p.allergies.length ? (
        <div className="mk-alert alert-row" data-sev="critical" role="alert">
          <span className="sev">ALLERGY</span>
          <span className="alert-text">
            <strong>{p.allergies.join(", ")}</strong>
            <span className="alert-detail"> — check before prescribing</span>
          </span>
        </div>
      ) : null}

      <nav className="tabs" role="tablist">
        {[
          ["history", "History"],
          ["appointments", "Appointments"],
          ["conditions", "Conditions and allergies"],
        ].map(([k, label]) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            className={`tab ${tab === k ? "on" : ""}`}
            onClick={() => setTab(k)}
          >
            {label}
          </button>
        ))}
      </nav>

      <div className="pd-body">
        {tab === "history" ? (
          !p.timeline.length ? (
            <Empty
              title="No history recorded yet"
              body="Encounters and uploaded documents appear here as they are captured."
            />
          ) : (
            <ol className="tl">
              {p.timeline.map((e, i) => (
                <li key={i} className="tl-item" data-type={e.type}>
                  <span className="tl-date mk-num">{fmt(e.date)}</span>
                  <span className="tl-dot" aria-hidden="true" />
                  <span className="tl-body">
                    <span className="tl-title">{e.title}</span>
                    <span className="tl-detail">{e.detail}</span>
                    {e.by ? <span className="tl-by">{e.by}</span> : null}
                  </span>
                </li>
              ))}
            </ol>
          )
        ) : null}

        {tab === "appointments" ? (
          !p.appointments.length ? (
            <Empty title="No appointments" body="Follow-ups set at the end of an encounter appear here." />
          ) : (
            <div className="appts">
              {p.appointments.map((a, i) => (
                <div key={i} className="appt" data-status={a.status}>
                  <span className="appt-date mk-num">{fmt(a.date)}</span>
                  <span className="appt-reason">{a.reason}</span>
                  <span className={`pill ${a.status === "scheduled" ? "ready" : ""}`}>{a.status}</span>
                </div>
              ))}
            </div>
          )
        ) : null}

        {tab === "conditions" ? (
          <div className="cond-cols">
            <section>
              <h2 className="bandhead">Conditions</h2>
              {p.conditions.length ? (
                <ul className="plain">{p.conditions.map((c) => <li key={c}>{c}</li>)}</ul>
              ) : (
                <p className="dim">None recorded.</p>
              )}
            </section>
            <section>
              <h2 className="bandhead">Allergies</h2>
              {p.allergies.length ? (
                <ul className="plain danger">{p.allergies.map((c) => <li key={c}>{c}</li>)}</ul>
              ) : (
                <p className="dim">No known allergies recorded.</p>
              )}
            </section>
          </div>
        ) : null}
      </div>

      {printing ? <PrintSheet patient={p} onClose={() => setPrinting(false)} /> : null}
    </div>
  );
}

function Empty({ title, body }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      <p className="empty-body">{body}</p>
    </div>
  );
}
