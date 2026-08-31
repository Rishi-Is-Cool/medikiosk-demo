/* S1 — the launcher. Docon's app root is a Dashboard, not the patient list:
   one oversized "Enter Clinic" tile dominates and everything administrative is
   demoted to small equal tiles. The EMR is one destination among several.

   Kept: the dominant action, the greeting card with honest status lines, the
   visits trend.
   Dropped: Need Support, Rate Us, Forward to a friend, What's New, FAQs, and
   the vendor phone number along the bottom — that is a private-clinic
   software vendor's surface area with no institutional equivalent. */

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

export default function Home({ onEnterClinic, onOpenDueBack, onOpenSettings }) {
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

  const priority = queue?.patients.filter((p) => p.priority).length ?? 0;
  const overdue = due?.filter((d) => d.days_overdue > 0).length ?? 0;
  const pendingIntake =
    queue ? queue.patients.filter((p) => p.intake_state !== "ready").length : 0;

  return (
    <div className="home">
      <header className="home-top">
        <h1 className="home-title">MediKiosk</h1>
        <span className="who">{queue?.doctor.name ?? ""}</span>
        <span className="who right">
          {new Date().toLocaleDateString("en-IN", {
            weekday: "long",
            day: "2-digit",
            month: "long",
            year: "numeric",
          })}
        </span>
      </header>

      <div className="home-grid">
        <div className="home-left">
          <section className="card greeting">
            <h2>{greet()}, {queue?.doctor.name ?? "Doctor"}</h2>
            {/* Status lines earn their place by being actionable — Docon's
                equivalent slot carried a subscription advert. */}
            <ul className="status">
              <li>
                <span className="status-n mk-num">{queue?.stats.seen_today ?? "—"}</span>
                patients seen today
              </li>
              <li className={priority ? "urgent" : undefined}>
                <span className="status-n mk-num">{priority}</span>
                {priority === 1 ? "patient flagged" : "patients flagged"} at intake, waiting ahead of the queue
              </li>
              <li className={overdue ? "warn" : undefined}>
                <span className="status-n mk-num">{overdue}</span>
                follow-{overdue === 1 ? "up" : "ups"} overdue
              </li>
              <li>
                <span className="status-n mk-num">{pendingIntake}</span>
                {pendingIntake === 1 ? "snapshot" : "snapshots"} still being prepared at the kiosk
              </li>
            </ul>
          </section>

          <section className="card chart-card">
            <div className="chart-head">
              <h3>Patients seen</h3>
              <span className="chart-note">this week</span>
            </div>
            <Sparkline data={WEEK} />
          </section>
        </div>

        <div className="home-right">
          <button type="button" className="tile tile-primary" onClick={onEnterClinic}>
            <svg viewBox="0 0 48 48" width="44" height="44" aria-hidden="true">
              <path
                d="M24 6 8 18v22h32V18L24 6Z"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinejoin="round"
              />
              <path d="M24 20v12M18 26h12" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
            </svg>
            <span className="tile-label">Enter OPD</span>
            <span className="tile-sub">
              {queue ? `${queue.stats.in_queue} waiting · ${queue.department}` : " "}
            </span>
          </button>

          <div className="tile-row">
            <button type="button" className="tile" onClick={onOpenDueBack}>
              <span className="tile-num mk-num">{due?.length ?? "—"}</span>
              <span className="tile-label">Due back</span>
              {overdue ? <span className="tile-flag">{overdue} overdue</span> : null}
            </button>
            <button type="button" className="tile" onClick={onOpenSettings}>
              <span className="tile-num">⚙</span>
              <span className="tile-label">Settings</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function greet() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

/* Hand-drawn rather than pulled from a charting library — six points do not
   justify 90KB of dependency on a build this size. */
function Sparkline({ data }) {
  const w = 460;
  const h = 130;
  const pad = { l: 8, r: 8, t: 12, b: 22 };
  const max = Math.max(...data.map((d) => d.seen));
  const min = Math.min(...data.map((d) => d.seen));
  const span = Math.max(max - min, 1);
  const x = (i) => pad.l + (i * (w - pad.l - pad.r)) / (data.length - 1);
  const y = (v) => pad.t + (1 - (v - min) / span) * (h - pad.t - pad.b);
  const line = data.map((d, i) => `${i ? "L" : "M"}${x(i)},${y(d.seen)}`).join(" ");
  const area = `${line} L${x(data.length - 1)},${h - pad.b} L${x(0)},${h - pad.b} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="spark" role="img" aria-label={data.map((d) => `${d.day} ${d.seen}`).join(", ")}>
      <path d={area} className="spark-fill" />
      <path d={line} className="spark-line" />
      {data.map((d, i) => (
        <g key={d.day}>
          <circle cx={x(i)} cy={y(d.seen)} r={i === data.length - 1 ? 4 : 2.5} className="spark-dot" />
          <text x={x(i)} y={h - 6} className="spark-label">{d.day}</text>
        </g>
      ))}
    </svg>
  );
}
