/* Every patient waiting anywhere in the hospital, one flat list — Rooms
   groups by doctor for "who's free"; this answers the opposite question,
   "who's been waiting longest," which only makes sense flattened and
   re-sorted across doctors. */

import { useEffect, useState } from "react";
import { fetchHospitalOverview } from "../../api/client.js";
import { getRefreshMs } from "../../api/adminPrefs.js";

export default function AdminWaitingRoom() {
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

  if (error) return <p className="screen-msg">Could not load the waiting room — {error}</p>;
  if (!data) return <p className="screen-msg">Loading waiting room…</p>;

  const rows = data.doctors
    .flatMap((d) => d.patients.map((p) => ({ ...p, doctor_name: d.name, department: d.department, cls: d.practitioner_type === "ayurveda" ? "ayu" : "gen" })))
    .sort((a, b) => (b.wait_min ?? 0) - (a.wait_min ?? 0));

  return (
    <div className="overview">
      <div className="stats stats-2">
        <div className="stat">
          <span className="n">Waiting hospital-wide</span>
          <span className="v mk-num">{rows.length}</span>
        </div>
        <div className="stat">
          <span className="n">Longest wait</span>
          <span className="v mk-num">{rows.length ? `${rows[0].wait_min ?? 0} min` : "—"}</span>
        </div>
      </div>

      {rows.length ? (
        <div className="wr-table">
          <div className="wr-head">
            <span>Patient</span>
            <span>Complaint</span>
            <span>Doctor</span>
            <span>Department</span>
            <span>Waiting</span>
          </div>
          {rows.map((p) => (
            <div key={p.encounter_id} className={`wr-row ${p.priority ? "p" : ""}`}>
              <span className="ov-who">
                <span className="qn">{p.name}</span>
                <span className="qm">
                  {p.age_years} y · {p.sex === "female" ? "F" : "M"}
                </span>
              </span>
              <span className="ov-complaint">{p.complaint ?? "Not yet recorded"}</span>
              <span>{p.doctor_name}</span>
              <span>
                <span className={`pill ${p.cls}`}>{p.department}</span>
              </span>
              <span className="wait mk-num">{p.wait_min == null ? "—" : `${p.wait_min} min`}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="ov-empty">Nobody waiting anywhere in the hospital.</p>
      )}
    </div>
  );
}
