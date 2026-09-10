/* The take-home sheet — a complete patient summary, not just a prescription
   pad: what the patient came in with, what the doctor made of it, what to
   take, and what to do. In order: chief complaint (their own condition, in
   brief), the doctor's assessment (only when treatment changed and a
   rationale was recorded — nothing invented when there isn't one), medicines,
   then pathya/apathya diet and conduct advice and any free-text note as the
   doctor's instructions. That last part follows the problem statement: the
   users are elderly, low-literacy and often first-visit, and diet/conduct
   guidance is what's most often lost to handwriting — so it stays prominent
   even though the sheet is no longer drug-list-free.

   The letterhead is the doctor profile rendered, not markup — every
   deployment prints under a different institution's name, and a profile edit
   should never require a code change.

   Bilingual is a property of the patient, not the doctor: whether Hindi
   prints alongside English depends on what the patient actually chose on
   the kiosk (patient.preferred_language), the same signal AdvicePanel
   already keys off during the encounter — not the doctor's own profile
   languages, which say nothing about who is reading this sheet.

   The QR resolves to /api/public/visit/{share_token} — a real, unauthenticated
   page built from this same encounter's finalized record. It only exists once
   the encounter is finalized (finalize is what mints the token), so a sheet
   opened earlier for a preview falls back to a placeholder rather than
   encoding a URL that doesn't work yet. */

import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { fetchDoctorProfile, publicVisitUrl } from "../api/client.js";
import { fmt } from "../screens/Patients.jsx";

export default function PrintSheet({ patient, chiefComplaint, rationale, advice = [], medicines = [], notes, followUp, shareToken, onClose }) {
  const [profile, setProfile] = useState(null);
  const [qrDataUrl, setQrDataUrl] = useState(null);

  useEffect(() => {
    fetchDoctorProfile().then(setProfile);
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!shareToken) {
      setQrDataUrl(null);
      return;
    }
    let alive = true;
    QRCode.toDataURL(publicVisitUrl(shareToken), { margin: 1, width: 144 })
      .then((url) => alive && setQrDataUrl(url))
      .catch(() => alive && setQrDataUrl(null));
    return () => {
      alive = false;
    };
  }, [shareToken]);

  if (!profile) return null;
  const next = followUp ?? patient.next_appointment;
  const bilingual = patient.preferred_language === "hi";

  return (
    <div className="scrim" role="presentation">
      <div className="print-wrap" role="dialog" aria-modal="true" aria-labelledby="ps-h">
        <div className="print-bar no-print">
          <h2 id="ps-h">Patient sheet</h2>
          <span className="print-note">Printed in {bilingual ? "Hindi and English" : "English"}</span>
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

          {chiefComplaint ? (
            <section className="sheet-block">
              <h3>{bilingual ? <>मरीज़ की स्थिति <span className="sheet-en">Patient's condition</span></> : "Patient's condition"}</h3>
              <p className="sheet-notes">{chiefComplaint}</p>
            </section>
          ) : null}

          {rationale ? (
            <section className="sheet-block">
              <h3>{bilingual ? <>डॉक्टर की राय <span className="sheet-en">Doctor's assessment</span></> : "Doctor's assessment"}</h3>
              <p className="sheet-notes">{rationale}</p>
            </section>
          ) : null}

          {medicines.length ? (
            <section className="sheet-block">
              <h3>{bilingual ? <>दवाएँ <span className="sheet-en">Medicines</span></> : "Medicines"}</h3>
              <ul className="sheet-meds">
                {medicines.map((m, i) => (
                  <li key={i}>
                    <span className="sheet-med-name">{m.name}</span>
                    <span className="sheet-med-detail">
                      {[m.dosage, m.frequency, m.duration].filter(Boolean).join(" · ")}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <section className="sheet-block">
            <h3>{bilingual ? <>आपके लिए सलाह <span className="sheet-en">Advice for you</span></> : "Advice for you"}</h3>
            {!advice.length ? (
              <p className="sheet-none">
                No advice was recorded for this visit.
                {bilingual ? (
                  <span className="sheet-en-line">
                    Add pathya and apathya during the encounter and it prints here in the patient's language.
                  </span>
                ) : null}
              </p>
            ) : null}
            <ul className="sheet-advice">
              {advice.map((a, i) => (
                <li key={i} data-kind={a.kind}>
                  <span className="sheet-mark" aria-hidden="true">{a.kind === "pathya" ? "✓" : "✕"}</span>
                  <span>
                    {bilingual ? <span className="sheet-hi mk-deva">{a.hi}</span> : null}
                    <span className={bilingual ? "sheet-en-line" : ""}>{a.text}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          {notes ? (
            <section className="sheet-block">
              <h3>{bilingual ? <>डॉक्टर की टिप्पणी <span className="sheet-en">Doctor's note</span></> : "Doctor's note"}</h3>
              <p className="sheet-notes">{notes}</p>
            </section>
          ) : null}

          {next ? (
            <section className="sheet-block sheet-next">
              <h3>{bilingual ? <>अगली मुलाक़ात <span className="sheet-en">Come back on</span></> : "Come back on"}</h3>
              <p className="sheet-date mk-num">{fmt(next)}</p>
            </section>
          ) : null}

          <footer className="sheet-foot">
            <div className="sheet-qr" aria-hidden="true">
              {qrDataUrl ? <img src={qrDataUrl} width="72" height="72" alt="" /> : <QrPlaceholder />}
            </div>
            <p className="sheet-qr-note">
              {shareToken ? (
                <>
                  {bilingual ? <>इस QR को स्कैन करके अपनी विज़िट देखें<br /></> : null}
                  <span className={bilingual ? "sheet-en-line" : ""}>
                    Scan to view this visit summary on your own phone. Nothing else is shared.
                  </span>
                </>
              ) : (
                <span className={bilingual ? "sheet-en-line" : ""}>
                  This sheet isn't finalised yet — finalise the encounter to generate a scannable code.
                </span>
              )}
            </p>
            <p className="sheet-reg mk-num">{profile.registration}</p>
          </footer>
        </div>
      </div>
    </div>
  );
}

/* Shown only until the encounter is finalized (finalize mints the
   share_token the real QR encodes) — an honest "not ready yet" placeholder,
   not a fake code that would scan to nothing. */
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
