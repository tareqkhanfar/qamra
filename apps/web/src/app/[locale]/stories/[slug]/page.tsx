import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getLocale } from "next-intl/server";
import { PageShell } from "@/components/site/PageShell";
import { StoryProduct } from "@/components/story/StoryProduct";
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
  const [theme, catalog, examples] = await Promise.all([
    getTheme(slug, locale),
    getStoreCatalog(),
    examplesFor(locale, slug),
  ]);
  if (!theme || theme.status !== "available") notFound(); // stories still being written are not listed
  const line = LINES.includes(query.line as Line) ? (query.line as Line) : null;
  const ld = <StoryJsonLd data={storyJsonLd(theme, pickExample(examples, slug), catalog, locale)} />;

  return (
    <PageShell>
      {ld}
      <StoryProduct theme={theme} catalog={catalog} examples={examples} initialLine={line} />
    </PageShell>
  );
}
