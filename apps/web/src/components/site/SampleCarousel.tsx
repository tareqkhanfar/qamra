"use client";

import { useRef, useState, type TouchEvent } from "react";
import { Scene, fromArt, type SceneArt } from "@/components/art/Scene";

type Spread = { index: number; text: string; art: SceneArt };

/** "Pages from X's story": real story pages as open-book spreads (text page + illustration). */
export function SampleCarousel({
  spreads,
  labels,
}: {
  spreads: Spread[];
  labels: { prev: string; next: string; page: string; hint: string };
}) {
  const [i, setI] = useState(0);
  const startX = useRef<number | null>(null);
  const go = (d: number) => setI((v) => (v + d + spreads.length) % spreads.length);
  const s = spreads[i];
  if (!s) return null;
  const onTouchStart = (e: TouchEvent) => (startX.current = e.touches[0]?.clientX ?? null);
  const onTouchEnd = (e: TouchEvent) => {
    const x0 = startX.current;
    const x1 = e.changedTouches[0]?.clientX;
    if (x0 !== null && x1 !== undefined && Math.abs(x1 - x0) > 40) go(x1 < x0 ? 1 : -1);
    startX.current = null;
  };
  const arrow = "size-6";
  return (
    <div className="flex w-full flex-col items-center gap-5">
      <div className="flex w-full items-center justify-center gap-4 md:gap-8">
        <button
          type="button"
          onClick={() => go(-1)}
          aria-label={labels.prev}
          className="hidden size-14 shrink-0 items-center justify-center rounded-full border border-line bg-paper-raised text-night-900 md:flex"
        >
          <svg
            className={`${arrow} rtl:-scale-x-100`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M19 12H5" />
            <path d="M11 6l-6 6 6 6" />
          </svg>
        </button>
        <div
          key={s.index}
          onTouchStart={onTouchStart}
          onTouchEnd={onTouchEnd}
          aria-live="polite"
          className="flex w-full max-w-[880px] animate-page-in flex-col overflow-hidden rounded-sm shadow-book md:flex-row"
        >
          <div className="order-2 flex flex-col justify-center gap-5 bg-paper-raised p-6 md:order-1 md:aspect-square md:w-1/2 md:bg-[linear-gradient(to_left,rgba(22,32,74,0.08),transparent_32px)] md:p-14 ltr:md:bg-[linear-gradient(to_right,rgba(22,32,74,0.08),transparent_32px)]">
            <p className="font-display text-[19px] leading-[1.8] font-semibold text-ink md:text-[26px]">{s.text}</p>
            <span className="self-center text-small text-ink-muted">— {s.index} —</span>
          </div>
          <div className="order-1 md:order-2 md:w-1/2">
            <Scene {...fromArt(s.art)} ratio={1} kidScale={s.art.kid_scale ?? 0.55} />
          </div>
        </div>
        <button
          type="button"
          onClick={() => go(1)}
          aria-label={labels.next}
          className="hidden size-14 shrink-0 items-center justify-center rounded-full bg-night-900 text-paper md:flex"
        >
          <svg
            className={`${arrow} ltr:-scale-x-100`}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M19 12H5" />
            <path d="M11 6l-6 6 6 6" />
          </svg>
        </button>
      </div>
      <div className="flex gap-2">
        {spreads.map((sp, n) => (
          <button
            key={sp.index}
            type="button"
            onClick={() => setI(n)}
            aria-label={labels.page.replace("{n}", String(sp.index))}
            aria-current={n === i}
            className={`h-2 rounded-full transition-all ${n === i ? "w-7 bg-night-900" : "w-2 bg-[#C9BCA3]"}`}
          />
        ))}
      </div>
      <span className="text-caption font-normal text-ink-muted md:hidden">{labels.hint}</span>
    </div>
  );
}
