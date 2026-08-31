/* Zone 3. One panel, three contents — a source document, the last-visit
   record, or a Q&A answer. None of these is a separate destination, because a
   doctor with two minutes will not navigate. */

import SourceChip from "./SourceChip.jsx";

export default function EvidencePanel({ view, onClose, collapsed, onToggle }) {
  /* Collapsed it is a 44px rail, the mirror of the patient list on the left.
     An empty panel holding 38% of the width is width the clinical content
     should have. */
  if (collapsed) {
    return (
      <aside className="evidence evidence-collapsed" aria-label="Evidence">
        <button
          type="button"
          className="ev-toggle"
          onClick={onToggle}
          aria-label="Show evidence panel"
          aria-expanded="false"
          title="Show evidence panel"
        >
          <span aria-hidden="true">‹</span>
        </button>
        <span className="ev-spine">Evidence</span>
        {view ? <span className="ev-dot" aria-label="Evidence is open" /> : null}
      </aside>
    );
  }

  return (
    <aside className="evidence" aria-label="Evidence">
      <header className="evhead">
        <h2 className="evtitle">{view?.title ?? "Evidence"}</h2>
        <span className="spacer" />
        {view ? (
          <button type="button" className="btn btn-quiet" onClick={onClose}>
            Clear
          </button>
        ) : null}
        <button
          type="button"
          className="ev-toggle"
          onClick={onToggle}
          aria-label="Collapse evidence panel"
          aria-expanded="true"
          title="Collapse evidence panel"
        >
          <span aria-hidden="true">›</span>
        </button>
      </header>

      <div className="evbody">
        {!view ? (
          <p className="ev-empty">
            Select any <span className="mk-chip-src" data-src="document">DOC</span> chip to see the record
            it came from, with the extracted field marked.
          </p>
        ) : null}

        {view?.kind === "loading" ? <p className="ev-empty">Loading…</p> : null}

        {view?.kind === "document" ? (
          <>
            <p className="evsrc">{view.doc.dated}</p>
            <pre className="scan">
              {view.doc.lines.map((l, i) => (
                <span key={i} className={l.field && l.field === view.field ? "boxed" : undefined}>
                  {l.text}
                  {"\n"}
                </span>
              ))}
            </pre>
            <p className="evnote">
              <strong>Why this opened.</strong> The highlighted line is the field the snapshot claim
              was extracted from — the doctor verifies the source without leaving the console.
            </p>
          </>
        ) : null}

        {view?.kind === "encounter" ? (
          <>
            <p className="evsrc">{view.date}</p>
            <p className="ev-para">{view.summary}</p>
          </>
        ) : null}

        {view?.kind === "answer" ? (
          <>
            <p className="ev-question">{view.question}</p>
            <p className="ev-para">{view.answer}</p>
            <p className="ev-sources">
              Answered from{" "}
              {view.sources.map((s, i) => (
                <SourceChip key={i} source={s} />
              ))}
            </p>
          </>
        ) : null}

        {view?.kind === "unavailable" ? (
          <p className="ev-empty">
            This claim came from the patient speaking at the kiosk. There is no document behind it —
            that is what the <span className="mk-chip-src" data-src="patient_spoken">MIC</span> chip means.
          </p>
        ) : null}
      </div>
    </aside>
  );
}
