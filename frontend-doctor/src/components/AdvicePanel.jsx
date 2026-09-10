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
     the common case is one tap

   The underlying diet/conduct advice is useful to any doctor, but "pathya"
   and "apathya" are themselves Ayurvedic terms — the same reasoning that
   keeps AYUSH assessment data away from a general-medicine account (see
   Settings.jsx) says a general doctor shouldn't see that vocabulary either,
   even though the feature itself stays available to them. */

import { useEffect, useMemo, useState } from "react";
import { fetchAdviceLibrary } from "../api/client.js";
import Catalogue from "./Catalogue.jsx";

export default function AdvicePanel({ selected, onChange, language = "hi", practitionerType }) {
  const isAyurveda = practitionerType === "ayurveda";
  const KIND_LABEL = isAyurveda ? { pathya: "Pathya", apathya: "Apathya" } : { pathya: "Recommended", apathya: "Avoid" };
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
        {isAyurveda ? "Pathya · apathya — advice for this encounter" : "Advice for this encounter"}
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
          { key: "pathya", label: KIND_LABEL.pathya },
          { key: "apathya", label: KIND_LABEL.apathya },
        ]}
        searchPlaceholder="Search advice — “warm water”, “दही”"
        renderSecondary={(a) =>
          language === "hi" ? <span className="advice-hi mk-deva">{a.hi}</span> : null
        }
      />
    </section>
  );
}
