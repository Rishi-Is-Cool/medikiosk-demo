/* The encounter screen. One route, four zones:
     Zone 0  alert bar        — only present when a rule fires
     Zone 1  the ten-second read — never scrolls
     Zone 2  the scan         — HPI, Dashavidha, trend
     Zone 3  evidence panel   — documents, prior encounters, Q&A answers

   The doctor's eyes are here for about ten seconds before they must look at
   the patient. Everything that does not earn a slot in Zone 1 is one click
   away, not one navigation away. */

import { useEffect, useState } from "react";
import {
  fetchSnapshot,
  fetchDocument,
  askQuestion,
  saveLedger,
  finalizeEncounter,
  fetchCarryForward,
  fetchAdviceLibrary,
} from "../api/client.js";
import AlertBar from "../components/AlertBar.jsx";
import SourceChip from "../components/SourceChip.jsx";
import TrendTable from "../components/TrendTable.jsx";
import DashavidhaPanel from "../components/DashavidhaPanel.jsx";
import EvidencePanel from "../components/EvidencePanel.jsx";
import LedgerModal from "../components/LedgerModal.jsx";
import CarryForwardModal from "../components/CarryForwardModal.jsx";
import AdvicePanel from "../components/AdvicePanel.jsx";
import MedicinePanel from "../components/MedicinePanel.jsx";
import PatientRail from "../components/PatientRail.jsx";
import PrintSheet from "../components/PrintSheet.jsx";

