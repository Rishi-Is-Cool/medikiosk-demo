import type { NextConfig } from "next";

/** Where the FastAPI backend listens, as seen from this Next.js server. */
const BACKEND_ORIGIN = (process.env.KIOSK_BACKEND_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/$/, "");

/** Hostname of NEXT_PUBLIC_KIOSK_PUBLIC_ORIGIN (the kiosk's LAN address), so
 *  the patient's phone may load the dev server's assets. */
function lanHost(): string[] {
  try {
    const origin = process.env.NEXT_PUBLIC_KIOSK_PUBLIC_ORIGIN;
    return origin ? [new URL(origin).hostname] : [];
  } catch {
    return [];
  }
}

const nextConfig: NextConfig = {
  allowedDevOrigins: lanHost(),

  // The kiosk and the patient's phone both reach the API through this app's
  // own origin (/backend/*). The phone only knows the kiosk's address from
  // the QR code, and one origin means no CORS configuration on the backend.
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${BACKEND_ORIGIN}/:path*` }];
  },
};

export default nextConfig;
