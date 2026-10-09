"use client";

import { useLocale, useTranslations } from "next-intl";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { Scene, fromArt, type SceneArt } from "@/components/art/Scene";
import { Link } from "@/i18n/navigation";
import { nameCases } from "@/lib/arabicName";
import { rememberedVariant, type Example, type ExamplePage, type ExampleVariant } from "@/lib/examples";
import { ExampleImage } from "./ExampleImage";
import { naskh } from "./fonts";
import { VariantSwitch } from "./VariantSwitch";

export type FallbackPage = { index: number; text: string; art: SceneArt };
export type ViewerEnd = { href: string; label: string; title: string; body: string };

type View =
  | { kind: "title"; key: string }
  | { kind: "page"; key: string; page: ExamplePage; last: boolean }
  | { kind: "art"; key: string; page: FallbackPage }
  | { kind: "parents"; key: string }
  | { kind: "end"; key: string };

function viewsOf(example: Example | null, fallback: FallbackPage[], end: boolean, title: boolean): View[] {
  const out: View[] = [];
  if (example) {
    if (title) out.push({ kind: "title", key: "title" });
    const story = example.pages.filter((p) => p.beat > 0);
    story.forEach((p, i) => out.push({ kind: "page", key: `p${p.beat}`, page: p, last: i === story.length - 1 }));
    if (example.parents) out.push({ kind: "parents", key: "parents" });
  } else {
    fallback.forEach((p) => out.push({ kind: "art", key: `a${p.index}`, page: p }));
  }
  if (end) out.push({ kind: "end", key: "end" });
  return out;
}

const ASPECT: Record<ExamplePage["aspect"], string> = {
  "1:1": "aspect-square",
  "3:2": "aspect-[3/2]",
  "16:9": "aspect-video",
};

const subscribe = (cb: () => void) => {
  window.addEventListener("storage", cb);
  return () => window.removeEventListener("storage", cb);
};