export default function Encounter({ encounterId, showAyush, patients = [], onSelectPatient, onBack }) {
  const [snap, setSnap] = useState(null);
  const [error, setError] = useState("");
  const [view, setView] = useState(null);
  const [question, setQuestion] = useState("");
  const [ledgerOpen, setLedgerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [finalised, setFinalised] = useState(false);
  const [carry, setCarry] = useState(null);        // Docon #07 dialog payload
  const [carried, setCarried] = useState([]);      // what was brought forward
  const [carriedFrom, setCarriedFrom] = useState(""); // survives closing the dialog
  const [advice, setAdvice] = useState([]);        // Docon #10 selections
  const [medicines, setMedicines] = useState([]);  // prescribed medicines, catalog or template driven
  const [adviceLibrary, setAdviceLibrary] = useState([]); // for template-applied advice lookups
  const [ayushEdits, setAyushEdits] = useState([]); // doctor amendments to the kiosk reading
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [evCollapsed, setEvCollapsed] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [followUpDate, setFollowUpDate] = useState(null);
  const [shareToken, setShareToken] = useState(null);
  const [notes, setNotes] = useState(null);
  const [rationale, setRationale] = useState(null);
  const [mgmtCollapsed, setMgmtCollapsed] = useState(false);

  useEffect(() => {
    fetchAdviceLibrary().then(setAdviceLibrary);
  }, []);

  useEffect(() => {
    let alive = true;
    setSnap(null);
    setError("");
    setView(null);
    setFinalised(false);
    setCarried([]);
    setCarriedFrom("");
    setAdvice([]);
    setMedicines([]);
    setPrinting(false);
    setFollowUpDate(null);
    setShareToken(null);
    setNotes(null);
    setRationale(null);
    setAyushEdits([]);
    fetchSnapshot(encounterId, { viewerShowsAyush: showAyush })
      .then((d) => alive && setSnap(d))
      .catch((e) => alive && setError(e.message));
    return () => {
      alive = false;
    };
  }, [encounterId, showAyush]);

  async function openSource(source) {
    setEvCollapsed(false);
    if (source.type === "document") {
      setView({ kind: "loading", title: "Evidence" });
      const doc = await fetchDocument(source.id);
      setView(
        doc
          ? { kind: "document", title: doc.title, doc, field: source.locator?.field }
          : { kind: "unavailable", title: "Evidence" }
      );
      return;
    }
    if (source.type === "prior_encounter" && snap?.last_visit) {
      setView({
        kind: "encounter",
        title: "Previous encounter",
        date: fmtDate(snap.last_visit.date),
        summary: snap.last_visit.summary,
      });
      return;
    }
    setView({ kind: "unavailable", title: "Evidence" });
  }

  async function ask(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setEvCollapsed(false);
    setView({ kind: "loading", title: "Answer" });
    const res = await askQuestion(encounterId, q);
    setView({ kind: "answer", title: "Answer", ...res });
    setQuestion("");
  }

  async function openCarryForward() {
    const data = await fetchCarryForward(encounterId);
    if (data) setCarry(data);
  }

  async function commitLedger(entry) {
    setSaving(true);
    try {
      /* The backend's LedgerRequest.advice is List[Dict], not List[str] — it
         stores (and the public visit page later re-derives) full entries, not
         bare ids. Sending ids here 422s the save, which is why finalize was
         never reachable in practice even after being wired up. */
      await saveLedger(encounterId, {
        ...entry,
        advice,
        medicines,
        carried_forward: carried.map((c) => c.key),
        ayush_amendments: ayushEdits,
      });
      /* Finalize is the actual end of the consultation, not just the ledger
         save — it's what removes the patient from GET /api/queue and mints
         the share_token the printed sheet's QR points at. */
      const result = await finalizeEncounter(encounterId);
      setShareToken(result?.share_token ?? null);
    } catch (e) {
      setSaving(false);
      alert(`Could not finalise this encounter: ${e.message}`);
      return;
    }
    setSaving(false);
    setLedgerOpen(false);
    setFinalised(true);
    setNotes(entry.notes ?? null);
    setRationale(entry.treatment_change ? entry.doctor_rationale ?? null : null);
    setFollowUpDate(entry.follow_up_required ? dateFromTimeframe(entry.follow_up_timeframe) : null);
    /* Finishing the encounter is the moment the sheet is wanted — the patient
       is still in the room. Offering it later, from the record, is too late. */
    setPrinting(true);
  }

  const rail = patients.length ? (
    <PatientRail
      patients={patients}
      activeId={encounterId}
      onSelect={onSelectPatient}
      collapsed={railCollapsed}
      onToggle={() => setRailCollapsed((v) => !v)}
    />
  ) : null;

  /* Loading and failure states keep the shell. A doctor who taps a patient
     whose snapshot will not load must still be able to reach the next one. */
  if (error || !snap) {
    return (
      <div className={`shell ${railCollapsed ? "rail-tight" : ""}`}>
        {rail}
        <div className="encounter">
          <header className="idstrip">
            <h1 className="pname">{patients.find((p) => p.encounter_id === encounterId)?.name ?? "Patient"}</h1>
          </header>
          <p className="screen-msg">
            {error
              ? "No snapshot for this patient in the demo dataset — Rahul Verma and Anjali Deshmukh are the two seeded encounters. Pick either from the list."
              : "Loading snapshot…"}
          </p>
        </div>
      </div>
    );
  }

  const s = snap.sections;
  const suppressed = snap.ayush_status === "suppressed_by_viewer";

  return (
    <div className={`shell ${railCollapsed ? "rail-tight" : ""}`}>
      {rail}

      <div className="encounter">
      {/* identity — never leaves the screen */}
      <header className="idstrip">
        <h1 className="pname">{snap.patient.name}</h1>
        <span className="pmeta mk-num">
          {snap.patient.age_years} y · {snap.patient.sex === "female" ? "F" : "M"} · ABHA{" "}
          {snap.patient.abha_id}
        </span>
        {snap.ayush ? (
          <>
            <span className="badge ayu">Prakriti · {snap.ayush.prakriti.value}</span>
            <span className="badge">Vaya · {snap.ayush.vaya.value}</span>
          </>
        ) : null}
        <span className="spacer" />
        <span className={`badge ${finalised ? "confirmed" : "draft"}`}>
          {finalised ? "CONFIRMED" : "DRAFT — NOT CONFIRMED"}
        </span>
      </header>

      <AlertBar alerts={snap.alerts} onOpenSource={openSource} />

      <div
        className={`split ${evCollapsed ? "ev-tight" : ""}`}
        style={{ gridTemplateColumns: evCollapsed ? "minmax(0, 1fr) 44px" : "minmax(0, 62fr) minmax(0, 38fr)" }}
      >
        <div className="left">
          {/* Zone 1 — the ten-second read. Does not scroll. Patient identity
              itself stays in .idstrip only, which is already always visible —
              this card is chief complaint + conditions + medications read as
              one group, with allergies pulled out into their own banner
              instead of splitting three ways across equal columns. */}
          <section className="band zone1">
            <div className="clinical-card">
              <h2 className="clinical-card-title">Primary Clinical Info</h2>
              <div className="clinical-subcards">
                <div className="subcard">
                  <span className="subcard-label">{s.chief_complaint.label}</span>
                  <p className="subcard-cc">
                    {s.chief_complaint.text.value}
                    <span className="cc-dur"> · {s.chief_complaint.text.duration}</span>
                    <SourceChip source={s.chief_complaint.text.source} onOpen={openSource} />
                  </p>
                  {snap.ayush ? <p className="ccsub">Vikriti — {snap.ayush.vikriti.value}</p> : null}
                </div>
                <div className="subcard">
                  <span className="subcard-label">Active conditions</span>
                  {s.past_medical_surgical.items.length ? (
                    s.past_medical_surgical.items.map((it) => (
                      <Item key={it.fact_id} value={it.value} sub={it.normalized?.display} source={it.source} onOpen={openSource} />
                    ))
                  ) : (
                    <p className="item muted col-empty">None recorded</p>
                  )}
                </div>
                <div className="subcard">
                  <span className="subcard-label">Current medications</span>
                  {s.drug_and_allergy.medications.length ? (
                    s.drug_and_allergy.medications.map((m) => (
                      <Item key={m.fact_id} value={m.value} source={m.source} onOpen={openSource} />
                    ))
                  ) : (
                    <p className="item muted col-empty">None recorded</p>
                  )}
                </div>
              </div>
            </div>

            <div className="allergy-banner">
              <b>Allergies:</b>
              {s.drug_and_allergy.allergies.length ? (
                <span className="allergy-list">
                  {s.drug_and_allergy.allergies.map((a, i) => (
                    <Item
                      key={a.fact_id ?? `a-${i}`}
                      value={a.value}
                      sub={a.reaction}
                      source={a.source}
                      onOpen={openSource}
                      muted={!a.fact_id}
                    />
                  ))}
                </span>
              ) : (
                <span>None recorded</span>
              )}
            </div>
          </section>

          {/* Zone 2 — the scan. HPI and pathya/apathya advice read side by
              side as one collapsible "Advice & Management" section — between
              them the longest part of the scan, and collapsible so a doctor
              who has already read both gets that space back. */}
          <section className="band">
            <button
              type="button"
              className="collapse-toggle"
              onClick={() => setMgmtCollapsed((v) => !v)}
              aria-expanded={!mgmtCollapsed}
            >
              <h2 className="bandhead" style={{ marginBottom: 0 }}>Advice &amp; Management</h2>
              <span className={`collapse-chevron ${mgmtCollapsed ? "" : "open"}`} aria-hidden="true">▾</span>
            </button>
            {!mgmtCollapsed ? (
              <div className="mgmt-grid">
                <div>
                  <h3>{s.hpi.label} · {s.hpi.framework}</h3>
                  <dl className="socr">
                    {s.hpi.items.map((it) => (
                      <div className="sc" key={it.key}>
                        <dt>{it.label}</dt>
                        <dd>{it.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div>
                  <AdvicePanel
                    selected={advice}
                    onChange={setAdvice}
                    language={snap.patient.preferred_language}
                  />
                </div>
              </div>
            ) : null}
          </section>

          <DashavidhaPanel
            ayush={snap.ayush}
            onOpenSource={openSource}
            onEdit={(e) => setAyushEdits((prev) => [...prev.filter((p) => p.key !== e.key), e])}
          />

          <section className="band">
            <div className="tl-head">
              <h2 className="bandhead" style={{ marginBottom: 0 }}>Patient Journey Timeline</h2>
              <div className="tl-rail" aria-hidden="true">
                <div className="tl-rail-fill" />
                <div className="tl-rail-thumb" />
              </div>
            </div>
            <TrendTable trend={snap.trend} onOpenSource={openSource} />
          </section>

          {carried.length ? (
            <section className="band carried">
              <h2 className="bandhead">
                Carried forward from {carriedFrom}
              </h2>
              <dl className="cf-applied">
                {carried.map((c) => (
                  <div key={c.key}>
                    <dt>{c.label}</dt>
                    <dd>{c.value}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : null}

          <MedicinePanel
            selected={medicines}
            onChange={setMedicines}
            advice={advice}
            onApplyAdvice={setAdvice}
            adviceLibrary={adviceLibrary}
          />

          <section className="band last">
            <h2 className="bandhead">On file — not shown</h2>
            <div className="badges">
              <span className="badge">Family history · {s.family_history.count} entries</span>
              <span className="badge">Personal history · {s.personal_history.count} entries</span>
              <span className="badge">
                Review of systems · {s.review_of_systems.systems_reviewed} reviewed,{" "}
                {s.review_of_systems.positive_count} positive
              </span>
              {suppressed ? <span className="badge">Ayurvedic assessment · on file</span> : null}
            </div>
          </section>
        </div>

        <EvidencePanel
          view={view}
          onClose={() => setView(null)}
          collapsed={evCollapsed}
          onToggle={() => setEvCollapsed((v) => !v)}
        />
      </div>

      <form className="actionbar" onSubmit={ask}>
        <input
          className="qin"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about this patient — “what happened during his last visit?”"
          aria-label="Ask about this patient"
        />
        <button type="button" className="btn" onClick={openCarryForward}>
          Carry forward
        </button>
        <button
          type="button"
          className={`btn ${finalised ? "btn-primary" : ""}`}
          onClick={() => setPrinting(true)}
        >
          Patient sheet
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => setLedgerOpen(true)}
          disabled={finalised}
        >
          {finalised ? "Finalised" : "Confirm and finalise"}
        </button>
      </form>

      </div>

      {printing ? (
        <PrintSheet
          patient={snap.patient}
          chiefComplaint={s.chief_complaint.text.value}
          rationale={rationale}
          advice={advice}
          medicines={medicines}
          notes={notes}
          followUp={followUpDate}
          shareToken={shareToken}
          onClose={() => setPrinting(false)}
        />
      ) : null}

      {carry ? (
        <CarryForwardModal
          data={carry}
          onCancel={() => setCarry(null)}
          onApply={(groups) => {
            setCarried(groups);
            setCarriedFrom(carry.from_date);
            setCarry(null);
          }}
        />
      ) : null}

      {ledgerOpen ? (
        <LedgerModal
          patientName={snap.patient.name}
          saving={saving}
          onCancel={() => setLedgerOpen(false)}
          onSave={commitLedger}
        />
      ) : null}
    </div>
  );
}

function Item({ value, sub, source, onOpen, muted }) {
  return (
    <p className={`item ${muted ? "muted" : ""}`}>
      <span className="txt">
        {value}
        {sub ? <span className="sub mk-deva"> {sub}</span> : null}
      </span>
      <SourceChip source={source} onOpen={onOpen} />
    </p>
  );
}

/* The ledger records "7 days"; the sheet prints a date the patient can read. */
function dateFromTimeframe(tf) {
  if (!tf) return null;
  const m = /^(\d+)\s*(day|week|month)/i.exec(tf);
  if (!m) return null;
  const n = Number(m[1]);
  const d = new Date();
  if (/day/i.test(m[2])) d.setDate(d.getDate() + n);
  if (/week/i.test(m[2])) d.setDate(d.getDate() + n * 7);
  if (/month/i.test(m[2])) d.setMonth(d.getMonth() + n);
  return d.toISOString().slice(0, 10);
}

function fmtDate(iso) {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
