/** Structured data (schema.org) for the public pages: the site, the FAQ, the activity books. */
import { brandName } from "@/config/brand";
import { COLORING_AGES, coloringPreviews } from "@/lib/coloring";
import { absolute, SITE } from "@/lib/seo";
import type { CatalogProduct, Currency } from "@/lib/store";
import { PREVIEWS, soldAges } from "@/lib/workbook";

const CONTEXT = "https://schema.org";

/** The business and the site, for the home page. */
export function siteJsonLd(locale: string, description: string): Record<string, unknown> {
  const name = brandName(locale);
  return {
    "@context": CONTEXT,
    "@graph": [
      { "@type": "Organization", name, url: SITE, logo: absolute("/icon.svg"), description },
      { "@type": "WebSite", name, url: `${SITE}/${locale}`, inLanguage: locale },
    ],
  };
}

/** The questions a parent asks, as search engines show them. */
export function faqJsonLd(items: { q: string; a: string }[], locale: string): Record<string, unknown> {
  return {
    "@context": CONTEXT,
    "@type": "FAQPage",
    inLanguage: locale,
    mainEntity: items.map((i) => ({
      "@type": "Question",
      name: i.q,
      acceptedAnswer: { "@type": "Answer", text: i.a },
    })),
  };
}

const nameOf = (p: CatalogProduct, locale: string) => (locale === "ar" ? p.name_ar : p.name_en);

/** One activity book: what it is, its real cover, and the prices it sells at. */
export function workbookJsonLd(
  product: CatalogProduct,
  locale: string,
  currency: Currency,
  description?: string,
): Record<string, unknown> {
  // no Offer while prices are hidden from customers (the API sends none, `show_prices` off)
  const prices = product.variants
    .filter((v) => v.price !== null && v.price !== undefined)
    .map((v) => Number(v.price))
    .filter(Number.isFinite);
  const ages = soldAges(product);
  const url = `${SITE}/${locale}/workbooks/${product.slug}`;
  const cover = PREVIEWS[product.slug]?.[0];
  return {
    "@context": CONTEXT,
    "@type": "Product",
    name: nameOf(product, locale),
    description: description ?? (locale === "ar" ? product.description_ar : product.description_en),
    url,
    inLanguage: locale,
    ...(cover ? { image: absolute(cover.src) } : {}),
    brand: { "@type": "Brand", name: brandName(locale) },
    ...(ages ? { audience: { "@type": "PeopleAudience", suggestedMinAge: ages[0], suggestedMaxAge: ages[1] } } : {}),
    ...(prices.length
      ? {
          offers: {
            "@type": "AggregateOffer",
            priceCurrency: currency,
            lowPrice: Math.min(...prices).toFixed(2),
            highPrice: Math.max(...prices).toFixed(2),
            offerCount: prices.length,
            availability: `${CONTEXT}/InStock`,
            url,
          },
        }
      : {}),
  };
}

/** One coloring or drawing book (/coloring/<slug>): ages 3–7, its cover when exported, its prices when shown. */
export function coloringJsonLd(
  product: CatalogProduct,
  locale: string,
  currency: Currency,
  description?: string,
): Record<string, unknown> {
  const prices = product.variants
    .filter((v) => v.price !== null && v.price !== undefined)
    .map((v) => Number(v.price))
    .filter(Number.isFinite);
  const url = `${SITE}/${locale}/coloring/${product.slug}`;
  const cover = coloringPreviews(product.slug).cover;
  return {
    "@context": CONTEXT,
    "@type": "Product",
    name: nameOf(product, locale),
    description: description ?? (locale === "ar" ? product.description_ar : product.description_en),
    url,
    inLanguage: locale,
    ...(cover ? { image: absolute(cover.src) } : {}),
    brand: { "@type": "Brand", name: brandName(locale) },
    audience: { "@type": "PeopleAudience", suggestedMinAge: COLORING_AGES[0], suggestedMaxAge: COLORING_AGES[1] },
    ...(prices.length
      ? {
          offers: {
            "@type": "AggregateOffer",
            priceCurrency: currency,
            lowPrice: Math.min(...prices).toFixed(2),
            highPrice: Math.max(...prices).toFixed(2),
            offerCount: prices.length,
            availability: `${CONTEXT}/InStock`,
            url,
          },
        }
      : {}),
  };
}

/** The coloring and drawing books hub (/coloring): the list of books on it. */
export function coloringListJsonLd(products: CatalogProduct[], locale: string): Record<string, unknown> {
  return {
    "@context": CONTEXT,
    "@type": "ItemList",
    itemListElement: products.map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      url: `${SITE}/${locale}/coloring/${p.slug}`,
      name: nameOf(p, locale),
    })),
  };
}

/** The activity books hub: the list of books on it. */
export function workbooksListJsonLd(products: CatalogProduct[], locale: string): Record<string, unknown> {
  return {
    "@context": CONTEXT,
    "@type": "ItemList",
    itemListElement: products.map((p, i) => ({
      "@type": "ListItem",
      position: i + 1,
      url: `${SITE}/${locale}/workbooks/${p.slug}`,
      name: nameOf(p, locale),
    })),
  };
}
