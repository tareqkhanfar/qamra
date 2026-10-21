/* eslint-disable @next/next/no-img-element -- the books' exported preview pages (static files in /public) */
import { getLocale, getTranslations } from "next-intl/server";
import { Arrow } from "@/components/site/blocks";
import { Link } from "@/i18n/navigation";
import { coloringFacts, coloringPreviews, imageSources } from "@/lib/coloring";
import { productFrom, productPath } from "@/lib/shop";
import { money, type CatalogProduct, type Currency } from "@/lib/store";
import { ColoringCover } from "./ColoringCover";

/**
 * One coloring or drawing book as a card: its cover (or the drawn stand-in), ages, pages, binding and black and
 * white inside, the price it starts from while prices are shown, and a button to its page. `detailed` (the hub)
 * adds what's inside and a strip of real pages when they are exported.
 */
export async function ColoringBookCard({
  product,
  currency,
  detailed = false,
}: {
  product: CatalogProduct;
  currency: Currency;
  detailed?: boolean;
}) {
  const [t, locale] = await Promise.all([getTranslations("coloring"), getLocale()]);
  const facts = coloringFacts(product);
  const { cover, pages } = coloringPreviews(product.slug);
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const href = productPath(product);
  const from = productFrom(product); // null while prices are hidden (the API sends none)
  const pagesLabel = t("pagesCount", { pages: facts.pages });
  const inside = detailed && t.has(`insideList.${facts.title}`) ? (t.raw(`insideList.${facts.title}`) as string[]) : [];
  const peek = detailed ? pages.slice(0, 3) : [];
  const chip = "rounded-full px-2.5 py-1";
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[20px] border border-line bg-paper-raised">
      <Link
        href={href}
        tabIndex={-1}
        aria-hidden="true"
        className="flex items-end justify-center bg-paper-sunk px-4 pt-4 md:px-6 md:pt-6"
      >
        <ColoringCover
          cover={cover}
          title={facts.title}
          name={name}
          pagesLabel={pagesLabel}
          binding={facts.binding}
          alt={t("coverAlt", { name })}
          className="max-w-[150px] shadow-[0_-8px_24px_rgba(22,32,74,0.15)] md:max-w-[200px]"
        />
      </Link>
      <div className="flex grow flex-col gap-3 p-4 md:p-5">
        <div className="flex flex-wrap gap-2 text-caption font-semibold">
          <span className={`${chip} bg-night-100 text-night-900`}>{t("ages")}</span>
          <span className={`${chip} bg-paper-sunk`}>{pagesLabel}</span>
          <span className={`${chip} bg-success-bg text-success`}>
            {t(`bindingShort.${facts.binding}`)} · {t("bw")}
          </span>
        </div>
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-[22px] leading-tight text-night-900 md:text-[24px]">{name}</h3>
          {from !== null && (
            <strong className="shrink-0 pt-0.5 font-display text-[19px] leading-tight text-night-900 md:text-[20px]">
              {t("from", { price: money(from, currency, locale) })}
            </strong>
          )}
        </div>
        <p className="text-[15px] leading-[1.7] text-ink-muted">
          {t.has(`desc.${facts.title}`)
            ? t(`desc.${facts.title}`)
            : locale === "ar"
              ? product.description_ar
              : product.description_en}
        </p>
        {inside.length > 0 && (
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
        )}
        {peek.length > 0 && (
          <div role="group" className="flex gap-2" aria-label={t("peek")}>
            {peek.map((p) => (
              <img
                key={p.src}
                {...imageSources(p)}
                sizes="(min-width: 768px) 120px, 30vw"
                alt={locale === "ar" ? p.caption_ar : p.caption_en}
                width={p.w}
                height={p.h}
                loading="lazy"
                className="aspect-[1/1.414] w-1/3 rounded-[8px] border border-line object-cover"
              />
            ))}
          </div>
        )}
        <Link
          href={href}
          className="mt-auto flex min-h-12 items-center justify-center gap-1.5 rounded-full bg-amber-500 px-6 font-bold text-night-950 transition hover:-translate-y-0.5"
        >
          {t("order")} <span className="sr-only">{name}</span> <Arrow />
        </Link>
      </div>
    </article>
  );
}
