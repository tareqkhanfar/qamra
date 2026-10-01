"use client";

import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type ReactNode } from "react";
import type { ReaderBook } from "@/lib/reader";
import { ReaderPage } from "./ReaderPage";
import { useReaderNav } from "./useReaderNav";

const NIGHT_KEY = "qamra-reader-night";
const round = "flex size-11 shrink-0 items-center justify-center rounded-full";

function Icon({ d, className = "size-5" }: { d: string; className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={d} />
    </svg>
  );
}
const BACK = "M19 12H5M11 6l-6 6 6 6";
const NEXT = "M5 12h14M13 6l6 6-6 6";

function readNight(): boolean {
  try {
    return window.localStorage.getItem(NIGHT_KEY) !== "0";
  } catch {
    return true;
  }
}

type Props = {
  book: ReaderBook;
  lead?: ReactNode; // the close button (owner) or the brand (share link)
  actions?: ReactNode; // e.g. the share button
  end: ReactNode; // what the last page offers
  keysEnabled?: boolean;
};

/** The web reader (design: Reader): page flip, RTL for Arabic books, swipe, keyboard, night mode. */
export function BookReader({ book, lead, actions, end, keysEnabled = true }: Props) {
  const t = useTranslations("reader");
  const dir = book.language === "ar" ? "rtl" : "ltr";
  const total = book.pages.length + 1; // + the end page
  const pageRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const { index, go, swipe } = useReaderNav(total, dir, keysEnabled, pageRef);
  const [night, setNight] = useState(readNight);
  const [full, setFull] = useState(false);
  const page = book.pages[index];
  const lastBeat = book.pages.at(-1)?.beat ?? 0;

  useEffect(() => {
    const next = book.pages[index + 1]?.image;
    if (next) new window.Image().src = next; // the next picture is ready before the turn
  }, [book.pages, index]);
  useEffect(() => {
    const onChange = () => setFull(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleNight = (on: boolean) => {
    setNight(on);
    try {
      window.localStorage.setItem(NIGHT_KEY, on ? "1" : "0");
    } catch {}
  };
  const toggleFull = () => {
    if (document.fullscreenElement) void document.exitFullscreen?.();
    else void rootRef.current?.requestFullscreen?.().catch(() => {});
  };
  const where = !page ? t("theEnd") : page.beat === 0 ? t("cover") : t("pageOf", { n: page.beat, total: lastBeat });
  const chip = night ? "bg-night-900 text-paper hover:bg-night-800" : "bg-paper-sunk text-night-900 hover:bg-line";

  return (
    <div ref={rootRef} className={`flex min-h-dvh flex-col ${night ? "bg-night-950 text-paper" : "bg-paper text-ink"}`}>
      <header className="flex h-16 items-center gap-2 px-3 md:h-[72px] md:gap-4 md:px-8">
        {lead}
        <h1 className="min-w-0 grow truncate text-[17px] md:text-[20px]">{book.title}</h1>
        {book.kind === "preview" && (
          <span className="shrink-0 rounded-full bg-amber-100 px-3 py-1 text-caption font-bold text-amber-700">
            {t("previewBadge")}
          </span>
        )}
        <button
          type="button"
          onClick={toggleFull}
          aria-label={full ? t("exitFullscreen") : t("fullscreen")}
          className={`${round} ${chip}`}
        >
          <Icon d={full ? "M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5" : "M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"} />
        </button>
        {actions}
      </header>

      <main
        dir={dir}
        className="flex grow touch-pan-y items-center justify-center gap-4 px-4 py-2 md:gap-10"
        {...swipe}
      >
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={index === 0}
          aria-label={t("previous")}
          className={`hidden size-16 md:flex ${round} border disabled:opacity-30 ${night ? "border-line-dark bg-night-900" : "border-line bg-paper-raised"}`}
        >
          <Icon d={BACK} className="size-[26px] rtl:-scale-x-100" />
        </button>
        <div ref={pageRef} aria-live="polite" className="flex w-full justify-center md:w-auto">
          {page ? (
            <ReaderPage page={page} title={book.title} dir={dir} pageLabel={where} coverLabel={t("coverLabel")} />
          ) : (
            <div className="flex aspect-square w-full max-w-[440px] flex-col items-center justify-center gap-5 rounded-[10px] bg-paper-raised p-8 text-center text-ink shadow-[0_30px_80px_rgba(0,0,0,0.45)] md:w-[min(60vw,560px)] md:max-w-none">
              <span className="text-[40px] text-amber-500" aria-hidden="true">
                ☾
              </span>
              <h2 className="font-display text-[34px] font-extrabold text-night-900">{t("theEnd")}</h2>
              {end}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => go(1)}
          disabled={index === total - 1}
          aria-label={t("next")}
          className={`hidden size-16 md:flex ${round} bg-amber-500 text-night-950 disabled:opacity-30`}
        >
          <Icon d={NEXT} className="size-[26px] rtl:-scale-x-100" />
        </button>
      </main>

      <footer dir={dir} className="flex items-center gap-3 px-4 pt-2 pb-5 md:h-24 md:gap-5 md:px-[12vw] md:pb-0">
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={index === 0}
          aria-label={t("previous")}
          className={`${round} border disabled:opacity-30 md:hidden ${night ? "border-line-dark bg-night-900" : "border-line bg-paper-raised"}`}
        >
          <Icon d={BACK} className="size-5 rtl:-scale-x-100" />
        </button>
        <span className={`text-small whitespace-nowrap ${night ? "text-ink-dark-muted" : "text-ink-muted"}`}>
          {where}
        </span>
        <div
          role="progressbar"
          aria-label={t("progress")}
          aria-valuemin={1}
          aria-valuemax={total}
          aria-valuenow={index + 1}
          className={`flex h-1.5 grow overflow-hidden rounded-full ${night ? "bg-night-800" : "bg-paper-sunk"}`}
        >
          <div
            className="rounded-full bg-amber-500 transition-[width] duration-300"
            style={{ width: `${((index + 1) / total) * 100}%` }}
          />
        </div>
        <label
          className={`hidden min-h-11 items-center gap-2 text-small md:flex ${night ? "text-ink-dark-muted" : "text-ink-muted"}`}
        >
          {t("night")}
          <input
            type="checkbox"
            checked={night}
            onChange={(e) => toggleNight(e.target.checked)}
            className="size-5 accent-amber-500"
          />
        </label>
        <button
          type="button"
          onClick={() => go(1)}
          disabled={index === total - 1}
          aria-label={t("next")}
          className={`${round} bg-amber-500 text-night-950 disabled:opacity-30 md:hidden`}
        >
          <Icon d={NEXT} className="size-5 rtl:-scale-x-100" />
        </button>
      </footer>
    </div>
  );
}
