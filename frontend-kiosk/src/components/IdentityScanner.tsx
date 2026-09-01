"use client";

import { useRef, useState } from "react";
import { patientApi } from "@/api/patientApi";
import type { IdentityMethod } from "@/api/types";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ErrorState } from "./ErrorState";
import { Icon } from "./Icon";
import { ProcessingState } from "./ProcessingState";

/**
 * "Enters/scans ABHA ID" — the scan half (problem statement, step 1).
 *
 * Uses the same capture pattern as the phone document upload: a file input
 * with `capture`, which opens the rear camera on a kiosk tablet and a file
 * picker on a desktop. No live camera preview, no getUserMedia — a permission
 * prompt the patient has to understand is a worse first screen than a photo
 * they already know how to take.
 *
 * Reading the card is OCR and belongs to the document/AI layer. This uploads
 * and fills in the answer; the patient can always correct it or type instead.
 */
export function IdentityScanner({
  method,
  onScanned,
}: {
  method: IdentityMethod;
  onScanned: (identifier: string) => void;
}) {
  const { t } = useLanguage();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setBusy(true);
    setFailed(false);

    try {
      const result = await patientApi.scanIdentity(method, file);
      onScanned(result.identifier);
    } catch (error) {
      console.warn("[identity] scan failed", error);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  if (busy) return <ProcessingState label={t("register.scanning")} />;

  return (
    <div className="mk-stack mk-stack--tight">
      <button
        type="button"
        className="mk-btn mk-btn--secondary mk-btn--lg"
        onClick={() => inputRef.current?.click()}
      >
        <Icon name="camera" size={26} />
        {t("register.scan")}
      </button>
      <p className="mk-help">{t("register.scanHelp")}</p>

      {failed && (
        <ErrorState title={t("register.scanFailed")} message={t("register.scanFailedHelp")} />
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        onChange={(event) => {
          void handleFile(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </div>
  );
}
