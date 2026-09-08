/* Real sign-in — replaces the earlier stopgap that silently authenticated
   every session as the demo doctor account. Specialty isn't chosen here:
   it's fixed at signup and comes back from the server on every login. */

import { useState } from "react";
import { login } from "../api/client.js";

export default function Login({ onLoggedIn, onGoToSignup }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const profile = await login(username.trim(), password);
      onLoggedIn(profile);
    } catch (err) {
      setError(err.message || "Could not sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card" onSubmit={submit}>
        <span className="applogo">MediKiosk</span>
        <h1 className="auth-title">Doctor sign in</h1>

        <label className="auth-field">
          <span className="set-label">Username</span>
          <input
            className="prof-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>

        <label className="auth-field">
          <span className="set-label">Password</span>
          <input
            className="prof-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>

        {error ? <p className="set-limit warn">{error}</p> : null}

        <button type="submit" className="btn btn-primary auth-submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>

        <p className="auth-switch">
          New here?{" "}
          <button type="button" className="btn-quiet auth-link" onClick={onGoToSignup}>
            Create a doctor account
          </button>
        </p>
      </form>
    </div>
  );
}
