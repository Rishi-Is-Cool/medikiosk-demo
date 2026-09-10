"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { patientApi } from "@/api/patientApi";
import { ApiError, type IdentityCard, type PatientSessionInfo } from "@/api/types";
import { ChoiceTile } from "@/components/ChoiceTile";
import { ErrorState } from "@/components/ErrorState";
import { Icon } from "@/components/Icon";
import { IdentityExample } from "@/components/IdentityExample";
import { IdentityScanner } from "@/components/IdentityScanner";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { usePatientSession } from "@/context/PatientSession";
import { speakChoice } from "@/hooks/useSpeech";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/**
 * Build spec §6.2, reshaped around the question every OPD desk actually asks
 * first: "have you been here before?"
 *
 * - Old patient → pick ABHA or Aadhaar, see a sample card with the number
 *   highlighted, enter or scan it, and their record is opened.
 * - New patient → name, age and sex, plus an optional ABHA/Aadhaar so the
 *   next visit is a single number.
 *
 * Nothing here verifies identity against a national database, and the notice
 * at the bottom says so (§19). The backend keeps only a keyed hash and the
 * last four digits of an Aadhaar number.
 */

type Stage = "visit" | "findBy" | "returning" | "new";
type Problem = "notFound" | "invalid" | "already" | "generic" | null;

const DIGITS: Record<IdentityCard, number> = { abha: 14, aadhaar: 12 };

/** 91-7267-4417-6579 */
function formatAbha(digits: string): string {
  return [digits.slice(0, 2), digits.slice(2, 6), digits.slice(6, 10), digits.slice(10, 14)]
    .filter(Boolean)
    .join("-");
}

/** 2345 6789 0123 */
function formatAadhaar(digits: string): string {
  return (digits.match(/.{1,4}/g) ?? []).join(" ");
}

function IdNumberField({
  card,
  digits,
  onChange,
}: {
  card: IdentityCard;
  digits: string;
  onChange: (digits: string) => void;
}) {
  const { t } = useLanguage();
  return (
    <label className="mk-field">
      <span className="mk-label">
        {t(card === "abha" ? "register.abhaNumberLabel" : "register.aadhaarNumberLabel")}
      </span>
      <input
        className="mk-input mk-idinput"
        value={card === "abha" ? formatAbha(digits) : formatAadhaar(digits)}
        inputMode="numeric"
        autoComplete="off"
        placeholder={card === "abha" ? "XX-XXXX-XXXX-XXXX" : "XXXX XXXX XXXX"}
        onChange={(event) => onChange(event.target.value.replace(/\D/g, "").slice(0, DIGITS[card]))}
      />
      {card === "aadhaar" && <span className="mk-help">{t("register.aadhaarPrivacy")}</span>}
    </label>
  );
}

