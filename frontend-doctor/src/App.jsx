/* App shell.

   The frame is pinned to the viewport and only the content region scrolls.
   That single structural choice is most of what separates something that
   feels like an application from something that feels like a web page: the
   chrome never moves, back is always in the same place, and a long patient
   record does not push the header off screen.

   Five destinations, no router — the console moves home → clinic → encounter
   and home → patients → patient, and a router buys nothing at this size. */

import { useEffect, useState } from "react";
import Home from "./screens/Home.jsx";
import Queue from "./screens/Queue.jsx";
import Encounter from "./screens/Encounter.jsx";
import Patients from "./screens/Patients.jsx";
import PatientDetail from "./screens/PatientDetail.jsx";
import Settings from "./screens/Settings.jsx";
import SyncStatus from "./components/SyncStatus.jsx";
import { fetchQueue } from "./api/client.js";

const TITLES = {
  home: "Home",
  clinic: "Ayurveda OPD",
  patients: "Patients",
  patient: "Patient record",
  settings: "Settings",
};

export default function App() {
  const [view, setView] = useState("home");
  const [encounterId, setEncounterId] = useState(null);
  const [patientId, setPatientId] = useState(null);
  const [clinicTab, setClinicTab] = useState("queue");
  const [showAyush, setShowAyush] = useState(true);
  const [patients, setPatients] = useState([]);

  useEffect(() => {
    let alive = true;
    fetchQueue()
      .then((q) => alive && setPatients(q.patients))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  /* One definition of "back", so every screen behaves the same way. */
  const back = (() => {
    if (view === "clinic" && encounterId) return { label: "Queue", go: () => setEncounterId(null) };
    if (view === "patient") return { label: "Patients", go: () => setView("patients") };
    if (view !== "home") return { label: "Home", go: () => goHome() };
    return null;
  })();

  function goHome() {
    setView("home");
    setEncounterId(null);
    setPatientId(null);
  }

  return (
    <div className="app">
      <header className="appbar">
        {back ? (
          <button type="button" className="backbtn" onClick={back.go}>
            <span aria-hidden="true">‹</span> {back.label}
          </button>
        ) : (
          <span className="applogo">MediKiosk</span>
        )}

        <span className="apptitle">{TITLES[view]}</span>

        <nav className="appnav" aria-label="Sections">
          <button type="button" className={`navbtn ${view === "home" ? "on" : ""}`} onClick={goHome}>
            Home
          </button>
          <button
            type="button"
            className={`navbtn ${view === "clinic" ? "on" : ""}`}
            onClick={() => {
              setPatientId(null);
              setClinicTab("queue");
              setView("clinic");
            }}
          >
            Clinic
          </button>
          <button
            type="button"
            className={`navbtn ${view === "patients" || view === "patient" ? "on" : ""}`}
            onClick={() => {
              setEncounterId(null);
              setView("patients");
            }}
          >
            Patients
          </button>
          <button
            type="button"
            className={`navbtn ${view === "settings" ? "on" : ""}`}
            onClick={() => setView("settings")}
          >
            Settings
          </button>
        </nav>

        <SyncStatus />
      </header>

      <main className="appmain">
        {view === "home" ? (
          <Home
            onEnterClinic={() => {
              setClinicTab("queue");
              setView("clinic");
            }}
            onOpenDueBack={() => {
              setClinicTab("due");
              setView("clinic");
            }}
            onOpenPatients={() => setView("patients")}
            onOpenSettings={() => setView("settings")}
          />
        ) : null}

        {view === "settings" ? (
          <Settings showAyush={showAyush} onToggleAyush={setShowAyush} onBack={goHome} />
        ) : null}

        {view === "patients" ? (
          <Patients
            onOpen={(id) => {
              setPatientId(id);
              setView("patient");
            }}
          />
        ) : null}

        {view === "patient" ? (
          <PatientDetail
            patientId={patientId}
            onOpenEncounter={(id) => {
              setEncounterId(id);
              setView("clinic");
            }}
            onBack={() => setView("patients")}
          />
        ) : null}

        {view === "clinic" && !encounterId ? (
          <Queue tab={clinicTab} onTab={setClinicTab} onOpen={setEncounterId} />
        ) : null}

        {view === "clinic" && encounterId ? (
          <Encounter
            encounterId={encounterId}
            showAyush={showAyush}
            patients={patients}
            onSelectPatient={setEncounterId}
            onBack={() => setEncounterId(null)}
          />
        ) : null}
      </main>
    </div>
  );
}
