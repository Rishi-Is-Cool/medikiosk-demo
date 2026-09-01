"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { Icon } from "./Icon";

/** Small focus-trapping dialog. Used for the help panel and for confirmations
 *  that must not be dismissed by an accidental tap on the background. */
export function Modal({
  open,
  title,
  onClose,
  children,
  closeLabel,
}: {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  closeLabel: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    panelRef.current?.focus();

    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="mk-modal" role="presentation">
      <div className="mk-modal__backdrop" onClick={onClose} />
      <div
        ref={panelRef}
        className="mk-modal__panel"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
      >
        <div className="mk-modal__head">
          <h2 className="mk-h2">{title}</h2>
          <button type="button" className="mk-btn mk-btn--ghost mk-modal__close" onClick={onClose}>
            <Icon name="close" />
            <span className="mk-sr-only">{closeLabel}</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
