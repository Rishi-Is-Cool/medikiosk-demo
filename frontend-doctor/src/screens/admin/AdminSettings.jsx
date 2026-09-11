/* What's actually adjustable here, honestly: there's no admin-editable
   hospital configuration in the data model today (roster, departments,
   routing rules are all set elsewhere) — the one real preference is how
   often the dashboard tabs re-poll, which every other admin tab reads via
   adminPrefs.js. Padding this out with settings that don't do anything
   would be worse than a short screen. */

import { useState } from "react";
import { logout, getStoredProfile } from "../../api/client.js";
import { getRefreshMs, setRefreshMs, REFRESH_OPTIONS } from "../../api/adminPrefs.js";

export default function AdminSettings() {
  const profile = getStoredProfile();
  const [refresh, setRefresh] = useState(getRefreshMs());

  function onChangeRefresh(ms) {
    setRefreshMs(ms);
    setRefresh(ms);
  }

  return (
    <div className="overview">
      <section className="ov-group">
        <h2 className="qsec">Account</h2>
        <div className="settings-card">
          <div className="settings-row">
            <span className="settings-label">Signed in as</span>
            <span className="mk-num">
              {profile?.name}
              {profile?.username && profile.username !== profile.name ? ` (${profile.username})` : ""}
            </span>
          </div>
          <div className="settings-row">
            <span className="settings-label">Role</span>
            <span>Hospital admin / reception</span>
          </div>
          <button type="button" className="btn" onClick={logout}>
            Log out
          </button>
        </div>
      </section>

      <section className="ov-group">
        <h2 className="qsec">Dashboard refresh</h2>
        <div className="settings-card">
          <p className="ov-empty" style={{ padding: 0, marginBottom: "var(--space-2)" }}>
            How often Home, Rooms and the Waiting Room re-check the backend. Takes effect next time a tab loads.
          </p>
          <div className="settings-options">
            {REFRESH_OPTIONS.map((o) => (
              <label key={o.ms} className="settings-option">
                <input type="radio" name="refresh" checked={refresh === o.ms} onChange={() => onChangeRefresh(o.ms)} />
                {o.label}
              </label>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
