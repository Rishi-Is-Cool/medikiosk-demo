/* S18 — settings as a left nav rail plus a content pane.

   Docon's rail reads General · Profile · Patient Queue Management · Bank
   Details · Letterhead · Prescription · Signature · Medication · Billing ·
   App. Bank Details and Billing are a private clinic's commercial surface and
   are dropped; the rest map onto things an institutional deployment needs.

   The rail is the point, not the contents: it is the same two-pane shape as
   the encounter screen, so a doctor never learns a second navigation model. */

import { useEffect, useState } from "react";
import { fetchDoctorProfile, saveDoctorProfile } from "../api/client.js";
import { initials } from "./Patients.jsx";

const SECTIONS = [
  { key: "profile", label: "Your profile" },
  { key: "practitioner", label: "Practitioner view" },
  { key: "queue", label: "Queue and triage" },
  { key: "modules", label: "Department modules" },
  { key: "terminology", label: "Terminology" },
  { key: "letterhead", label: "Letterhead and signature" },
  { key: "app", label: "About" },
];

export default function Settings({ showAyush, onToggleAyush, onBack }) {
  const [active, setActive] = useState("profile");

  return (
    <div className="settings">
      <header className="set-top">
        <button type="button" className="btn btn-quiet" onClick={onBack}>
          ← Home
        </button>
        <h1 className="set-title">Settings</h1>
      </header>

      <div className="set-body">
        <nav className="set-rail" aria-label="Settings sections">
          {SECTIONS.map((s) => (
            <button
              key={s.key}
              type="button"
              className={`set-item ${active === s.key ? "on" : ""}`}
              aria-current={active === s.key ? "page" : undefined}
              onClick={() => setActive(s.key)}
            >
              {s.label}
            </button>
          ))}
        </nav>

        <div className="set-pane">
          {active === "profile" ? <ProfileSection /> : null}

          {active === "practitioner" ? (
            <Section
              title="Practitioner view"
              note="Defaults from your practitioner type on the HPR register. Changing it affects what the server sends you, not what is stored."
            >
              <Row
                label="Show Ayurvedic assessment"
                help="Dashavidha pariksha, Prakriti and Vikriti. Suppressed server-side when off — the data is never sent to this browser."
              >
                <label className="switch">
                  <input type="checkbox" checked={showAyush} onChange={(e) => onToggleAyush(e.target.checked)} />
                  <span>{showAyush ? "Shown" : "Hidden"}</span>
                </label>
              </Row>
              <p className="set-limit">
                This preference covers the constitutional block only. It cannot hide allergies, red flags,
                medications, conditions or abnormal results — those are always shown to every practitioner.
              </p>
            </Section>
          ) : null}

          {active === "queue" ? (
            <Section title="Queue and triage" note="How patients are ordered and when they jump the queue.">
              <Row label="Red-flag priority band" help="Flagged patients appear above the token order in their own section.">
                <span className="set-value">On — cannot be disabled</span>
              </Row>
              <Row label="Order waiting patients by" help="">
                <span className="set-value">Token number</span>
              </Row>
              <Row label="Show intake state per row" help="Ready, documents processing, intake in progress, not started.">
                <span className="set-value">On</span>
              </Row>
            </Section>
          ) : null}

          {active === "modules" ? (
            <Section
              title="Department modules"
              note="Which history frameworks this deployment offers. The kiosk question tree follows the department the patient registers for."
            >
              <Row label="Ayurveda OPD" help="Dashavidha pariksha capture, pathya/apathya advice."><span className="set-value on">Enabled</span></Row>
              <Row label="General medicine" help="SOCRATES history, standard review of systems."><span className="set-value on">Enabled</span></Row>
              <Row label="Panchakarma" help="Procedure scheduling and protocol adherence."><span className="set-value">Not enabled</span></Row>
              <Row label="Unani · Siddha · Homoeopathy" help="Each needs its own case-taking shape and vocabulary."><span className="set-value">Not enabled</span></Row>
            </Section>
          ) : null}

          {active === "terminology" ? (
            <Section
              title="Terminology"
              note="Coded terms make district-level reporting fall out of the data. Free text does not — no amount of later work recovers it."
            >
              <Row label="NAMASTE morbidity codes" help="National AYUSH Morbidity and Standardized Terminologies.">
                <span className="set-value on">Loaded</span>
              </Row>
              <Row label="ICD-11 TM2 dual coding" help="Traditional Medicine Module 2, released on the WHO browser in Feb 2025.">
                <span className="set-value on">Loaded</span>
              </Row>
              <Row label="WHO Standardised Terminologies for Ayurveda" help="Used for the examination frameworks and assessment axes.">
                <span className="set-value on">Loaded</span>
              </Row>
              <p className="set-limit warn">
                Codes are currently loaded from a public mirror, not the official portal. Verify against
                namaste.ayush.gov.in before any demonstration.
              </p>
            </Section>
          ) : null}

          {active === "letterhead" ? (
            <Section
              title="Letterhead and signature"
              note="The institution header printed on every document is configuration, not markup — every deployment prints under a different name."
            >
              <p className="set-limit">
                The letterhead is your profile, rendered. Edit it under <b>Your profile</b> — there is no
                second copy to keep in step, and nothing about it is hardcoded.
              </p>
            </Section>
          ) : null}

          {active === "app" ? (
            <Section title="About" note="">
              <Row label="Build" help=""><span className="set-value mk-num">frontend-doctor 0.1.0</span></Row>
              <Row label="Problem statement" help=""><span className="set-value">SIH26047 · Ministry of Ayush · AIIA</span></Row>
              <Row label="Data source" help="Flip VITE_USE_MOCKS to 0 once the API is serving."><span className="set-value">Fixtures</span></Row>
            </Section>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Section({ title, note, children }) {
  return (
    <section className="set-section">
      <h2>{title}</h2>
      {note ? <p className="set-note">{note}</p> : null}
      {children}
    </section>
  );
}

function Row({ label, help, children }) {
  return (
    <div className="set-row">
      <span className="set-label">
        {label}
        {help ? <span className="set-help">{help}</span> : null}
      </span>
      {children}
    </div>
  );
}


/* The profile is also the letterhead block on every printed document, which
   is why it is edited here rather than buried: a stale name prints. */
function ProfileSection() {
  const [p, setP] = useState(null);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchDoctorProfile().then((d) => {
      setP(d);
      setDraft(d);
    });
  }, []);

  if (!draft) return <p className="screen-msg">Loading profile…</p>;

  const dirty = JSON.stringify(draft) !== JSON.stringify(p);
  const set = (k) => (e) => {
    setDraft({ ...draft, [k]: e.target.value });
    setSaved(false);
  };

  async function save() {
    setSaving(true);
    const next = await saveDoctorProfile(draft);
    setP(next);
    setDraft(next);
    setSaving(false);
    setSaved(true);
  }

  return (
    <Section
      title="Your profile"
      note="This is what prints at the top of every patient sheet, advice note and referral. Changing it here changes every document."
    >
      <div className="prof-head">
        <span className="avatar avatar-lg" aria-hidden="true">{initials(draft.name)}</span>
        <div>
          <p className="prof-name">{draft.name}</p>
          <p className="prof-sub">{draft.qualifications}</p>
          <p className="prof-sub">{draft.title}</p>
        </div>
      </div>

      <Field label="Name" help="As it should appear on documents." value={draft.name} onChange={set("name")} />
      <Field label="Qualifications" help="Degrees and diplomas, comma separated." value={draft.qualifications} onChange={set("qualifications")} />
      <Field label="Title" help="Consultant Physician, Medical Officer, and so on." value={draft.title} onChange={set("title")} />
      <Field label="Registration number" help="Printed in the footer of every document." value={draft.registration} onChange={set("registration")} />
      <Field label="Institution" help="" value={draft.clinic_name} onChange={set("clinic_name")} />
      <Field label="Department" help="" value={draft.department} onChange={set("department")} />
      <Field label="Tagline" help="Optional. Printed in Devanagari beneath the institution name." value={draft.tagline} onChange={set("tagline")} />
      <Field label="Slogan" help="Optional. Printed in quotation marks." value={draft.slogan} onChange={set("slogan")} />
      <Field label="Address" help="" value={draft.address} onChange={set("address")} />

      <div className="prof-actions">
        {saved && !dirty ? <span className="prof-saved">Saved</span> : null}
        <button type="button" className="btn" disabled={!dirty} onClick={() => setDraft(p)}>
          Discard changes
        </button>
        <button type="button" className="btn btn-primary" disabled={!dirty || saving} onClick={save}>
          {saving ? "Saving…" : "Save profile"}
        </button>
      </div>
    </Section>
  );
}

function Field({ label, help, value, onChange }) {
  return (
    <div className="set-row">
      <span className="set-label">
        {label}
        {help ? <span className="set-help">{help}</span> : null}
      </span>
      <input className="prof-input" value={value ?? ""} onChange={onChange} aria-label={label} />
    </div>
  );
}
