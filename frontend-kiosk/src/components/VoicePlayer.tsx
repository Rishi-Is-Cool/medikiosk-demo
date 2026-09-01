"use client";

import { useEffect } from "react";
import { useSpeech } from "@/hooks/useSpeech";
import { useLanguage } from "@/i18n/LanguageProvider";
import { Icon } from "./Icon";

/**
 * The Listen control (build spec §6.9).
 *
 * `autoPlayKey` re-reads the text whenever it changes, which is how a
 * low-literacy patient hears each new question without hunting for a button.
 * It is opt-in per screen: a foyer full of talking kiosks is its own problem,
 * so the team should decide where this is on before deployment.
 */
export function VoicePlayer({
  text,
  autoPlayKey,
  label,
  onPlay,
}: {
  text: string;
  autoPlayKey?: string;
  label?: string;
  /** Fires when playback is requested. The consent screen records that the
   *  audio explanation was offered and played (build spec §6.3). */
  onPlay?: () => void;
}) {
  const { t } = useLanguage();
  const { speakQuestion, stop, speaking } = useSpeech();

  useEffect(() => {
    if (!autoPlayKey || !text) return;
    void speakQuestion(text);
    return stop;
  }, [autoPlayKey, text, speakQuestion, stop]);

  return (
    <button
      type="button"
      className="mk-btn mk-btn--secondary"
      onClick={() => {
        if (speaking) {
          stop();
          return;
        }
        onPlay?.();
        void speakQuestion(text);
      }}
      aria-live="off"
    >
      <Icon name={speaking ? "stop" : "speaker"} />
      {speaking ? t("common.stopListening") : (label ?? t("common.listen"))}
    </button>
  );
}
