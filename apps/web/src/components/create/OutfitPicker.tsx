"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { nameCases } from "@/lib/arabicName";
import { createApi } from "@/lib/create";
import { outfitSrc, type Outfit, type Outfits } from "@/lib/outfits";

let cached: Promise<Outfits | null> | null = null;

/** The outfit catalogue (`GET /api/create/outfits`), fetched once per page load. */
export function useOutfits(): Outfits | null {
  const [catalog, setCatalog] = useState<Outfits | null>(null);
  useEffect(() => {
    let alive = true;
    cached ??= createApi.outfits().then((r) => (r.ok ? r.data : null));
    void cached.then((c) => {
      if (!c) cached = null; // try again next time
      if (alive) setCatalog(c);
    });
    return () => {
      alive = false;
    };
  }, []);
  return catalog;
}

/**
 * «ماذا يلبس {name}؟» (owner, 2026-10-20): a grid of drawn swatches, one per outfit offered to this child on this
 * line (lib/outfits), as a radio group (arrow keys move the choice; each swatch is a 44 px+ target). A girl with a
 * hijab sees each swatch with the hijab colour that goes with it.
 */
export function OutfitPicker({
  child,
  outfits,
  value,
  onChange,
  id = "outfit",
}: {
  child: { name: string; gender: "f" | "m"; hijab: boolean };
  outfits: Outfit[];
  value: string;
  onChange: (id: string) => void;
  id?: string;
}) {
  const t = useTranslations("create");
  const locale = useLocale();
  const who = { ...nameCases(child.name), gender: child.gender };
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  function onKey(e: KeyboardEvent<HTMLDivElement>) {
    const at = outfits.findIndex((o) => o.id === value);
    const rtl = locale === "ar";
    const step =
      e.key === "ArrowDown" || e.key === (rtl ? "ArrowLeft" : "ArrowRight")
        ? 1
        : e.key === "ArrowUp" || e.key === (rtl ? "ArrowRight" : "ArrowLeft")
          ? -1
          : 0;
    if (!step || at < 0) return;
    e.preventDefault();
    const next = (at + step + outfits.length) % outfits.length;
    onChange(outfits[next].id);
    refs.current[next]?.focus();
  }

  return (
    <section aria-labelledby={`${id}-title`} className="flex flex-col gap-2">
      <h2 id={`${id}-title`} className="text-[20px] text-night-900">
        {t("outfit.title", who)}
      </h2>
      <p id={`${id}-hint`} className="text-small text-ink-muted">
        {t("outfit.hint", who)}
      </p>
      <div
        role="radiogroup"
        aria-labelledby={`${id}-title`}
        aria-describedby={`${id}-hint`}
        onKeyDown={onKey}
        className="grid grid-cols-3 gap-2.5"
      >
        {outfits.map((o, i) => {
          const on = o.id === value;
          return (
            <button
              key={o.id}
              ref={(el) => {
                refs.current[i] = el;
              }}
              type="button"
              role="radio"
              aria-checked={on}
              tabIndex={on ? 0 : -1}
              onClick={() => onChange(o.id)}
              className={`flex min-h-11 flex-col items-center gap-1 rounded-2xl bg-paper-raised p-1.5 text-center transition focus-visible:ring-4 focus-visible:ring-night-100 focus-visible:outline-none ${on ? "border-[3px] border-amber-500 shadow-[0_8px_24px_rgba(242,179,61,0.25)]" : "border-[1.5px] border-line"}`}
            >
              <span className="flex h-[104px] w-full items-center justify-center rounded-xl bg-paper-sunk">
                {/* eslint-disable-next-line @next/next/no-img-element -- a drawn SVG swatch (data URI), no AI image */}
                <img src={outfitSrc(o, child.gender, child.hijab)} alt="" className="h-[96px] w-auto" />
              </span>
              <span className="text-caption leading-snug font-semibold text-night-900">
                {locale === "ar" ? o.name_ar : o.name_en}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
