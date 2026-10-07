import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { StoryCard } from "@/components/site/StoryCard";
import { StoryProduct } from "@/components/story/StoryProduct";
import { addonMedia } from "@/lib/addonsMedia";
import { examplesFor, getStoreCatalog, getTheme, getThemes, type ThemeCard } from "@/lib/catalog";
import { pickExample } from "@/lib/examples";
import { LINES, coversOf, storyFrom, type Line } from "@/lib/story";
import { storyJsonLd, storyMetadata } from "@/lib/storySeo";
import { StoryJsonLd } from "@/components/story/StoryJsonLd";

type Props = { params: Promise<{ slug: string }>; searchParams: Promise<{ line?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return storyMetadata(slug, await getLocale()); // Phase 5 SEO: title, description, OG cover, hreflang
}

/** The stories closest to this one first: a shared occasion, then the most overlapping ages. */
function relatedTo(theme: ThemeCard, all: ThemeCard[]): ThemeCard[] {
  const overlap = (t: ThemeCard) =>
    Math.max(0, Math.min(t.age_max, theme.age_max) - Math.max(t.age_min, theme.age_min));
  const shared = (t: ThemeCard) => t.occasions.filter((o) => theme.occasions.includes(o)).length;
  return all
    .filter((t) => t.slug !== theme.slug && t.status === "available")
    .sort((a, b) => shared(b) - shared(a) || overlap(b) - overlap(a))
    .slice(0, 3);
}

/** Addendum 9 StoryProduct (replaces ThemeDetail; /themes/[slug] redirects here). */
export default async function StoryPage({ params, searchParams }: Props) {
  const [{ slug }, query, locale] = await Promise.all([params, searchParams, getLocale()]);
  const [theme, catalog, examples, themes, allExamples, t] = await Promise.all([
    getTheme(slug, locale),
    getStoreCatalog(),
    examplesFor(locale, slug),
    getThemes(locale),
    examplesFor(locale),
    getTranslations("storyShowcase.related"),
  ]);
  if (!theme || theme.status !== "available") notFound(); // stories still being written are not listed
  const line = LINES.includes(query.line as Line) ? (query.line as Line) : null;
  const ld = <StoryJsonLd data={storyJsonLd(theme, pickExample(examples, slug), catalog, locale)} />;
  const live = (themes ?? []).filter((th) => th.status === "available");
  const names = Object.fromEntries(live.map((th) => [th.slug, th.name]));
  const related = relatedTo(theme, live);
  const covers = coversOf(allExamples);
  const styles = (catalog?.styles ?? [])
    .filter((s) => (line ? s.lines.includes(line) : s.lines.includes("classic") || s.lines.includes("magic")))
    .map((s) => ({ slug: s.slug, name: locale === "ar" ? s.name_ar : s.name_en }));

  return (
    <PageShell>
      {ld}
      <StoryProduct
        theme={theme}
        catalog={catalog}
        examples={examples}
        initialLine={line}
        themeNames={names}
        media={addonMedia}
        related={
          related.length > 0 && (
            <section aria-labelledby="related-title" className="flex flex-col gap-3 border-t border-line pt-8">
              <div className="flex flex-col gap-1">
                <h2 id="related-title" className="text-[24px] text-night-900">
                  {t("title")}
                </h2>
                <p className="text-small text-ink-muted">{t("lead")}</p>
              </div>
              <div className="grid grid-cols-2 gap-3 md:gap-5 lg:grid-cols-3">
                {related.map((th) => (
                  <StoryCard
                    key={th.slug}
                    theme={th}
                    example={covers[th.slug] ?? null}
                    from={storyFrom(catalog, th, line)}
                    currency={catalog?.currency ?? "ILS"}
                    line={line}
                    styles={styles}
                  />
                ))}
              </div>
            </section>
          )
        }
      />
    </PageShell>
  );
}
