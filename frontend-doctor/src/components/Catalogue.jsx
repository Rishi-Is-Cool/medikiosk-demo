/* C10 — CatalogueList. The Docon UI spec ranks this "Highest — reuse
   everywhere", and it is the same shape for advice, diagnoses, symptoms and
   investigations, so it is built once and parameterised.

   Structure, from the spec:
     search box  →  starred "most frequent" block  →  A–Z sections  →  index rail

   Frequency comes from real usage per site and per practitioner. A fixed
   "common" list ships feeling pre-baked; a ranked one feels adapted.

   Accessibility note carried from the spec: Docon distinguishes a symptom
   from a finding by border colour alone. Every item here carries a text
   label as well, so the category never depends on hue. */

import { useMemo, useRef, useState } from "react";

export default function Catalogue({
  items,
  selectedIds,
  onToggle,
  kinds,
  searchPlaceholder = "Search",
  frequentCount = 6,
  renderSecondary,
}) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const sectionRefs = useRef({});

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((it) => {
      if (kind !== "all" && it.kind !== kind) return false;
      if (!q) return true;
      return (
        it.text.toLowerCase().includes(q) ||
        (it.hi ?? "").includes(query.trim()) ||
        (it.aliases ?? []).some((a) => a.toLowerCase().includes(q))
      );
    });
  }, [items, query, kind]);

  const searching = query.trim().length > 0;

  const frequent = useMemo(
    () => [...filtered].sort((a, b) => b.used_count - a.used_count).slice(0, frequentCount),
    [filtered, frequentCount]
  );

  /* A–Z sections over everything that is not already in the frequent block —
     the spec keeps the full list reachable behind the starred set. */
  const sections = useMemo(() => {
    const freqIds = new Set(frequent.map((f) => f.id));
    const rest = filtered.filter((f) => !freqIds.has(f.id));
    const map = new Map();
    for (const it of [...rest].sort((a, b) => a.text.localeCompare(b.text))) {
      const letter = it.text[0].toUpperCase();
      if (!map.has(letter)) map.set(letter, []);
      map.get(letter).push(it);
    }
    return [...map.entries()];
  }, [filtered, frequent]);

  const letters = sections.map(([l]) => l);

  return (
    <div className="cat">
      <div className="cat-controls">
        <input
          className="cat-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={searchPlaceholder}
          aria-label={searchPlaceholder}
        />
        {kinds?.length ? (
          <div className="cat-filters" role="group" aria-label="Filter by type">
            <button
              type="button"
              className={`filter ${kind === "all" ? "on" : ""}`}
              aria-pressed={kind === "all"}
              onClick={() => setKind("all")}
            >
              All
            </button>
            {kinds.map((k) => (
              <button
                key={k.key}
                type="button"
                className={`filter ${kind === k.key ? "on" : ""}`}
                aria-pressed={kind === k.key}
                onClick={() => setKind(k.key)}
              >
                {k.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {!filtered.length ? (
        <p className="cat-empty">Nothing matches “{query}”.</p>
      ) : (
        <div className="cat-body">
          <div className="cat-main">
            <h4 className="cat-grouph">
              {searching ? "Best matches" : "★ Most frequent here"}
            </h4>
            <div className="cat-grid">
              {frequent.map((it) => (
                <CatItem
                  key={it.id}
                  it={it}
                  on={selectedIds.has(it.id)}
                  onToggle={onToggle}
                  kinds={kinds}
                  renderSecondary={renderSecondary}
                />
              ))}
            </div>

            {sections.map(([letter, group]) => (
              <section
                key={letter}
                ref={(el) => (sectionRefs.current[letter] = el)}
                className="cat-section"
              >
                <h4 className="cat-letter">{letter}</h4>
                <div className="cat-grid">
                  {group.map((it) => (
                    <CatItem
                      key={it.id}
                      it={it}
                      on={selectedIds.has(it.id)}
                      onToggle={onToggle}
                      kinds={kinds}
                      renderSecondary={renderSecondary}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>

          {letters.length > 1 ? (
            <nav className="cat-index" aria-label="Jump to letter">
              {letters.map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() =>
                    sectionRefs.current[l]?.scrollIntoView({ block: "nearest", behavior: "smooth" })
                  }
                >
                  {l}
                </button>
              ))}
            </nav>
          ) : null}
        </div>
      )}
    </div>
  );
}

function CatItem({ it, on, onToggle, kinds, renderSecondary }) {
  const kindLabel = kinds?.find((k) => k.key === it.kind)?.label;
  return (
    <button
      type="button"
      className={`cat-item ${on ? "on" : ""}`}
      data-kind={it.kind}
      aria-pressed={on}
      onClick={() => onToggle(it)}
    >
      {/* text label, not just a border colour — see the accessibility note above */}
      {kindLabel ? <span className="cat-kind">{kindLabel}</span> : null}
      <span className="cat-text">
        {it.text}
        {renderSecondary ? renderSecondary(it) : null}
      </span>
      <span className="cat-count mk-num">{it.used_count}</span>
    </button>
  );
}
