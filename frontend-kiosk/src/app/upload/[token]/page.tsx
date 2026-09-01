import type { LanguageCode } from "@/api/types";
import { LanguageProvider } from "@/i18n/LanguageProvider";
import { LANGUAGES, DEFAULT_LANGUAGE } from "@/i18n/languages";
import { MobileUploadScreen } from "@/screens/MobileUploadScreen";

/* The page the QR opens on the patient's phone (build spec §6.13).

   Outside the kiosk route group on purpose: it gets its own language context
   from the URL and has no access to the kiosk's patient session. All it holds
   is an opaque upload token. */

export default async function UploadPage({
  params,
  searchParams,
}: {
  params: Promise<{ token: string }>;
  searchParams: Promise<{ lang?: string }>;
}) {
  const { token } = await params;
  const { lang } = await searchParams;

  const language: LanguageCode =
    LANGUAGES.find((l) => l.code === lang && l.translated)?.code ?? DEFAULT_LANGUAGE;

  return (
    <LanguageProvider language={language}>
      <MobileUploadScreen token={token} />
    </LanguageProvider>
  );
}
