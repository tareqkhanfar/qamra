/** Search metadata and structured data for a story page (/stories/[slug]). */
import type { Metadata } from "next";
import { brandName } from "@/config/brand";
import { examplesFor, getTheme, type ThemeDetail } from "@/lib/catalog";
import { pickExample, type Example } from "@/lib/examples";
import { absolute, alternates, SITE } from "@/lib/seo";
import type { Catalog } from "@/lib/store";
import { storyFrom } from "@/lib/story";
import { themeArt } from "@/lib/themeArt";

const clip = (text: string, n = 160) => (text.length <= n ? text : `${text.slice(0, n - 1).trimEnd()}…`);

/** Title and description in the page's language, the published example's cover as the share picture. */
export async function storyMetadata(slug: string, locale: string): Promise<Metadata> {
  const [theme, examples] = await Promise.all([getTheme(slug, locale), examplesFor(locale, slug)]);
  if (!theme) return {};
  const cover = pickExample(examples, slug)?.cover ?? themeArt(slug)?.src; // else the story's own cover art
  const title = `${theme.name} | ${brandName(locale)}`;
  const description = clip(theme.tagline || theme.description);
  const images = cover ? [{ url: absolute(cover), alt: theme.name }] : undefined;
  return {
    title,
    description,
    alternates: alternates(`/stories/${slug}`, locale),
    openGraph: {
      type: "website",
      siteName: brandName(locale),
      locale: locale === "ar" ? "ar_AR" : "en_US",
      url: `${SITE}/${locale}/stories/${slug}`,
      title,
      description,
      images,
    },
    twitter: { card: cover ? "summary_large_image" : "summary", title, description, images: images?.map((i) => i.url) },
  };
}

/** schema.org Product + Book, with the lowest price a parent can order it at (₪). */
export function storyJsonLd(
  theme: ThemeDetail,
  example: Example | null,
  catalog: Catalog | null,
  locale: string,
): Record<string, unknown> {
  const from = theme.status === "available" ? storyFrom(catalog, theme) : null;
  const url = `${SITE}/${locale}/stories/${theme.slug}`;
  const picture = themeArt(theme.slug);
  return {
    "@context": "https://schema.org",
    "@type": ["Product", "Book"],
    name: theme.name,
    description: theme.description || theme.tagline,
    url,
    inLanguage: locale,
    ...(example
      ? { image: absolute(example.cover), numberOfPages: example.page_count }
      : picture
        ? { image: absolute(picture.src), numberOfPages: theme.pages }
        : {}),
    brand: { "@type": "Brand", name: brandName(locale) },
    audience: { "@type": "PeopleAudience", suggestedMinAge: theme.age_min, suggestedMaxAge: theme.age_max },
    ...(from !== null
      ? {
          offers: {
            "@type": "Offer",
            price: from.toFixed(2),
            priceCurrency: catalog?.currency ?? "ILS",
            availability: "https://schema.org/InStock",
            url,
          },
        }
      : {}),
  };
}
