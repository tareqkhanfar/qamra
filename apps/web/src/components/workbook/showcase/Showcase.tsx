"use client";

/* eslint-disable @next/next/no-img-element -- static pages from /public, exported once by scripts/export_workbook_previews.py */
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent, type TouchEvent } from "react";
import type { Part, Preview } from "@/lib/workbook";

const title = (p: Preview, locale: string) => (locale === "ar" ? p.title_ar : p.title_en);
const ratio = (p: Preview) => (p.w && p.h ? `${p.w} / ${p.h}` : "1 / 1.414");

/** A page image: the small copy for strips and fans, the big one where it is shown large. */
function Page({
  page,
  sizes,
  eager = false,
  gray,
  className = "",
}: {
  page: Preview;
  sizes: string;
  eager?: boolean;
  gray: boolean;
  className?: string;
}) {
  return (
    <img
      src={page.sm ?? page.src}
      srcSet={page.sm ? `${page.sm} 360w, ${page.src} 720w` : undefined}
      sizes={sizes}
      alt=""
      width={page.w ?? 720}
      height={page.h ?? 1018}
      loading={eager ? "eager" : "lazy"}
      fetchPriority={eager ? "high" : undefined}
      decoding="async"
      style={{ aspectRatio: ratio(page) }}
      className={`block h-auto w-full bg-white object-cover ${gray ? "grayscale" : ""} ${className}`}
    />
  );
}

