import { IdleGuard } from "@/components/IdleGuard";
import { PatientSessionProvider } from "@/context/PatientSession";

/* Everything inside this group shares one patient session. The phone upload
   route deliberately sits outside it — that device is not the kiosk and must
   never be able to read the kiosk's session.

   IdleGuard lives here rather than on each screen so an abandoned session is
   cleared from wherever the patient walked away, not only from the screens
   somebody remembered to wire it into. */

export default function KioskLayout({ children }: { children: React.ReactNode }) {
  return (
    <PatientSessionProvider>
      {children}
      <IdleGuard />
    </PatientSessionProvider>
  );
}
