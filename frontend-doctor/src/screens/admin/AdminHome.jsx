/* The admin landing tab — a dashboard, not a work queue. Answers "is
   anything wrong right now" and "how has the week gone" in one glance;
   anyone who needs to act on a specific patient goes to Rooms or Waiting
   Room instead. No charting library — two data points (a 7-day count and a
   2-way specialty split) don't need one, and hand-rolled bars stay
   consistent with how the rest of the app already visualizes trends
   (TrendTable.jsx has no chart library either). */

import { useEffect, useState } from "react";
import { fetchHospitalOverview, fetchHospitalTrend } from "../../api/client.js";
import { getRefreshMs } from "../../api/adminPrefs.js";

const SEVERITY_LABEL = { critical: "Critical", high: "High", moderate: "Moderate", low: "Low" };

export default function AdminHome() {
  const [overview, setOverview] = useState(null);
  const [trend, setTrend] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    function load() {
      Promise.all([fetchHospitalOverview(), fetchHospitalTrend()])
        .then(([ov, tr]) => {
          if (!alive) return;
          setOverview(ov);
          setTrend(tr);
        })
        .catch((e) => alive && setError(e.message));
    }
    load();
    const ms = getRefreshMs();
    const id = ms > 0 ? setInterval(load, ms) : null;
    return () => {
      alive = false;
      if (id) clearInterval(id);
    };
  }, []);

  if (error) return <p className="screen-msg">Could not load the dashboard — {error}</p>;
  if (!overview || !trend) return <p className="screen-msg">Loading dashboard…</p>;

  const { hospital_stats: stats, doctors, alerts } = overview;
  const ayurvedaQueue = doctors.filter((d) => d.practitioner_type === "ayurveda").reduce((s, d) => s + d.in_queue, 0);
  const generalQueue = doctors.filter((d) => d.practitioner_type !== "ayurveda").reduce((s, d) => s + d.in_queue, 0);

  return (
    <div className="overview">
      <div className="stats ov-stats">
        <Stat n="Doctors on duty" v={stats.doctors_on_duty} />
        <Stat n="In queue" v={stats.total_in_queue} />
        <Stat n="Seen today" v={stats.total_seen_today} />
        <Stat n="Open alerts" v={stats.open_alerts} tone={stats.open_alerts > 0 ? "alert" : undefined} />
      </div>

      <div className="dash-charts">
        <div className="dash-card">
          <h2 className="qsec">Patients seen — last 7 days</h2>
          <TrendChart days={trend.days} />
        </div>
        <div className="dash-card">
          <h2 className="qsec">Queue by specialty</h2>
          <SpecialtySplit ayurveda={ayurvedaQueue} general={generalQueue} />
        </div>
      </div>

      <h2 className="qsec prio">Red flags — every doctor, every specialty</h2>
      {alerts.length ? (
        <div className="ov-alerts ov-alerts-compact">
          {alerts.map((a) => (
            <div key={a.alert_id} className={`ov-alert-line sev-${a.severity}`}>
              <span className="ov-alert-sev">{SEVERITY_LABEL[a.severity] ?? a.severity}</span>
              <span className="ov-alert-headline">{a.headline}</span>
              <span className="ov-alert-who">
                {a.patient_name ?? "Unknown patient"} · {a.doctor_name ?? "Unassigned"}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="ov-empty">No open red flags right now.</p>
      )}
    </div>
  );
}

function Stat({ n, v, tone }) {
  return (
    <div className={`stat ${tone ? `stat-${tone}` : ""}`}>
      <span className="n">{n}</span>
      <span className="v mk-num">{v}</span>
    </div>
  );
}

function TrendChart({ days }) {
  const max = Math.max(1, ...days.map((d) => d.seen));
  return (
    <div className="bars">
      {days.map((d) => (
        <div key={d.date} className="bar-col">
          <span className="bar-v mk-num">{d.seen}</span>
          <div className="bar-track">
            <div className="bar-fill" style={{ height: `${(d.seen / max) * 100}%` }} />
          </div>
          <span className="bar-label">{d.label}</span>
        </div>
      ))}
    </div>
  );
}

function SpecialtySplit({ ayurveda, general }) {
  const total = ayurveda + general;
  const ayuPct = total ? (ayurveda / total) * 100 : 0;
  return (
    <div className="split-chart">
      <div className="split-track">
        {total ? (
          <>
            <div className="split-seg ayu" style={{ width: `${ayuPct}%` }} />
            <div className="split-seg gen" style={{ width: `${100 - ayuPct}%` }} />
          </>
        ) : null}
      </div>
      <div className="split-legend">
        <span className="split-legend-item">
          <span className="split-dot ayu" /> Ayurveda — {ayurveda} waiting
        </span>
        <span className="split-legend-item">
          <span className="split-dot gen" /> General Medicine — {general} waiting
        </span>
      </div>
    </div>
  );
}
