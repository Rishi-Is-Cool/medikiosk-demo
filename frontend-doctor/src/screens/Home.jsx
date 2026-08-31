/* The launcher. Docon's app root is a dashboard, not the patient list — one
   dominant action, everything else demoted. That structure is kept.

   What is not kept is Docon's habit of rendering the important things as
   counts. A flagged patient is a person with a name and a reason, and the
   whole point of the red-flag rule is that the doctor acts on it — so it is
   an actionable card, not the numeral 1.

   Everything on this screen is either something to do next, or the evidence
   that there is nothing to do next. */

import { useEffect, useState } from "react";
import { fetchQueue, fetchDueBack } from "../api/client.js";

const WEEK = [
  { day: "Mon", seen: 41 },
  { day: "Tue", seen: 38 },
  { day: "Wed", seen: 52 },
  { day: "Thu", seen: 47 },
  { day: "Fri", seen: 61 },
  { day: "Sat", seen: 34 },
];

export default function Home({ onEnterClinic, onOpenDueBack, onOpenPatients, onOpenEncounter }) {
  const [queue, setQueue] = useState(null);
  const [due, setDue] = useState(null);

  useEffect(() => {
    let alive = true;
    Promise.all([fetchQueue(), fetchDueBack()]).then(([q, d]) => {
      if (!alive) return;
      setQueue(q);
      setDue(d);
    });
    return () => {
      alive = false;
    };
  }, []);

  const flagged = queue?.patients.filter((p) => p.priority) ?? [];
  const waiting = queue?.patients.filter((p) => !p.priority && !p.in_consultation) ?? [];
  const inRoom = queue?.patients.find((p) => p.in_consultation);
  const overdue = due?.filter((d) => d.days_overdue > 0) ?? [];
  const pendingIntake = queue?.patients.filter((p) => p.intake_state !== "ready").length ?? 0;

  return (
    <div className="home">
      <header className="home-top">
        <div>
          <h1 className="home-greet">{greet()}, {queue?.doctor.name ?? "Doctor"}</h1>
          <p className="home-sub">
            {queue ? `${queue.department} · ${queue.stats.in_queue} waiting · ${queue.stats.seen_today} seen today` : "Loading…"}
          </p>
        </div>
        <span className="home-date mk-num">
          {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })}
        </span>
      </header>

      {/* The one thing that must never be a statistic. */}
      {flagged.map((p) => (
        <button key={p.encounter_id} type="button" className="flagcard" onClick={() => onOpenEncounter(p.encounter_id)}>
          <span className="flag-sev">PRIORITY</span>
          <span className="flag-body">
            <span className="flag-name">
              {p.name} <span className="flag-meta mk-num">{p.age_years} y · {p.sex === "female" ? "F" : "M"} · {p.token}</span>
            </span>
            <span className="flag-reason">{p.priority_reason}</span>
          </span>
          <span className="flag-wait mk-num">waiting {p.wait_min} min</span>
          <span className="flag-go">See now →</span>
        </button>
      ))}

      <div className="home-grid">
        <button type="button" className="tile tile-primary" onClick={onEnterClinic}>
          <svg viewBox="0 0 48 48" width="40" height="40" aria-hidden="true">
            <path d="M24 6 8 18v22h32V18L24 6Z" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinejoin="round" />
            <path d="M24 20v12M18 26h12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
          </svg>
          <span className="tile-label">Enter OPD</span>
          <span className="tile-sub">
            {inRoom ? `${inRoom.name} is in the room` : queue ? `${waiting.length} waiting` : " "}
          </span>
          {pendingIntake ? (
            <span className="tile-note">{pendingIntake} still completing intake at the kiosk</span>
          ) : null}
        </button>

        <section className="panel">
          <header className="panel-head">
            <h2>Next in queue</h2>
            <button type="button" className="panel-link" onClick={onEnterClinic}>See all</button>
          </header>
          {!queue ? (
            <p className="panel-empty">Loading…</p>
          ) : !waiting.length ? (
            <p className="panel-empty">Nobody waiting.</p>
          ) : (
            <ul className="minilist">
              {waiting.slice(0, 4).map((p) => (
                <li key={p.encounter_id}>
                  <button
                    type="button"
                    className="minirow"
                    disabled={p.intake_state === "not_started"}
                    onClick={() => onOpenEncounter(p.encounter_id)}
                  >
                    <span className="mini-tok mk-num">{p.token}</span>
                    <span className="mini-body">
                      <span className="mini-name">{p.name}</span>
                      <span className="mini-sub">{p.complaint ?? "Intake not started"}</span>
                    </span>
                    <span className="mini-right mk-num">{p.wait_min}m</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel">
          <header className="panel-head">
            <h2>Due back</h2>
            <button type="button" className="panel-link" onClick={onOpenDueBack}>See all</button>
          </header>
          {!due ? (
            <p className="panel-empty">Loading…</p>
          ) : (
            <>
              {overdue.length ? (
                <p className="panel-alert">{overdue.length} overdue</p>
              ) : (
                <p className="panel-ok">Nobody overdue</p>
              )}
              <ul className="minilist">
                {due.slice(0, 4).map((d) => (
                  <li key={d.patient_id}>
                    <button type="button" className="minirow" onClick={onOpenDueBack}>
                      <span className={`mini-days mk-num ${d.days_overdue > 0 ? "late" : ""}`}>
                        {d.days_overdue > 0 ? `+${d.days_overdue}d` : d.days_overdue === 0 ? "today" : `${Math.abs(d.days_overdue)}d`}
                      </span>
                      <span className="mini-body">
                        <span className="mini-name">{d.name}</span>
                        <span className="mini-sub">{d.reason}</span>
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </div>

      <section className="card chart-card">
        <div className="chart-head">
          <h3>Patients seen</h3>
          <span className="chart-note">this week · {WEEK.reduce((a, b) => a + b.seen, 0)} total</span>
          <button type="button" className="panel-link" onClick={onOpenPatients}>All patient records</button>
        </div>
        <Sparkline data={WEEK} />
      </section>
    </div>
  );
}

function greet() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

/* Six points do not justify a charting dependency. Padding is set so the
   first and last day labels sit inside the box rather than clipping, which
   the previous version got wrong. */
function Sparkline({ data }) {
  const w = 1600;
  const h = 210;
  const pad = { l: 40, r: 40, t: 34, b: 34 };
  const max = Math.max(...data.map((d) => d.seen));
  const min = Math.min(...data.map((d) => d.seen));
  const span = Math.max(max - min, 1);
  const x = (i) => pad.l + (i * (w - pad.l - pad.r)) / (data.length - 1);
  const y = (v) => pad.t + (1 - (v - min) / span) * (h - pad.t - pad.b);
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i)},${y(d.seen)}`).join(" ");
  const area = `${line} L${x(data.length - 1)},${h - pad.b} L${x(0)},${h - pad.b} Z`;
  const peak = data.reduce((a, b) => (b.seen > a.seen ? b : a));

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="spark" role="img" aria-label={data.map((d) => `${d.day} ${d.seen}`).join(", ")}>
      <line x1={pad.l} x2={w - pad.r} y1={h - pad.b} y2={h - pad.b} className="spark-base" />
      <path d={area} className="spark-fill" />
      <path d={line} className="spark-line" />
      {data.map((d, i) => (
        <g key={d.day}>
          <circle cx={x(i)} cy={y(d.seen)} r={d.day === peak.day ? 5 : 3.5} className="spark-dot" />
          <text x={x(i)} y={y(d.seen) - 14} className={`spark-val ${d.day === peak.day ? "peak" : ""}`}>{d.seen}</text>
          <text x={x(i)} y={h - 10} className="spark-label">{d.day}</text>
        </g>
      ))}
    </svg>
  );
}
