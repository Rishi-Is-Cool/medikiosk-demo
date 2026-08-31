/* The take-home sheet.

   Docon prints a prescription pad. This prints the patient's own summary —
   what they were told, their pathya/apathya advice in their own language, and
   when to come back. That choice follows the problem statement: the users are
   elderly, low-literacy and often first-visit, and the thing most often lost
   to handwriting is the diet and conduct guidance, not the drug list.

   The letterhead is the doctor profile rendered, not markup — every
   deployment prints under a different institution's name, and a profile edit
   should never require a code change.

   The QR resolves to the patient's own ABHA-linked record. Docon's resolves
   into a private silo; the right shape, the wrong destination. */

import { useEffect, useState } from "react";
import { fetchDoctorProfile } from "../api/client.js";
import { fmt } from "../screens/Patients.jsx";

const SAMPLE_ADVICE = [
  { kind: "pathya", text: "Drink lukewarm water through the day", hi: "दिनभर गुनगुना पानी पिएँ" },
  { kind: "apathya", text: "Avoid curd at night", hi: "रात में दही से परहेज़ करें" },
  { kind: "pathya", text: "Light, warm, freshly cooked meals", hi: "हल्का, गर्म, ताज़ा बना भोजन लें" },
];

export default function PrintSheet({ patient, advice = SAMPLE_ADVICE, followUp, onClose }) {
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    fetchDoctorProfile().then(setProfile);
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!profile) return null;
  const next = followUp ?? patient.next_appointment;

  return (
    <div className="scrim" role="presentation">
      <div className="print-wrap" role="dialog" aria-modal="true" aria-labelledby="ps-h">
        <div className="print-bar no-print">
          <h2 id="ps-h">Patient sheet</h2>
          <span className="print-note">Printed in {profile.languages.includes("hi") ? "Hindi and English" : "English"}</span>
          <span className="spacer" />
          <button type="button" className="btn" onClick={onClose}>Close</button>
          <button type="button" className="btn btn-primary" onClick={() => window.print()}>Print</button>
        </div>

        <div className="sheet" id="print-area">
          {/* letterhead — this whole block is profile data */}
          <header className="sheet-head">
            <p className="sheet-clinic">{profile.clinic_name}</p>
            {profile.tagline ? <p className="sheet-tagline mk-deva">{profile.tagline}</p> : null}
            {profile.slogan ? <p className="sheet-slogan">“{profile.slogan}”</p> : null}
            <p className="sheet-doc">{profile.name}</p>
            <p className="sheet-quals">{profile.qualifications}</p>
            <p className="sheet-title">{profile.title}</p>
            <p className="sheet-addr">{profile.address}</p>
          </header>

          <div className="sheet-pt">
            <span><b>{patient.name}</b> · {patient.age_years} y · {patient.sex === "female" ? "Female" : "Male"}</span>
            <span className="mk-num">ABHA {patient.abha_id}</span>
            <span className="mk-num">{fmt(new Date().toISOString())}</span>
          </div>

          <section className="sheet-block">
            <h3>आपके लिए सलाह <span className="sheet-en">Advice for you</span></h3>
            <ul className="sheet-advice">
              {advice.map((a, i) => (
                <li key={i} data-kind={a.kind}>
                  <span className="sheet-mark" aria-hidden="true">{a.kind === "pathya" ? "✓" : "✕"}</span>
                  <span>
                    <span className="sheet-hi mk-deva">{a.hi}</span>
                    <span className="sheet-en-line">{a.text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {next ? (
            <section className="sheet-block sheet-next">
              <h3>अगली मुलाक़ात <span className="sheet-en">Come back on</span></h3>
              <p className="sheet-date mk-num">{fmt(next)}</p>
            </section>
          ) : null}

          <footer className="sheet-foot">
            <div className="sheet-qr" aria-hidden="true">
              <QrPlaceholder />
            </div>
            <p className="sheet-qr-note">
              इस QR को स्कैन करके अपना रिकॉर्ड देखें
              <span className="sheet-en-line">
                Scan to open this visit in your own ABHA health record. Nothing is stored on this sheet.
              </span>
            </p>
            <p className="sheet-reg mk-num">{profile.registration}</p>
          </footer>
        </div>
      </div>
    </div>
  );
}

/* A drawn placeholder, not a real code — wiring this to an actual ABHA
   deep link is Kartik's endpoint plus a QR library, and a fake code that
   scans to nothing would be worse than an obvious placeholder. */
function QrPlaceholder() {
  const cells = [];
  for (let y = 0; y < 9; y++) {
    for (let x = 0; x < 9; x++) {
      const corner = (x < 3 && y < 3) || (x > 5 && y < 3) || (x < 3 && y > 5);
      const on = corner ? !(x % 2 === 1 && y % 2 === 1) : (x * 7 + y * 3) % 3 === 0;
      if (on) cells.push(<rect key={`${x}-${y}`} x={x * 6} y={y * 6} width="6" height="6" />);
    }
  }
  return (
    <svg viewBox="0 0 54 54" width="72" height="72" role="img" aria-label="QR code placeholder">
      <g fill="currentColor">{cells}</g>
    </svg>
  );
}
