"use client";

const BAR_COUNT = 9;

function formatDuration(ms: number): string {
  const total = Math.floor(ms / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

/** Build spec §6.7: a clear recording indicator and the running duration.
 *  The bars respond to the actual microphone level, so a patient who is not
 *  being picked up can see it rather than discovering it after they finish. */
export function RecordingIndicator({
  durationMs,
  level,
  label,
}: {
  durationMs: number;
  level: number;
  label: string;
}) {
  return (
    <div className="mk-recording" role="status" aria-live="polite">
      <span className="mk-rec-dot" aria-hidden="true" />
      <span className="mk-recording__label">{label}</span>

      <span className="mk-recording__bars" aria-hidden="true">
        {Array.from({ length: BAR_COUNT }, (_, index) => {
          // Centre bars react most, so the meter reads as a voice rather than
          // a progress bar.
          const distance = Math.abs(index - (BAR_COUNT - 1) / 2) / ((BAR_COUNT - 1) / 2);
          const height = 18 + level * 100 * (1 - distance * 0.65);
          return (
            <span
              key={index}
              className="mk-recording__bar"
              style={{ height: `${Math.min(46, height)}%` }}
            />
          );
        })}
      </span>

      <span className="mk-num mk-recording__time">{formatDuration(durationMs)}</span>
    </div>
  );
}
