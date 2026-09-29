import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { ThemesGrid } from "@/components/site/ThemesGrid";
import { Alert } from "@/components/ui/Alert";
import { Link } from "@/i18n/navigation";
import { examplesFor, getStoreCatalog, getThemes } from "@/lib/catalog";
import { money } from "@/lib/store";
import { LINES, coversOf, offer, storyFrom, type Line } from "@/lib/story";

type Props = { searchParams: Promise<{ line?: string }> };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("themes");
  return { title: t("title"), description: t("lead") };
}

/** The stories (Addendum 9: /stories; /themes redirects here), with real covers where an example exists. */
export default async function StoriesPage({ searchParams }: Props) {
  const [query, locale] = await Promise.all([searchParams, getLocale()]);
  const [t, tc, themes, catalog, examples] = await Promise.all([
    getTranslations("themes"),
    getTranslations("common"),
    getThemes(locale),
    getStoreCatalog(),
    examplesFor(locale),
  ]);
  const line = LINES.includes(query.line as Line) ? (query.line as Line) : null;
  const chosen = line ? offer(catalog, line) : null;
  const currency = catalog?.currency ?? "ILS";
  const covers = coversOf(examples);
  const prices = Object.fromEntries((themes ?? []).map((th) => [th.slug, storyFrom(catalog, th, line)]));
  const occasionLabels = tc.raw("occasions") as Record<string, string>;
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
            labels={{
              age: t("age"),
              all: t("all"),
              occasion: t("occasion"),
              sort: t("sort"),
              sortPopular: t("sortPopular"),
              sortAge: t("sortAge"),
              empty: t("empty"),
              reset: t("reset"),
              soonTitle: t("soonTitle"),
              soonLead: t("soonLead"),
            }}
          />
        ) : (
          <Alert>{t("unavailable")}</Alert>
        )}
      </div>
    </PageShell>
  );
}
