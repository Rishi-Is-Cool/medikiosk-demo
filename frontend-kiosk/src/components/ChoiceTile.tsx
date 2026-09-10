"use client";

import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";

/** The kiosk's primary target: big, icon-supported, unambiguous when
 *  selected (build spec §14). Used for languages, identity methods,
 *  complaints and every touch answer. */
export function ChoiceTile({
  label,
  sub,
  icon,
  selected = false,
  disabled = false,
  showCheck = true,
  badge,
  lang,
  onClick,
}: {
  label: string;
  sub?: string;
  icon?: IconName;
  selected?: boolean;
  disabled?: boolean;
  /** Off for single-choice lists that advance immediately on tap — a tick
   *  that appears for 200ms before the screen changes is just noise. */
  showCheck?: boolean;
  badge?: ReactNode;
  lang?: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      className="mk-choice"
      data-selected={selected}
      aria-pressed={showCheck ? selected : undefined}
      disabled={disabled}
      onClick={onClick}
      lang={lang}
    >
      {icon && (
        <span className="mk-choice__icon">
          <Icon name={icon} size={28} />
        </span>
      )}

      <span className="mk-choice__body">
        <span className="mk-choice__label">{label}</span>
        {sub && <span className="mk-choice__sub">{sub}</span>}
      </span>

      {badge}

      {showCheck && !disabled && (
        <span className="mk-choice__check" aria-hidden="true">
          <Icon name="check" size={20} strokeWidth={3} />
        </span>
      )}
    </button>
  );
}
