import { PatientSessionProvider } from "@/context/PatientSession";

/* Everything inside this group shares one patient session. The phone upload
   route deliberately sits outside it — that device is not the kiosk and must
   never be able to read the kiosk's session. */

export default function KioskLayout({ children }: { children: React.ReactNode }) {
  return <PatientSessionProvider>{children}</PatientSessionProvider>;
}
