/* Borrowed from Docon (#08): one column per visit, not a single-visit form.
   Ayurvedic measures share the grid with biomedical ones because change over
   time is what an Ayurvedic assessment is for — a flat list discards it. */

import SourceChip from "./SourceChip.jsx";

export default function TrendTable({ trend, onOpenSource }) {
  if (!trend?.groups?.length) return null;
  const last = trend.dates.length - 1;

  return (
    <div className="table-scroll">
      <table className="trend">
        <thead>
          <tr>
            <th className="rowlab">Measure</th>
            {trend.dates.map((d, i) => (
              <th key={d} className={i === last ? "today" : undefined}>
                {d}
                {i === last ? " · today" : ""}
              </th>
            ))}
            <th className="rowref">Reference</th>
            <th className="rowsrc"><span className="sr-only">Source</span></th>
          </tr>
        </thead>
        <tbody>
          {trend.groups.map((g) => (
            <FragmentGroup key={g.label} group={g} last={last} onOpenSource={onOpenSource} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FragmentGroup({ group, last, onOpenSource }) {
  return (
    <>
      <tr className="grp">
        <td colSpan={99}>{group.label}</td>
      </tr>
      {group.rows.map((r) => (
        <tr key={r.key}>
          <td className="rowlab">{r.label}</td>
          {r.values.map((v, i) => (
            <td
              key={i}
              className={["num", i === last ? "today" : "", r.flags?.[i] ?? ""].filter(Boolean).join(" ")}
            >
              {v ?? "—"}
              {r.flags?.[i] === "high" ? " \u2191" : r.flags?.[i] === "low" ? " \u2193" : ""}
            </td>
          ))}
          <td className="rng">{r.ref}</td>
          <td className="rowsrc"><SourceChip source={r.source} onOpen={onOpenSource} /></td>
        </tr>
      ))}
    </>
  );
}
