"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { documentApi } from "@/api/documentApi";
import type { UploadSession } from "@/api/types";
import { DocumentCard } from "@/components/DocumentCard";
import { ErrorState } from "@/components/ErrorState";
import { Icon } from "@/components/Icon";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { QrCode } from "@/components/QrCode";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

const POLL_INTERVAL_MS = 2000;

/**
 * Build spec §6.12 — QR to the patient's own phone.
 *
 * The patient does not feed paper into the kiosk. The kiosk shows a code, the
 * phone does the scanning, and the document service does everything after
 * that. Nothing here touches a file: this screen only ever sees status.
 */
export function DocumentUploadScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { patient, dispatch } = usePatientSession();
  const ready = useJourneyGuard("complaint");

  const [session, setSession] = useState<UploadSession | null>(null);
  const [failed, setFailed] = useState(false);
  const creatingRef = useRef(false);

  const createSession = useCallback(async () => {
    if (!patient || creatingRef.current) return;
    creatingRef.current = true;
    setFailed(false);

    try {
      const created = await documentApi.createUploadSession(patient.session_id);
      setSession(created);
      dispatch({ type: "setDocumentSession", session: created });
    } catch (error) {
      console.warn("[documents] could not create upload session", error);
      setFailed(true);
    } finally {
      creatingRef.current = false;
    }
  }, [patient, dispatch]);

  useEffect(() => {
    if (ready && !session) void createSession();
  }, [ready, session, createSession]);

  // Poll for the phone. A websocket would be tidier; polling is honest about
  // the fact that the real document service's push story is not agreed yet.
  useEffect(() => {
    if (!session || session.status === "expired") return;

    const timer = setInterval(async () => {
      try {
        const latest = await documentApi.getUploadSession(session.token);
        setSession(latest);
        dispatch({ type: "setDocumentSession", session: latest });
      } catch (error) {
        console.warn("[documents] status poll failed", error);
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [session, dispatch]);

  if (!ready) return null;

  const documents = session?.documents ?? [];
  const expired = session?.status === "expired";
  // The phone inherits the language the patient already chose, so they are
  // not handed an English page after picking Hindi on the kiosk.
  const phoneUrl = session ? `${session.upload_url}?lang=${language}` : "";

  const statusLabel = expired
    ? t("documents.expired")
    : documents.length > 0
      ? t(documents.length === 1 ? "documents.received" : "documents.receivedPlural", {
          count: documents.length,
        })
      : session?.status === "connected"
        ? t("documents.connected")
        : t("documents.waiting");

  function finish() {
    dispatch({ type: "setIntakeComplete", complete: true });
    router.push(ROUTES.complete);
  }

  return (
    <KioskScreen
      step="documents"
      align="top"
      actions={
        <>
          <BackButton onClick={() => router.push(ROUTES.intake)} label={t("common.back")} />
          <button
            type="button"
            className="mk-btn mk-btn--ghost"
            onClick={() => {
              dispatch({ type: "skipDocuments" });
              finish();
            }}
          >
            {t("documents.noPhone")}
          </button>
          <div className="mk-actionbar__spacer" />
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--lg"
            disabled={documents.length === 0}
            onClick={finish}
          >
            <Icon name="check" />
            {t("documents.finish")}
          </button>
        </>
      }
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight mk-center">
          <h1 className="mk-h1">{t("documents.title")}</h1>
          <p className="mk-lead">{t("documents.subtitle")}</p>
        </div>

        {failed && (
          <ErrorState
            title={t("error.title")}
            message={t("error.offline")}
            actions={
              <button type="button" className="mk-btn mk-btn--secondary" onClick={createSession}>
                <Icon name="refresh" />
                {t("common.retry")}
              </button>
            }
          />
        )}

        {!session && !failed && <ProcessingState label={t("common.pleaseWait")} />}

        {session && (
          <div className="mk-upload">
            <div className="mk-upload__qr">
              {expired ? (
                <div className="mk-stack mk-center">
                  <p className="mk-lead">{t("documents.expired")}</p>
                  <button
                    type="button"
                    className="mk-btn mk-btn--primary"
                    onClick={() => {
                      setSession(null);
                      void createSession();
                    }}
                  >
                    <Icon name="refresh" />
                    {t("documents.newCode")}
                  </button>
                </div>
              ) : (
                <>
                  <QrCode value={phoneUrl} size={280} />
                  <p className="mk-meta mk-center">{t("documents.orVisit")}</p>
                  <p className="mk-meta mk-center mk-upload__url">{phoneUrl}</p>
                </>
              )}
            </div>

            <div className="mk-upload__side mk-stack">
              <ol className="mk-steplist">
                {[t("documents.step1"), t("documents.step2"), t("documents.step3")].map((step, index) => (
                  <li key={step} className="mk-steplist__item">
                    <span className="mk-steplist__num mk-num">{index + 1}</span>
                    {step}
                  </li>
                ))}
              </ol>

              <div className="mk-upload__status" data-active={documents.length > 0}>
                {documents.length === 0 && !expired && <span className="mk-spinner mk-spinner--sm" />}
                {documents.length > 0 && <Icon name="check" strokeWidth={3} />}
                <span>{statusLabel}</span>
              </div>

              {documents.length > 0 && (
                <ul className="mk-stack mk-stack--tight">
                  {documents.map((document) => (
                    <DocumentCard key={document.document_id} document={document} />
                  ))}
                </ul>
              )}

              <p className="mk-meta">{t("documents.staffHelp")}</p>

              {process.env.NODE_ENV === "development" && !expired && (
                <a className="mk-meta" href={phoneUrl} target="_blank" rel="noreferrer">
                  dev: open the phone page in a new tab →
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </KioskScreen>
  );
}
