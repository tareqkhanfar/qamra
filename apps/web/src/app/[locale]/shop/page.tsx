import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { Scene } from "@/components/art/Scene";
import { ActivityArt } from "@/components/shop/ActivityArt";
import { CartBar } from "@/components/shop/CartBar";
import { StoryLines } from "@/components/shop/StoryLines";
import { PageShell } from "@/components/site/PageShell";
import { Link } from "@/i18n/navigation";
import { examplesFor, getPublicSettings, getShopSummary, getStoreCatalog, getThemes } from "@/lib/catalog";
import { ACTIVITY_LINES, WORKBOOK_PAGES, productFrom } from "@/lib/shop";
import { money } from "@/lib/store";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("shop");
  return { title: t("title"), description: t("lead") };
}

const ICON = "size-[22px] shrink-0";

/** Addendum 9 Shop: every Qamra book in one place, the quiz, kindergartens, trust, and the cart bar. */
export default async function ShopPage() {
  const locale = await getLocale();
  const [t, catalog, themes, examples, summary, site] = await Promise.all([
    getTranslations("shop"),
    getStoreCatalog(),
    getThemes(locale),
    examplesFor(locale),
    getShopSummary(),
    getPublicSettings(),
  ]);
  const currency = catalog?.currency ?? "ILS";
  const price = (n: number | string | null) => (n === null ? "—" : money(n, currency, locale));
  const stories = (themes ?? []).filter((th) => th.status === "available");
  const styles = (catalog?.styles ?? []).filter((s) => s.lines.some((l) => l === "classic" || l === "magic"));
  const activity = (catalog?.products ?? []).filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line));
  const freeCover = (site as Record<string, unknown> | null)?.free_cover === true;
  const name = (p: { name_ar: string; name_en: string }) => (locale === "ar" ? p.name_ar : p.name_en);

  return (
    <PageShell>
      <div className="mx-auto flex max-w-[1100px] flex-col gap-6 px-4 pt-6 pb-32 md:gap-8 md:px-10 md:pt-12">
        <header className="flex flex-col gap-1.5">
          <h1 className="text-[30px] text-night-900 md:text-[44px]">{t("title")}</h1>
          <p className="max-w-[640px] text-[15px] leading-[1.7] text-ink-muted md:text-body-l">{t("lead")}</p>
        </header>

        {freeCover && (
          <Link
            href="/free-cover"
            className="flex items-center gap-3.5 overflow-hidden rounded-[24px] bg-night-900 p-[18px] text-paper"
          >
            <div className="flex grow flex-col gap-1.5">
              <span className="self-start rounded-full bg-amber-500 px-2.5 py-1 text-caption font-bold text-night-950">
                {t("freeCover.badge")}
              </span>
              <h2 className="text-[21px] leading-snug text-paper">{t("freeCover.title")}</h2>
              <span className="text-small text-night-100">{t("freeCover.body")}</span>
            </div>
            <div className="w-[104px] shrink-0 -rotate-[4deg] overflow-hidden rounded-s-[4px] rounded-e-[10px] border-e-[5px] border-night-950">
              <Scene
                theme="night"
                ratio={104 / 120}
                hijab
                hijabColor="#E9826B"
                outfit="#F2B33D"
                pose="wave"
                kidScale={0.7}
              />
            </div>
          </Link>
        )}

        <Link href="/quiz" className="flex min-h-[72px] items-center gap-3.5 rounded-[20px] bg-paper-sunk p-4">
          <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-paper-raised">
            <svg
              className="size-[26px]"
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
          </span>
          <span className="flex grow flex-col gap-0.5">
            <strong className="text-[17px] text-night-900">{t("quiz.title")}</strong>
            <span className="text-small text-ink-muted">{t("quiz.body")}</span>
          </span>
          <svg
            className="size-5 shrink-0 text-night-900 ltr:-scale-x-100"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M19 12H5" />
            <path d="M11 6l-6 6 6 6" />
          </svg>
        </Link>

        <section aria-labelledby="stories-title" className="flex flex-col gap-3">
          <div className="flex items-end justify-between gap-3">
            <div className="flex flex-col gap-0.5">
              <h2 id="stories-title" className="text-[22px] text-night-900 md:text-[28px]">
                {t("stories.title")}
              </h2>
              <span className="text-small text-ink-muted">
                {t("stories.count", { stories: stories.length, styles: styles.length })}
              </span>
            </div>
            <Link href="/stories" className="flex min-h-11 items-center gap-1 text-small font-bold text-amber-700">
              {t("stories.all")} <span className="inline-block rtl:-scale-x-100">→</span>
            </Link>
          </div>
          <StoryLines catalog={catalog} stories={stories} examples={examples} />
        </section>

        {activity.length > 0 && (
          <section aria-labelledby="learn-title" className="flex flex-col gap-3">
            <div className="flex flex-col gap-0.5">
              <h2 id="learn-title" className="text-[22px] text-night-900 md:text-[28px]">
                {t("learn.title")}
              </h2>
              <span className="text-small text-ink-muted">{t("learn.lead")}</span>
            </div>
            <div className="grid gap-3 md:grid-cols-3 md:gap-5">
              {activity.map((p) => {
                const from = productFrom(p);
                const card = (
                  <>
                    <ActivityArt line={p.line} />
                    <div className="flex grow flex-col gap-1">
                      <span className="flex flex-wrap gap-1.5">
                        {t.has(`learn.chip.${p.line}`) && (
                          <span className="rounded-full bg-night-100 px-2 py-0.5 text-[12px] font-semibold text-night-900">
                            {t(`learn.chip.${p.line}`)}
                          </span>
                        )}
                        {(!WORKBOOK_PAGES || summary?.orderable?.[p.slug] === false) && (
                          <span className="rounded-full bg-lav-300 px-2 py-0.5 text-[12px] font-bold text-night-900">
                            {t("soon")}
                          </span>
                        )}
                      </span>
                      <h3 className="text-[18px] text-night-900">{name(p)}</h3>
                      <span className="text-caption leading-[1.5] text-ink-muted">
                        {locale === "ar" ? p.description_ar : p.description_en}
                      </span>
                      {from !== null && (
                        <strong className="text-body text-night-900">
                          {t.has(`learn.unit.${p.line}`)
                            ? t(`learn.unit.${p.line}`, { price: price(from) })
                            : price(from)}
                        </strong>
                      )}
                    </div>
                  </>
                );
                const cls = "flex items-center gap-3.5 rounded-[20px] border border-line bg-paper-raised p-3";
                return WORKBOOK_PAGES ? (
                  <Link key={p.slug} href={`/workbooks/${p.slug}`} className={cls}>
                    {card}
                  </Link>
                ) : (
                  <div key={p.slug} className={cls}>
                    {card}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        <Link href="/kindergartens" className="flex flex-col gap-2 rounded-[24px] bg-night-950 p-5 text-paper md:p-8">
          <span className="text-caption font-bold text-amber-300">{t("b2b.eyebrow")}</span>
          <h2 className="text-[21px] leading-snug text-paper md:text-[28px]">{t("b2b.title")}</h2>
          {summary?.class_book_from && summary.class_book_min_qty && (
            <span className="text-small text-night-100">
              {t("b2b.price", { price: price(summary.class_book_from), n: summary.class_book_min_qty })}
            </span>
          )}
          <span className="mt-1.5 flex min-h-11 items-center self-start rounded-full bg-amber-500 px-[18px] text-[15px] font-bold text-night-950">
            {t("b2b.cta")}
          </span>
        </Link>

        <ul className="grid grid-cols-2 gap-2.5 md:grid-cols-4">
          {(["privacy", "cod", "reprint", "local"] as const).map((k) => (
            <li key={k} className="flex flex-col gap-1.5 rounded-2xl border border-line bg-paper-raised p-3">
              <svg
                className={ICON}
                viewBox="0 0 24 24"
                fill="none"
                stroke="#2E7A52"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {k === "privacy" && (
                  <>
                    <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z" />
                    <path d="M9 12l2 2 4-4" />
                  </>
                )}
                {k === "cod" && (
                  <>
                    <rect x="3" y="6" width="18" height="12" rx="2" />
                    <circle cx="12" cy="12" r="2.5" />
                  </>
                )}
                {k === "reprint" && (
                  <>
                    <path d="M4 12a8 8 0 0 1 14-5.3L20 9" />
                    <path d="M20 4v5h-5" />
                    <path d="M20 12a8 8 0 0 1-14 5.3L4 15" />
                    <path d="M4 20v-5h5" />
                  </>
                )}
                {k === "local" && (
                  <>
                    <path d="M3 21h18" />
                    <path d="M5 21V10l7-5 7 5v11" />
                    <path d="M10 21v-6h4v6" />
                  </>
                )}
              </svg>
              <span className="text-small leading-normal font-semibold">{t(`trust.${k}`)}</span>
            </li>
          ))}
        </ul>
      </div>
      <CartBar />
    </PageShell>
  );
}
