"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, type KeyboardEvent, type TouchEvent } from "react";
import { sampleAlt, type StyleSample } from "@/lib/styleSamples";

/**
 * A sample page large, in a modal <dialog> (focus stays inside, Esc closes): the previous and next pages by
 * button, arrow key (right-to-left aware) or swipe, with the page's description and «3 من 8».
 * `index === null` keeps it closed.
 */
export function SampleLightbox({
  samples,
  index,
  onIndex,
  caption,
}: {
  samples: StyleSample[];
  index: number | null;
  onIndex: (i: number | null) => void;
  caption?: (s: StyleSample) => string | null;
}) {
  const t = useTranslations("storyShowcase.lightbox");
  const locale = useLocale();
  const rtl = locale === "ar";
  const dialog = useRef<HTMLDialogElement>(null);
  const touch = useRef<number | null>(null);
  const open = index !== null && samples[index] !== undefined;
  const current = open ? samples[index] : null;

  useEffect(() => {
    const d = dialog.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);

  const go = (step: number) => {
    if (index === null || !samples.length) return;
    onIndex((index + step + samples.length) % samples.length);
  };

  function onKey(e: KeyboardEvent) {
    const forward = rtl ? "ArrowLeft" : "ArrowRight";
    const back = rtl ? "ArrowRight" : "ArrowLeft";
    if (e.key === forward) go(1);
    else if (e.key === back) go(-1);
    else return;
    e.preventDefault();
  }

  function onTouchEnd(e: TouchEvent) {
    const start = touch.current;
    touch.current = null;
    const end = e.changedTouches[0]?.clientX;
    if (start === null || end === undefined || Math.abs(end - start) < 40) return;
    const leftward = end < start;
    go(leftward === rtl ? -1 : 1); // RTL: swiping right brings the next page
  }

  const arrow = (flip: boolean) => (
    <svg
      className={`size-[22px] ${flip ? "rtl:-scale-x-100" : "ltr:-scale-x-100"}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 6l-6 6 6 6" />
    </svg>
  );

  const text = current ? sampleAlt(current, locale) : "";
  const extra = current && caption ? caption(current) : null;

  return (
    <dialog
      ref={dialog}
      onClose={() => onIndex(null)}
      onClick={(e) => e.target === dialog.current && dialog.current?.close()}
      onKeyDown={onKey}
      aria-label={t("title")}
      className="m-auto max-h-[100dvh] w-full max-w-[min(100vw,960px)] bg-transparent p-2 backdrop:bg-night-950/85"
    >
      {current && (
        <div className="flex flex-col items-center gap-3">
          <div
            className="relative w-full"
            onTouchStart={(e) => (touch.current = e.touches[0]?.clientX ?? null)}
            onTouchEnd={onTouchEnd}
          >
            {/* eslint-disable-next-line @next/next/no-img-element -- static sample pages, already sized */}
            <img
              src={current.src}
              width={current.width}
              height={current.height}
              alt={text}
              decoding="async"
              draggable={false}
              className="mx-auto max-h-[72dvh] w-auto max-w-full rounded-lg object-contain shadow-book"
            />
          </div>
          <p className="max-w-[640px] px-2 text-center text-small leading-[1.6] text-paper" aria-live="polite">
            {extra ? <span className="font-semibold text-amber-300">{extra} · </span> : null}
            {text}
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => go(-1)}
              aria-label={t("prev")}
              disabled={samples.length < 2}
              className="flex size-12 items-center justify-center rounded-full bg-paper/15 text-paper hover:bg-paper/25 disabled:opacity-30"
            >
              {arrow(true)}
            </button>
            <span className="min-w-16 text-center text-small font-semibold text-paper tabular-nums">
              {t("count", { n: (index ?? 0) + 1, total: samples.length })}
            </span>
            <button
              type="button"
              onClick={() => go(1)}
              aria-label={t("next")}
              disabled={samples.length < 2}
              className="flex size-12 items-center justify-center rounded-full bg-paper/15 text-paper hover:bg-paper/25 disabled:opacity-30"
            >
              {arrow(false)}
            </button>
            <button
              type="button"
              onClick={() => dialog.current?.close()}
              className="min-h-12 rounded-full bg-paper px-6 font-bold text-night-900"
              autoFocus
            >
              {t("close")}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );
}
