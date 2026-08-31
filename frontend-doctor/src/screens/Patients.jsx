/* Everyone on file, not just today's clinic.

   A longitudinal record you cannot search is a contradiction — the queue only
   answers "who is in front of me now", and the platform's whole claim is that
   it remembers people between visits. */

import { useEffect, useMemo, useState } from "react";
import { fetchPatients } from "../api/client.js";

const SORTS = [
  { key: "name", label: "Name" },
  { key: "recent", label: "Last seen" },
  { key: "age", label: "Age" },
  { key: "visits", label: "Visits" },
];

export default function Patients({ onOpen }) {
  const [all, setAll] = useState(null);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("name");
  const [dir, setDir] = useState("asc");
  const [dept, setDept] = useState("all");

  useEffect(() => {
    let alive = true;
    fetchPatients().then((p) => alive && setAll(p));
    return () => {
      alive = false;
    };
  }, []);

  const departments = useMemo(
    () => (all ? ["all", ...new Set(all.map((p) => p.department))] : ["all"]),
    [all]
  );

  const shown = useMemo(() => {
    if (!all) return [];
    const needle = q.trim().toLowerCase();
    let list = all.filter((p) => {
      if (dept !== "all" && p.department !== dept) return false;
      if (!needle) return true;
      return (
        p.name.toLowerCase().includes(needle) ||
        p.abha_id.includes(needle) ||
        p.conditions.some((c) => c.toLowerCase().includes(needle))
      );
    });
    const cmp = {
      name: (a, b) => a.name.localeCompare(b.name),
      age: (a, b) => a.age_years - b.age_years,
      visits: (a, b) => a.visits - b.visits,
      recent: (a, b) => (a.last_visit ?? "").localeCompare(b.last_visit ?? ""),
    }[sort];
    list = [...list].sort(cmp);
    return dir === "asc" ? list : list.reverse();
  }, [all, q, sort, dir, dept]);

  if (!all) return <p className="screen-msg">Loading patients…</p>;

  return (
    <div className="patients">
      <div className="pat-controls">
        <input
          className="pat-search"
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search name, ABHA number or condition"
          aria-label="Search patients"
        />
        <label className="pat-field">
          <span>Department</span>
          <select value={dept} onChange={(e) => setDept(e.target.value)}>
            {departments.map((d) => (
              <option key={d} value={d}>{d === "all" ? "All" : d}</option>
            ))}
          </select>
        </label>
        <label className="pat-field">
          <span>Sort by</span>
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map((s) => (
              <option key={s.key} value={s.key}>{s.label}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          className="btn pat-dir"
          onClick={() => setDir((d) => (d === "asc" ? "desc" : "asc"))}
          aria-label={dir === "asc" ? "Sort descending" : "Sort ascending"}
        >
          {dir === "asc" ? "↑ A–Z" : "↓ Z–A"}
        </button>
      </div>

      <p className="pat-count">
        {shown.length} of {all.length} patients
        {q ? <> matching “{q}”</> : null}
      </p>

      <div className="pat-head" aria-hidden="true">
        <span>Patient</span>
        <span>ABHA</span>
        <span>Department</span>
        <span>Conditions</span>
        <span>Last seen</span>
        <span>Visits</span>
      </div>

      <div className="pat-list">
        {!shown.length ? <p className="screen-msg">No patient matches that search.</p> : null}
        {shown.map((p) => (
          <button key={p.patient_id} type="button" className="pat-row" onClick={() => onOpen(p.patient_id)}>
            <span className="pat-who">
              <span className="avatar" aria-hidden="true">{initials(p.name)}</span>
              <span className="pat-body">
                <span className="pat-name">{p.name}</span>
                <span className="pat-meta">
                  {p.age_years} y · {p.sex === "female" ? "F" : "M"}
                </span>
              </span>
            </span>
            <span className="pat-abha mk-num">{p.abha_id}</span>
            <span>
              <span className={`pill ${p.department === "Ayurveda" || p.department === "Panchakarma" ? "ayu" : ""}`}>
                {p.department}
              </span>
            </span>
            <span className="pat-cond">
              {p.conditions.length ? p.conditions.join(" · ") : <span className="dim">None recorded</span>}
              {p.allergies.length ? <span className="pat-allergy">Allergy: {p.allergies.join(", ")}</span> : null}
            </span>
            <span className="pat-when mk-num">{p.last_visit ? fmt(p.last_visit) : <span className="dim">Never</span>}</span>
            <span className="pat-visits mk-num">{p.visits}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function initials(name) {
  return name
    .replace(/^Dr\.?\s+/i, "")
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();
}

export function fmt(iso) {
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}
