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

/* There is no login screen yet — a real gap, not something to fake in this
   client. Until one exists, authenticate once with the same demo doctor
   credentials the backend's own test suite uses, and attach the token to
   every protected call. Replace this with a real sign-in flow. */
let tokenPromise = null;
async function getToken() {
  if (USE_MOCKS) return null;
  if (!tokenPromise) {
    tokenPromise = fetch("/api/auth/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: "username=doctor_opd_101&password=doc%40MediK2026",
    })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`auth failed: ${res.status}`))))
      .then((data) => data.access_token);
  }
  return tokenPromise;
}

async function authHeaders() {
  const token = await getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function get(path) {
  const res = await fetch(path, { headers: { Accept: "application/json", ...(await authHeaders()) } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json();
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
  return fetch(`/api/encounters/${encounterId}/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify({ question }),
  }).then((r) => r.json());
}

export async function saveLedger(encounterId, entry) {
  if (USE_MOCKS) {
    await sleep(400);
    console.info("[mock] ledger entry saved", { encounterId, ...entry });
    return { ok: true, encounter_id: encounterId, ...entry };
  }
  return fetch(`/api/encounters/${encounterId}/ledger`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(entry),
  }).then((r) => r.json());
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
  return fetch("/api/me", {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...(await authHeaders()) },
    body: JSON.stringify(profile),
  }).then((r) => r.json());
}