export function RegistrationScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { dispatch } = usePatientSession();

  const [stage, setStage] = useState<Stage>("visit");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Problem>(null);

  /* Returning patient */
  const [card, setCard] = useState<IdentityCard>("abha");
  const [idDigits, setIdDigits] = useState("");
  /** Set when the number came off a photographed card rather than the keypad,
   *  so the patient is asked to check it before continuing. */
  const [fromScan, setFromScan] = useState(false);

  /* New patient */
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [phone, setPhone] = useState("");
  const [newCard, setNewCard] = useState<IdentityCard | null>(null);
  const [newIdDigits, setNewIdDigits] = useState("");
  const [showExample, setShowExample] = useState(false);

  const idComplete = idDigits.length === DIGITS[card];
  const newIdComplete = newCard !== null && newIdDigits.length === DIGITS[newCard];
  const canRegister =
    name.trim().length > 1 &&
    age !== "" &&
    Number(age) <= 120 &&
    sex !== "" &&
    (newCard === null || newIdComplete);

  function go(next: Stage) {
    setStage(next);
    setProblem(null);
    setShowExample(false);
    // Each stage is a new screen; arriving half-scrolled hides its heading.
    window.scrollTo({ top: 0 });
  }

  async function run(action: () => Promise<PatientSessionInfo>) {
    setBusy(true);
    setProblem(null);
    try {
      const patient = await action();
      dispatch({ type: "setPatient", patient });
      router.push(ROUTES.consent);
    } catch (error) {
      console.warn("[register] failed", error);
      const code = error instanceof ApiError ? error.code : "";
      setProblem(
        code === "http_404" ? "notFound" : code === "http_409" ? "already" : code === "http_422" ? "invalid" : "generic",
      );
    } finally {
      setBusy(false);
    }
  }

  const lookup = (method: IdentityCard, digits: string) =>
    run(() => patientApi.lookup({ identity_method: method, identifier: digits, language }));

  const register = () =>
    run(() =>
      patientApi.register({
        identity_method: "new",
        language,
        new_patient: { name: name.trim(), age, sex, phone: phone || undefined },
        abha_number: newCard === "abha" ? newIdDigits : undefined,
        aadhaar_number: newCard === "aadhaar" ? newIdDigits : undefined,
      }),
    );

  const retry = (action: () => void) => (
    <button type="button" className="mk-btn mk-btn--secondary" onClick={action}>
      <Icon name="refresh" />
      {t("common.retry")}
    </button>
  );

  /* --- Have you been here before? ------------------------------------------ */

  if (stage === "visit") {
    return (
      <KioskScreen
        step="identity"
        align="top"
        actions={<BackButton onClick={() => router.push(ROUTES.language)} label={t("common.back")} />}
      >
        <div className="mk-container mk-stack mk-stack--loose">
          <div className="mk-stack mk-stack--tight mk-center">
            <h1 className="mk-h1">{t("register.visitTitle")}</h1>
            <p className="mk-lead">{t("register.visitSubtitle")}</p>
          </div>

          <div className="mk-choices mk-choices--wide">
            <ChoiceTile
              icon="userPlus"
              label={t("register.newPatient")}
              sub={t("register.newPatientSub")}
              showCheck={false}
              onClick={() => {
                speakChoice(t("register.newPatient"), language);
                go("new");
              }}
            />
            <ChoiceTile
              icon="idCard"
              label={t("register.oldPatient")}
              sub={t("register.oldPatientSub")}
              showCheck={false}
              onClick={() => {
                speakChoice(t("register.oldPatient"), language);
                go("findBy");
              }}
            />
          </div>

          <p className="mk-meta mk-center">{t("register.demoNotice")}</p>
        </div>
      </KioskScreen>
    );
  }

  /* --- Old patient: which card? -------------------------------------------- */

  if (stage === "findBy") {
    const pick = (chosen: IdentityCard) => {
      speakChoice(t(chosen === "abha" ? "register.abha" : "register.aadhaar"), language);
      setCard(chosen);
      setIdDigits("");
      setFromScan(false);
      go("returning");
    };

    return (
      <KioskScreen
        step="identity"
        align="top"
        actions={<BackButton onClick={() => go("visit")} label={t("common.back")} />}
      >
        <div className="mk-container mk-stack mk-stack--loose">
          <div className="mk-stack mk-stack--tight mk-center">
            <h1 className="mk-h1">{t("register.findTitle")}</h1>
            <p className="mk-lead">{t("register.findSubtitle")}</p>
          </div>

          <div className="mk-choices mk-choices--wide">
            <ChoiceTile
              icon="shield"
              label={t("register.abha")}
              sub={t("register.abhaSub")}
              showCheck={false}
              onClick={() => pick("abha")}
            />
            <ChoiceTile
              icon="idCard"
              label={t("register.aadhaar")}
              sub={t("register.aadhaarSubFull")}
              showCheck={false}
              onClick={() => pick("aadhaar")}
            />
          </div>

          <p className="mk-meta mk-center">{t("register.demoNotice")}</p>
        </div>
      </KioskScreen>
    );
  }

  /* --- Old patient: enter the number --------------------------------------- */

  if (stage === "returning") {
    return (
      <KioskScreen
        step="identity"
        align="top"
        actions={
          <>
            <BackButton onClick={() => go("findBy")} label={t("common.back")} />
            <div className="mk-actionbar__spacer" />
            <button
              type="button"
              className="mk-btn mk-btn--primary mk-btn--lg"
              disabled={!idComplete || busy}
              onClick={() => lookup(card, idDigits)}
            >
              {t("register.verify")}
              <Icon name="chevronRight" />
            </button>
          </>
        }
      >
        <div className="mk-container mk-stack mk-stack--loose">
          <div className="mk-stack mk-stack--tight mk-center">
            <h1 className="mk-h1">{t(card === "abha" ? "register.abha" : "register.aadhaar")}</h1>
            <p className="mk-lead">{t("register.exampleTitle")}</p>
          </div>

          {busy ? (
            <ProcessingState label={t("register.verifying")} />
          ) : (
            <div className="mk-idgrid">
              <IdentityExample card={card} />

              <div className="mk-card mk-stack">
                <IdNumberField
                  card={card}
                  digits={idDigits}
                  onChange={(digits) => {
                    setIdDigits(digits);
                    setFromScan(false);
                    setProblem(null);
                  }}
                />

                {/* A scanned number is a machine's reading of a photograph, not
                    a verified identity. Asking the patient to confirm it costs
                    one glance and prevents a session filed under the wrong ID. */}
                {fromScan && idDigits && (
                  <p className="mk-help mk-scanned">
                    <Icon name="check" size={18} strokeWidth={3} />
                    {t("register.scanned")}
                  </p>
                )}

                <p className="mk-help mk-center">{t("common.or")}</p>
                <IdentityScanner
                  method={card}
                  onScanned={(value) => {
                    setIdDigits(value.replace(/\D/g, "").slice(0, DIGITS[card]));
                    setFromScan(true);
                    setProblem(null);
                  }}
                />
              </div>
            </div>
          )}

          {problem === "notFound" && (
            <ErrorState
              title={t("register.notFoundTitle")}
              message={t("register.notFoundBody")}
              actions={
                <button
                  type="button"
                  className="mk-btn mk-btn--secondary"
                  onClick={() => {
                    setNewCard(card);
                    setNewIdDigits(idDigits);
                    go("new");
                  }}
                >
                  <Icon name="userPlus" />
                  {t("register.registerNew")}
                </button>
              }
            />
          )}
          {problem === "invalid" && <ErrorState title={t("register.invalidId")} />}
          {problem === "generic" && (
            <ErrorState
              title={t("error.title")}
              message={t("error.generic")}
              actions={retry(() => lookup(card, idDigits))}
            />
          )}

          <p className="mk-meta mk-center">{t("register.demoNotice")}</p>
        </div>
      </KioskScreen>
    );
  }

  /* --- New patient --------------------------------------------------------- */

  return (
    <KioskScreen
      step="identity"
      align="top"
      actions={
        <>
          <BackButton onClick={() => go("visit")} label={t("common.back")} />
          <div className="mk-actionbar__spacer" />
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--lg"
            disabled={!canRegister || busy}
            onClick={register}
          >
            {t("register.verify")}
            <Icon name="chevronRight" />
          </button>
        </>
      }
    >
      <div className="mk-container mk-container--narrow mk-stack mk-stack--loose">
        <h1 className="mk-h1">{t("register.newPatient")}</h1>

        {busy ? (
          <ProcessingState label={t("register.verifying")} />
        ) : (
          <div className="mk-card mk-stack">
            <label className="mk-field">
              <span className="mk-label">{t("register.nameLabel")}</span>
              <input
                className="mk-input"
                value={name}
                autoComplete="off"
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

            <label className="mk-field">
              <span className="mk-label">{t("register.phoneLabel")}</span>
              <input
                className="mk-input"
                value={phone}
                inputMode="tel"
                maxLength={10}
                autoComplete="off"
                placeholder={t("register.phonePlaceholder")}
                onChange={(event) => setPhone(event.target.value.replace(/\D/g, ""))}
              />
            </label>

            <div className="mk-field mk-divided">
              <span className="mk-label">{t("register.newIdTitle")}</span>
              <span className="mk-help">{t("register.newIdHelp")}</span>
              <div className="mk-row mk-row--wrap">
                {(
                  [
                    [null, t("register.idNone")],
                    ["abha", t("register.abhaShort")],
                    ["aadhaar", t("register.aadhaarShort")],
                  ] as const
                ).map(([value, label]) => (
                  <button
                    key={label}
                    type="button"
                    className="mk-btn"
                    data-selected={newCard === value}
                    aria-pressed={newCard === value}
                    onClick={() => {
                      setNewCard(value);
                      setNewIdDigits("");
                      setProblem(null);
                    }}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {newCard && (
              <>
                <IdNumberField
                  card={newCard}
                  digits={newIdDigits}
                  onChange={(digits) => {
                    setNewIdDigits(digits);
                    setProblem(null);
                  }}
                />
                <button
                  type="button"
                  className="mk-btn mk-btn--ghost"
                  aria-expanded={showExample}
                  onClick={() => setShowExample((open) => !open)}
                >
                  <Icon name="help" />
                  {t(showExample ? "register.hideExample" : "register.showExample")}
                </button>
                {showExample && <IdentityExample card={newCard} />}
              </>
            )}
          </div>
        )}

        {problem === "already" && newCard && (
          <ErrorState
            title={t("register.alreadyTitle")}
            message={t("register.alreadyBody")}
            actions={
              <button
                type="button"
                className="mk-btn mk-btn--secondary"
                onClick={() => lookup(newCard, newIdDigits)}
              >
                <Icon name="idCard" />
                {t("register.continueReturning")}
              </button>
            }
          />
        )}
        {problem === "invalid" && <ErrorState title={t("register.invalidId")} />}
        {problem === "generic" && (
          <ErrorState title={t("error.title")} message={t("error.generic")} actions={retry(register)} />
        )}

        <p className="mk-meta">{t("register.demoNotice")}</p>
      </div>
    </KioskScreen>
  );
}
