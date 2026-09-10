/* Renders if and only if the API returned a non-null ayush block. There is no
   flag to fall out of sync with the data: suppression happens server-side from
   the doctor's practitioner type, so an allopathic viewer never receives this.

   EDITABLE, not read-only. The problem statement is explicit that the summary
   is "a draft to accept, amend, or reject" and that the physician "retains
   full control" — a panel the doctor cannot correct fails that outright. The
   kiosk's reading of Sattva is a patient self-report; the practitioner in the
   room is the authority on it.

   The Docon UI spec (S8) puts this on the symptoms screen with a filter rail
   of body systems. Here the axes themselves are the structure, so each one is
   a three-way segmented control over the classical grading. */

import { useState } from "react";
import SourceChip from "./SourceChip.jsx";

const GRADES = [
  { key: "avara", label: "Avara", hint: "least" },
  { key: "madhyama", label: "Madhyama", hint: "moderate" },
  { key: "pravara", label: "Pravara", hint: "optimum" },
];

export default function DashavidhaPanel({ ayush, onOpenSource, onEdit }) {
  const [edits, setEdits] = useState({});

  if (!ayush?.captured) return null;

  function setGrade(item, grade) {
    if (grade === current(item)) return;
    setEdits({ ...edits, [item.key]: grade });
    onEdit?.({ key: item.key, grade, previous: item.grade });
  }

  const current = (item) => edits[item.key] ?? item.grade;
  const edited = (item) => edits[item.key] !== undefined;

  return (
    <section className="band" aria-labelledby="dashavidha-h">
      <h2 className="bandhead" id="dashavidha-h">
        Dashavidha pariksha · captured at kiosk · tap to amend
      </h2>

      <div className="dosha">
        <span className="dosha-label mk-deva">Prakriti</span>
        <span
          className="dosha-bar"
          role="img"
          aria-label={`Vata ${ayush.prakriti.components.vata} percent, Pitta ${ayush.prakriti.components.pitta} percent, Kapha ${ayush.prakriti.components.kapha} percent`}
        >
          <span className="seg vata" style={{ width: `${ayush.prakriti.components.vata}%` }}>V</span>
          <span className="seg pitta" style={{ width: `${ayush.prakriti.components.pitta}%` }}>P</span>
          <span className="seg kapha" style={{ width: `${ayush.prakriti.components.kapha}%` }}>K</span>
        </span>
        <span className="dosha-value">{ayush.prakriti.value}</span>
        <SourceChip source={ayush.prakriti.source} onOpen={onOpenSource} />
      </div>

      <dl className="dash-grid">
        {ayush.graded.map((g) => {
          const grade = current(g);
          const isEdited = edited(g);
          return (
            <div className="dv" key={g.key} data-edited={isEdited || undefined}>
              <dt>
                {g.label}
                <SourceChip
                  source={isEdited ? { type: "clinician", id: "current_user" } : g.source}
                  onOpen={isEdited ? undefined : onOpenSource}
                />
              </dt>
              <dd data-grade={grade}>
                {/* Always visible: a popup inside a narrow card overflows it,
                    and this is one tap instead of two. Order is fixed
                    least → optimum so position encodes the value. */}
                <div className="grades" role="radiogroup" aria-label={`${g.label} grade`}>
                  {GRADES.map((opt) => (
                    <button
                      key={opt.key}
                      type="button"
                      role="radio"
                      aria-checked={grade === opt.key}
                      className={`grade-seg ${grade === opt.key ? "on" : ""}`}
                      data-grade={opt.key}
                      title={`${opt.label} — ${opt.hint}`}
                      onClick={() => setGrade(g, opt.key)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
              </dd>
              {isEdited ? (
                <p className="dv-edited">
                  Amended from <span>{g.grade}</span> — kiosk reading kept in the record
                </p>
              ) : null}
            </div>
          );
        })}
      </dl>
    </section>
  );
}
