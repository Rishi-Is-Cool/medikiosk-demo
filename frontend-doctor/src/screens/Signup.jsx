/* Open self-serve doctor signup. Specialty is chosen once, here, and is
   permanent from this screen's point of view — it decides which console
   (Ayurveda OPD or General Medicine OPD) this account opens into on every
   future login, and which patients ever reach it. See app/api/auth.py's
   register-doctor endpoint: practitioner_type is not editable afterward. */

import { useState } from "react";
import { registerDoctor } from "../api/client.js";

const SPECIALTIES = [
  { value: "general", label: "General Medicine", help: "SOCRATES history, standard review of systems." },
  { value: "ayurveda", label: "Ayurveda / AYUSH", help: "Dashavidha pariksha, Prakriti and Vikriti capture." },
];

export default function Signup({ onSignedUp, onGoToLogin }) {
  const [name, setName] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [practitionerType, setPractitionerType] = useState("general");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    setSubmitting(true);
    try {
      const profile = await registerDoctor({ username: username.trim(), password, name: name.trim(), practitionerType });
      onSignedUp(profile);
    } catch (err) {
      setError(err.message || "Could not create the account.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <span className="applogo">MediKiosk</span>
        <h1 className="auth-title">Create a doctor account</h1>

        <label className="auth-field">
          <span className="set-label">Full name</span>
          <input className="prof-input" value={name} onChange={(e) => setName(e.target.value)} autoFocus required />
        </label>

        <label className="auth-field">
          <span className="set-label">Username</span>
          <input className="prof-input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>

        <label className="auth-field">
          <span className="set-label">
            Password
            <span className="set-help">At least 6 characters.</span>
          </span>
          <input
            className="prof-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>

        <fieldset className="auth-field auth-specialty">
          <legend className="set-label">
            Specialty
            <span className="set-help">Fixed once you sign up — sets which console you see and which patients reach you.</span>
          </legend>
          {SPECIALTIES.map((s) => (
            <label key={s.value} className={`auth-specialty-option ${practitionerType === s.value ? "on" : ""}`}>
              <input
                type="radio"
                name="practitioner_type"
                value={s.value}
                checked={practitionerType === s.value}
                onChange={() => setPractitionerType(s.value)}
              />
              <span>
                <strong>{s.label}</strong>
                <span className="set-help">{s.help}</span>
              </span>
            </label>
          ))}
        </fieldset>

        {error ? <p className="set-limit warn">{error}</p> : null}

        <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </button>

        <p className="auth-switch">
          Already have an account?{" "}
          <button type="button" className="btn-quiet auth-link" onClick={onGoToLogin}>
            Sign in
          </button>
        </p>
      </form>
    </div>
  );
}
