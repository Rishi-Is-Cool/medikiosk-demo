/* The entry point. A doctor looks at this for about three seconds between
   consultations, so it answers exactly two questions: who is next, and whose
   snapshot is not ready yet.

   Red-flagged patients sit in their own band rather than being sorted to the
   top — a re-sort is easy to miss, a labelled section is structural. */

import { useEffect, useState } from "react";
import { fetchQueue } from "../api/client.js";
import DueBack from "../components/DueBack.jsx";

const INTAKE = {
  ready: { label: "Snapshot ready", tone: "ready" },
  documents_processing: { label: "Documents processing", tone: "part" },
  intake_in_progress: { label: "Intake in progress", tone: "part" },
  not_started: { label: "Not started", tone: "none" },
};

export default function Queue({ onOpen }) {
  const [tab, setTab] = useState("queue");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    fetchQueue()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, []);

  if (error) return <p className="screen-msg">Could not load the queue — {error}</p>;
  if (!data) return <p className="screen-msg">Loading queue…</p>;

  return (
    <div className="queue">
      <header className="qtop">
        <h1 className="dept">{data.department}</h1>
        <span className="who">
          {data.doctor.name} · HPR {data.doctor.hpr}
        </span>
        <span className="who right">
          {new Date().toLocaleDateString("en-IN", {
            weekday: "short",
            day: "2-digit",
            month: "short",
            year: "numeric",
          })}
        </span>
      </header>

      {/* The only place the build says anything measurable about throughput,
          which is what the problem statement actually argues from. */}
      {/* Docon #16 — who is due back belongs beside the queue, not in a
          separate report nobody opens. */}
      <nav className="tabs" role="tablist">
        {[
          ["queue", "Today's queue"],
          ["due", "Due back"],
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

      {tab === "due" ? <DueBack /> : <QueueList data={data} onOpen={onOpen} />}
    </div>
  );
}

function QueueList({ data, onOpen }) {
  const priority = data.patients.filter((p) => p.priority);
  const current = data.patients.filter((p) => p.in_consultation);
  const waiting = data.patients.filter((p) => !p.priority && !p.in_consultation);

  return (
    <>
      <div className="stats">
        <Stat n="Seen today" v={data.stats.seen_today} />
        <Stat n="In queue" v={data.stats.in_queue} />
        <Stat n="Median wait" v={data.stats.median_wait_min} unit="min" />
        <Stat n="Intake complete" v={data.stats.intake_complete} unit={`of ${data.stats.in_queue}`} />
      </div>

      {priority.length ? (
        <>
          <h2 className="qsec prio">Priority — red flag detected at intake</h2>
          {priority.map((p) => (
            <Row key={p.encounter_id} p={p} onOpen={onOpen} variant="p" cta="Open now" />
          ))}
        </>
      ) : null}

      {current.length ? (
        <>
          <h2 className="qsec">In consultation</h2>
          {current.map((p) => (
            <Row key={p.encounter_id} p={p} onOpen={onOpen} variant="now" cta="Resume" />
          ))}
        </>
      ) : null}

      <h2 className="qsec">Waiting — by token</h2>
      {waiting.map((p) => (
        <Row key={p.encounter_id} p={p} onOpen={onOpen} cta="Open" />
      ))}
    </>
  );
}

function Stat({ n, v, unit }) {
  return (
    <div className="stat">
      <span className="n">{n}</span>
      <span className="v mk-num">
        {v}
        {unit ? <small> {unit}</small> : null}
      </span>
    </div>
  );
}

function Row({ p, onOpen, variant, cta }) {
  const intake = INTAKE[p.intake_state] ?? INTAKE.not_started;
  const disabled = p.intake_state === "not_started";

  return (
    <div className={`qrow ${variant ?? ""}`}>
      <span className="tok mk-num">{p.token}</span>
      <span className="qwho">
        <span className="qn">{p.name}</span>
        <span className="qm">
          {p.age_years} y · {p.sex === "female" ? "F" : "M"}
        </span>
      </span>
      <span className="qc">
        <span className="t">{p.complaint ?? "Not yet recorded"}</span>
        {p.priority_reason ? <span className="r">{p.priority_reason}</span> : null}
      </span>
      <span>
        <span className={`pill ${p.intake_framework === "ayush" ? "ayu" : ""}`}>{p.department}</span>
      </span>
      <span>
        <span className={`pill ${intake.tone}`}>
          <span className="dot" aria-hidden="true" />
          {intake.label}
        </span>
      </span>
      <span className="wait mk-num">{p.wait_min == null ? "—" : `${p.wait_min} min`}</span>
      <button
        type="button"
        className={`qbtn ${variant === "p" ? "prio" : ""}`}
        onClick={() => onOpen(p.encounter_id)}
        disabled={disabled}
        title={disabled ? "This patient has not started intake yet" : undefined}
      >
        {cta}
      </button>
    </div>
  );
}
