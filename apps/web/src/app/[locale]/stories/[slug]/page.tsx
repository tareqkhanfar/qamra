import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getLocale, getTranslations } from "next-intl/server";
import { CoverArt, splitTemplate } from "@/components/book/CoverArt";
import { PageShell } from "@/components/site/PageShell";
import { StoryProduct } from "@/components/story/StoryProduct";
import { Link } from "@/i18n/navigation";
import { examplesFor, getStoreCatalog, getTheme } from "@/lib/catalog";
import { pickExample } from "@/lib/examples";
import { LINES, type Line } from "@/lib/story";
import { storyJsonLd, storyMetadata } from "@/lib/storySeo";
import { StoryJsonLd } from "@/components/story/StoryJsonLd";

type Props = { params: Promise<{ slug: string }>; searchParams: Promise<{ line?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  return storyMetadata(slug, await getLocale()); // Phase 5 SEO: title, description, OG cover, hreflang
}

/** Addendum 9 StoryProduct (replaces ThemeDetail; /themes/[slug] redirects here). */
export default async function StoryPage({ params, searchParams }: Props) {
  const [{ slug }, query, locale] = await Promise.all([params, searchParams, getLocale()]);
  const [t, tc, theme, catalog, examples] = await Promise.all([
    getTranslations("themeDetail"),
    getTranslations("common"),
    getTheme(slug, locale),
    getStoreCatalog(),
    examplesFor(locale, slug),
  ]);
  if (!theme) notFound();
  const line = LINES.includes(query.line as Line) ? (query.line as Line) : null;
  const ld = <StoryJsonLd data={storyJsonLd(theme, pickExample(examples, slug), catalog, locale)} />;

  if (theme.status === "coming_soon") {
    const [name, rest] = splitTemplate(theme.title, theme.sample_name ?? theme.name);
    return (
      <PageShell>
        {ld}
        <div className="mx-auto flex max-w-[720px] flex-col gap-5 px-4 py-8 md:py-14">
          <CoverArt
            example={null}
            art={theme.art}
            titleName={name}
            titleRest={rest}
            alt={t("placeholderCoverAlt")}
            sizes="(min-width: 768px) 720px, 100vw"
            priority
            className="rounded-2xl"
          />
          <div className="flex flex-wrap gap-2 text-caption font-semibold">
            <span className="rounded-full bg-night-100 px-2.5 py-1 text-night-900">
              {tc("ages", { min: theme.age_min, max: theme.age_max })}
            </span>
            <span className="rounded-full bg-lav-300 px-2.5 py-1 text-night-900">{tc("comingSoon")}</span>
          </div>
          <h1 className="text-[32px] leading-tight text-night-900 md:text-[40px]">{theme.name}</h1>
          <p className="text-body leading-[1.75] text-ink-muted">{theme.description}</p>
          <div className="flex flex-col gap-2 rounded-lg bg-paper-sunk p-5">
            <h2 className="text-[20px] text-night-900">{t("soonTitle")}</h2>
            <p className="text-body text-ink-muted">{t("soonBody")}</p>
          </div>
          <Link
            href="/stories"
            className="flex min-h-14 items-center justify-center rounded-full border-2 border-night-900 px-6 text-[17px] font-bold text-night-900"
          >
            {t("browseAvailable")}
          </Link>
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      {ld}
      <StoryProduct theme={theme} catalog={catalog} examples={examples} initialLine={line} />
    </PageShell>
  );
}
