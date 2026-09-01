"use client";

import { useState, type ReactNode } from "react";
import { useLanguage } from "@/i18n/LanguageProvider";
import { STEPS, stepIndex, type StepId } from "@/lib/journey";
import { Icon } from "./Icon";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { Modal } from "./Modal";

/** The frame every kiosk screen sits in: identity strip on top, one task in
 *  the middle, one primary action at the bottom (build spec §3, §14). */
export function KioskScreen({
  step,
  children,
  actions,
  align = "center",
  showChrome = true,
}: {
  step?: StepId;
  children: ReactNode;
  actions?: ReactNode;
  align?: "center" | "top";
  showChrome?: boolean;
}) {
  return (
    <div className="mk-screen mk-app">
      {showChrome && <TopBar step={step} />}
      <main className={align === "top" ? "mk-main mk-main--top" : "mk-main"}>{children}</main>
      {actions && <div className="mk-actionbar">{actions}</div>}
    </div>
  );
}

function TopBar({ step }: { step?: StepId }) {
  const { t } = useLanguage();
  const current = step ? stepIndex(step) : -1;

  return (
    <header className="mk-topbar">
      <span className="mk-topbar__brand">
        <Icon name="stethoscope" size={26} />
        MediKiosk
      </span>

      <div className="mk-topbar__spacer" />

      {step && (
        <ol className="mk-steps" aria-label={t("common.step")}>
          {STEPS.map((s, index) => (
            <li
              key={s}
              className="mk-steps__dot"
              data-state={index < current ? "done" : index === current ? "current" : "todo"}
            />
          ))}
        </ol>
      )}

      <div className="mk-topbar__spacer" />

      <LanguageSwitcher />
      <HelpButton />
    </header>
  );
}

function HelpButton() {
  const { t } = useLanguage();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button type="button" className="mk-btn mk-btn--secondary" onClick={() => setOpen(true)}>
        <Icon name="help" />
        {t("common.staffHelp")}
      </button>

      <Modal
        open={open}
        title={t("help.title")}
        onClose={() => setOpen(false)}
        closeLabel={t("help.ok")}
      >
        <div className="mk-stack">
          <div className="mk-row">
            <span className="mk-help-icon">
              <Icon name="hand" size={32} />
            </span>
            <p className="mk-lead">{t("help.body")}</p>
          </div>
          <p className="mk-help">{t("help.body2")}</p>
          <button
            type="button"
            className="mk-btn mk-btn--primary mk-btn--block"
            onClick={() => setOpen(false)}
          >
            {t("help.ok")}
          </button>
        </div>
      </Modal>
    </>
  );
}

/** Bottom-bar back button. Present on every screen after the first, because a
 *  kiosk with no way back traps a patient who mistapped. */
export function BackButton({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button type="button" className="mk-btn mk-btn--ghost" onClick={onClick}>
      <Icon name="chevronLeft" />
      {label}
    </button>
  );
}
