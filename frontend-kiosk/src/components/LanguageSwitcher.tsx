"use client";

import { useEffect, useRef, useState } from "react";
import { usePatientSession } from "@/context/PatientSession";
import { useLanguage } from "@/i18n/LanguageProvider";
import { LANGUAGES } from "@/i18n/languages";
import { Icon } from "./Icon";

/** Language stays reachable from every screen. A patient who picked the wrong
 *  one on the first tap must not have to restart to fix it. */
export function LanguageSwitcher() {
  const { dispatch } = usePatientSession();
  const { language, option, t } = useLanguage();
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!wrapRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onPointer);
    return () => document.removeEventListener("pointerdown", onPointer);
  }, [open]);

  const available = LANGUAGES.filter((l) => l.translated);

  return (
    <div className="mk-langswitch" ref={wrapRef}>
      <button
        type="button"
        className="mk-pill mk-langswitch__trigger"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className={option.script === "deva" ? "mk-deva" : undefined}>{option.native}</span>
        <Icon name="chevronRight" size={18} />
        <span className="mk-sr-only">{t("language.title")}</span>
      </button>

      {open && (
        <ul className="mk-langswitch__menu" role="listbox" aria-label={t("language.title")}>
          {available.map((l) => (
            <li key={l.code}>
              <button
                type="button"
                role="option"
                aria-selected={l.code === language}
                className="mk-langswitch__item"
                data-selected={l.code === language}
                onClick={() => {
                  dispatch({ type: "setLanguage", language: l.code });
                  setOpen(false);
                }}
              >
                <span className={l.script === "deva" ? "mk-deva" : undefined}>{l.native}</span>
                {l.code === language && <Icon name="check" size={20} />}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
