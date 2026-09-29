"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "@/i18n/navigation";

const PREF_KEY = "qamra-music";
const TRACK = "/audio/lullaby.mp3";

function prefersOff(): boolean {
  try {
    return window.localStorage.getItem(PREF_KEY) === "off";
  } catch {
    return false;
  }
}

function savePref(on: boolean) {
  try {
    window.localStorage.setItem(PREF_KEY, on ? "on" : "off");
  } catch {
    /* private mode: preference just isn't remembered */
  }
}

/**
 * Background lullaby (admin: music_enabled / music_volume). Browsers only allow sound after a user
 * gesture, so it starts on the first tap/key anywhere; the floating button toggles it (remembered).
 * Web Audio gives a gapless loop and soft fades. Never plays in the admin area, and stays out of the way of the
 * create flow and checkout, whose own action bars sit at the bottom of the screen.
 */
export function MusicPlayer({ volume, labels }: { volume: number; labels: { play: string; pause: string } }) {
  const pathname = usePathname();
  const hidden =
    ["/admin", "/create", "/cart", "/checkout", "/r/", "/v/"].some((p) => pathname.startsWith(p)) ||
    /\/voice(\/|$)/.test(pathname); // «صوت أهلي»: never over a recording or a family voice
  const [playing, setPlaying] = useState(false);
  const ctx = useRef<AudioContext | null>(null);
  const gain = useRef<GainNode | null>(null);
  const started = useRef(false);
  const target = Math.max(0, Math.min(1, volume / 100)) * 0.5;

  const start = useCallback(async () => {
    try {
      if (!ctx.current) {
        const Ctor =
          window.AudioContext ?? (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        ctx.current = new Ctor();
        gain.current = ctx.current.createGain();
        gain.current.gain.value = 0;
        gain.current.connect(ctx.current.destination);
      }
      const c = ctx.current;
      await c.resume();
      if (!started.current) {
        started.current = true;
        const data = await (await fetch(TRACK)).arrayBuffer();
        const buffer = await c.decodeAudioData(data);
        const src = c.createBufferSource();
        src.buffer = buffer;
        src.loop = true;
        src.connect(gain.current!);
        src.start();
      }
      gain.current!.gain.setTargetAtTime(target, c.currentTime, 1.2);
      setPlaying(true);
    } catch {
      started.current = false;
      setPlaying(false);
    }
  }, [target]);

  const stop = useCallback(() => {
    const c = ctx.current;
    if (c && gain.current) {
      gain.current.gain.setTargetAtTime(0, c.currentTime, 0.35);
      window.setTimeout(() => void c.suspend().catch(() => undefined), 1400);
    }
    setPlaying(false);
  }, []);

  // first user gesture anywhere starts the music (unless the visitor muted it before)
  useEffect(() => {
    if (hidden) return;
    const onFirst = (e: Event) => {
      if ((e.target as Element | null)?.closest?.("[data-music-toggle]")) return;
      window.removeEventListener("pointerdown", onFirst);
      window.removeEventListener("keydown", onFirst);
      if (!prefersOff()) void start();
    };
    window.addEventListener("pointerdown", onFirst, { passive: true });
    window.addEventListener("keydown", onFirst);
    return () => {
      window.removeEventListener("pointerdown", onFirst);
      window.removeEventListener("keydown", onFirst);
    };
  }, [hidden, start]);

  // silence in background tabs and on admin pages
  useEffect(() => {
    const onVis = () => {
      const c = ctx.current;
      if (!c) return;
      if (document.hidden) void c.suspend().catch(() => undefined);
      else if (playing && !hidden) void c.resume().catch(() => undefined);
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [playing, hidden]);

  useEffect(() => {
    if (hidden && ctx.current) void ctx.current.suspend().catch(() => undefined);
  }, [hidden]);

  if (hidden) return null;
  return (
    <button
      type="button"
      data-music-toggle
      aria-label={playing ? labels.pause : labels.play}
      aria-pressed={playing}
      onClick={() => {
        if (playing) {
          savePref(false);
          stop();
        } else {
          savePref(true);
          void start();
        }
      }}
      className="fixed end-4 bottom-[96px] z-50 flex size-12 items-center justify-center rounded-full bg-night-900/90 text-amber-300 shadow-2 ring-1 ring-night-700 backdrop-blur transition hover:scale-105 md:end-6 md:bottom-6"
    >
      {playing ? (
        <span className="flex h-5 items-end gap-[3px]" aria-hidden="true">
          <span className="w-[3px] animate-[eq_0.9s_ease-in-out_infinite] rounded-full bg-current" />
          <span className="w-[3px] animate-[eq_0.9s_ease-in-out_0.2s_infinite] rounded-full bg-current" />
          <span className="w-[3px] animate-[eq_0.9s_ease-in-out_0.4s_infinite] rounded-full bg-current" />
        </span>
      ) : (
        <svg
          className="size-6"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M9 18V6l10-2v12" />
          <circle cx="6.5" cy="18" r="2.5" />
          <circle cx="16.5" cy="16" r="2.5" />
        </svg>
      )}
    </button>
  );
}
