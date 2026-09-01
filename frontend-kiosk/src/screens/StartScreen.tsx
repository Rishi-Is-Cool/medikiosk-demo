"use client";

import { useRouter } from "next/navigation";
import { KioskScreen } from "@/components/KioskScreen";
import { Icon } from "@/components/Icon";
import { useLanguage } from "@/i18n/LanguageProvider";
import { ROUTES } from "@/lib/journey";

/** The idle screen a patient walks up to. One target, and it is enormous. */
export function StartScreen() {
  const { t } = useLanguage();
  const router = useRouter();

  return (
    <KioskScreen>
      <div className="mk-container mk-container--narrow mk-stack mk-stack--loose mk-center">
        <div className="mk-stack mk-stack--tight">
          <h1 className="mk-display">{t("start.title")}</h1>
          <p className="mk-lead">{t("start.subtitle")}</p>
        </div>

        <ul className="mk-points">
          {(
            [
              ["mic", t("start.point1")],
              ["clock", t("start.point2")],
              ["hand", t("start.point3")],
            ] as const
          ).map(([icon, text]) => (
            <li key={text} className="mk-points__item">
              <span className="mk-points__icon">
                <Icon name={icon} size={26} />
              </span>
              {text}
            </li>
          ))}
        </ul>

        <button
          type="button"
          className="mk-btn mk-btn--primary mk-btn--lg mk-start"
          onClick={() => router.push(ROUTES.language)}
        >
          {t("start.begin")}
          <Icon name="chevronRight" size={28} />
        </button>
      </div>
    </KioskScreen>
  );
}
