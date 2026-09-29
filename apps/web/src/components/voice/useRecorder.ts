"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** MP4 first (it plays everywhere, Safari included), then WebM/Opus, then Ogg. */
const TYPES = ["audio/mp4", "audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"];
const MAX_MS = 3 * 60 * 1000;
const BARS = 40;

export type RecorderState = "idle" | "starting" | "recording" | "recorded";
export type RecorderError = "denied" | "unsupported" | null;

/** The browser's own recorder: a real voice, recorded on the phone, uploaded as it is (never altered). */
export function useRecorder() {
  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<RecorderError>(null);
  const [ms, setMs] = useState(0);
  const [levels, setLevels] = useState<number[]>([]);
  const [blob, setBlob] = useState<Blob | null>(null);
  const [url, setUrl] = useState<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const ctx = useRef<AudioContext | null>(null);
  const frame = useRef<number | null>(null);
  const started = useRef(0);

  const release = useCallback(() => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    frame.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    void ctx.current?.close().catch(() => undefined);
    ctx.current = null;
  }, []);

  useEffect(() => release, [release]);
  useEffect(() => () => void (url && URL.revokeObjectURL(url)), [url]);

  const stop = useCallback(() => {
    if (rec.current?.state === "recording") rec.current.stop();
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (typeof window === "undefined" || !("MediaRecorder" in window) || !navigator.mediaDevices?.getUserMedia) {
      setError("unsupported");
      return;
    }
    setState("starting");
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
      });
    } catch {
      setState("idle");
      setError("denied");
      return;
    }
    const mimeType = TYPES.find((t) => MediaRecorder.isTypeSupported(t));
    const recorder = new MediaRecorder(stream.current, mimeType ? { mimeType } : undefined);
    const chunks: Blob[] = [];
    recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    recorder.onstop = () => {
      const out = new Blob(chunks, { type: recorder.mimeType || mimeType || "audio/webm" });
      setMs(Date.now() - started.current);
      setBlob(out);
      setUrl(URL.createObjectURL(out));
      setState("recorded");
      release();
    };
    ctx.current = new AudioContext();
    const analyser = ctx.current.createAnalyser();
    analyser.fftSize = 512;
    ctx.current.createMediaStreamSource(stream.current).connect(analyser);
    const data = new Uint8Array(analyser.fftSize);
    let last = 0;
    const tick = (now: number) => {
      const elapsed = Date.now() - started.current;
      if (elapsed >= MAX_MS && recorder.state === "recording") recorder.stop();
      if (now - last > 90) {
        last = now;
        analyser.getByteTimeDomainData(data);
        const rms = Math.sqrt(data.reduce((s, v) => s + ((v - 128) / 128) ** 2, 0) / data.length);
        setLevels((l) => [...l.slice(1 - BARS), Math.min(1, rms * 4)]);
        setMs(elapsed);
      }
      frame.current = requestAnimationFrame(tick);
    };
    rec.current = recorder;
    started.current = Date.now();
    setBlob(null);
    setLevels([]);
    setMs(0);
    recorder.start(250);
    setState("recording");
    frame.current = requestAnimationFrame(tick);
  }, [release]);

  const reset = useCallback(() => {
    setBlob(null);
    setUrl(null);
    setMs(0);
    setLevels([]);
    setState("idle");
  }, []);

  return { state, error, ms, levels, blob, url, start, stop, reset, bars: BARS };
}
