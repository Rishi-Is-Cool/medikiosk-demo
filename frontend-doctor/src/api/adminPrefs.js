/* Per-viewer only (localStorage, not synced anywhere) — how often the admin
   dashboard tabs re-poll the backend. Read once at mount by each tab rather
   than watched live, so changing it takes effect next time that tab loads,
   the same way most settings screens work. */

const REFRESH_KEY = "medikiosk_admin_refresh_ms";
const DEFAULT_REFRESH_MS = 30000;
export const REFRESH_OPTIONS = [
  { ms: 15000, label: "15 seconds" },
  { ms: 30000, label: "30 seconds" },
  { ms: 60000, label: "1 minute" },
  { ms: 0, label: "Manual only" },
];

export function getRefreshMs() {
  const stored = localStorage.getItem(REFRESH_KEY);
  // No preference saved yet vs. explicitly set to 0 ("Manual only") look
  // identical after Number(null) === 0 — check for "nothing saved" first,
  // or a first-time admin silently gets manual-only instead of the default.
  if (stored === null) return DEFAULT_REFRESH_MS;
  const ms = Number(stored);
  return REFRESH_OPTIONS.some((o) => o.ms === ms) ? ms : DEFAULT_REFRESH_MS;
}

export function setRefreshMs(ms) {
  localStorage.setItem(REFRESH_KEY, String(ms));
}
