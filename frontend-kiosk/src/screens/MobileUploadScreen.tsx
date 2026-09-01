"use client";

import { useEffect, useRef, useState } from "react";
import { documentApi } from "@/api/documentApi";
import { ApiError } from "@/api/types";
import { ErrorState } from "@/components/ErrorState";
import { Icon } from "@/components/Icon";
import { ProcessingState } from "@/components/ProcessingState";
import { useLanguage } from "@/i18n/LanguageProvider";

/**
 * Build spec §6.13 — the page the QR opens on the patient's phone.
 *
 * Deliberately the simplest screen in the product: it is being used one-handed,
 * on an unfamiliar phone, in a queue. Take a photo, check it, send it. No
 * account, no navigation, and no document AI — the file goes straight to the
 * document service, which owns every part of reading it.
 */

const MAX_BYTES = 12 * 1024 * 1024;
const ACCEPTED = "image/*,application/pdf";

type Phase = "checking" | "ready" | "preview" | "sending" | "sent" | "expired" | "error";

export function MobileUploadScreen({ token }: { token: string }) {
  const { t } = useLanguage();
  const [phase, setPhase] = useState<Phase>("checking");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [sentCount, setSentCount] = useState(0);
  const [problem, setProblem] = useState<string | null>(null);

  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);

  /* Announce the phone so the kiosk can stop saying "waiting". */
  useEffect(() => {
    let cancelled = false;

    documentApi
      .getUploadSession(token)
      .then(async (session) => {
        if (cancelled) return;
        if (session.status === "expired") {
          setPhase("expired");
          return;
        }
        await documentApi.markConnected(token).catch(() => {});
        if (!cancelled) {
          setSentCount(session.documents.length);
          setPhase("ready");
        }
      })
      .catch((error) => {
        if (cancelled) return;
        console.warn("[upload] session check failed", error);
        setPhase(error instanceof ApiError && error.code === "http_404" ? "expired" : "error");
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function choose(selected: File | undefined) {
    if (!selected) return;

    if (selected.size > MAX_BYTES) {
      setProblem(t("upload.tooLarge"));
      return;
    }
    const mime = selected.type ? selected.type.toLowerCase() : "";
    if (mime && !mime.startsWith("image/") && mime !== "application/pdf") {
      setProblem(t("upload.wrongType"));
      return;
    }

    setProblem(null);
    setFile(selected);
    setPhase("preview");
  }

  async function send() {
    if (!file) return;
    setPhase("sending");
    setProblem(null);

    try {
      await documentApi.uploadDocument(token, file);
      setSentCount((count) => count + 1);
      setFile(null);
      setPhase("sent");
    } catch (error) {
      console.warn("[upload] failed", error);
      if (error instanceof ApiError && error.code === "session_expired") {
        setPhase("expired");
        return;
      }
      setProblem(t("upload.failed"));
      setPhase("preview");
    }
  }

  function reset() {
    setFile(null);
    setProblem(null);
    setPhase("ready");
  }

  /* --- Shell --------------------------------------------------------------- */

  const shell = (children: React.ReactNode) => (
    <div className="mk-screen mk-app mk-mobile">
      <header className="mk-topbar">
        <span className="mk-topbar__brand">
          <Icon name="stethoscope" size={22} />
          MediKiosk
        </span>
      </header>
      <main className="mk-main mk-main--top">
        <div className="mk-container mk-container--narrow mk-stack mk-stack--loose">{children}</div>
      </main>
    </div>
  );

  if (phase === "checking") return shell(<ProcessingState label={t("common.pleaseWait")} />);

  if (phase === "expired") {
    return shell(
      <div className="mk-stack mk-center">
        <span className="mk-bigicon" data-tone="warning">
          <Icon name="clock" size={44} />
        </span>
        <h1 className="mk-h1">{t("upload.expiredTitle")}</h1>
        <p className="mk-lead">{t("upload.expiredBody")}</p>
      </div>,
    );
  }

  if (phase === "error") {
    return shell(<ErrorState title={t("error.title")} message={t("error.offline")} />);
  }

  if (phase === "sending") {
    return shell(<ProcessingState label={t("upload.sending")} />);
  }

  /* --- Preview ------------------------------------------------------------- */

  if (phase === "preview" && file) {
    return shell(
      <>
        <div className="mk-stack mk-stack--tight">
          <h1 className="mk-h1">{t("upload.preview")}</h1>
          <p className="mk-lead">{t("upload.previewHelp")}</p>
        </div>

        <div className="mk-preview">
          {previewUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={previewUrl} alt={file.name} />
          ) : (
            <div className="mk-preview__file">
              <Icon name="document" size={44} />
              <span>{file.name}</span>
            </div>
          )}
        </div>

        {problem && <ErrorState title={problem} />}

        <div className="mk-stack mk-stack--tight">
          <button type="button" className="mk-btn mk-btn--primary mk-btn--lg mk-btn--block" onClick={send}>
            <Icon name="check" />
            {t("upload.send")}
          </button>
          <button type="button" className="mk-btn mk-btn--secondary mk-btn--block" onClick={reset}>
            <Icon name="refresh" />
            {t("upload.retake")}
          </button>
        </div>
      </>,
    );
  }

  /* --- Ready / sent -------------------------------------------------------- */

  return shell(
    <>
      <div className="mk-stack mk-stack--tight">
        <span className="mk-pill mk-pill--success">
          <Icon name="check" size={16} strokeWidth={3} />
          {t("upload.connected")}
        </span>
        <h1 className="mk-h1">{phase === "sent" ? t("upload.sent") : t("upload.title")}</h1>
        <p className="mk-lead">{phase === "sent" ? t("upload.allDoneBody") : t("upload.instruction")}</p>
      </div>

      {problem && <ErrorState title={problem} />}

      <div className="mk-stack mk-stack--tight">
        <button
          type="button"
          className="mk-btn mk-btn--primary mk-btn--lg mk-btn--block"
          onClick={() => cameraRef.current?.click()}
        >
          <Icon name="camera" size={26} />
          {phase === "sent" ? t("upload.addAnother") : t("upload.camera")}
        </button>

        <button
          type="button"
          className="mk-btn mk-btn--secondary mk-btn--block"
          onClick={() => galleryRef.current?.click()}
        >
          <Icon name="gallery" size={26} />
          {t("upload.gallery")}
        </button>
      </div>

      {sentCount > 0 && (
        <p className="mk-help mk-center">{t("upload.sentCount", { count: sentCount })}</p>
      )}

      {phase === "sent" && (
        <div className="mk-sunken mk-center">
          <p className="mk-lead">{t("upload.allDone")}</p>
          <p className="mk-help">{t("upload.allDoneBody")}</p>
        </div>
      )}

      <input
        ref={cameraRef}
        type="file"
        accept={ACCEPTED}
        capture="environment"
        hidden
        onChange={(event) => {
          choose(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
      <input
        ref={galleryRef}
        type="file"
        accept={ACCEPTED}
        hidden
        onChange={(event) => {
          choose(event.target.files?.[0]);
          event.target.value = "";
        }}
      />
    </>,
  );
}
