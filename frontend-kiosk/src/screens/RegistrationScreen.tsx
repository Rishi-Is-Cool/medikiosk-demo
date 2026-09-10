"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { patientApi } from "@/api/patientApi";
import type { IdentityMethod } from "@/api/types";
import { ChoiceTile } from "@/components/ChoiceTile";
import { ErrorState } from "@/components/ErrorState";
import { Icon } from "@/components/Icon";
import { IdentityScanner } from "@/components/IdentityScanner";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { usePatientSession } from "@/context/PatientSession";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.2. All three identity paths are represented so none of them
 * needs a redesign later — but nothing here verifies anything. There is no
 * ABHA lookup and no Aadhaar check behind these fields, and the notice at the
 * bottom of the screen says so rather than implying an integration that does
 * not exist (§19).
 */
export function RegistrationScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { dispatch } = usePatientSession();

  const [method, setMethod] = useState<IdentityMethod | null>(null);
  const [identifier, setIdentifier] = useState("");
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  /** Set when the identifier came off a photographed card rather than the
   *  keypad, so the patient is asked to check it before continuing. */
  const [fromScan, setFromScan] = useState(false);

  const canSubmit =
    method === "new"
      ? name.trim().length > 1 && age.trim().length > 0 && sex.length > 0
      : identifier.trim().length > 0;

  async function submit() {
    if (!method || !canSubmit) return;
    setBusy(true);
    setFailed(false);

    try {
      const patient = await patientApi.register({
        identity_method: method,
        identifier: method === "new" ? undefined : identifier.trim(),
        language,
        new_patient: method === "new" ? { name: name.trim(), age: age.trim(), sex } : undefined,
      });
      dispatch({ type: "setPatient", patient });
      router.push(ROUTES.consent);
    } catch (error) {
      console.warn("[register] failed", error);
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  /* --- Method chooser ------------------------------------------------------ */

  if (!method) {
    return (
      <KioskScreen
        step="identity"
        align="top"
        actions={<BackButton onClick={() => router.push(ROUTES.language)} label={t("common.back")} />}
      >
        <div className="mk-container mk-stack mk-stack--loose">
          <div className="mk-stack mk-stack--tight mk-center">
            <h1 className="mk-h1">{t("register.title")}</h1>
            <p className="mk-lead">{t("register.subtitle")}</p>
          </div>

          <div className="mk-choices mk-choices--wide">
            <ChoiceTile
              icon="shield"
              label={t("register.abha")}
              sub={t("register.abhaSub")}
              showCheck={false}
              onClick={() => setMethod("abha")}
            />
            <ChoiceTile
              icon="idCard"
              label={t("register.aadhaar")}
              sub={t("register.aadhaarSub")}
              showCheck={false}
              onClick={() => setMethod("aadhaar")}
            />
            <ChoiceTile
              icon="userPlus"
              label={t("register.new")}
              sub={t("register.newSub")}
              showCheck={false}
              onClick={() => setMethod("new")}
            />
          </div>

          <p className="mk-meta mk-center">{t("register.demoNotice")}</p>
        </div>
      </KioskScreen>
    );
  }

  /* --- Details ------------------------------------------------------------- */

  return (
    <KioskScreen
      step="identity"
      align="top"
      actions={
        <>
          <BackButton
            onClick={() => {
              setMethod(null);
              setFailed(false);
              setFromScan(false);
            }}
            label={t("common.back")}
          />
          <div className="mk-actionbar__spacer" />
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--lg"
            disabled={!canSubmit || busy}
            onClick={submit}
          >
            {t("register.verify")}
            <Icon name="chevronRight" />
          </button>
        </>
      }
    >
      <div className="mk-container mk-container--narrow mk-stack mk-stack--loose">
        <h1 className="mk-h1">{t("register.title")}</h1>

        {busy ? (
          <ProcessingState label={t("register.verifying")} />
        ) : (
          <div className="mk-card mk-stack">
            {method !== "new" && (
              <>
                <IdentityScanner
                  method={method}
                  onScanned={(value) => {
                    setIdentifier(method === "aadhaar" ? value.replace(/\D/g, "").slice(-4) : value);
                    setFromScan(true);
                  }}
                />
                <p className="mk-help mk-center">{t("register.orType")}</p>
              </>
            )}

            {method === "abha" && (
              <label className="mk-field">
                <span className="mk-label">{t("register.abhaLabel")}</span>
                <input
                  className="mk-input"
                  value={identifier}
                  inputMode="text"
                  placeholder={t("register.abhaPlaceholder")}
                  onChange={(event) => {
                    setIdentifier(event.target.value);
                    setFromScan(false);
                  }}
                />
              </label>
            )}

            {method === "aadhaar" && (
              <label className="mk-field">
                <span className="mk-label">{t("register.aadhaarLabel")}</span>
                <input
                  className="mk-input"
                  value={identifier}
                  inputMode="numeric"
                  maxLength={4}
                  placeholder={t("register.aadhaarPlaceholder")}
                  onChange={(event) => {
                    setIdentifier(event.target.value.replace(/\D/g, ""));
                    setFromScan(false);
                  }}
                />
              </label>
            )}

            {/* A scanned number is a machine's reading of a photograph, not a
                verified identity. Asking the patient to confirm it costs one
                glance and prevents a whole session filed under the wrong ID. */}
            {fromScan && identifier && (
              <p className="mk-help mk-scanned">
                <Icon name="check" size={18} strokeWidth={3} />
                {t("register.scanned")}
              </p>
            )}

            {method === "new" && (
              <>
                <label className="mk-field">
                  <span className="mk-label">{t("register.nameLabel")}</span>
                  <input
                    className="mk-input"
                    value={name}
                    placeholder={t("register.namePlaceholder")}
                    onChange={(event) => setName(event.target.value)}
                  />
                </label>

                <label className="mk-field">
                  <span className="mk-label">{t("register.ageLabel")}</span>
                  <input
                    className="mk-input"
                    value={age}
                    inputMode="numeric"
                    maxLength={3}
                    placeholder={t("register.agePlaceholder")}
                    onChange={(event) => setAge(event.target.value.replace(/\D/g, ""))}
                  />
                </label>

                <div className="mk-field">
                  <span className="mk-label">{t("register.sexLabel")}</span>
                  <div className="mk-row mk-row--wrap">
                    {(
                      [
                        ["M", t("register.sexMale")],
                        ["F", t("register.sexFemale")],
                        ["O", t("register.sexOther")],
                      ] as const
                    ).map(([value, label]) => (
                      <button
                        key={value}
                        type="button"
                        className="mk-btn"
                        data-selected={sex === value}
                        aria-pressed={sex === value}
                        onClick={() => setSex(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {failed && (
          <ErrorState
            title={t("error.title")}
            message={t("error.generic")}
            actions={
              <button type="button" className="mk-btn mk-btn--secondary" onClick={submit}>
                <Icon name="refresh" />
                {t("common.retry")}
              </button>
            }
          />
        )}

        <p className="mk-meta">{t("register.demoNotice")}</p>
      </div>
    </KioskScreen>
  );
}
