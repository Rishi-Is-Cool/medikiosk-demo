/* Pravara / Madhyama / Avara is a genuine three-level ordinal scale, so it
   renders as three pips rather than a colour alone — position carries the
   value for anyone who cannot separate the hues. */

const FILLED = { pravara: 3, madhyama: 2, avara: 1 };
const TONE = { pravara: "high", madhyama: "mid", avara: "low" };

export default function GradePips({ grade }) {
  const filled = FILLED[grade] ?? 0;
  const tone = TONE[grade] ?? "mid";
  return (
    <span className="pips" role="img" aria-label={`${grade}, ${filled} of 3`}>
      {[0, 1, 2].map((i) => (
        <span key={i} className="pip" data-on={i < filled ? tone : "off"} />
      ))}
    </span>
  );
}
