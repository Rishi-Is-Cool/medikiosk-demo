/* Every network call the console makes goes through here.
   Flip VITE_USE_MOCKS to 0 once Kartik's FastAPI is serving these routes —
   no component changes, the shapes are already identical to
   shared/snapshot-contract.json. */

import {
  QUEUE,
  SNAPSHOTS,
  DOCUMENT_BODIES,
  CARRY_FORWARD,
  ADVICE_LIBRARY,
  DUE_BACK,
  PATIENT_DIRECTORY,
  PATIENT_RECORDS,
  DOCTOR_PROFILE,
  MEDICINE_CATALOG,
  PRESCRIPTION_TEMPLATES,
} from "./mock.js";

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "0";
const LATENCY_MS = 220; // keep the loading states honest during development

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* --- Session -------------------------------------------------------------
   A real login/signup flow, replacing the earlier stopgap that always
   authenticated as the demo doctor account. Token + profile are cached in
   localStorage so a reload doesn't force a re-login; a 401 from any
   protected call clears the session and fires "medikiosk:logged-out" so
   App.jsx can drop back to the Login screen. In mock mode there is no
   session to manage — the app behaves as it always has. */
const TOKEN_KEY = "medikiosk_doctor_token";
const PROFILE_KEY = "medikiosk_doctor_profile";

export function getStoredToken() {
  return USE_MOCKS ? null : localStorage.getItem(TOKEN_KEY);
}

export function getStoredProfile() {
  if (USE_MOCKS) return structuredClone(DOCTOR_PROFILE);
  try {
    return JSON.parse(localStorage.getItem(PROFILE_KEY) || "null");
  } catch {
    return null;
  }
}

export function isLoggedIn() {
  return USE_MOCKS || Boolean(getStoredToken());
}

function storeSession(token, profile) {
  localStorage.setItem(TOKEN_KEY, token);
  if (profile) localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(PROFILE_KEY);
  window.dispatchEvent(new Event("medikiosk:logged-out"));
}

async function authHeaders() {
  const token = getStoredToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Every protected fetch funnels through here so a 401 always ends the session
 *  the same way, instead of each call handling it (or not) independently. */
async function guarded(res) {
  if (res.status === 401) logout();
  return res;
}

async function get(path) {
  const res = await guarded(await fetch(path, { headers: { Accept: "application/json", ...(await authHeaders()) } }));
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json();
}

async function send(method, path, body) {
  const res = await guarded(await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: body === undefined ? undefined : JSON.stringify(body),
  }));
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.status === 204 ? null : res.json();
}

/* FastAPI's validation-error body shapes `detail` as a list of
   {loc, msg, type} objects, not a string — the register-doctor form used to
   show a bare "(422)" for e.g. a too-short username because it only handled
   the string case. This reads either shape into one readable line. */
async function _authErrorMessage(res, fallback) {
  const detail = await res.json().catch(() => null);
  if (typeof detail?.detail === "string") return detail.detail;
  if (Array.isArray(detail?.detail) && detail.detail.length) {
    return detail.detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
        const label = typeof field === "string" ? field[0].toUpperCase() + field.slice(1) : null;
        return label ? `${label}: ${d.msg}` : d.msg || JSON.stringify(d);
      })
      .join("; ");
  }
  return `${fallback} (${res.status}).`;
}

export async function login(username, password) {
  if (USE_MOCKS) {
    await sleep(400);
    const profile = await fetchDoctorProfile();
    return profile;
  }
  const res = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
  });
  if (!res.ok) throw new Error(res.status === 401 ? "Incorrect username or password." : await _authErrorMessage(res, "Could not sign in"));
  const { access_token: token } = await res.json();
  storeSession(token, null);
  const profile = await fetchDoctorProfile();
  storeSession(token, profile);
  return profile;
}

