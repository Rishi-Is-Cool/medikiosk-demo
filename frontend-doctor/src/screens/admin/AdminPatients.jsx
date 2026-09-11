/* The full hospital patient directory — every patient ever registered,
   not scoped to one doctor's assigned encounters the way the doctor
   console's own Patients screen is. Search is server-side (name or ABHA)
   since the directory can grow well past what's reasonable to filter
   client-side. */

import { useEffect, useState } from "react";
import { fetchAdminPatients } from "../../api/client.js";

const PAGE_SIZE = 25;

export default function AdminPatients() {
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const [skip, setSkip] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    fetchAdminPatients({ q, skip, limit: PAGE_SIZE })
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [q, skip]);

  return (
    <div className="overview">
      <div className="pat-search">
        <input
          className="pat-search-input"
          type="search"
          placeholder="Search by name or ABHA number…"
          value={q}
          onChange={(e) => {
            setSkip(0);
            setQ(e.target.value);
          }}
        />
        {data ? <span className="pat-search-count">{data.total} patient{data.total === 1 ? "" : "s"}</span> : null}
      </div>

      {error ? <p className="screen-msg">Could not load patients — {error}</p> : null}
      {!error && !data ? <p className="screen-msg">Loading patients…</p> : null}

      {data ? (
        data.patients.length ? (
          <>
            <div className="wr-table pat-table">
              <div className="wr-head pat-head">
                <span>Name</span>
                <span>Age / Sex</span>
                <span>Language</span>
                <span>ABHA</span>
                <span>Consent</span>
                <span>Registered</span>
              </div>
              {data.patients.map((p) => (
                <div key={p.patient_id} className="wr-row pat-row">
                  <span className="qn">{p.name}</span>
                  <span>
                    {p.age} y · {p.gender}
                  </span>
                  <span>{p.language ?? "—"}</span>
                  <span className="mk-num">{p.abha_id ?? "—"}</span>
                  <span>{p.consent_granted ? "Granted" : "Not on file"}</span>
                  <span>{p.registered_at ? new Date(p.registered_at).toLocaleDateString("en-IN") : "—"}</span>
                </div>
              ))}
            </div>
            <div className="pat-pager">
              <button type="button" className="btn" disabled={skip === 0} onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}>
                ‹ Previous
              </button>
              <span className="pat-pager-label">
                {skip + 1}–{Math.min(skip + PAGE_SIZE, data.total)} of {data.total}
              </span>
              <button type="button" className="btn" disabled={skip + PAGE_SIZE >= data.total} onClick={() => setSkip(skip + PAGE_SIZE)}>
                Next ›
              </button>
            </div>
          </>
        ) : (
          <p className="ov-empty">No patients match “{q}”.</p>
        )
      ) : null}
    </div>
  );
}
