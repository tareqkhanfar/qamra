/** Structured data (schema.org) for the public pages: the site, the FAQ, the activity books. */
import { brandName } from "@/config/brand";
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
  const prices = product.variants.filter((v) => v.price !== null).map((v) => Number(v.price));
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
