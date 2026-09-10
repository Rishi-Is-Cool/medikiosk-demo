import type { Metadata, Viewport } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

/* Self-hosted at build time. A kiosk behind a hospital's captive portal must
   not depend on fonts.googleapis.com being reachable at 9am. */

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex-sans",
  display: "swap",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
  display: "swap",
});

const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "500", "600"],
  variable: "--font-noto-deva",
  display: "swap",
});

export const metadata: Metadata = {
  title: "MediKiosk",
  description: "Patient clinical intake kiosk",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // A kiosk should not pinch-zoom under a stray palm; the phone upload page
  // is large enough that it does not need to.
  maximumScale: 1,
  // No themeColor: it would have to be a literal hex here, and tokens.css is
  // the only place a MediKiosk colour is allowed to be written down.
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      /* Density and theme are set once, here. tokens.css does the rest:
         data-density="kiosk" is what makes every target 56px and every
         question readable at arm's length. The kiosk stays light — it runs in
         a bright foyer, and only the doctor's console needs the dark set. */
      data-density="kiosk"
      data-theme="light"
      className={`${plexSans.variable} ${plexMono.variable} ${notoDevanagari.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
