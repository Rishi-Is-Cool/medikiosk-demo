/* Every doctor as a "room": who they're with right now (if anyone) and who
   is waiting for them next. Grouped by specialty so reception can compare
   load within a specialty at a glance.

   "With patient" has no explicit backend event to key off — no one ever
   tells the system "consultation started." The room status is a heuristic
   from the backend (most recently opened chart, within the last 20
   minutes) — see the comment on hospital_overview() in integration.py. */

import { useEffect, useState } from "react";
import { fetchHospitalOverview } from "../../api/client.js";
import { getRefreshMs } from "../../api/adminPrefs.js";

const GROUPS = [
  { key: "ayurveda", label: "Ayurveda OPD", cls: "ayu" },
  { key: "general", label: "General Medicine OPD", cls: "gen" },
];

export default function AdminRooms() {
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
    const ms = getRefreshMs();
    const id = ms > 0 ? setInterval(load, ms) : null;
    return () => {
      alive = false;
      if (id) clearInterval(id);
    };
  }, []);

  if (error) return <p className="screen-msg">Could not load rooms — {error}</p>;
  if (!data) return <p className="screen-msg">Loading rooms…</p>;

  const { doctors } = data;

  return (
    <div className="overview">
      {GROUPS.map(({ key, label, cls }) => {
        const group = doctors.filter((d) => (d.practitioner_type === "ayurveda") === (key === "ayurveda"));
        if (!group.length) return null;
        return (
          <section key={key} className="ov-group">
            <h2 className="qsec">
              {label} <span className="ov-group-count">· {group.length} doctor{group.length === 1 ? "" : "s"}</span>
            </h2>
            <div className="ov-cards">
              {group.map((d) => (
                <RoomCard key={d.username} d={d} cls={cls} />
              ))}
            </div>
          </section>
        );
      })}
      {!doctors.length ? <p className="ov-empty">No doctors on duty.</p> : null}
    </div>
  );
}

function RoomCard({ d, cls }) {
  const withPatient = d.room?.status === "with_patient";
  return (
    <div className={`ov-card ${cls}`}>
      <div className="ov-card-head">
        <span className="ov-doctor-id">
          <span className="ov-doctor-name">{d.name}</span>
          <span className="ov-doctor-username">{d.username}</span>
        </span>
        <span className={`room-status ${withPatient ? "busy" : "free"}`}>
          <span className="dot" aria-hidden="true" />
          {withPatient ? `With ${d.room.patient_name}` : "Free"}
        </span>
      </div>
      <div className="ov-card-sub">
        {d.in_queue} waiting · {d.seen_today} seen today
      </div>
      {d.patients.length ? (
        <div className="ov-card-body">
          {d.patients.map((p) => (
            <div key={p.encounter_id} className={`ov-row ${p.priority ? "p" : ""} ${p.encounter_id === d.room?.encounter_id ? "current" : ""}`}>
              <span className="ov-who">
                <span className="qn">{p.name}</span>
                <span className="qm">
                  {p.age_years} y · {p.sex === "female" ? "F" : "M"}
                </span>
              </span>
              <span className="ov-complaint">{p.complaint ?? "Not yet recorded"}</span>
              <span className="wait mk-num">{p.wait_min == null ? "—" : `${p.wait_min} min`}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="ov-empty">Nobody waiting.</p>
      )}
    </div>
  );
}
