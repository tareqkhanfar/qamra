import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { Alert } from "@/components/ui/Alert";
import { Photo } from "@/components/site/Photo";
import { Arrow, CtaBand, SECTION, SectionHead } from "@/components/site/blocks";
import { Link } from "@/i18n/navigation";
import { getShopSummary, getStoreCatalog } from "@/lib/catalog";
import { pageMetadata } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";
import { money, type CatalogProduct, type CatalogVariant } from "@/lib/store";

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("pricingPage"), getLocale()]);
  return pageMetadata({ path: "/pricing", locale, title: t("title"), description: t("lead") });
}

const STORY_LINES = ["classic", "magic", "coloring"];
const FORMAT_ORDER = ["softcover", "hardcover", "spiral", "digital"];

type Props = { searchParams: Promise<{ country?: string }> };

/**
 * Every price on one page, all from the catalog API: story formats, add-ons, activity books, class books,
 * delivery. `?country=jo` shows the same page in Jordanian dinars (the cart's currency follows the zone).
 */
export default async function PricingPage({ searchParams }: Props) {
  const [query, locale] = await Promise.all([searchParams, getLocale()]);
  const wanted = query.country === "jo" ? "JOD" : "ILS";
  const [t, tw, tn, te, catalog, summary] = await Promise.all([
    getTranslations("pricingPage"),
    getTranslations("workbook"),
    getTranslations("nav"),
    getTranslations("errors"),
    getStoreCatalog(wanted),
    getShopSummary(wanted),
  ]);
  const currency = catalog?.currency ?? "ILS";
  const countries = [...new Set((catalog?.zones ?? []).map((z) => z.country))].sort().reverse(); // PS, JO
  const amount = (n: string | number) => money(n, currency, locale);
  const name = (p: { name_ar: string; name_en: string }) => (locale === "ar" ? p.name_ar : p.name_en);
  const desc = (p: { description_ar: string; description_en: string }) =>
    locale === "ar" ? p.description_ar : p.description_en;
  const products = catalog?.products ?? [];
  const stories = products.filter((p) => STORY_LINES.includes(p.line));
  const activity = products.filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line));
  const zones = (catalog?.zones ?? []).filter((z) => z.currency === currency);
  const lineName = (line: string) => name(products.find((p) => p.line === line) ?? { name_ar: line, name_en: line });
  const priced = (p: CatalogProduct) =>
    p.variants
      .filter((v) => v.price !== null)
      .sort((a, b) => FORMAT_ORDER.indexOf(a.options.format ?? "") - FORMAT_ORDER.indexOf(b.options.format ?? ""));
  const optionLabel = (group: string, value: string) =>
    group === "format"
      ? t(`formats.${value}`)
      : tw.has(`values.${group}.${value}`)
        ? tw(`values.${group}.${value}`)
        : value.toUpperCase();
  // activity books: one row per volume or stage (with its level), its formats side by side
  const WHICH = ["level", "stage", "volume"];
  const whichLabel = (v: CatalogVariant) =>
    WHICH.filter((g) => v.options[g])
      .map((g) =>
        g === "level"
          ? optionLabel(g, v.options[g]!).split(" ·")[0]
          : `${tw(`options.${g}`)} ${optionLabel(g, v.options[g]!)}`,
      )
      .join(" · ");
  const formatLabel = (v: CatalogVariant) =>
    ["interior", "format"]
      .filter((g) => v.options[g])
      .map((g) =>
        tw.has(`values.${g}.${v.options[g]}`) ? tw(`values.${g}.${v.options[g]}`) : optionLabel(g, v.options[g]!),
      )
      .join(" · ");
  const rows = (p: CatalogProduct) => {
    const out = new Map<string, CatalogVariant[]>();
    for (const v of priced(p)) out.set(whichLabel(v), [...(out.get(whichLabel(v)) ?? []), v]);
    return [...out.entries()];
  };
  const row = "flex items-baseline justify-between gap-3 border-b border-dashed border-line py-2.5 last:border-0";
  const card = "flex flex-col gap-3 rounded-[20px] border border-line bg-paper-raised p-5";

  return (
    <PageShell>
      <div className={`${SECTION} flex flex-col gap-10 pt-8 pb-16 md:gap-14 md:pt-14 md:pb-24`}>
        <header className="flex flex-col gap-3">
          <h1 className="text-[32px] leading-tight text-night-900 md:text-[52px]">{t("title")}</h1>
          <p className="max-w-[680px] text-body text-ink-muted md:text-body-l">{t("lead")}</p>
          {countries.length > 1 && (
            <nav aria-label={t("country.label")} className="mt-1 flex flex-wrap items-center gap-2">
              <span className="text-small font-semibold text-ink-muted">{t("country.label")}</span>
              {countries.map((c) => {
                const on = (c === "JO") === (currency === "JOD");
                return (
                  <Link
                    key={c}
                    href={c === "JO" ? "/pricing?country=jo" : "/pricing"}
                    aria-current={on ? "page" : undefined}
                    className={`flex min-h-11 items-center rounded-full border-[1.5px] px-4 text-[15px] transition ${on ? "border-night-900 bg-night-900 font-semibold text-paper" : "border-line bg-paper-raised text-ink hover:border-night-500"}`}
                  >
                    {t(`country.${c}`)}
                  </Link>
                );
              })}
            </nav>
          )}
        </header>

        {catalog === null && <Alert>{te("unknown")}</Alert>}

        {/* STORY BOOKS */}
        <section className="flex flex-col gap-5">
          <SectionHead
            title={t("storiesTitle")}
            lead={t("storiesLead")}
            more={{ href: "/stories", label: t("chooseStory") }}
          />
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {stories.map((p) => (
              <div key={p.slug} className={card}>
                <h3 className="text-[22px] text-night-900">{name(p)}</h3>
                <p className="text-small text-ink-muted">{desc(p)}</p>
                {typeof p.features.pages === "number" && (
                  <span className="text-caption font-semibold text-ink-muted">
                    {t("pages", { count: p.features.pages })}
                  </span>
                )}
                <dl>
                  {priced(p).map((v) => (
                    <div key={v.sku} className={row}>
                      <dt>{optionLabel("format", v.options.format ?? "")}</dt>
                      <dd className="font-display text-[20px] font-extrabold text-night-900">{amount(v.price!)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            ))}
          </div>
        </section>

        {/* ADD-ONS */}
        <section className="grid gap-6 lg:grid-cols-[1fr_260px]">
          <div className="flex flex-col gap-5">
            <SectionHead title={t("addonsTitle")} lead={t("addonsLead")} />
            <dl className="grid gap-x-8 md:grid-cols-2">
              {(catalog?.addons ?? []).map((a) => (
                <div key={a.slug} className={row}>
                  <dt className="flex flex-col">
                    <span className="font-semibold text-ink">{name(a)}</span>
                    {desc(a) && <span className="text-caption text-ink-muted">{desc(a)}</span>}
                    {a.included_lines.length > 0 && (
                      <span className="text-caption font-semibold text-success">
                        {t("included", { lines: a.included_lines.map(lineName).join("، ") })}
                      </span>
                    )}
                  </dt>
                  <dd className="shrink-0 font-display text-[18px] font-extrabold text-night-900">
                    {a.percent
                      ? t("percent", { percent: Number(a.percent) })
                      : Number(a.price) === 0
                        ? t("free")
                        : amount(a.price!)}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
          <Photo name="gift-box" alt={t("photoAlt")} sizes="260px" className="hidden rounded-[24px] lg:block" />
        </section>

        {/* ACTIVITY BOOKS */}
        <section className="flex flex-col gap-5">
          <SectionHead
            title={t("activityTitle")}
            lead={t("activityLead")}
            more={{ href: "/workbooks", label: tn("workbooks") }}
          />
          <div className="grid gap-4 md:grid-cols-3">
            {activity.map((p) => (
              <div key={p.slug} className={card}>
                <h3 className="text-[22px] text-night-900">{name(p)}</h3>
                <dl className="flex flex-col">
                  {rows(p).map(([which, variants]) => (
                    <div
                      key={which || p.slug}
                      className="flex flex-col gap-1.5 border-b border-dashed border-line py-3 last:border-0"
                    >
                      {which && <dt className="font-bold text-night-900">{which}</dt>}
                      {variants.map((v) => (
                        <dd key={v.sku} className="flex items-baseline justify-between gap-3 text-small">
                          <span>{formatLabel(v)}</span>
                          <strong className="shrink-0 font-display text-[18px] text-night-900">
                            {amount(v.price!)}
                          </strong>
                        </dd>
                      ))}
                    </div>
                  ))}
                </dl>
                <Link
                  href={`/workbooks/${p.slug}`}
                  className="mt-auto flex min-h-11 items-center self-start font-bold text-amber-700"
                >
                  {t("orderBook", { name: name(p) })} <Arrow />
                </Link>
              </div>
            ))}
          </div>
        </section>

        {/* KINDERGARTENS */}
        {summary?.class_book_from && summary.class_book_min_qty && (
          <Link
            href="/kindergartens#demo"
            className="flex flex-col gap-2 rounded-[24px] bg-night-950 p-6 text-paper md:p-8"
          >
            <h2 className="text-[24px] md:text-[30px]">{t("kgTitle")}</h2>
            <p className="max-w-[720px] text-small text-night-100 md:text-body">
              {t("kgBody", { price: amount(summary.class_book_from), n: summary.class_book_min_qty })}
            </p>
            <span className="mt-2 flex min-h-11 items-center self-start rounded-full bg-amber-500 px-[18px] text-[15px] font-bold text-night-950">
              {t("kgCta")}
            </span>
          </Link>
        )}

        {/* DELIVERY AND PAYMENT */}
        <section className="flex flex-col gap-5">
          <SectionHead title={t("deliveryTitle")} />
          <div className="grid gap-4 md:grid-cols-[1.4fr_1fr]">
            <table className="w-full border-collapse overflow-hidden rounded-[20px] border border-line bg-paper-raised text-start text-[15px]">
              <thead className="bg-paper-sunk text-caption font-bold text-ink-muted">
                <tr>
                  <th className="p-3 text-start">{t("zone")}</th>
                  <th className="p-3 text-start">{t("fee")}</th>
                  <th className="p-3 text-start">{t("etaHead")}</th>
                </tr>
              </thead>
              <tbody>
                {zones.map((z) => (
                  <tr key={z.slug} className="border-t border-line">
                    <td className="p-3 font-semibold text-night-900">{name(z)}</td>
                    <td className="p-3">
                      {amount(z.fee)}
                      {z.free_over && (
                        <span className="block text-caption text-success">
                          {t("freeOver", { amount: amount(z.free_over) })}
                        </span>
                      )}
                    </td>
                    <td className="p-3">{t("eta", { min: z.eta_days[0], max: z.eta_days[1] })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className={card}>
              <h3 className="text-[20px] text-night-900">{t("codTitle")}</h3>
              <p className="text-[15px] leading-[1.7] text-ink-muted">{t("codBody")}</p>
              {zones.some((z) => Number(z.cod_fee) > 0) && (
                <p className="text-caption text-ink-muted">
                  {t("codFee", { fee: amount(Math.max(...zones.map((z) => Number(z.cod_fee)))) })}
                </p>
              )}
            </div>
          </div>
        </section>
      </div>
      <CtaBand
        title={t("ctaTitle")}
        body={t("ctaBody")}
        primary={{ href: "/stories", label: tn("themes") }}
        secondary={{ href: "/workbooks", label: tn("workbooks") }}
      />
      <div className="h-12 md:h-20" />
    </PageShell>
  );
}
