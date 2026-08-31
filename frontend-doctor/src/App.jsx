/* Four destinations, no router — the console only moves home → clinic →
   encounter → back, and a router is a dependency that buys nothing at this
   size.

   The shape follows Docon's S1: the EMR is not the app root. You enter the
   clinic as a mode and leave it again, which is what makes "Enter OPD" a
   real decision rather than a page you land on.

   showAyush models the doctor's display preference. In production it derives
   from the practitioner type on their HPR record and is applied server-side;
   the Settings toggle exists so the behaviour is demonstrable. */

import { useEffect, useState } from "react";
import Home from "./screens/Home.jsx";
import Queue from "./screens/Queue.jsx";
import Encounter from "./screens/Encounter.jsx";
import Settings from "./screens/Settings.jsx";
import SyncStatus from "./components/SyncStatus.jsx";
import { fetchQueue } from "./api/client.js";

export default function App() {
  const [view, setView] = useState("home");        // home | clinic | settings
  const [encounterId, setEncounterId] = useState(null);
  const [clinicTab, setClinicTab] = useState("queue");
  const [showAyush, setShowAyush] = useState(true);
  const [patients, setPatients] = useState([]);

  /* The rail needs the full list wherever the doctor is, so it is fetched
     once here rather than per screen. */
  useEffect(() => {
    let alive = true;
    fetchQueue()
      .then((q) => alive && setPatients(q.patients))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  return (
    <div className="app">
      <div className="appbar">
        <button
          type="button"
          className={`crumb ${view === "home" ? "on" : ""}`}
          onClick={() => {
            setView("home");
            setEncounterId(null);
          }}
        >
          MediKiosk
        </button>
        {view !== "home" ? (
          <>
            <span className="crumb-sep">/</span>
            <span className="crumb on">{view === "settings" ? "Settings" : "Ayurveda OPD"}</span>
          </>
        ) : null}
        <span className="spacer" />
        <SyncStatus />
      </div>

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
          onOpenSettings={() => setView("settings")}
        />
      ) : null}

      {view === "settings" ? (
        <Settings showAyush={showAyush} onToggleAyush={setShowAyush} onBack={() => setView("home")} />
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
    </div>
  );
}
