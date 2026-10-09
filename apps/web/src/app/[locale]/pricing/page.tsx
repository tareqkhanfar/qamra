/* eslint-disable @next/next/no-img-element -- the books' real covers (static files in /public) */
import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { Arrow } from "@/components/site/blocks";
import { Alert } from "@/components/ui/Alert";
import { buttonClasses } from "@/components/ui/Button";
import { Link } from "@/i18n/navigation";
import { getStoreCatalog } from "@/lib/catalog";
import { priceFamilies, type PriceFamily, type PriceRow } from "@/lib/pricing";
import { pageMetadata } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";
import { money } from "@/lib/store";
import { ISLAMIC_SETS, PREVIEWS } from "@/lib/workbook";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("pricingPage"), getLocale()]);
  return pageMetadata({ path: "/pricing", locale, title: t("title"), description: t("lead") });
}

const STORY_LINES = ["classic", "magic", "coloring"];
const LINES = [...STORY_LINES, ...ACTIVITY_LINES];
/** The stories' covers: a real «قمرة كلاسيك» cover, and the same story drawn for «قمرة سحري». */
const STORY_COVERS: Record<string, string> = {
  classic: "/samples/cartoon/first-day-cover-sm.webp",
  magic: "/samples/3d/first-day-cover-sm.webp",
};

/**
 * Prices, simply (the owner, 2026-10-09): one card per book with its cover, the price it starts from, its main
 * options and an order button; then one line on delivery and cash on delivery, and the add-ons folded away.
 * Every price comes from the catalog API (only what is on sale: hidden variants and add-ons never reach it).
 */
