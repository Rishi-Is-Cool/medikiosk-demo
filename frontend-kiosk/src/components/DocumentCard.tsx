"use client";

import type { UploadedDocument } from "@/api/types";
import { useLanguage } from "@/i18n/LanguageProvider";
import { Icon } from "./Icon";

/* Every status here is a document that ARRIVED — "failed" means only that
   it could not be read automatically, so it is amber, never "not sent". */
const STATUS_PILL: Record<UploadedDocument["status"], string> = {
  received: "mk-pill",
  processing: "mk-pill mk-pill--warning",
  processed: "mk-pill mk-pill--success",
  failed: "mk-pill mk-pill--warning",
};

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** One received document, on the kiosk screen. Shows that it arrived — never
 *  what was read out of it. Extracted clinical content belongs on the
 *  doctor's console, not on a screen in a public foyer. */
export function DocumentCard({ document }: { document: UploadedDocument }) {
  const { t } = useLanguage();

  const statusLabel =
    document.status === "failed"
      ? t("documents.statusUnread")
      : document.status === "processed"
        ? t("documents.statusRead")
        : t("documents.statusReading");

  return (
    <li className="mk-doccard">
      <span className="mk-doccard__icon">
        <Icon name="document" size={26} />
      </span>
      <span className="mk-doccard__body">
        <span className="mk-doccard__name">{document.file_name}</span>
        <span className="mk-meta mk-num">{formatSize(document.size_bytes)}</span>
      </span>
      <span className={STATUS_PILL[document.status]}>
        {document.status === "processing" && <span className="mk-spinner mk-spinner--sm" />}
        {document.status === "processed" && <Icon name="check" size={16} strokeWidth={3} />}
        {statusLabel}
      </span>
    </li>
  );
}
