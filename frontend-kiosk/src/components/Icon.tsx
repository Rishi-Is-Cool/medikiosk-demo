/* Inline icon set. No icon library and no CDN — a kiosk in a hospital foyer
   may sit behind a captive network, and an icon that fails to load takes the
   meaning of a button with it. Every icon inherits currentColor so it picks
   up the token colour of whatever it sits inside. */

export type IconName =
  | "mic"
  | "stop"
  | "speaker"
  | "check"
  | "chevronLeft"
  | "chevronRight"
  | "alert"
  | "hand"
  | "thermometer"
  | "heart"
  | "stomach"
  | "head"
  | "lungs"
  | "wind"
  | "droplet"
  | "bone"
  | "dizzy"
  | "skin"
  | "dots"
  | "document"
  | "camera"
  | "gallery"
  | "phone"
  | "shield"
  | "idCard"
  | "userPlus"
  | "keyboard"
  | "refresh"
  | "close"
  | "clock"
  | "help"
  | "leaf"
  | "stethoscope";

const PATHS: Record<IconName, React.ReactNode> = {
  mic: (
    <>
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 18v4M8 22h8" />
    </>
  ),
  stop: <rect x="6" y="6" width="12" height="12" rx="2" />,
  speaker: (
    <>
      <path d="M11 5 6 9H3v6h3l5 4z" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7M18.5 5.5a9 9 0 0 1 0 13" />
    </>
  ),
  check: <path d="m4 12 5.5 5.5L20 7" />,
  chevronLeft: <path d="m15 5-7 7 7 7" />,
  chevronRight: <path d="m9 5 7 7-7 7" />,
  alert: (
    <>
      <path d="M12 3 2 20h20z" />
      <path d="M12 9v5M12 17.5v.5" />
    </>
  ),
  hand: (
    <>
      <path d="M8 11V5.5a1.5 1.5 0 0 1 3 0V11" />
      <path d="M11 11V4.5a1.5 1.5 0 0 1 3 0V11" />
      <path d="M14 11V6.5a1.5 1.5 0 0 1 3 0V13" />
      <path d="M8 11V9.5a1.5 1.5 0 0 0-3 0V15a7 7 0 0 0 7 7h1a6 6 0 0 0 6-6v-3" />
    </>
  ),
  thermometer: (
    <>
      <path d="M10 13.5V5a2 2 0 1 1 4 0v8.5a4 4 0 1 1-4 0z" />
      <path d="M12 8v8" />
    </>
  ),
  heart: <path d="M12 20s-7-4.6-7-9.4A3.9 3.9 0 0 1 12 7.6a3.9 3.9 0 0 1 7 3C19 15.4 12 20 12 20z" />,
  stomach: (
    <>
      <path d="M9 4v4.5c0 3-4 3.2-4 7A5.5 5.5 0 0 0 10.5 21h2A6.5 6.5 0 0 0 19 14.5c0-3.6-2.5-5.5-5-5.5-1.6 0-2.5.8-2.5 2" />
      <path d="M7 4h4" />
    </>
  ),
  head: (
    <>
      <path d="M16.5 20v-2.5c2-1 3.5-3.3 3.5-6A7 7 0 0 0 6.2 9.6L4.4 13a.8.8 0 0 0 .7 1.2H7v2.3A3.5 3.5 0 0 0 10.5 20z" />
      <path d="M10 9.5h.01M14.5 9.5h.01" />
    </>
  ),
  lungs: (
    <>
      <path d="M12 3v9" />
      <path d="M12 8c-1.8 0-2.5 1-2.5 2.4V12c0 2-4.5 2.3-4.5 6.2C5 20.2 6.2 21 7.5 21c1.6 0 2-1.2 2-2.4V13" />
      <path d="M12 8c1.8 0 2.5 1 2.5 2.4V12c0 2 4.5 2.3 4.5 6.2 0 2-1.2 2.8-2.5 2.8-1.6 0-2-1.2-2-2.4V13" />
    </>
  ),
  wind: (
    <>
      <path d="M3 8h10a3 3 0 1 0-3-3" />
      <path d="M3 12h15a3 3 0 1 1-3 3" />
      <path d="M3 16h6" />
    </>
  ),
  droplet: <path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z" />,
  bone: (
    <path d="M8.2 4.2a2.6 2.6 0 0 0-4 3.2 2.6 2.6 0 0 0 1.4 3.6L13 18.4a2.6 2.6 0 0 0 3.6 1.4 2.6 2.6 0 0 0 3.2-4 2.6 2.6 0 0 0-1.4-3.6L11 4.8a2.6 2.6 0 0 0-2.8-.6z" />
  ),
  dizzy: (
    <>
      <path d="M12 12a1.5 1.5 0 1 1 1.5-1.5 3.5 3.5 0 1 1-3.5-3.5 5.5 5.5 0 1 1-5.5 5.5" />
      <path d="M18.5 4.5l1 1M20 8h1" />
    </>
  ),
  skin: (
    <>
      <path d="M4 20c1.5-6 6-10 16-10" />
      <circle cx="9" cy="7" r="1.3" />
      <circle cx="14" cy="5" r="1.3" />
      <circle cx="17.5" cy="15" r="1.3" />
    </>
  ),
  dots: (
    <>
      <circle cx="5" cy="12" r="1.6" />
      <circle cx="12" cy="12" r="1.6" />
      <circle cx="19" cy="12" r="1.6" />
    </>
  ),
  document: (
    <>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
      <path d="M14 3v5h5M9 13h6M9 17h4" />
    </>
  ),
  camera: (
    <>
      <path d="M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1z" />
      <circle cx="12" cy="13.5" r="3.5" />
    </>
  ),
  gallery: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 16 4.5-4.5 4 4L15 12l6 5.5" />
      <circle cx="8.5" cy="9.5" r="1.2" />
    </>
  ),
  phone: (
    <>
      <rect x="6" y="2" width="12" height="20" rx="2.5" />
      <path d="M10.5 18.5h3" />
    </>
  ),
  shield: (
    <>
      <path d="M12 3 5 6v5.5c0 4.3 3 8 7 9.5 4-1.5 7-5.2 7-9.5V6z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  idCard: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="9" cy="11" r="2" />
      <path d="M5.5 16.5c.6-1.5 2-2.2 3.5-2.2s2.9.7 3.5 2.2M15 9.5h4M15 13h3" />
    </>
  ),
  userPlus: (
    <>
      <circle cx="10" cy="8" r="3.5" />
      <path d="M3.5 20a6.5 6.5 0 0 1 13 0" />
      <path d="M19 8v6M22 11h-6" />
    </>
  ),
  keyboard: (
    <>
      <rect x="2.5" y="6" width="19" height="12" rx="2" />
      <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8" />
    </>
  ),
  refresh: (
    <>
      <path d="M20 12a8 8 0 1 1-2.6-5.9" />
      <path d="M20 4v5h-5" />
    </>
  ),
  close: <path d="m6 6 12 12M18 6 6 18" />,
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5.5l3.5 2" />
    </>
  ),
  help: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9.5a2.5 2.5 0 1 1 3.3 2.4c-.6.2-.8.7-.8 1.3v.3M12 17h.01" />
    </>
  ),
  leaf: (
    <>
      <path d="M5 19c0-8 5-13 14-13 0 9-4.5 13-9.5 13A4.5 4.5 0 0 1 5 19z" />
      <path d="M5 19c2.5-3 5-5.5 8.5-7.5" />
    </>
  ),
  stethoscope: (
    <>
      <path d="M6 3v5a4 4 0 0 0 8 0V3" />
      <path d="M4.5 3h3M12.5 3h3" />
      <path d="M10 12v2.5A5.5 5.5 0 0 0 15.5 20h.5a3 3 0 0 0 3-3v-2" />
      <circle cx="19" cy="13" r="2" />
    </>
  ),
};

/** Icon names arrive from the question service as plain strings. */
export function isIconName(name: string | undefined): name is IconName {
  return !!name && Object.prototype.hasOwnProperty.call(PATHS, name);
}

export function Icon({
  name,
  size = 24,
  strokeWidth = 1.8,
  className,
}: {
  name: IconName;
  size?: number;
  strokeWidth?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}