function Chevron({ next }: { next: boolean }) {
  // "next" points left in RTL and right in LTR, like the story reader's arrows
  return (
    <svg
      className={`size-5 ${next ? "rtl:-scale-x-100" : "ltr:-scale-x-100"}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.4"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

function Zoom() {
  return (
    <svg
      className="size-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="6.5" />
      <path d="M16 16l4.5 4.5M11 8.5v5M8.5 11h5" />
    </svg>
  );
}

/**
 * The pages of the part the parent picked, as the product page shows them: the cover on a "stage" with two of
 * its pages fanned behind it (a set fans the covers of its parts), a strip of its pages (a tab per part of a
 * set) and a full-screen viewer with previous/next, arrow keys and swipes. `heroClass`/`stripClass` place the
 * two blocks in the page's layout (the strip sits under the choices on phones). Black and white shows the pages
 * in grayscale; a PDF gets its badge. Remount it (a `key`) when the picks change.
 */
export function Showcase({
  parts,
  partName,
  caption,
  tone,
  bw,
  pdf,
  binding,
  heroClass = "",
  stripClass = "",
}: {
  parts: Part[];
  partName: (key: string) => string;
  caption: string; // where the pages come from, e.g. «صفحات من KG1، الجزء الثاني»
  tone: string;
  bw: boolean;
  pdf: boolean;
  binding: string | null;
  heroClass?: string;
  stripClass?: string;
}) {
  const t = useTranslations("workbookShowcase");
  const locale = useLocale();
  const rtl = locale === "ar";
  const [active, setActive] = useState(0);
  const [zoom, setZoom] = useState<number | null>(null); // index in [cover, ...pages] of the active part
  const dialog = useRef<HTMLDialogElement>(null);
  const touch = useRef<number | null>(null);
  const part = parts[Math.min(active, parts.length - 1)];
  const sequence = useMemo(() => (part ? [part.cover, ...part.pages] : []), [part]);
  const set = parts.length > 1;

  useEffect(() => {
    // fetch the neighbours of the page in the viewer, so previous/next is instant
    if (zoom === null) return;
    for (const i of [zoom - 1, zoom + 1]) {
      const p = sequence[i];
      if (p) new Image().src = p.src;
    }
  }, [zoom, sequence]);

  if (!part) return null;

  function open(partIndex: number, index: number) {
    setActive(partIndex);
    setZoom(index);
    if (!dialog.current?.open) dialog.current?.showModal();
  }
  const go = (step: number) => setZoom((z) => (z === null ? z : Math.min(Math.max(z + step, 0), sequence.length - 1)));
  function onKey(e: KeyboardEvent<HTMLDialogElement>) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    go((e.key === "ArrowLeft") === rtl ? 1 : -1); // the next page is to the left in Arabic
  }
  function onTouchEnd(e: TouchEvent) {
    const start = touch.current;
    touch.current = null;
    const end = e.changedTouches[0]?.clientX;
    if (start === null || end === undefined || Math.abs(end - start) < 40) return;
    go(end > start === rtl ? 1 : -1); // dragging the page towards the reading direction's end
  }
  function scrollRail(el: HTMLElement | null | undefined, next: boolean) {
    if (!el) return;
    const step = el.clientWidth * 0.8;
    el.scrollBy({ left: (next === rtl ? -1 : 1) * step, behavior: "smooth" });
  }

  const shown = zoom === null ? null : sequence[zoom];
  const fan = set ? parts.slice(0, 5) : [];
  const middle = (fan.length - 1) / 2;
  // the covers of a set fanned out: the first part in front, towards the start of the reading direction
  const spread =
    fan.length > 3
      ? "[transform:translateX(calc(var(--i)*40px))_rotate(calc(var(--i)*5deg))] md:[transform:translateX(calc(var(--i)*58px))_rotate(calc(var(--i)*5deg))]"
      : "[transform:translateX(calc(var(--i)*64px))_rotate(calc(var(--i)*6deg))] md:[transform:translateX(calc(var(--i)*92px))_rotate(calc(var(--i)*6deg))]";
  const badge = "rounded-full bg-paper-raised/95 px-2.5 py-1 text-caption font-bold text-night-900 shadow-sm";

  return (
    <>
      <div
        className={`relative mx-4 flex h-[330px] items-start justify-center overflow-hidden rounded-[24px] pt-5 md:mx-0 md:h-[420px] md:pt-6 ${tone} ${heroClass}`}
      >
        {set ? (
          fan.map((p, i) => {
            const off = (i - middle) * (rtl ? -1 : 1);
            return (
              <button
                key={p.key}
                type="button"
                onClick={() => open(i, 0)}
                aria-label={t("openCover", { part: partName(p.key) })}
                style={{ "--i": off, zIndex: fan.length - i } as CSSProperties}
                className={`absolute w-[128px] overflow-hidden rounded-[8px] shadow-[0_10px_26px_rgba(22,32,74,0.28)] transition hover:-translate-y-1 focus-visible:outline-3 focus-visible:outline-amber-500 md:w-[178px] ${spread}`}
              >
                <Page page={p.cover} sizes="(min-width: 768px) 178px, 128px" eager={i === 0} gray={bw} />
              </button>
            );
          })
        ) : (
          <>
            {part.pages.slice(0, 2).map((p, i) => (
              <div
                key={p.src}
                aria-hidden="true"
                style={{ transform: `translateX(${(i ? -1 : 1) * 30}%) rotate(${(i ? -1 : 1) * 7}deg) scale(0.9)` }}
                className="absolute w-[170px] overflow-hidden rounded-[6px] border border-line opacity-95 shadow-[0_6px_18px_rgba(22,32,74,0.18)] md:w-[224px]"
              >
                <Page page={p} sizes="(min-width: 768px) 224px, 170px" gray={bw} />
              </div>
            ))}
            <button
              type="button"
              onClick={() => open(0, 0)}
              aria-label={t("openCover", { part: partName(part.key) })}
              className="group relative w-[186px] overflow-hidden rounded-[8px] shadow-[0_14px_32px_rgba(22,32,74,0.32)] focus-visible:outline-3 focus-visible:outline-amber-500 md:w-[248px]"
            >
              <Page
                page={part.cover}
                sizes="(min-width: 768px) 248px, 186px"
                eager
                gray={bw}
                className="transition group-hover:scale-[1.02]"
              />
              <span className="absolute end-2 bottom-2 flex size-8 items-center justify-center rounded-full bg-night-900/80 text-paper">
                <Zoom />
              </span>
            </button>
          </>
        )}
        <div className="pointer-events-none absolute end-3 bottom-3 flex flex-wrap justify-end gap-1.5">
          {bw && <span className={badge}>{t("bwBadge")}</span>}
          {set && <span className={badge}>{t("parts", { count: parts.length })}</span>}
        </div>
        {(pdf || binding) && (
          <span
            className={`pointer-events-none absolute start-3 bottom-3 ${pdf ? "bg-night-900! text-paper!" : ""} ${badge}`}
          >
            {pdf ? t("pdfBadge") : binding}
          </span>
        )}
      </div>

      <section aria-labelledby="peek-title" className={`flex flex-col gap-2.5 px-4 md:px-0 ${stripClass}`}>
        <div className="flex flex-col gap-0.5">
          <h2 id="peek-title" className="text-[20px] text-night-900">
            {t("peek")}
          </h2>
          <p className="text-caption text-ink-muted" aria-live="polite">
            {caption}
          </p>
        </div>
        {set && (
          <div
            role="tablist"
            aria-label={t("partsLabel")}
            className="-mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:flex-wrap md:overflow-visible md:px-0"
          >
            {parts.map((p, i) => (
              <button
                key={p.key}
                type="button"
                role="tab"
                id={`part-tab-${p.key}`}
                aria-selected={i === active}
                aria-controls="part-pages"
                onClick={() => setActive(i)}
                className={`min-h-11 shrink-0 rounded-full px-4 text-[14px] font-semibold transition ${
                  i === active
                    ? "bg-night-900 text-paper"
                    : "border-[1.5px] border-line bg-paper-raised text-night-900 hover:border-night-500"
                }`}
              >
                {partName(p.key)}
              </button>
            ))}
          </div>
        )}
        {(bw || pdf) && (
          <p className="rounded-[12px] bg-paper-sunk px-3 py-2 text-caption leading-[1.6] text-ink-muted">
            {bw ? t("bwNote") : t("pdfNote")}
          </p>
        )}
        <div
          className="relative"
          id="part-pages"
          role={set ? "tabpanel" : undefined}
          aria-labelledby={set ? `part-tab-${part.key}` : undefined}
        >
          <ul className="-mx-4 flex snap-x snap-mandatory scroll-px-4 gap-2.5 overflow-x-auto px-4 pb-2 md:mx-0 md:scroll-px-0 md:px-0">
            {part.pages.map((p, i) => (
              <li key={p.src} className="w-[132px] shrink-0 snap-start md:w-[122px]">
                <figure className="flex flex-col gap-1.5">
                  <button
                    type="button"
                    onClick={() => open(active, i + 1)}
                    aria-label={t("open", { title: title(p, locale) })}
                    className="overflow-hidden rounded-[10px] border border-line bg-white transition hover:-translate-y-0.5 hover:shadow-md focus-visible:outline-3 focus-visible:outline-amber-500"
                  >
                    <Page page={p} sizes="(min-width: 768px) 122px, 132px" gray={bw} />
                  </button>
                  <figcaption className="line-clamp-2 text-caption leading-[1.45] text-ink-muted">
                    {title(p, locale)}
                  </figcaption>
                </figure>
              </li>
            ))}
          </ul>
          {part.pages.length > 3 &&
            ([false, true] as const).map((next) => (
              <button
                key={String(next)}
                type="button"
                onClick={(e) => scrollRail(e.currentTarget.parentElement?.querySelector("ul"), next)}
                aria-label={t(next ? "morePages" : "earlierPages")}
                className={`absolute top-[62px] hidden size-10 items-center justify-center rounded-full border border-line bg-paper-raised text-night-900 shadow-md transition hover:bg-paper md:flex ${
                  next ? "-end-4" : "-start-4"
                }`}
              >
                <Chevron next={next} />
              </button>
            ))}
        </div>
      </section>

      <dialog
        ref={dialog}
        onClose={() => setZoom(null)}
        onKeyDown={onKey}
        aria-label={t("viewer", { part: partName(part.key) })}
        className="m-0 h-dvh max-h-none w-screen max-w-none bg-night-950/95 p-0 text-paper backdrop:bg-night-950/85"
      >
        {shown && zoom !== null && (
          <div className="flex h-full flex-col">
            <div className="flex items-center justify-between gap-3 px-4 pt-3 pb-2">
              <span className="text-small font-semibold text-night-100">
                {partName(part.key)} · {t("counter", { n: zoom + 1, total: sequence.length })}
              </span>
              <button
                type="button"
                autoFocus
                onClick={() => dialog.current?.close()}
                className="flex min-h-11 items-center rounded-full bg-paper px-5 text-small font-bold text-night-900"
              >
                {t("close")}
              </button>
            </div>
            <div
              className="relative flex min-h-0 grow items-center justify-center px-2 md:px-20"
              onTouchStart={(e) => (touch.current = e.touches[0]?.clientX ?? null)}
              onTouchEnd={onTouchEnd}
              onClick={(e) => e.target === e.currentTarget && dialog.current?.close()}
            >
              <img
                key={shown.src}
                src={shown.src}
                alt={title(shown, locale)}
                width={shown.w ?? 720}
                height={shown.h ?? 1018}
                className={`max-h-full w-auto max-w-full rounded-lg bg-white object-contain ${bw ? "grayscale" : ""}`}
              />
              {([false, true] as const).map((next) => {
                const disabled = next ? zoom >= sequence.length - 1 : zoom <= 0;
                return (
                  <button
                    key={String(next)}
                    type="button"
                    onClick={() => go(next ? 1 : -1)}
                    disabled={disabled}
                    aria-label={t(next ? "next" : "previous")}
                    className={`absolute top-1/2 flex size-12 -translate-y-1/2 items-center justify-center rounded-full bg-paper/90 text-night-900 shadow-lg transition disabled:opacity-30 ${
                      next ? "end-2 md:end-5" : "start-2 md:start-5"
                    }`}
                  >
                    <Chevron next={next} />
                  </button>
                );
              })}
            </div>
            <p className="px-4 pt-2 pb-[max(16px,env(safe-area-inset-bottom))] text-center text-small font-semibold">
              {title(shown, locale)}
            </p>
          </div>
        )}
      </dialog>
    </>
  );
}
