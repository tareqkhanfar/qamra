import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { ThemesGrid } from "@/components/site/ThemesGrid";
import { LineCompare } from "@/components/store/LineCompare";
import { StyleShowcase } from "@/components/story/StyleShowcase";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";
import { addonMedia } from "@/lib/addonsMedia";
import { examplesFor, getStoreCatalog, getThemes } from "@/lib/catalog";
import { pageMetadata } from "@/lib/seo";
import { money } from "@/lib/store";
import { LINES, classicStylesFor, coversOf, offer, storyFrom, type Line } from "@/lib/story";

type Props = { searchParams: Promise<{ line?: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const [t, locale] = await Promise.all([getTranslations("themes"), getLocale()]);
  return pageMetadata({ path: "/stories", locale, title: t("title"), description: t("lead") });
}

/** The stories (Addendum 9: /stories; /themes redirects here), with real covers where an example exists. */
export default async function StoriesPage({ searchParams }: Props) {
  const [query, locale] = await Promise.all([searchParams, getLocale()]);
  const [t, tc, ts, themes, catalog, examples] = await Promise.all([
    getTranslations("themes"),
    getTranslations("common"),
    getTranslations("storyShowcase"),
    getThemes(locale),
    getStoreCatalog(),
    examplesFor(locale),
  ]);
  const line = LINES.includes(query.line as Line) ? (query.line as Line) : null;
  const chosen = line ? offer(catalog, line) : null;
  const currency = catalog?.currency ?? "ILS";
  const covers = coversOf(examples);
  // a story not sold in the chosen line still shows the price it can be ordered at (its card says «سحري فقط»)
  const prices = Object.fromEntries(
    (themes ?? []).map((th) => [th.slug, storyFrom(catalog, th, line) ?? storyFrom(catalog, th)]),
  );
  const occasionLabels = tc.raw("occasions") as Record<string, string>;
  const ar = locale === "ar";
  const classic = Object.fromEntries(
    (themes ?? []).map((th) => [th.slug, classicStylesFor(catalog, th).map((s) => (ar ? s.name_ar : s.name_en))]),
  );
  // the story books' art styles (catalog order), only those of the chosen line when there is one
  const styles = (catalog?.styles ?? [])
    .filter((s) => (line ? s.lines.includes(line) : s.lines.includes("classic") || s.lines.includes("magic")))
    .map((s) => ({ slug: s.slug, name: ar ? s.name_ar : s.name_en, lines: s.lines }));
  const live = (themes ?? []).filter((th) => th.status === "available");
  const themeNames = Object.fromEntries(live.map((th) => [th.slug, th.name]));
  const lineNames = Object.fromEntries(
    (catalog?.products ?? [])
      .filter((p) => p.line === "classic" || p.line === "magic")
      .filter((p, i, all) => all.findIndex((q) => q.line === p.line) === i)
      .map((p) => [p.line, ar ? p.name_ar : p.name_en]),
  );
  const pageCounts = [...new Set(live.map((th) => th.pages))];
  return (
    <PageShell>
      <div className="mx-auto max-w-[1440px] px-4 pb-16 md:px-10 md:pb-24 xl:px-24">
        <header className="flex flex-col gap-2 pt-8 pb-6 md:pt-14 md:pb-8">
          <h1 className="text-[32px] text-night-900 md:text-[52px]">{t("title")}</h1>
          <p className="max-w-[640px] text-body text-ink-muted md:text-body-l">{t("lead")}</p>
        </header>
        {chosen && (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-[20px] bg-night-900 px-4 py-3.5 text-paper">
            <span className="text-small">
              {t("lineChosen", {
                line: locale === "ar" ? chosen.product.name_ar : chosen.product.name_en,
                price: chosen.from === null ? "—" : money(chosen.from, currency, locale),
              })}
            </span>
            <Link href="/stories" className="min-h-11 content-center text-small font-bold text-amber-300 underline">
              {t("lineAll")}
            </Link>
          </div>
        )}
        {themes ? (
          <ThemesGrid
            themes={themes}
            covers={covers}
            prices={prices}
            currency={currency}
            line={line}
            occasionLabels={occasionLabels}
            styles={styles}
            classic={catalog ? classic : undefined}
            labels={{
              age: t("age"),
              all: t("all"),
              occasion: t("occasion"),
              sort: t("sort"),
              sortPopular: t("sortPopular"),
              sortAge: t("sortAge"),
              empty: t("empty"),
              reset: t("reset"),
            }}
          />
        ) : (
          <Alert>{t("unavailable")}</Alert>
        )}
        {styles.length > 0 && (
          <section aria-labelledby="styles-title" className="mt-12 flex flex-col gap-4 md:mt-16">
            <div className="flex flex-col gap-1.5">
              <h2 id="styles-title" className="text-[26px] text-night-900 md:text-h2">
                {ts("title")}
              </h2>
              <p className="max-w-[680px] text-body leading-[1.7] text-ink-muted">{ts("lead")}</p>
            </div>
            <StyleShowcase styles={styles} themeNames={themeNames} lineNames={lineNames} />
          </section>
        )}
        {catalog && !line && (
          <div className="mt-12 md:mt-16">
            <LineCompare catalog={catalog} pages={pageCounts.length === 1 ? pageCounts[0] : null} media={addonMedia} />
          </div>
        )}
      </div>
    </PageShell>
  );
}
