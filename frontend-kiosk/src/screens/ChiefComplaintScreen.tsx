"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { intakeApi } from "@/api/intakeApi";
import type { ChiefComplaintOption } from "@/api/types";
import { ChoiceTile } from "@/components/ChoiceTile";
import { ErrorState } from "@/components/ErrorState";
import { Icon, type IconName } from "@/components/Icon";
import { BackButton, KioskScreen } from "@/components/KioskScreen";
import { ProcessingState } from "@/components/ProcessingState";
import { TextAnswer } from "@/components/TextAnswer";
import { usePatientSession } from "@/context/PatientSession";
import { useJourneyGuard } from "@/hooks/useJourneyGuard";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/** Build spec §6.5. The complaint list comes from the question service, not
 *  from a constant in this file — the demo's two flows are the minimum, and
 *  adding a third must not require a frontend release. */
export function ChiefComplaintScreen() {
  const router = useRouter();
  const { t, language } = useLanguage();
  const { dispatch } = usePatientSession();
  const ready = useJourneyGuard("consent");

  const [options, setOptions] = useState<ChiefComplaintOption[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [freeText, setFreeText] = useState("");
  const [showOther, setShowOther] = useState(false);

  useEffect(() => {
    if (!ready) return;
    let cancelled = false;

    intakeApi
      .getComplaints(language)
      .then((result) => {
        if (!cancelled) setOptions(result);
      })
      .catch((error) => {
        console.warn("[complaints] failed", error);
        if (!cancelled) setFailed(true);
      });

    return () => {
      cancelled = true;
    };
  }, [ready, language]);

  if (!ready) return null;

  function choose(id: string, label: string, text?: string) {
    dispatch({ type: "setComplaint", complaint: { id, label, text } });
    router.push(ROUTES.intake);
  }

  return (
    <KioskScreen
      step="complaint"
      align="top"
      actions={
        <BackButton
          onClick={() => (showOther ? setShowOther(false) : router.push(ROUTES.mode))}
          label={t("common.back")}
        />
      }
    >
      <div className="mk-container mk-stack mk-stack--loose">
        <div className="mk-stack mk-stack--tight mk-center">
          <h1 className="mk-h1">{t("complaint.title")}</h1>
          <p className="mk-lead">{t("complaint.subtitle")}</p>
        </div>

        {failed && <ErrorState title={t("error.title")} message={t("error.offline")} />}

        {!options && !failed && <ProcessingState label={t("common.pleaseWait")} />}

        {options && !showOther && (
          <div className="mk-choices mk-choices--wide">
            {options.map((option) => (
              <ChoiceTile
                key={option.id}
                icon={option.icon as IconName}
                label={option.label}
                showCheck={false}
                onClick={() => choose(option.id, option.label)}
              />
            ))}
            <ChoiceTile
              icon="dots"
              label={t("complaint.other")}
              sub={t("complaint.otherSub")}
              showCheck={false}
              onClick={() => setShowOther(true)}
            />
          </div>
        )}

        {showOther && (
          <div className="mk-card mk-stack">
            <div className="mk-row">
              <Icon name="keyboard" />
              <span className="mk-label">{t("complaint.otherLabel")}</span>
            </div>
            <TextAnswer
              value={freeText}
              onChange={setFreeText}
              autoFocus
              onSubmit={() => choose("other", t("complaint.other"), freeText.trim())}
              onCancel={() => setShowOther(false)}
            />
          </div>
        )}
      </div>
    </KioskScreen>
  );
}
