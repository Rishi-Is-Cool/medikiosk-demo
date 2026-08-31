/* Docon #10 — a reusable advice library, read as pathya (to follow) and
   apathya (to avoid).

   Docon ships this as generic prewritten instruction lines for a GP. The
   payoff is much higher here: dietary and conduct guidance is a far larger
   share of an Ayurvedic consultation than of an allopathic one, and it is
   currently the part most often lost to handwriting.

   Two things follow from that:
   - entries are coded, not free text, so they can be printed in the patient's
     own language and counted in aggregate reporting
   - the most-used block is frequency-ranked (Docon #05) from real usage, so
     the common case is one tap */

import { useEffect, useMemo, useState } from "react";
import { fetchAdviceLibrary } from "../api/client.js";

const KIND_LABEL = { pathya: "Pathya", apathya: "Apathya" };

export default function AdvicePanel({ selected, onChange, language = "hi" }) {
  const [library, setLibrary] = useState([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    let alive = true;
    fetchAdviceLibrary().then((l) => alive && setLibrary(l));
    return () => {
      alive = false;
    };
  }, []);

  const chosen = useMemo(() => new Set(selected.map((s) => s.id)), [selected]);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return library.filter((a) => {
      if (filter !== "all" && a.kind !== filter) return false;
      if (!q) return true;
      return a.text.toLowerCase().includes(q) || a.hi.includes(query.trim());
    });
  }, [library, query, filter]);

  const searching = query.trim().length > 0 || filter !== "all";
  const mostUsed = matches.slice(0, 5);
  const rest = matches.slice(5);

  function toggle(item) {
    onChange(
      chosen.has(item.id) ? selected.filter((s) => s.id !== item.id) : [...selected, item]
    );
  }

  return (
    <section className="band advice" aria-labelledby="advice-h">
      <h2 className="bandhead" id="advice-h">
        Pathya · apathya — advice for this encounter
      </h2>

      {selected.length ? (
        <ul className="advice-chosen">
          {selected.map((s) => (
            <li key={s.id} className="advice-pick" data-kind={s.kind}>
              <span className="advice-kind">{KIND_LABEL[s.kind]}</span>
              <span className="advice-text">
                {s.text}
                {language === "hi" ? <span className="advice-hi mk-deva">{s.hi}</span> : null}
              </span>
              <button
                type="button"
                className="advice-remove"
                aria-label={`Remove ${s.text}`}
                onClick={() => toggle(s)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="advice-empty">
          Nothing added yet. Advice is printed on the patient's sheet in their own language.
        </p>
      )}

      <div className="advice-controls">
        <input
          className="advice-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search advice — “warm water”, “दही”"
          aria-label="Search the advice library"
        />
        <div className="advice-filters" role="group" aria-label="Filter by type">
          {["all", "pathya", "apathya"].map((f) => (
            <button
              key={f}
              type="button"
              className={`filter ${filter === f ? "on" : ""}`}
              aria-pressed={filter === f}
              onClick={() => setFilter(f)}
            >
              {f === "all" ? "All" : KIND_LABEL[f]}
            </button>
          ))}
        </div>
      </div>

      {!matches.length ? (
        <p className="advice-empty">No advice matches “{query}”.</p>
      ) : (
        <>
          <h3 className="advice-grouph">{searching ? "Matches" : "Most used here"}</h3>
          <div className="advice-grid">
            {mostUsed.map((a) => (
              <AdviceButton key={a.id} a={a} on={chosen.has(a.id)} onToggle={toggle} />
            ))}
          </div>

          {rest.length ? (
            <details className="advice-more">
              <summary>Full library · {rest.length} more</summary>
              <div className="advice-grid">
                {rest.map((a) => (
                  <AdviceButton key={a.id} a={a} on={chosen.has(a.id)} onToggle={toggle} />
                ))}
              </div>
            </details>
          ) : null}
        </>
      )}
    </section>
  );
}

function AdviceButton({ a, on, onToggle }) {
  return (
    <button
      type="button"
      className={`advice-opt ${on ? "on" : ""}`}
      data-kind={a.kind}
      aria-pressed={on}
      onClick={() => onToggle(a)}
    >
      <span className="advice-kind">{KIND_LABEL[a.kind]}</span>
      <span className="advice-text">{a.text}</span>
      <span className="advice-count mk-num">{a.used_count}</span>
    </button>
  );
}
