/* Every network call the console makes goes through here.
   Flip VITE_USE_MOCKS to 0 once Kartik's FastAPI is serving these routes —
   no component changes, the shapes are already identical to
   shared/snapshot-contract.json. */

import { QUEUE, SNAPSHOTS, DOCUMENT_BODIES } from "./mock.js";

const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "0";
const LATENCY_MS = 220; // keep the loading states honest during development

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function get(path) {
  const res = await fetch(path, { headers: { Accept: "application/json" } });
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
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(entry),
  }).then((r) => r.json());
}
