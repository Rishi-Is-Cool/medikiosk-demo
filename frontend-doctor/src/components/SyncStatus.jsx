/* Docon #04 — records stay readable when the network drops.
   A kiosk in a PHC will lose connectivity mid-encounter, and a system that
   silently discards work will not be trusted twice. The state has to be
   visible: what has reached the server, and what has not. */

import { useEffect, useState } from "react";

export default function SyncStatus() {
  const [online, setOnline] = useState(navigator.onLine);
  const [queued, setQueued] = useState(0);

  useEffect(() => {
    const up = () => {
      setOnline(true);
      setQueued(0);
    };
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);

  // While offline, writes accumulate locally rather than failing.
  useEffect(() => {
    if (online) return undefined;
    const t = setInterval(() => setQueued((q) => q + 1), 8000);
    return () => clearInterval(t);
  }, [online]);

  return (
    <span className="sync" data-state={online ? "online" : "offline"}>
      <span className="sync-dot" aria-hidden="true" />
      {online
        ? "All changes saved"
        : `Offline — ${queued} change${queued === 1 ? "" : "s"} queued locally`}
    </span>
  );
}
