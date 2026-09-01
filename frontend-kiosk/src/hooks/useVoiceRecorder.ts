"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/* Browser microphone capture (build spec §6.7). This hook owns MediaRecorder
   and nothing else — it produces an audio Blob and hands it back. It does not
   know what speech recognition is, and it must stay that way. */

export type RecorderStatus = "idle" | "requesting" | "recording";

export type RecorderError = "permission_denied" | "no_microphone" | "unsupported" | "failed";

export interface Recording {
  blob: Blob;
  durationMs: number;
}

/** Hard stop. A patient who forgets to press "finished" should not record
 *  until the tab runs out of memory. */
const MAX_DURATION_MS = 60_000;

const PREFERRED_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return PREFERRED_MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
}

export function useVoiceRecorder() {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [error, setError] = useState<RecorderError | null>(null);
  const [durationMs, setDurationMs] = useState(0);
  /** 0..1 — drives the "we can hear you" indicator. Elderly patients need to
   *  see that the machine is listening, not just be told. */
  const [level, setLevel] = useState(0);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const startedAtRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const autoStopRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const durationTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const cancelledRef = useRef(false);

  const teardown = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    rafRef.current = null;

    if (autoStopRef.current) clearTimeout(autoStopRef.current);
    autoStopRef.current = null;

    if (durationTimerRef.current) clearInterval(durationTimerRef.current);
    durationTimerRef.current = null;

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    void audioCtxRef.current?.close().catch(() => {});
    audioCtxRef.current = null;

    recorderRef.current = null;
    setLevel(0);
  }, []);

  useEffect(() => teardown, [teardown]);

  const monitorLevel = useCallback((stream: MediaStream) => {
    try {
      const AudioCtx =
        window.AudioContext ??
        (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!AudioCtx) return;

      const ctx = new AudioCtx();
      audioCtxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(analyser);

      const data = new Uint8Array(analyser.frequencyBinCount);
      let lastPaint = 0;

      const tick = (now: number) => {
        analyser.getByteTimeDomainData(data);

        // Repaint at ~15fps. A kiosk render loop at 60fps buys nothing a
        // patient can perceive and costs battery on the tablet builds.
        if (now - lastPaint > 66) {
          lastPaint = now;
          let peak = 0;
          for (const sample of data) {
            peak = Math.max(peak, Math.abs(sample - 128) / 128);
          }
          setLevel(peak);
        }

        rafRef.current = requestAnimationFrame(tick);
      };

      rafRef.current = requestAnimationFrame(tick);
    } catch {
      // Level metering is a nicety. Losing it must never block recording.
    }
  }, []);

  const start = useCallback(async (): Promise<boolean> => {
    setError(null);
    cancelledRef.current = false;

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setError("unsupported");
      return false;
    }

    setStatus("requesting");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
    } catch (err) {
      const name = err instanceof DOMException ? err.name : "";
      setStatus("idle");
      setError(
        name === "NotAllowedError" || name === "SecurityError"
          ? "permission_denied"
          : name === "NotFoundError"
            ? "no_microphone"
            : "failed",
      );
      return false;
    }

    try {
      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);

      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorderRef.current = recorder;
      streamRef.current = stream;
      startedAtRef.current = Date.now();

      recorder.start();
      setStatus("recording");
      setDurationMs(0);
      monitorLevel(stream);

      // The elapsed counter runs on its own timer rather than off the level
      // meter's animation frame: requestAnimationFrame is throttled or paused
      // whenever the page is not painting, and a timer that silently stops is
      // worse feedback than none.
      durationTimerRef.current = setInterval(() => {
        setDurationMs(Date.now() - startedAtRef.current);
      }, 200);

      autoStopRef.current = setTimeout(() => {
        if (recorderRef.current?.state === "recording") recorderRef.current.stop();
      }, MAX_DURATION_MS);

      return true;
    } catch {
      stream.getTracks().forEach((track) => track.stop());
      setStatus("idle");
      setError("failed");
      return false;
    }
  }, [monitorLevel]);

  const stop = useCallback((): Promise<Recording | null> => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      setStatus("idle");
      return Promise.resolve(null);
    }

    const durationAtStop = Date.now() - startedAtRef.current;

    return new Promise<Recording | null>((resolve) => {
      recorder.onstop = () => {
        const wasCancelled = cancelledRef.current;
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        chunksRef.current = [];
        teardown();
        setStatus("idle");
        setDurationMs(0);
        resolve(wasCancelled ? null : { blob, durationMs: durationAtStop });
      };
      recorder.stop();
    });
  }, [teardown]);

  /** Patient changed their mind — throw the audio away, do not transcribe. */
  const cancel = useCallback(async () => {
    cancelledRef.current = true;
    await stop();
  }, [stop]);

  return { status, error, durationMs, level, start, stop, cancel, setError };
}
