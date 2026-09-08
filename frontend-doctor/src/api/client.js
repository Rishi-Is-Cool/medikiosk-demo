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

export async function login(username, password) {
  const res = await fetch("/api/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
  });
  if (!res.ok) throw new Error(res.status === 401 ? "Incorrect username or password." : `Could not sign in (${res.status}).`);
  const { access_token: token } = await res.json();
  storeSession(token, null);
  const profile = await fetchDoctorProfile();
  storeSession(token, profile);
  return profile;
}

export async function registerDoctor({ username, password, name, practitionerType, qualifications }) {
  const res = await fetch("/api/auth/register-doctor", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, name, practitioner_type: practitionerType, qualifications: qualifications || null }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(typeof detail?.detail === "string" ? detail.detail : `Could not create the account (${res.status}).`);
  }
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
  return res.json();
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
