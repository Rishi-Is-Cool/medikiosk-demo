/* Docon #16 — who is due back, as a report rather than a memory.
   Panchakarma and most classical protocols run for weeks, so adherence is the
   outcome that decides whether the treatment worked. Rows come from ledger
   follow-up entries, which closes the loop from the finalise form.

   Docon's version drives an SMS credit economy; the reachable channel here is
   the patient's own ABHA-linked record. */

import { useEffect, useState } from "react";
import { fetchDueBack } from "../api/client.js";

export default function DueBack() {
  const [rows, setRows] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchDueBack().then((r) => alive && setRows(r));
    return () => {
      alive = false;
    };
  }, []);

  if (!rows) return <p className="screen-msg">Loading follow-ups…</p>;

  const overdue = rows.filter((r) => r.days_overdue > 0);
  const today = rows.filter((r) => r.days_overdue === 0);
  const upcoming = rows.filter((r) => r.days_overdue < 0);

  return (
    <div className="dueback">
      {overdue.length ? (
        <>
          <h2 className="qsec prio">Overdue — {overdue.length}</h2>
          {overdue.map((r) => (
            <DueRow key={r.patient_id} r={r} tone="p" />
          ))}
        </>
      ) : null}

      {today.length ? (
        <>
          <h2 className="qsec">Due today</h2>
          {today.map((r) => (
            <DueRow key={r.patient_id} r={r} />
          ))}
        </>
      ) : null}

      <h2 className="qsec">Upcoming</h2>
      {upcoming.map((r) => (
        <DueRow key={r.patient_id} r={r} />
      ))}
    </div>
  );
}

function DueRow({ r, tone }) {
  const label =
    r.days_overdue > 0
      ? `${r.days_overdue} day${r.days_overdue === 1 ? "" : "s"} overdue`
      : r.days_overdue === 0
        ? "Due today"
        : `in ${Math.abs(r.days_overdue)} days`;

  return (
    <div className={`durow ${tone ?? ""}`}>
      <span className="qwho">
        <span className="qn">{r.name}</span>
        <span className="qm">
          {r.age_years} y · {r.sex === "female" ? "F" : "M"}
        </span>
      </span>
      <span className="qc">
        <span className="t">{r.reason}</span>
        <span className="qm">Last seen {r.last_seen}</span>
      </span>
      <span className={`pill ${r.days_overdue > 0 ? "part" : ""}`}>{label}</span>
      <span className="qm">{r.contact}</span>
      <button type="button" className="qbtn" onClick={() => alert("Reminder via ABHA-linked app — not wired yet")}>
        Remind
      </button>
    </div>
  );
}