function Arrow({ back = false }: { back?: boolean }) {
  // "next" points left in RTL and right in LTR (design README); "back" the other way
  return (
    <svg
      className={`size-6 ${back ? "ltr:-scale-x-100" : "rtl:-scale-x-100"}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </svg>
  );
}

/** A page's words as the book prints them: the story font, generous line height for the tashkeel. */
function Words({ text, lang, last, endLabel }: { text: string; lang: string; last?: boolean; endLabel: string }) {
  return (
    <p
      lang={lang}
      dir={lang === "ar" ? "rtl" : "ltr"}
      className={`${lang === "ar" ? naskh.className : "font-body"} text-center text-[17px] leading-[1.95] text-ink md:text-[18px]`}
    >
      {text}
      {last && <span className="mt-1 block font-display text-small font-bold text-amber-700">— {endLabel} —</span>}
    </p>
  );
}

function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`flex grow flex-col overflow-hidden rounded-2xl border border-line bg-paper-raised shadow-1 ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * «تصفّحوا الكتاب»: flip through a real example, page by page (swipe, arrows, keyboard; RTL-aware). Only the
 * pages next to the one shown load their images. A tap opens the page large (pinch to zoom). Without a
 * published example it shows the theme's illustrated sample pages with a note, so it always looks finished.
 */
export function BookViewer({
  examples,
  initialVariant = null,
  fallback = [],
  end = null,
  headingId,
  variant = null,
  onVariant,
  titlePage = true,
}: {
  examples: Example[];
  initialVariant?: ExampleVariant | null;
  fallback?: FallbackPage[];
  end?: ViewerEnd | null;
  headingId?: string;
  /** Controlled look (the page shows the same example elsewhere, e.g. its cover). */
  variant?: ExampleVariant | null;
  onVariant?: (v: ExampleVariant) => void;
  /** Start with the title and dedication page (as the printed book does, right after its cover). */
  titlePage?: boolean;
}) {
  const t = useTranslations("examples");
  const rtl = useLocale() === "ar";
  const available = useMemo(() => [...new Set(examples.map((e) => e.variant))], [examples]);
  const remembered = useSyncExternalStore(
    subscribe,
    () => rememberedVariant.get(),
    () => null,
  );
  const [chosen, setChosen] = useState<ExampleVariant | null>(null);
  const wanted = variant ?? chosen ?? initialVariant ?? remembered;
  const example = examples.find((e) => e.variant === wanted) ?? examples[0] ?? null;
  const views = useMemo(() => viewsOf(example, fallback, !!end, titlePage), [example, fallback, end, titlePage]);
  const [index, setIndex] = useState(0);
  const [zoom, setZoom] = useState<ExamplePage | null>(null);
  const scroller = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const current = Math.min(index, views.length - 1);

  const goTo = useCallback(
    (i: number) => {
      const el = scroller.current;
      if (!el) return;
      const next = Math.max(0, Math.min(views.length - 1, i));
      el.scrollTo({ left: (rtl ? -1 : 1) * next * el.clientWidth, behavior: "smooth" });
    },
    [rtl, views.length],
  );

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    let frame = 0;
    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => setIndex(Math.round(Math.abs(el.scrollLeft) / Math.max(1, el.clientWidth))));
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(frame);
    };
  }, []);

  // the book is as tall as the page shown (a short page doesn't leave the tallest page's gap under it)
  const [height, setHeight] = useState<number | undefined>(undefined);
  useEffect(() => {
    const slide = scroller.current?.children[current] as HTMLElement | undefined;
    if (!slide) return;
    const observer = new ResizeObserver(() => setHeight(slide.offsetHeight));
    observer.observe(slide);
    return () => observer.disconnect();
  }, [current, views]);

  useEffect(() => {
    if (zoom) dialog.current?.showModal();
  }, [zoom]);

  function onKey(e: KeyboardEvent) {
    const forward = rtl ? "ArrowLeft" : "ArrowRight";
    const back = rtl ? "ArrowRight" : "ArrowLeft";
    if (e.key === forward) goTo(current + 1);
    else if (e.key === back) goTo(current - 1);
    else if (e.key === "Home") goTo(0);
    else if (e.key === "End") goTo(views.length - 1);
    else return;
    e.preventDefault();
  }

  function pick(v: ExampleVariant) {
    setChosen(v);
    rememberedVariant.set(v);
    onVariant?.(v);
  }

  const lang = example?.lang ?? "ar";
  const pageLabel = (v: View) =>
    v.kind === "page" && v.page.numbers.length
      ? t("pageNumbers", { pages: v.page.numbers.join("–") })
      : v.kind === "title"
        ? t("titlePage")
        : v.kind === "parents"
          ? t("parents.title")
          : "";

  function slide(v: View, i: number) {
    const near = Math.abs(i - current) <= 1; // only the neighbours load their pictures
    if (v.kind === "page") {
      const alt = v.page.text
        ? t("pageAlt", { pages: v.page.numbers.join("–"), text: v.page.text.slice(0, 90) })
        : pageLabel(v);
      return (
        <Card>
          <button
            type="button"
            onClick={() => setZoom(v.page)}
            aria-label={t("zoom", { page: pageLabel(v) })}
            className={`relative block w-full cursor-zoom-in overflow-hidden bg-paper-sunk ${ASPECT[v.page.aspect]}`}
          >
            {near && (
              <ExampleImage
                page={v.page}
                alt={alt}
                sizes="(min-width: 1024px) 560px, calc(100vw - 32px)"
                priority={i === 0}
                className="absolute inset-0 size-full object-cover"
              />
            )}
          </button>
          {v.page.text && (
            <div className="flex grow items-center justify-center px-4 py-4 md:px-6">
              <Words text={v.page.text} lang={lang} last={v.last} endLabel={t("theEnd")} />
            </div>
          )}
        </Card>
      );
    }
    if (v.kind === "art") {
      return (
        <Card>
          <div role="img" aria-label={t("placeholderAlt")} className="relative">
            <Scene {...fromArt(v.page.art)} ratio={1} kidScale={v.page.art.kid_scale ?? 0.55} />
            <span className="absolute start-3 top-3 rounded-full bg-night-950/75 px-2.5 py-1 text-caption font-semibold text-paper">
              {t("placeholder")}
            </span>
          </div>
          <div className="flex grow items-center justify-center px-4 py-4 md:px-6">
            <Words text={v.page.text} lang="ar" endLabel={t("theEnd")} />
          </div>
        </Card>
      );
    }
    if (v.kind === "title" && example) {
      return (
        <Card className="items-center justify-center gap-3 bg-[radial-gradient(circle_at_50%_0%,var(--color-amber-100),transparent_60%)] px-6 py-10 text-center">
          <span aria-hidden="true" className="text-[28px] text-amber-500">
            ✦
          </span>
          <p lang={lang} className={`${naskh.className} text-[26px] leading-[1.6] font-bold text-night-900`}>
            {example.title}
          </p>
          <p className="text-small text-ink-muted">{t("madeFor", nameCases(example.child_name))}</p>
          {example.dedication && (
            <div className="mt-2 flex flex-col gap-1">
              <span className="text-caption font-bold text-amber-700">{t("dedication")}</span>
              <p lang={lang} className={`${naskh.className} text-[18px] leading-[1.9] font-semibold`}>
                {example.dedication}
              </p>
            </div>
          )}
        </Card>
      );
    }
    if (v.kind === "parents" && example?.parents) {
      return (
        <Card className="justify-center gap-3 px-5 py-8 md:px-8">
          <h3 className="font-display text-[24px] text-night-900">{t("parents.title")}</h3>
          <p lang={lang} className={`${naskh.className} text-[17px] leading-[1.9]`}>
            {example.parents.lesson}
          </p>
          <ol className="flex flex-col gap-2 rounded-xl border border-line bg-paper p-4">
            {example.parents.questions.map((q, n) => (
              <li key={q} className="flex items-baseline gap-2.5">
                <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-amber-500 text-caption font-bold text-night-950">
                  {n + 1}
                </span>
                <span lang={lang} className={`${naskh.className} text-[16px] leading-[1.9]`}>
                  {q}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      );
    }
    if (v.kind === "end" && end) {
      const cta =
        "flex min-h-14 items-center justify-center rounded-full bg-amber-500 px-6 text-[17px] font-bold text-night-950";
      return (
        <Card className="items-center justify-center gap-4 bg-night-900 px-6 py-12 text-center text-paper">
          <h3 className="font-display text-[26px] text-paper">{end.title}</h3>
          <p className="max-w-[420px] text-body text-night-100">{end.body}</p>
          {end.href.startsWith("#") ? (
            <a href={end.href} className={cta}>
              {end.label}
            </a>
          ) : (
            <Link href={end.href} className={cta}>
              {end.label}
            </Link>
          )}
        </Card>
      );
    }
    return null;
  }

  const shown = views[current];
  return (
    <div className="flex flex-col gap-3">
      {example && available.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <VariantSwitch value={example.variant} available={available} onChange={pick} />
          <span className="text-caption text-ink-muted">
            {t("synthetic", { ...nameCases(example.child_name), variant: example.variant })}
          </span>
        </div>
      )}
      {!example && fallback.length > 0 && <p className="text-caption text-ink-muted">{t("placeholderNote")}</p>}
      <div
        ref={scroller}
        tabIndex={0}
        role="region"
        aria-roledescription={t("carousel")}
        aria-labelledby={headingId}
        onKeyDown={onKey}
        style={height ? { height } : undefined}
        className="flex snap-x snap-mandatory [scrollbar-width:none] items-start overflow-x-auto overflow-y-hidden overscroll-x-contain scroll-smooth rounded-2xl transition-[height] duration-300 focus-visible:outline-offset-4 [&::-webkit-scrollbar]:hidden"
      >
        {views.map((v, i) => (
          <div
            key={`${example?.id ?? "art"}-${v.key}`}
            role="group"
            aria-roledescription={t("slide")}
            aria-label={t("position", { n: i + 1, total: views.length })}
            aria-hidden={i !== current}
            inert={i !== current}
            className="w-full shrink-0 snap-center snap-always"
          >
            {slide(v, i)}
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => goTo(current - 1)}
          disabled={current === 0}
          aria-label={t("prev")}
          className="flex size-12 shrink-0 items-center justify-center rounded-full border border-line bg-paper-raised text-night-900 disabled:opacity-40"
        >
          <Arrow back />
        </button>
        <div className="flex grow flex-col gap-1.5">
          <div className="flex justify-between text-caption text-ink-muted">
            <span aria-live="polite">{t("position", { n: current + 1, total: views.length })}</span>
            <span>{shown ? pageLabel(shown) : ""}</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-paper-sunk" aria-hidden="true">
            <div
              className="h-full rounded-full bg-amber-500 transition-[width]"
              style={{ width: `${((current + 1) / Math.max(1, views.length)) * 100}%` }}
            />
          </div>
        </div>
        <button
          type="button"
          onClick={() => goTo(current + 1)}
          disabled={current >= views.length - 1}
          aria-label={t("next")}
          className="flex size-12 shrink-0 items-center justify-center rounded-full bg-night-900 text-paper disabled:opacity-40"
        >
          <Arrow />
        </button>
      </div>
      <span className="text-center text-caption text-ink-muted md:hidden">{t("swipe")}</span>

      <dialog
        ref={dialog}
        onClose={() => setZoom(null)}
        onClick={(e) => e.target === dialog.current && dialog.current?.close()}
        aria-label={t("zoomTitle")}
        className="m-auto max-h-[100dvh] w-full max-w-[min(100vw,1100px)] bg-transparent p-2 backdrop:bg-night-950/85"
      >
        {zoom && (
          <div className="flex flex-col items-center gap-3">
            <ExampleImage
              page={zoom}
              alt={zoom.text ?? t("titlePage")}
              sizes="100vw"
              priority
              className="max-h-[80dvh] w-auto max-w-full rounded-lg object-contain"
            />
            <button
              type="button"
              onClick={() => dialog.current?.close()}
              className="min-h-11 rounded-full bg-paper px-6 font-bold text-night-900"
              autoFocus
            >
              {t("close")}
            </button>
          </div>
        )}
      </dialog>
    </div>
  );
}
