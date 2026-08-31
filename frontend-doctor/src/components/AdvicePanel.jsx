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
import Catalogue from "./Catalogue.jsx";

const KIND_LABEL = { pathya: "Pathya", apathya: "Apathya" };

export default function AdvicePanel({ selected, onChange, language = "hi" }) {
  const [library, setLibrary] = useState([]);

  useEffect(() => {
    let alive = true;
    fetchAdviceLibrary().then((l) => alive && setLibrary(l));
    return () => {
      alive = false;
    };
  }, []);

  const chosen = useMemo(() => new Set(selected.map((s) => s.id)), [selected]);

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

      <Catalogue
        items={library}
        selectedIds={chosen}
        onToggle={toggle}
        kinds={[
          { key: "pathya", label: "Pathya" },
          { key: "apathya", label: "Apathya" },
        ]}
        searchPlaceholder="Search advice — “warm water”, “दही”"
        renderSecondary={(a) =>
          language === "hi" ? <span className="advice-hi mk-deva">{a.hi}</span> : null
        }
      />
    </section>
  );
}