export default async function PricingPage() {
  const [t, te, locale, catalog] = await Promise.all([
    getTranslations("pricingPage"),
    getTranslations("errors"),
    getLocale(),
    getStoreCatalog(),
  ]);
  const currency = catalog?.currency ?? "ILS";
  const amount = (n: string | number) => money(n, currency, locale);
  const name = (p: { name_ar: string; name_en: string }) => (locale === "ar" ? p.name_ar : p.name_en);
  const families = priceFamilies(catalog?.products ?? [], LINES, { islamic: ISLAMIC_SETS });
  const zones = (catalog?.zones ?? []).filter((z) => z.currency === currency);
  const codFee = Math.max(0, ...zones.map((z) => Number(z.cod_fee)));
  const addons = catalog?.addons ?? [];

  /** A row's words: what it is, and (when that isn't the format itself) its format, smaller. */
  const rowLabel = (family: PriceFamily, row: PriceRow): [string, string | null] => {
    const story = STORY_LINES.includes(family.line);
    const printed = row.format === "digital" ? t("format.pdf") : t("format.printed");
    if (row.unit) {
      const own = `unit.${family.line}.${row.unit}`;
      const words = t.has(own)
        ? t(own, { n: row.parts ?? 0 })
        : t(`unitFallback.${row.unit === "one" ? "one" : "set"}`);
      return [words, printed];
    }
    const format = story
      ? t(`format.${row.format === "digital" ? "digital" : row.format}`)
      : row.format === "digital"
        ? t("format.file")
        : t("format.book");
    if (family.products.length < 2) return [format, null];
    const product = family.products.find((p) => p.slug === row.product);
    const words = t.has(`product.${row.product}`) ? t(`product.${row.product}`) : product ? name(product) : "";
    return [words, story ? format : printed];
  };

  return (
    <PageShell>
      <div className="mx-auto flex w-full max-w-[1100px] flex-col gap-6 px-4 pt-8 pb-16 md:gap-8 md:px-10 md:pt-14 md:pb-24">
        <header className="flex flex-col gap-2">
          <h1 className="text-[32px] leading-tight text-night-900 md:text-[48px]">{t("title")}</h1>
          <p className="text-body text-ink-muted md:text-body-l">{t("lead")}</p>
        </header>

        {catalog === null && <Alert>{te("unknown")}</Alert>}

        <div className="grid gap-4 md:grid-cols-2 md:gap-5">
          {families.map((family) => {
            const lead = family.products[0]!;
            const story = STORY_LINES.includes(family.line);
            const first = PREVIEWS[lead.slug]?.[0];
            const cover = story ? STORY_COVERS[family.line] : (first?.sm ?? first?.src);
            const href = story ? `/stories?line=${family.line}` : `/workbooks/${lead.slug}`;
            return (
              <article
                key={family.line}
                aria-labelledby={`price-${family.line}`}
                className="flex flex-col gap-4 rounded-[20px] border border-line bg-paper-raised p-4 md:p-5"
              >
                <div className="flex items-center gap-3.5">
                  {cover && (
                    <img
                      src={cover}
                      alt=""
                      width={story ? 80 : 57}
                      height={80}
                      loading="lazy"
                      className={`h-20 shrink-0 rounded-[8px] border border-line object-cover object-top ${story ? "w-20" : "w-[57px]"}`}
                    />
                  )}
                  <div className="flex flex-col gap-0.5">
                    <h2 id={`price-${family.line}`} className="text-[20px] leading-snug text-night-900 md:text-[22px]">
                      {name(lead)}
                    </h2>
                    {family.from !== null && (
                      <span className="text-[15px] text-ink-muted">
                        {t.rich("from", {
                          price: amount(family.from),
                          b: (chunks) => <strong className="text-night-900">{chunks}</strong>,
                        })}
                      </span>
                    )}
                  </div>
                </div>
                <dl className="flex flex-col">
                  {family.rows.map((row) => {
                    const [words, sub] = rowLabel(family, row);
                    return (
                      <div
                        key={`${row.product}|${row.unit}|${row.format}`}
                        className="flex items-baseline justify-between gap-3 border-t border-line py-2.5 text-[15px]"
                      >
                        <dt className="text-ink">
                          {words}
                          {sub && <span className="ms-1.5 text-caption text-ink-muted">{sub}</span>}
                        </dt>
                        <dd className="shrink-0 font-display text-[18px] font-extrabold text-night-900">
                          {row.from ? t("fromRow", { price: amount(row.price) }) : amount(row.price)}
                        </dd>
                      </div>
                    );
                  })}
                </dl>
                <Link
                  href={href}
                  aria-label={t("orderLabel", { name: name(lead) })}
                  className={buttonClasses("solid", "md", "mt-auto w-full")}
                >
                  {t("order")}
                </Link>
              </article>
            );
          })}
        </div>

        {zones.length > 0 && (
          <section
            aria-labelledby="delivery-title"
            className="flex flex-col gap-1.5 rounded-[16px] bg-paper-sunk px-4 py-3.5 text-[15px] leading-[1.7] md:px-5"
          >
            <h2 id="delivery-title" className="text-[17px] text-night-900">
              {t("delivery")}
            </h2>
            <ul className="flex flex-col gap-1 md:flex-row md:flex-wrap md:gap-x-8">
              {zones.map((z) => (
                <li key={z.slug}>
                  {t.rich(z.free_over ? "zone" : "zonePlain", {
                    zone: name(z),
                    fee: amount(z.fee),
                    free: z.free_over ? amount(z.free_over) : "",
                    min: z.eta_days[0],
                    max: z.eta_days[1],
                    b: (chunks) => <strong className="text-night-900">{chunks}</strong>,
                    n: (chunks) => <span className="whitespace-nowrap">{chunks}</span>,
                  })}
                </li>
              ))}
              <li className="font-bold text-night-900">
                {codFee > 0 ? t("codFee", { fee: amount(codFee) }) : t("cod")}
              </li>
            </ul>
          </section>
        )}

        {addons.length > 0 && (
          <details className="group rounded-[16px] border border-line bg-paper-raised">
            <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 px-4 font-bold text-night-900 [&::-webkit-details-marker]:hidden">
              {t("addons")}
              <svg
                aria-hidden="true"
                className="size-5 shrink-0 transition group-open:rotate-180"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </summary>
            <dl className="grid gap-x-8 px-4 pb-2 md:grid-cols-2">
              {addons.map((a) => (
                <div
                  key={a.slug}
                  className="flex items-baseline justify-between gap-3 border-t border-line py-2.5 text-[15px]"
                >
                  <dt className="text-ink">{name(a)}</dt>
                  <dd className="shrink-0 font-bold text-night-900">
                    {a.percent
                      ? t("percent", { percent: Number(a.percent) })
                      : Number(a.price) === 0
                        ? t("free")
                        : amount(a.price ?? 0)}
                  </dd>
                </div>
              ))}
            </dl>
          </details>
        )}

        <p className="text-small text-ink-muted">
          {t("kg")}{" "}
          <Link href="/kindergartens#demo" className="inline-flex items-center gap-1 font-bold text-amber-700">
            {t("kgCta")} <Arrow />
          </Link>
        </p>
      </div>
    </PageShell>
  );
}
