/* Renders if and only if the API returned a non-null ayush block. There is no
   flag to fall out of sync with the data: suppression happens server-side from
   the doctor's practitioner type, so an allopathic viewer never receives this. */

import GradePips from "./GradePips.jsx";
import SourceChip from "./SourceChip.jsx";

export default function DashavidhaPanel({ ayush, onOpenSource }) {
  if (!ayush?.captured) return null;

  return (
    <section className="band" aria-labelledby="dashavidha-h">
      <h2 className="bandhead" id="dashavidha-h">
        Dashavidha pariksha · captured at kiosk
      </h2>

      <div className="dosha">
        <span className="dosha-label mk-deva">Prakriti</span>
        <span className="dosha-bar" role="img" aria-label={`Vata ${ayush.prakriti.components.vata} percent, Pitta ${ayush.prakriti.components.pitta} percent, Kapha ${ayush.prakriti.components.kapha} percent`}>
          <span className="seg vata" style={{ width: `${ayush.prakriti.components.vata}%` }}>V</span>
          <span className="seg pitta" style={{ width: `${ayush.prakriti.components.pitta}%` }}>P</span>
          <span className="seg kapha" style={{ width: `${ayush.prakriti.components.kapha}%` }}>K</span>
        </span>
        <span className="dosha-value">{ayush.prakriti.value}</span>
        <SourceChip source={ayush.prakriti.source} onOpen={onOpenSource} />
      </div>

      <dl className="dash-grid">
        {ayush.graded.map((g) => (
          <div className="dv" key={g.key}>
            <dt>{g.label}</dt>
            <dd data-grade={g.grade}>
              <span className="grade-word">{g.grade}</span>
              <GradePips grade={g.grade} />
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
