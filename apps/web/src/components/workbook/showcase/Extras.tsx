"use client";

/* eslint-disable @next/next/no-img-element -- small static photos from /public (public/included, public/addons) */
import { useLocale, useTranslations } from "next-intl";
import type { AddonMedia, IncludedItem } from "@/lib/addonsMedia";
import { money, type CatalogAddOn, type Currency } from "@/lib/store";

/** The cart offers add-ons of its own step (components/store/CartView); a free digital copy is added by itself. */
const CART_STEPS = new Set(["checkout"]);
const AUTOMATIC = new Set(["digital-copy"]);

/** The add-ons the cart will offer for this line and variant: active ones from the catalog, never a fixed list. */
export function extrasFor(addons: CatalogAddOn[], line: string, options: Record<string, string>): CatalogAddOn[] {
  return addons.filter(
    (a) =>
      CART_STEPS.has(a.step) &&
      !AUTOMATIC.has(a.slug) &&
      a.lines.includes(line) &&
      !a.included_lines.includes(line) &&
      (a.price !== null || a.percent !== null) &&
      Object.entries(a.requires).every(([option, allowed]) => allowed.includes(options[option] ?? "")),
  );
}

/**
 * What comes with the book, with photos (stickers, card sheets, the certificate…), and the optional extras the
 * cart offers for the chosen variant, each with its photo and price (owner's request, 2026-10-07).
 */
export function Extras({
  included,
  addons,
  media,
  line,
  options,
  pdf,
  currency,
  className = "",
}: {
  included: readonly IncludedItem[]; // lib/addonsMedia `includedItems[productSlug]`
  addons: CatalogAddOn[];
  media: Readonly<Record<string, AddonMedia | undefined>>; // lib/addonsMedia `addonMedia`
  line: string;
  options: Record<string, string>;
  pdf: boolean;
  currency: Currency;
  className?: string;
}) {
  const t = useTranslations("workbookShowcase");
  const locale = useLocale();
  const ar = locale === "ar";
  const extras = extrasFor(addons, line, options);
  if (!included.length && !extras.length) return null;
  const price = (a: CatalogAddOn) =>
    a.percent !== null
      ? t("percentOf", { n: Number(a.percent) })
      : Number(a.price) === 0
        ? t("free")
        : t("plus", { price: money(a.price!, currency, locale) });
  return (
    <div className={`flex flex-col gap-5 px-4 md:px-0 ${className}`}>
      {included.length > 0 && (
        <section aria-labelledby="comes-with" className="flex flex-col gap-3">
          <div className="flex flex-col gap-0.5">
            <h2 id="comes-with" className="text-[20px] text-night-900">
              {t("includedTitle")}
            </h2>
            {pdf && <p className="text-caption leading-[1.6] text-ink-muted">{t("includedPdf")}</p>}
          </div>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3">
            {included.map((item) => (
              <li
                key={item.src}
                className="flex flex-col overflow-hidden rounded-[16px] border border-line bg-paper-raised"
              >
                <img
                  src={item.src}
                  alt={ar ? item.title_ar : item.title_en}
                  width={480}
                  height={360}
                  loading="lazy"
                  decoding="async"
                  className="aspect-[4/3] w-full bg-paper-sunk object-cover"
                />
                <div className="flex flex-col gap-0.5 p-2.5">
                  <strong className="text-[14px] leading-snug text-night-900">
                    {ar ? item.title_ar : item.title_en}
                  </strong>
                  <span className="text-caption leading-[1.5] text-ink-muted">{ar ? item.desc_ar : item.desc_en}</span>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      {extras.length > 0 && (
        <section aria-labelledby="extras" className="flex flex-col gap-3">
          <div className="flex flex-col gap-0.5">
            <h2 id="extras" className="text-[20px] text-night-900">
              {t("extrasTitle")}
            </h2>
            <p className="text-caption leading-[1.6] text-ink-muted">{t("extrasLead")}</p>
          </div>
          <ul className="flex flex-col gap-2.5">
            {extras.map((a) => {
              const photo = media[a.slug];
              const description = ar ? a.description_ar : a.description_en;
              return (
                <li
                  key={a.slug}
                  className="flex items-center gap-3 rounded-[16px] border border-line bg-paper-raised p-2.5"
                >
                  {photo ? (
                    <img
                      src={photo.src}
                      alt={ar ? photo.alt_ar : photo.alt_en}
                      width={160}
                      height={160}
                      loading="lazy"
                      decoding="async"
                      className="size-[72px] shrink-0 rounded-[12px] bg-paper-sunk object-cover"
                    />
                  ) : (
                    <span
                      aria-hidden="true"
                      className="flex size-[72px] shrink-0 items-center justify-center rounded-[12px] bg-amber-100 font-display text-[28px] text-amber-700"
                    >
                      +
                    </span>
                  )}
                  <div className="flex min-w-0 grow flex-col gap-0.5">
                    <strong className="text-[15px] leading-snug text-night-900">{ar ? a.name_ar : a.name_en}</strong>
                    {description && <span className="text-caption leading-[1.5] text-ink-muted">{description}</span>}
                  </div>
                  <span className="shrink-0 rounded-full bg-success-bg px-2.5 py-1 text-caption font-bold text-success">
                    {price(a)}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
