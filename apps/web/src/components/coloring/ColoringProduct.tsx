"use client";

import { useLocale, useTranslations } from "next-intl";
import { useState } from "react";
import { useShowPrices } from "@/components/site/Prices";
import { Arrow } from "@/components/site/blocks";
import { ArrowForward } from "@/components/ui/Button";
import { AddWorkbook } from "@/components/workbook/AddWorkbook";
import { Link } from "@/i18n/navigation";
import { coloringFacts, coloringPreviews, optionGroups, pickVariant, sellsPdf, startVariant } from "@/lib/coloring";
import { money, type CatalogProduct, type Currency } from "@/lib/store";
import { ColoringCover, COLORING_TONE } from "./ColoringCover";
import { ColoringGallery, type Slide } from "./ColoringGallery";

const chip = (on: boolean) =>
  `min-h-12 rounded-full px-4 text-[15px] font-semibold transition ${
    on
      ? "border-2 border-night-900 bg-night-900 text-paper"
      : "border-[1.5px] border-line bg-paper-raised text-night-900 hover:border-night-500"
  }`;

/**
 * A coloring or drawing book's page (/coloring/[product]): its pages (the cover and a few inside pages, or the
 * drawn stand-in while none are exported), the facts, the format (printed, or a PDF to print at home), and the
 * same order path as the activity books: «أضيفوا للسلة» puts the chosen variant in the cart in one tap, and a
 * signed-in parent can open the order flow for it straight away (`/create?product=<sku>`).
 */
