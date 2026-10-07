/* eslint-disable @next/next/no-img-element -- static preview pages from /public (exported once by a script) */
import { getLocale, getTranslations } from "next-intl/server";
import { Link } from "@/i18n/navigation";
import { productFrom } from "@/lib/shop";
import { money, type CatalogProduct, type Currency } from "@/lib/store";
import { PREVIEWS, samplePages, soldAges, soldOptions } from "@/lib/workbook";
import { Arrow } from "./blocks";

/**
 * One activity book as a card: its real cover, age, pages, what it contains, the price it starts from, and a
 * button to its page. `detailed` (the hub) adds the list of what's inside and a strip of real pages. Everything
 * the card says about volumes and stages comes from what the catalog sells today, never from a fixed list.
 */
export async function ActivityBookCard({
  product,
  currency,
  detailed = false,
}: {
  product: CatalogProduct;
  currency: Currency;
  detailed?: boolean;
}) {
  const [t, tw, locale] = await Promise.all([
    getTranslations("workbooksHub"),
    getTranslations("workbook"),
    getLocale(),
  ]);
  const line = product.line;
  const name = locale === "ar" ? product.name_ar : product.name_en;
  const pages = PREVIEWS[product.slug] ?? [];
  const cover = pages[0];
  const inner = detailed ? samplePages(product) : [];
  const from = productFrom(product);
  const sold = soldOptions(product);
  const ages = soldAges(product);
  const comma = locale === "ar" ? "، " : ", ";
  const level = (sold.level ?? []).map((l) => (tw.has(`values.level.${l}`) ? tw(`values.level.${l}`) : l));
  const unit = (group: "volume" | "stage") => {
    const values = (sold[group] ?? []).filter((v) => v !== "set");
    return values.length ? t(values.length > 1 ? `${group}s` : group, { list: values.join(comma) }) : null;
  };
  const edition = [level.map((l) => l.split(" ·")[0]).join(comma), unit("volume"), unit("stage")]
    .filter(Boolean)
    .join(" · ");
  // a line without its list (a product just switched on) shows no list rather than breaking the page
  const inside = detailed && t.has(`insideList.${line}`) ? (t.raw(`insideList.${line}`) as string[]) : [];
  const chip = "rounded-full px-2.5 py-1";
  return (
    <article className="flex h-full flex-col overflow-hidden rounded-[20px] border border-line bg-paper-raised">
      <Link
        href={`/workbooks/${product.slug}`}
        className="flex items-end justify-center bg-paper-sunk px-4 pt-4 md:px-6 md:pt-6"
      >
        {cover ? (
          <img
            src={cover.src}
            alt={t("coverAlt", { name })}
            width={720}
            height={1018}
            loading="lazy"
            className="aspect-[1/1.3] w-full max-w-[150px] rounded-t-[8px] object-cover object-top shadow-[0_-8px_24px_rgba(22,32,74,0.15)] md:max-w-[220px]"
          />
        ) : (
          <div className="aspect-[1/1.3] w-full max-w-[150px] rounded-t-[8px] bg-night-100 md:max-w-[220px]" />
        )}
      </Link>
      <div className="flex grow flex-col gap-3 p-4 md:p-5">
        <div className="flex flex-wrap gap-2 text-caption font-semibold">
          {(ages || tw.has(`ages.${line}`)) && (
            <span className={`${chip} bg-night-100 text-night-900`}>
              {ages ? tw("ageRange", { min: ages[0], max: ages[1] }) : tw(`ages.${line}`)}
            </span>
          )}
          {tw.has(`pages.${line}`) && <span className={`${chip} bg-paper-sunk`}>{tw(`pages.${line}`)}</span>}
          {edition && <span className={`${chip} bg-success-bg text-success`}>{edition}</span>}
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
          {tw.has(`desc.${line}`)
            ? tw(`desc.${line}`)
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
        {detailed && inner.length > 0 && (
          <div className="flex gap-2" aria-label={t("peek")}>
            {inner.map((p) => (
              <img
                key={p.src}
                src={p.src}
                alt={locale === "ar" ? p.title_ar : p.title_en}
                width={720}
                height={1018}
                loading="lazy"
                className="aspect-[1/1.414] w-1/3 rounded-[8px] border border-line object-cover"
              />
            ))}
          </div>
        )}
        <Link
          href={`/workbooks/${product.slug}`}
          className="mt-auto flex min-h-12 items-center justify-center gap-1.5 rounded-full bg-amber-500 px-6 font-bold text-night-950 transition hover:-translate-y-0.5"
        >
          {t("order")} <Arrow />
        </Link>
      </div>
    </article>
  );
}