export async function registerDoctor({ username, password, name, practitionerType, qualifications }) {
  if (USE_MOCKS) {
    await sleep(400);
    const profile = await fetchDoctorProfile();
    profile.name = name;
    profile.practitioner_type = practitionerType;
    return profile;
  }
  const res = await fetch("/api/auth/register-doctor", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, name, practitioner_type: practitionerType, qualifications: qualifications || null }),
  });
  if (!res.ok) throw new Error(await _authErrorMessage(res, "Could not create the account"));
  const { access_token: token } = await res.json();
  storeSession(token, null);
  const profile = await fetchDoctorProfile();
  storeSession(token, profile);
  return profile;
}

export async function fetchQueue() {
  if (USE_MOCKS) {
    await sleep(LATENCY_MS);
    return structuredClone(QUEUE);
  }
  return get("/api/queue");
}

/* viewerShowsAyush mirrors the doctor's display preference. The real endpoint
   applies it server-side and returns ayush: null — we replicate that here so
   the component never learns to expect data it should not receive. */
export async function fetchSnapshot(encounterId, { viewerShowsAyush = true } = {}) {
  if (USE_MOCKS) {
    await sleep(LATENCY_MS);
    const snap = structuredClone(SNAPSHOTS[encounterId]);
    if (!snap) throw new Error(`No snapshot fixture for ${encounterId}`);
    if (!viewerShowsAyush && snap.ayush) {
      snap.ayush = null;
      snap.ayush_status = "suppressed_by_viewer";
      snap.trend.groups = snap.trend.groups.filter((g) => !g.ayush_only);
    }
    return snap;
  }
  return get(`/api/encounters/${encounterId}/snapshot`);
}

export async function fetchDocument(documentId) {
  if (USE_MOCKS) {
    await sleep(120);
    return structuredClone(DOCUMENT_BODIES[documentId] ?? null);
  }
  return get(`/api/documents/${documentId}`);
}

export async function askQuestion(encounterId, question) {
  if (USE_MOCKS) {
    await sleep(600);
    return {
      answer:
        "At the last visit on 14 Mar 2026 the patient was discharged following community-acquired pneumonia. Metformin 500mg BD and Amlodipine 5mg OD were continued, and review was advised in 4 weeks.",
      sources: [{ type: "prior_encounter", id: "enc_20260314_0088" }],
      question,
    };
  }
  const res = await guarded(await fetch(`/api/encounters/${encounterId}/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ question }),
  }));
  return res.json();
}

export async function saveLedger(encounterId, entry) {
  if (USE_MOCKS) {
    await sleep(400);
    console.info("[mock] ledger entry saved", { encounterId, ...entry });
    return { ok: true, encounter_id: encounterId, ...entry };
  }
  const res = await guarded(await fetch(`/api/encounters/${encounterId}/ledger`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(entry),
  }));
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — could not save the ledger entry`);
  return res.json();
}

/* The actual end of a consultation — removes the patient from GET /api/queue
   and mints the share_token the patient sheet's QR code points at. Must run
   after saveLedger, which finalize requires at least one ledger entry to exist. */
export async function finalizeEncounter(encounterId) {
  if (USE_MOCKS) {
    await sleep(250);
    return { ok: true, encounter_id: encounterId, status: "finalized", share_token: `mock_${encounterId}` };
  }
  return send("POST", `/api/encounters/${encounterId}/finalize`);
}

/* The URL the patient sheet's QR code encodes. Same "needs a real LAN/public
   address for a phone to actually reach it" caveat frontend-kiosk documents
   for NEXT_PUBLIC_KIOSK_PUBLIC_ORIGIN — window.location.origin is fine for a
   doctor viewing their own screen, but a phone scanning the printed sheet
   needs the deployment's real address, set via VITE_PUBLIC_BACKEND_ORIGIN. */
export function publicVisitUrl(shareToken) {
  const origin = import.meta.env.VITE_PUBLIC_BACKEND_ORIGIN || window.location.origin;
  return `${origin}/api/public/visit/${shareToken}`;
}

/* --- Docon-derived endpoints ------------------------------------------- */

export async function fetchCarryForward(encounterId) {
  if (USE_MOCKS) {
    await sleep(180);
    return structuredClone(CARRY_FORWARD[encounterId] ?? null);
  }
  return get(`/api/encounters/${encounterId}/carry-forward`);
}

/* Frequency ranking is applied server-side in production, per site and per
   practitioner from actual usage — a fixed "common" list feels pre-baked. */
export async function fetchAdviceLibrary() {
  if (USE_MOCKS) {
    await sleep(140);
    return structuredClone(ADVICE_LIBRARY).sort((a, b) => b.used_count - a.used_count);
  }
  return get("/api/advice-library");
}

export async function fetchDueBack() {
  if (USE_MOCKS) {
    await sleep(200);
    return structuredClone(DUE_BACK).sort((a, b) => b.days_overdue - a.days_overdue);
  }
  return get("/api/reports/due-back");
}

export async function fetchPatients() {
  if (USE_MOCKS) {
    await sleep(200);
    return structuredClone(PATIENT_DIRECTORY);
  }
  return get("/api/patients");
}

export async function fetchPatientRecord(patientId) {
  if (USE_MOCKS) {
    await sleep(180);
    const p = PATIENT_DIRECTORY.find((x) => x.patient_id === patientId);
    if (!p) throw new Error(`No patient ${patientId}`);
    return structuredClone({ ...p, ...(PATIENT_RECORDS[patientId] ?? { timeline: [], appointments: [] }) });
  }
  return get(`/api/patients/${patientId}`);
}

export async function fetchDoctorProfile() {
  if (USE_MOCKS) {
    await sleep(80);
    return structuredClone(DOCTOR_PROFILE);
  }
  return get("/api/me");
}

export async function saveDoctorProfile(profile) {
  if (USE_MOCKS) {
    await sleep(300);
    Object.assign(DOCTOR_PROFILE, profile);
    return structuredClone(DOCTOR_PROFILE);
  }
  const res = await guarded(await fetch("/api/me", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(profile),
  }));
  const saved = await res.json();
  // practitioner_type can't change from here (server-enforced), but keep the
  // cached profile in sync for everything else that was edited.
  if (!USE_MOCKS) storeSession(getStoredToken(), saved);
  return saved;
}