export function ColoringProduct({
  product,
  currency = "ILS",
  query,
  signedIn = false,
  others = [],
}: {
  product: CatalogProduct;
  /** None while prices are hidden (the API sends no currency): nothing is priced then. */
  currency?: Currency;
  query: Record<string, string>;
  signedIn?: boolean;
  others?: { slug: string; href: string; name: string }[]; // the line's other books
}) {
  const t = useTranslations("coloring");
  const locale = useLocale();
  const prices = useShowPrices(); // hidden from customers (`show_prices` off): no price at all
  const [variant, setVariant] = useState(() => startVariant(product, query));
  const facts = coloringFacts(product);
  const { cover, pages } = coloringPreviews(product.slug);
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const pagesLabel = t("pagesCount", { pages: facts.pages });
  const tone = COLORING_TONE[facts.title];
  const picks = variant?.options ?? {};
  const pdf = picks.format === "digital";
  const groups = optionGroups(product);
  const label = (group: string, value: string) =>
    group === "format" && t.has(`formats.${value}`) ? t(`formats.${value}`) : value;
  const note = pdf ? t("note.pdf") : sellsPdf(product) ? t("note.printed") : t("note.printedOnly");
  const inside = t.has(`insideList.${facts.title}`) ? (t.raw(`insideList.${facts.title}`) as string[]) : [];
  const price = variant?.price ?? null;
  const caption = (p: { caption_ar: string; caption_en: string }) => (locale === "ar" ? p.caption_ar : p.caption_en);
  const slides: Slide[] = [
    { key: "cover", img: cover, caption: t("galleryCover") },
    ...pages.map((p) => ({ key: p.src, img: p, caption: caption(p) })),
  ];
  const details = [
    { key: "pages", value: pagesLabel },
    { key: "size", value: t("value.size", { size: facts.size }) },
    { key: "binding", value: t(`value.binding.${facts.binding}`) },
    { key: "paper", value: t("value.paper") },
    { key: "interior", value: facts.title === "sketchbook" ? t("value.interiorSketch") : t("value.interior") },
    { key: "cover", value: t("value.cover") },
    { key: "ages", value: t("ages") },
  ];
  const row = "px-4 md:px-0";

  return (
    <>
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5 pt-2 pb-36 md:grid md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] md:gap-10 md:px-10 md:pt-10">
        <div className="contents md:sticky md:top-28 md:flex md:flex-col md:gap-5 md:self-start">
          <div className="order-1 -mb-2 flex h-[52px] items-center px-2 md:hidden">
            <Link
              href="/coloring"
              aria-label={t("back")}
              className="flex size-11 items-center justify-center text-night-900"
            >
              <svg
                className="size-[22px] ltr:-scale-x-100"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M5 12h14" />
                <path d="M13 6l6 6-6 6" />
              </svg>
            </Link>
          </div>
          <ColoringGallery
            className="order-2"
            tone={tone}
            slides={slides}
            placeholder={
              <ColoringCover
                cover={null}
                title={facts.title}
                name={name}
                pagesLabel={pagesLabel}
                binding={facts.binding}
                alt={t("coverAlt", { name })}
                nameSlot={t("nameSlot")}
                size="lg"
              />
            }
          />
        </div>

        <div className="contents md:flex md:flex-col md:gap-[22px]">
          <div className={`order-3 flex flex-col gap-2 ${row}`}>
            <div className="flex flex-wrap gap-2 text-caption font-semibold">
              <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">{t("ages")}</span>
              <span className="rounded-full bg-paper-sunk px-2.5 py-1">{pagesLabel}</span>
              <span dir="ltr" className="rounded-full bg-success-bg px-2.5 py-1 text-success">
                {facts.size}
              </span>
            </div>
            <h1 className="text-[32px] leading-tight text-night-900 md:text-[40px]">{name}</h1>
            <p className="text-body leading-[1.75] text-ink-muted">
              {t.has(`desc.${facts.title}`)
                ? t(`desc.${facts.title}`)
                : locale === "ar"
                  ? product.description_ar
                  : product.description_en}
            </p>
          </div>

          <section className={`order-4 flex flex-col gap-3.5 ${row}`}>
            {groups.map((g) => (
              <div key={g.name} className="flex flex-col gap-2">
                <h2 id={`group-${g.name}`} className="text-[17px] text-night-900">
                  {g.name === "format" ? t("format") : g.name}
                </h2>
                <div role="radiogroup" aria-labelledby={`group-${g.name}`} className="flex flex-wrap gap-2">
                  {g.values.map((value) => (
                    <button
                      key={value}
                      type="button"
                      role="radio"
                      aria-checked={picks[g.name] === value}
                      onClick={() => setVariant(pickVariant(product, picks, g.name, value) ?? variant)}
                      className={chip(picks[g.name] === value)}
                    >
                      {label(g.name, value)}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <p className="text-caption leading-[1.6] text-ink-muted">{note}</p>
            {signedIn && variant && (
              <Link
                href={`/create?product=${encodeURIComponent(variant.sku)}`}
                className="flex min-h-11 items-center gap-1.5 self-start font-display text-body font-bold text-night-900 underline underline-offset-4"
              >
                {t("start")} <ArrowForward />
              </Link>
            )}
          </section>

          <section aria-labelledby="facts-title" className={`order-6 flex flex-col gap-2 ${row}`}>
            <h2 id="facts-title" className="text-[20px] text-night-900">
              {t("factsTitle")}
            </h2>
            <dl className="grid grid-cols-2 gap-2">
              {details.map((f) => (
                <div key={f.key} className="flex flex-col gap-0.5 rounded-[14px] bg-paper-sunk px-3 py-2.5">
                  <dt className="text-caption text-ink-muted">{t(`fact.${f.key}`)}</dt>
                  <dd className="text-[15px] leading-snug font-semibold text-night-900">{f.value}</dd>
                </div>
              ))}
            </dl>
          </section>

          {inside.length > 0 && (
            <section aria-labelledby="inside-title" className={`order-7 flex flex-col gap-2 ${row}`}>
              <h2 id="inside-title" className="text-[20px] text-night-900">
                {t("insideTitle")}
              </h2>
              <ul className="flex flex-col gap-1.5 text-[15px]">
                {inside.map((item) => (
                  <li key={item} className="flex items-start gap-2">
                    <span aria-hidden="true" className="mt-0.5 font-extrabold text-success">
                      ✓
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className={`order-8 flex flex-col gap-[22px] ${row}`}>
            <div className="flex flex-col gap-1 rounded-[20px] bg-amber-100 p-4">
              <strong className="text-body text-night-900">{t("personalTitle")}</strong>
              <span className="text-small leading-[1.7] text-ink">{t("personalBody")}</span>
            </div>

            <Link href="/quiz" className="flex min-h-11 items-center gap-3 rounded-[16px] bg-paper-sunk p-3.5">
              <svg
                className="size-[22px] shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#9A620A"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="9" />
                <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.5V14" />
                <path d="M12 17.2v.1" />
              </svg>
              <span className="text-small font-semibold">{t("quiz")}</span>
            </Link>

            {others.length > 0 && (
              <nav aria-labelledby="more-title" className="flex flex-col gap-2">
                <h2 id="more-title" className="text-[17px] text-night-900">
                  {t("more")}
                </h2>
                <ul className="flex flex-col">
                  {others.map((o) => (
                    <li key={o.slug}>
                      <Link
                        href={o.href}
                        className="flex min-h-11 items-center justify-between gap-2 border-t border-line font-semibold text-night-900 hover:text-amber-700"
                      >
                        {o.name} <Arrow />
                      </Link>
                    </li>
                  ))}
                </ul>
              </nav>
            )}
            <Link
              href="/coloring#faq"
              className="flex min-h-11 items-center self-start text-small font-semibold text-amber-700 underline"
            >
              {t("faqMore")}
            </Link>
          </div>
        </div>
      </div>

      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-paper/97 pt-3 pb-[max(16px,env(safe-area-inset-bottom))] backdrop-blur">
        <div className="mx-auto flex max-w-[1100px] items-center gap-3 px-4 md:px-10">
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-xs text-ink-muted">
              {name}
              {variant?.options.format ? ` · ${label("format", variant.options.format)}` : ""}
            </span>
            {prices && (
              <strong className="text-[19px]" aria-live="polite">
                {price === null ? "—" : money(price, currency, locale)}
              </strong>
            )}
          </div>
          <AddWorkbook sku={variant?.sku ?? null} />
        </div>
      </div>
    </>
  );
}
