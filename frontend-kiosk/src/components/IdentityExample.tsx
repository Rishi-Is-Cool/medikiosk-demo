"use client";

import type { IdentityCard } from "@/api/types";
import { useLanguage } from "@/i18n/LanguageProvider";

/**
 * A sample card with the number the patient needs picked out.
 *
 * "Enter your ABHA number" means nothing to someone who has never looked
 * closely at their card; a picture of one, with the right line highlighted,
 * does. Both images are masked samples — not real people, not real numbers.
 * The box positions are percentages of each image, so the highlight stays on
 * the number at any size.
 */
const EXAMPLES: Record<
  IdentityCard,
  { src: string; width: number; height: number; box: { left: number; top: number; width: number; height: number } }
> = {
  abha: {
    src: "/id-examples/abha-example.jpg",
    width: 591,
    height: 338,
    box: { left: 30, top: 35.5, width: 40.5, height: 10.5 },
  },
  aadhaar: {
    src: "/id-examples/aadhaar-example.jpg",
    width: 1536,
    height: 1024,
    box: { left: 37, top: 63.8, width: 30.5, height: 8.6 },
  },
};

export function IdentityExample({ card }: { card: IdentityCard }) {
  const { t } = useLanguage();
  const example = EXAMPLES[card];
  const { box } = example;

  return (
    <figure className="mk-idexample">
      <div className="mk-idexample__card">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={example.src}
          width={example.width}
          height={example.height}
          alt={t(card === "abha" ? "register.exampleAltAbha" : "register.exampleAltAadhaar")}
        />
        <span
          className="mk-idexample__box"
          aria-hidden="true"
          style={{ left: `${box.left}%`, top: `${box.top}%`, width: `${box.width}%`, height: `${box.height}%` }}
        />
        <span className="mk-idexample__sample">{t("register.sample")}</span>
      </div>
      <figcaption className="mk-help mk-center">
        {t(card === "abha" ? "register.exampleAbhaHelp" : "register.exampleAadhaarHelp")}
      </figcaption>
    </figure>
  );
}