/* --- Prescribing: medicine catalog + templates --------------------------
   Both are specialty-scoped server-side (a general doctor never receives
   Ayurvedic formulation names or vice versa), and templates are further
   scoped to the logged-in doctor — the mocks reuse one fixed list since
   there's only ever one demo doctor signed in at a time. */

export async function fetchMedicines(query = "") {
  if (USE_MOCKS) {
    await sleep(140);
    const q = query.trim().toLowerCase();
    return structuredClone(MEDICINE_CATALOG)
      .filter((m) => !q || m.name.toLowerCase().includes(q))
      .sort((a, b) => b.used_count - a.used_count);
  }
  return get(`/api/medicines${query ? `?q=${encodeURIComponent(query)}` : ""}`);
}

export async function fetchTemplates() {
  if (USE_MOCKS) {
    await sleep(140);
    return structuredClone(PRESCRIPTION_TEMPLATES);
  }
  return get("/api/templates");
}

export async function createTemplate(template) {
  if (USE_MOCKS) {
    await sleep(250);
    const saved = { id: `tpl_mock_${Date.now()}`, ...template };
    PRESCRIPTION_TEMPLATES.push(saved);
    return structuredClone(saved);
  }
  return send("POST", "/api/templates", template);
}

export async function updateTemplate(templateId, template) {
  if (USE_MOCKS) {
    await sleep(250);
    const i = PRESCRIPTION_TEMPLATES.findIndex((t) => t.id === templateId);
    if (i >= 0) PRESCRIPTION_TEMPLATES[i] = { ...PRESCRIPTION_TEMPLATES[i], ...template };
    return structuredClone(PRESCRIPTION_TEMPLATES[i]);
  }
  return send("PUT", `/api/templates/${templateId}`, template);
}

export async function deleteTemplate(templateId) {
  if (USE_MOCKS) {
    await sleep(200);
    const i = PRESCRIPTION_TEMPLATES.findIndex((t) => t.id === templateId);
    if (i >= 0) PRESCRIPTION_TEMPLATES.splice(i, 1);
    return null;
  }
  return send("DELETE", `/api/templates/${templateId}`);
}
