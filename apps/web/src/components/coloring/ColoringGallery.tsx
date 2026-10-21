"use client";
/* eslint-disable @next/next/no-img-element -- the books' exported preview pages (static files in /public) */

import { useTranslations } from "next-intl";
import { useState, type ReactNode } from "react";
import { imageSources, smallSrc, type ColoringImage } from "@/lib/coloring";

export type Slide = { key: string; img: ColoringImage | null; caption: string };

/**
 * The book's pages: one large page with its caption, and a strip of small pages to choose another (buttons, so
 * the keyboard reaches them). A slide without an image (the cover before it is exported) shows `placeholder`.
 */
export function ColoringGallery({
  slides,
  placeholder,
  tone,
  className = "",
}: {
  slides: Slide[];
  placeholder: ReactNode;
  tone: string;
  className?: string;
}) {
  const t = useTranslations("coloring");
  const [at, setAt] = useState(0);
  const shown = slides[at] ?? slides[0];
  return (
    <section aria-label={t("gallery")} className={`flex flex-col gap-3 ${className}`}>
      <figure className={`mx-4 flex flex-col items-center gap-3 rounded-[24px] px-6 pt-6 pb-4 md:mx-0 ${tone}`}>
        <div className="w-full max-w-[300px] shadow-[0_12px_28px_rgba(22,32,74,0.22)]">
          {shown?.img ? (
            <img
              {...imageSources(shown.img)}
              sizes="(min-width: 768px) 300px, 70vw"
              alt={shown.caption}
              width={shown.img.w}
              height={shown.img.h}
              decoding="async"
              className="aspect-[1/1.414] w-full rounded-[8px] bg-white object-cover"
            />
          ) : (
            placeholder
          )}
        </div>
        {shown && (
          <figcaption aria-live="polite" className="text-center text-small font-semibold text-night-900">
            {shown.caption}
          </figcaption>
        )}
      </figure>
      {slides.length > 1 && (
        <ul className="flex gap-2.5 overflow-x-auto px-4 pb-1 md:flex-wrap md:overflow-visible md:px-0">
          {slides.map((s, i) => (
            <li key={s.key} className="shrink-0">
              <button
                type="button"
                onClick={() => setAt(i)}
                aria-pressed={i === at}
                aria-label={t("showPage", { caption: s.caption })}
                className={`block w-[64px] overflow-hidden rounded-[8px] border-2 bg-white transition ${i === at ? "border-night-900" : "border-line hover:border-night-500"}`}
              >
                {s.img ? (
                  <img
                    src={smallSrc(s.img.src)}
                    alt=""
                    width={s.img.w}
                    height={s.img.h}
                    loading="lazy"
                    className="aspect-[1/1.414] w-full object-cover"
                  />
                ) : (
                  <span className={`block aspect-[1/1.414] w-full ${tone}`} />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
