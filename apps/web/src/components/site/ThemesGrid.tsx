"use client";

import { useMemo, useState } from "react";
import type { ThemeCard } from "@/lib/catalog";
import { ThemeCardView } from "./ThemeCardView";

const AGE_BANDS: [number, number][] = [
  [2, 3],
  [4, 6],
  [7, 9],
];

type Labels = {
  age: string;
  all: string;
  occasion: string;
  sort: string;
  sortPopular: string;
  sortAge: string;
  empty: string;
  reset: string;
};

/** Catalog filters (design: themes — catalog): age chips, occasion chips, sort. */
export function ThemesGrid({
  themes,
  price,
  labels,
  occasionLabels,
}: {
  themes: ThemeCard[];
  price: string | null;
  labels: Labels;
  occasionLabels: Record<string, string>;
}) {
  const [band, setBand] = useState<number | null>(null);
  const [occasion, setOccasion] = useState<string | null>(null);
  const [sort, setSort] = useState<"popular" | "age">("popular");
  const occasions = useMemo(() => {
    const seen = new Set(themes.flatMap((t) => t.occasions));
    return Object.keys(occasionLabels).filter((o) => seen.has(o));
  }, [themes, occasionLabels]);

  const shown = themes
    .filter((t) => {
      if (band !== null) {
        const [lo, hi] = AGE_BANDS[band]!;
        if (t.age_max < lo || t.age_min > hi) return false;
      }
      return occasion === null || t.occasions.includes(occasion);
    })
    .sort(
      (a, b) =>
        (sort === "age" ? a.age_min - b.age_min : 0) || (a.status === b.status ? 0 : a.status === "available" ? -1 : 1),
    );

  const chip = (on: boolean) =>
    `min-h-11 rounded-full border-[1.5px] px-4 text-[15px] transition ${on ? "border-night-900 bg-night-900 font-semibold text-paper" : "border-line bg-paper-raised text-ink hover:border-night-500"}`;

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pb-8">
        <div role="group" aria-label={labels.age} className="flex flex-wrap items-center gap-2">
          <span className="text-small font-semibold text-ink-muted">{labels.age}</span>
          <button
            type="button"
            aria-pressed={band === null}
            onClick={() => setBand(null)}
            className={chip(band === null)}
          >
            {labels.all}
          </button>
          {AGE_BANDS.map(([lo, hi], i) => (
            <button
              key={lo}
              type="button"
              aria-pressed={band === i}
              onClick={() => setBand(band === i ? null : i)}
              className={chip(band === i)}
            >
              {lo}–{hi}
            </button>
          ))}
        </div>
        <div className="hidden h-8 w-px bg-line md:block" />
        <div role="group" aria-label={labels.occasion} className="flex flex-wrap items-center gap-2">
          {occasions.map((o) => (
            <button
              key={o}
              type="button"
              aria-pressed={occasion === o}
              onClick={() => setOccasion(occasion === o ? null : o)}
              className={chip(occasion === o)}
            >
              {occasionLabels[o]}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-small text-ink-muted md:ms-auto">
          {labels.sort}
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as "popular" | "age")}
            className="min-h-11 rounded-sm border-[1.5px] border-line bg-paper-raised px-3 text-[15px] text-ink"
          >
            <option value="popular">{labels.sortPopular}</option>
            <option value="age">{labels.sortAge}</option>
          </select>
        </label>
      </div>
      {shown.length ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 lg:gap-7">
          {shown.map((t) => (
            <ThemeCardView key={t.slug} theme={t} variant="catalog" price={price} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-line py-16 text-center">
          <p className="text-body-l text-ink-muted">{labels.empty}</p>
          <button
            type="button"
            onClick={() => {
              setBand(null);
              setOccasion(null);
            }}
            className="font-bold text-amber-700 underline underline-offset-4"
          >
            {labels.reset}
          </button>
        </div>
      )}
    </>
  );
}
