"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { containedSample, sampleAlt, type StyleSample } from "@/lib/styleSamples";
import { SampleLightbox } from "./SampleLightbox";

/**
 * A swipeable row of sample pages (scroll snap, right-to-left in Arabic); a tap opens the page large.
 * `caption` labels a page under its picture (e.g. «من حكاية …» when it comes from another story).
 */
export function StyleGallery({
  samples,
  caption,
  label,
  size = "md",
}: {
  samples: StyleSample[];
  caption?: (s: StyleSample) => string | null;
  label: string;
  size?: "sm" | "md";
}) {
  const t = useTranslations("storyShowcase.gallery");
  const locale = useLocale();
  const rtl = locale === "ar";
  const row = useRef<HTMLUListElement>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [edges, setEdges] = useState({ start: true, end: false });

  // a new style starts at its first page
  const key = samples.map((s) => s.id).join("|");
  useEffect(() => {
    row.current?.scrollTo({ left: 0 });
  }, [key]);

  useEffect(() => {
    const el = row.current;
    if (!el) return;
    const update = () => {
      const x = Math.abs(el.scrollLeft);
      setEdges({ start: x < 8, end: x + el.clientWidth >= el.scrollWidth - 8 });
    };
    update();
    el.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      el.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [key]);

  const page = (dir: 1 | -1) => {
    const el = row.current;
    if (!el) return;
    el.scrollBy({ left: dir * (rtl ? -1 : 1) * el.clientWidth * 0.85, behavior: "smooth" });
  };

  const width = size === "sm" ? "w-[44%] sm:w-[30%] lg:w-[23%]" : "w-[72%] sm:w-[44%] lg:w-[31%]";
  const arrowBtn =
    "absolute top-[38%] z-10 hidden size-11 -translate-y-1/2 items-center justify-center rounded-full bg-paper-raised/95 text-night-900 shadow-2 transition hover:bg-paper md:flex disabled:opacity-0";

  return (
    <div className="relative">
      <ul
        ref={row}
        aria-label={label}
        className="-mx-4 flex snap-x snap-mandatory scroll-px-4 [scrollbar-width:none] gap-3 overflow-x-auto px-4 pb-2 md:mx-0 md:scroll-px-0 md:px-0 [&::-webkit-scrollbar]:hidden"
      >
        {samples.map((s, i) => {
          const note = caption?.(s);
          return (
            <li key={s.id} className={`${width} shrink-0 snap-start`}>
              <button
                type="button"
                onClick={() => setOpen(i)}
                aria-label={t("zoom", { page: sampleAlt(s, locale) })}
                className="group block w-full cursor-zoom-in text-start"
              >
                <span className="relative block aspect-square overflow-hidden rounded-[18px] border border-line bg-paper-sunk shadow-1 transition group-hover:shadow-2">
                  {/* eslint-disable-next-line @next/next/no-img-element -- static sample pages in two sizes */}
                  <img
                    src={s.thumb}
                    srcSet={`${s.thumb} 480w, ${s.src} 900w`}
                    sizes={size === "sm" ? "(min-width: 1024px) 220px, 44vw" : "(min-width: 1024px) 340px, 72vw"}
                    width={s.width}
                    height={s.height}
                    alt=""
                    loading={i < 2 ? "eager" : "lazy"}
                    decoding="async"
                    draggable={false}
                    className={`size-full ${containedSample(s) ? "object-contain p-2" : "object-cover"} transition duration-300 group-hover:scale-[1.02]`}
                  />
                  {s.kind === "cover" && (
                    <span className="absolute start-2 top-2 rounded-full bg-night-950/75 px-2 py-0.5 text-[11px] font-semibold text-paper">
                      {t("cover")}
                    </span>
                  )}
                </span>
                {note && (
                  <span className="mt-1.5 line-clamp-2 block px-1 text-caption leading-[1.5] text-ink-muted">
                    {note}
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      {samples.length > 2 && (
        <>
          <button
            type="button"
            onClick={() => page(-1)}
            disabled={edges.start}
            aria-label={t("prev")}
            className={`${arrowBtn} -start-4`}
          >
            <Chevron back />
          </button>
          <button
            type="button"
            onClick={() => page(1)}
            disabled={edges.end}
            aria-label={t("next")}
            className={`${arrowBtn} -end-4`}
          >
            <Chevron />
          </button>
        </>
      )}
      <SampleLightbox samples={samples} index={open} onIndex={setOpen} caption={caption} />
    </div>
  );
}

/** ‹ / ›, pointing where the row moves in the page's direction. */
function Chevron({ back = false }: { back?: boolean }) {
  return (
    <svg
      className={`size-[22px] ${back ? "rtl:-scale-x-100" : "ltr:-scale-x-100"}`}
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
}
