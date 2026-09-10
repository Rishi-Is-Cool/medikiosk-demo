"use client";

import { useEffect, useState } from "react";
import QRCode from "qrcode";

/** Renders the upload-session URL as a QR image.
 *
 *  Generated locally — nothing is sent to a QR service, because the URL
 *  carries the upload token (build spec §11). Colours are read from the live
 *  token values rather than written as hex, so the code stays legible if the
 *  palette is re-signed-off. */
export function QrCode({ value, size = 300 }: { value: string; size?: number }) {
  const [dataUrl, setDataUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!value) return;
    let cancelled = false;

    const styles = getComputedStyle(document.documentElement);
    const dark = styles.getPropertyValue("--text").trim();
    const light = styles.getPropertyValue("--card").trim();

    QRCode.toDataURL(value, {
      width: size * 2, // Rendered at 2x so it stays crisp on a hi-dpi panel.
      margin: 1,
      errorCorrectionLevel: "M",
      color: { dark: dark || "#000000", light: light || "#ffffff" },
    })
      .then((url) => {
        if (!cancelled) setDataUrl(url);
      })
      .catch((error) => {
        console.warn("[qr] could not render code", error);
      });

    return () => {
      cancelled = true;
    };
  }, [value, size]);

  return (
    <div className="mk-qr" style={{ width: size, height: size }}>
      {dataUrl ? (
        // The QR is decorative: the same link is printed beside it as text.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={dataUrl} alt="" width={size} height={size} />
      ) : (
        <span className="mk-spinner" />
      )}
    </div>
  );
}
