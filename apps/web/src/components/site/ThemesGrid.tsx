"use client";

import { useMemo, useState } from "react";
import type { ThemeCard } from "@/lib/catalog";
import type { Example } from "@/lib/examples";
import type { Currency } from "@/lib/store";
import { StoryCard } from "./StoryCard";

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
  soonTitle: string;
  soonLead: string;
};

/** The stories: filters (age, occasion, sort) over the ones on sale; stories being written come after. */
export function ThemesGrid({
  themes,
  covers,
  prices,
  currency,
  line,
  labels,
  occasionLabels,
}: {
  themes: ThemeCard[];
  covers: Record<string, Example | null>;
  prices: Record<string, number | null>;
  currency: Currency;
  line: string | null;
  labels: Labels;
  occasionLabels: Record<string, string>;
}) {
  const [band, setBand] = useState<number | null>(null);
  const [occasion, setOccasion] = useState<string | null>(null);
  const [sort, setSort] = useState<"popular" | "age">("popular");
  const live = themes.filter((t) => t.status === "available");
  const soon = themes.filter((t) => t.status !== "available");
  const occasions = useMemo(() => {
    const seen = new Set(live.flatMap((t) => t.occasions));
    return Object.keys(occasionLabels).filter((o) => seen.has(o));
  }, [live, occasionLabels]);

  const shown = live
    .filter((t) => {
      if (band !== null) {
        const [lo, hi] = AGE_BANDS[band]!;
        if (t.age_max < lo || t.age_min > hi) return false;
      }
      return occasion === null || t.occasions.includes(occasion);
    })
    .sort((a, b) => (sort === "age" ? a.age_min - b.age_min : 0));

  const chip = (on: boolean) =>
    `min-h-11 rounded-full border-[1.5px] px-4 text-[15px] transition ${on ? "border-night-900 bg-night-900 font-semibold text-paper" : "border-line bg-paper-raised text-ink hover:border-night-500"}`;

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3 pb-6">
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
        {occasions.length > 1 && (
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
        )}
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
        <div className="grid grid-cols-2 gap-3 md:gap-5 lg:grid-cols-3 lg:gap-7">
          {shown.map((t, i) => (
            <div key={t.slug} data-reveal style={{ "--d": `${(i % 3) * 90}ms` } as React.CSSProperties}>
              <StoryCard
                theme={t}
                example={covers[t.slug] ?? null}
                from={prices[t.slug] ?? null}
                currency={currency}
                line={line}
                priority={i < 2}
              />
            </div>
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
      {soon.length > 0 && (
        <section
          aria-labelledby="soon-title"
          className="mt-14 flex flex-col gap-4 border-t border-dashed border-line pt-10"
        >
          <div className="flex flex-col gap-1">
            <h2 id="soon-title" className="text-[24px] text-night-900 md:text-[30px]">
              {labels.soonTitle}
            </h2>
            <p className="text-small text-ink-muted">{labels.soonLead}</p>
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 md:gap-5 lg:grid-cols-5">
            {soon.map((t) => (
              <StoryCard key={t.slug} theme={t} example={null} from={null} currency={currency} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
