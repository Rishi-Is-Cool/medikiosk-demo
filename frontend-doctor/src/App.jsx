/* Two screens, no router — the console only ever goes queue → encounter →
   queue, and a router is a dependency that buys nothing at this size.

   showAyush models the doctor's display preference. In production it is
   derived from the practitioner type on their HPR record and applied
   server-side; the switch here exists so the behaviour is demonstrable. */

import { useState } from "react";
import Queue from "./screens/Queue.jsx";
import Encounter from "./screens/Encounter.jsx";

export default function App() {
  const [encounterId, setEncounterId] = useState(null);
  const [showAyush, setShowAyush] = useState(true);

  return (
    <div className="app">
      <div className="devbar">
        <span className="devbar-label">Practitioner view</span>
        <label className="devbar-toggle">
          <input
            type="checkbox"
            checked={showAyush}
            onChange={(e) => setShowAyush(e.target.checked)}
          />
          {showAyush ? "Ayurveda — constitutional block shown" : "Modern medicine — suppressed"}
        </label>
        <span className="devbar-note">
          Derived from HPR practitioner type in production; applied server-side.
        </span>
      </div>

      {encounterId ? (
        <Encounter
          encounterId={encounterId}
          showAyush={showAyush}
          onBack={() => setEncounterId(null)}
        />
      ) : (
        <Queue onOpen={setEncounterId} />
      )}
    </div>
  );
}
