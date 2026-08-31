/* Alerts arrive as their own top-level array from the API, never embedded in
   the clinical sections — they are produced by deterministic rules, not the
   LLM, and the payload shape is what makes that auditable. */

import SourceChip from "./SourceChip.jsx";

const SEV_LABEL = { critical: "CRITICAL", warning: "WARNING", info: "INFO" };

export default function AlertBar({ alerts, onOpenSource }) {
  if (!alerts?.length) return null;

  return (
    <div className="alerts">
      {alerts.map((a) => (
        <div key={a.alert_id} className="mk-alert alert-row" data-sev={a.severity} role="alert">
          <span className="sev">{SEV_LABEL[a.severity] ?? a.severity}</span>
          <span className="alert-text">
            <strong>{a.headline}</strong>
            {a.detail ? <span className="alert-detail"> — {a.detail}</span> : null}
          </span>
          {a.conflicting_sources?.length ? (
            <span className="alert-srcs">
              {a.conflicting_sources.map((s, i) => (
                <SourceChip key={`${s.id}-${i}`} source={s} onOpen={onOpenSource} />
              ))}
            </span>
          ) : null}
        </div>
      ))}
    </div>
  );
}
