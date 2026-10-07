"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { money, type Catalog, type CatalogAddOn } from "@/lib/store";
import { num } from "@/lib/story";

/** A picture for an add-on (the shared media list); the catalog's own `image` wins when the admin set one. */
export type AddonMedia = Record<string, { src: string; alt_ar: string; alt_en: string } | undefined>;

const free = (a: CatalogAddOn) => a.percent === null && a.price !== null && num(a.price) === 0;

/**
 * What a line's price already includes: add-ons marked included for it, and the free ones it offers (the
 * digital copy with a printed book). Only active add-ons reach the catalog API, so nothing here is invented.
 */
export function includedAddons(catalog: Catalog | null, line: string): CatalogAddOn[] {
  return (catalog?.addons ?? []).filter((a) => a.included_lines.includes(line) || (a.lines.includes(line) && free(a)));
}

/** The paid extras a line offers (each with its price or percent), in the catalog's order. */
export function extraAddons(catalog: Catalog | null, line: string): CatalogAddOn[] {
  return (catalog?.addons ?? []).filter(
    (a) =>
      a.lines.includes(line) &&
      !a.included_lines.includes(line) &&
      !free(a) &&
      (a.price !== null || a.percent !== null),
  );
}

/** One row per add-on: its picture, name, a line about it and its price («+20 ₪», «50% من سعر الكتاب»). */
export function AddonList({
  addons,
  catalog,
  media = {},
  tag,
  tone = "light",
  initial,
  wide = true,
}: {
  addons: CatalogAddOn[];
  catalog: Catalog | null;
  media?: AddonMedia;
  tag?: (a: CatalogAddOn) => string | null;
  tone?: "light" | "dark";
  /** Show this many first, the rest behind «عرض الإضافات كلّها». */
  initial?: number;
  /** Two columns from tablet width (false in a narrow column). */
  wide?: boolean;
}) {
  const t = useTranslations("storyShowcase.extras");
  const locale = useLocale();
  const ar = locale === "ar";
  const currency = catalog?.currency ?? "ILS";
  const [all, setAll] = useState(false);
  if (!addons.length) return null;
  const folded = !all && initial !== undefined && addons.length > initial + 1;
  const shown = folded ? addons.slice(0, initial) : addons;
  return (
    <div className="flex flex-col gap-2.5">
      <ul className={`grid gap-2.5 ${wide ? "sm:grid-cols-2" : ""}`}>
        {shown.map((a) => {
          const picture = a.image
            ? { src: a.image, alt: "" }
            : media[a.slug]
              ? { src: media[a.slug]!.src, alt: "" }
              : null;
          const price =
            a.percent !== null
              ? t("percent", { percent: num(a.percent) })
              : a.price !== null && num(a.price) > 0
                ? t("plus", { price: money(a.price, currency, locale) })
                : t("free");
          const note = tag?.(a);
          const description = ar ? a.description_ar : a.description_en;
          return (
            <li
              key={a.slug}
              className={`flex items-center gap-3 rounded-[16px] p-2.5 ${tone === "dark" ? "bg-night-800 text-paper" : "border border-line bg-paper-raised text-ink"}`}
            >
              <span className="flex size-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-paper-sunk">
                {picture ? (
                  // eslint-disable-next-line @next/next/no-img-element -- small static or admin-provided picture
                  <img
                    src={picture.src}
                    alt={picture.alt}
                    width={64}
                    height={64}
                    loading="lazy"
                    className="size-full object-cover"
                  />
                ) : (
                  <svg
                    className="size-7 text-amber-700"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M12 3l2.6 5.6 6.1.7-4.5 4.2 1.2 6L12 16.6 6.6 19.5l1.2-6L3.3 9.3l6.1-.7z" />
                  </svg>
                )}
              </span>
              <span className="flex min-w-0 grow flex-col gap-0.5">
                <strong className="text-[15px] leading-snug">{ar ? a.name_ar : a.name_en}</strong>
                {description && (
                  <span
                    className={`line-clamp-2 text-caption ${tone === "dark" ? "text-night-100" : "text-ink-muted"}`}
                  >
                    {description}
                  </span>
                )}
                {note && (
                  <span
                    className={`text-caption font-semibold ${tone === "dark" ? "text-amber-300" : "text-amber-700"}`}
                  >
                    {note}
                  </span>
                )}
              </span>
              <strong className="shrink-0 text-[15px] whitespace-nowrap">
                <bdi dir={a.percent === null ? "ltr" : undefined}>{price}</bdi>
              </strong>
            </li>
          );
        })}
      </ul>
      {folded && (
        <button
          type="button"
          onClick={() => setAll(true)}
          className="min-h-11 self-start rounded-full border-[1.5px] border-line bg-paper-raised px-4 text-small font-semibold text-night-900 hover:border-night-500"
        >
          {t("showAll", { count: addons.length })}
        </button>
      )}
    </div>
  );
}
