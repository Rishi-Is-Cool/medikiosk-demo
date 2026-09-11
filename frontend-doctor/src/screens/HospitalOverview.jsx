/* The hospital-wide board — reception/admin only, not a doctor's own
   console. Every doctor's queue side by side, and every unresolved red-flag
   alert regardless of specialty — exactly the two things a doctor's own
   console deliberately never shows across doctors (see
   _require_own_encounter on the backend). Read-only: opening a specific
   patient still happens from inside that doctor's own console, not here.

   Polls rather than pushing — reception glancing at a wall display doesn't
   need sub-second updates, and it's one GET instead of a websocket. */

import { useEffect, useState } from "react";
import { fetchHospitalOverview } from "../api/client.js";

const REFRESH_MS = 30000;
const SEVERITY_LABEL = { critical: "Critical", high: "High", moderate: "Moderate", low: "Low" };

export default function HospitalOverview() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    function load() {
      fetchHospitalOverview()
        .then((d) => alive && setData(d))
        .catch((e) => alive && setError(e.message));
    }
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (error) return <p className="screen-msg">Could not load the hospital overview — {error}</p>;
  if (!data) return <p className="screen-msg">Loading hospital overview…</p>;

  const { hospital_stats: stats, doctors, alerts } = data;

  return (
    <div className="overview">
      <div className="stats">
        <Stat n="Doctors on duty" v={stats.doctors_on_duty} />
        <Stat n="In queue" v={stats.total_in_queue} />
        <Stat n="Seen today" v={stats.total_seen_today} />
        <Stat n="Open alerts" v={stats.open_alerts} />
      </div>

      <h2 className="qsec prio">Red flags — every doctor, every specialty</h2>
      {alerts.length ? (
        <div className="ov-alerts">
          {alerts.map((a) => (
            <div key={a.alert_id} className={`ov-alert sev-${a.severity}`}>
              <span className="ov-alert-sev">{SEVERITY_LABEL[a.severity] ?? a.severity}</span>
              <span className="ov-alert-body">
                <span className="ov-alert-headline">{a.headline}</span>
                {a.detail ? <span className="ov-alert-detail">{a.detail}</span> : null}
              </span>
              <span className="ov-alert-who">
                {a.patient_name ?? "Unknown patient"} · {a.doctor_name ?? "Unassigned"}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <p className="ov-empty">No open red flags right now.</p>
      )}

      <h2 className="qsec">By doctor</h2>
      {doctors.length ? doctors.map((d) => <DoctorBlock key={d.username} d={d} />) : (
        <p className="ov-empty">No doctors on duty.</p>
      )}
    </div>
  );
}

function Stat({ n, v }) {
  return (
    <div className="stat">
      <span className="n">{n}</span>
      <span className="v mk-num">{v}</span>
    </div>
  );
}

function DoctorBlock({ d }) {
  return (
    <div className="ov-doctor">
      <div className="ov-doctor-head">
        <span className={`pill ${d.practitioner_type === "ayurveda" ? "ayu" : ""}`}>{d.department}</span>
        <span className="ov-doctor-name">{d.name}</span>
        <span className="ov-doctor-counts">
          {d.in_queue} waiting · {d.seen_today} seen today
        </span>
      </div>
      {d.patients.length ? (
        d.patients.map((p) => (
          <div key={p.encounter_id} className={`ov-row ${p.priority ? "p" : ""}`}>
            <span className="ov-who">
              <span className="qn">{p.name}</span>
              <span className="qm">
                {p.age_years} y · {p.sex === "female" ? "F" : "M"}
              </span>
            </span>
            <span className="ov-complaint">{p.complaint ?? "Not yet recorded"}</span>
            <span className="wait mk-num">{p.wait_min == null ? "—" : `${p.wait_min} min`}</span>
          </div>
        ))
      ) : (
        <p className="ov-empty">Nobody waiting.</p>
      )}
    </div>
  );
}
