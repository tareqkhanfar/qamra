/** Search pages (Phase 5): absolute URLs on the brand domain, ar/en alternates, and safe JSON-LD. */
import type { Metadata, MetadataRoute } from "next";
import { brand, brandName } from "@/config/brand";
import { routing } from "@/i18n/routing";

export const SITE = `https://${brand.domain}`;

/** Canonical for this language, hreflang for both, and x-default → Arabic (the default language). */
export function alternates(path: string, locale: string): Metadata["alternates"] {
  const at = (l: string) => `${SITE}/${l}${path === "/" ? "" : path}`;
  return {
    canonical: at(locale),
    languages: {
      ...Object.fromEntries(routing.locales.map((l) => [l, at(l)])),
      "x-default": at(routing.defaultLocale),
    },
  };
}

/**
 * Title ("page | brand"), description, canonical + hreflang and the share cards for a public page. `bare` keeps
 * the title as given (the home's already carries the brand); `image` is the picture a shared link shows.
 */
export function pageMetadata({
  path,
  locale,
  title,
  description,
  image,
  bare = false,
}: {
  path: string;
  locale: string;
  title: string;
  description: string;
  image?: { url: string; alt: string };
  bare?: boolean;
}): Metadata {
  const name = brandName(locale);
  const full = bare ? title : `${title} | ${name}`;
  description = description.length <= 160 ? description : `${description.slice(0, 159).trimEnd()}…`;
  const images = image ? [{ url: absolute(image.url), alt: image.alt }] : undefined;
  return {
    title: full,
    description,
    alternates: alternates(path, locale),
    openGraph: {
      type: "website",
      siteName: name,
      locale: locale === "ar" ? "ar_AR" : "en_US",
      url: `${SITE}/${locale}${path === "/" ? "" : path}`,
      title: full,
      description,
      images,
    },
    twitter: {
      card: image ? "summary_large_image" : "summary",
      title: full,
      description,
      images: images?.map((i) => i.url),
    },
  };
}

/** One sitemap entry per page, listing both languages. */
export function entry(
  path: string,
  priority: number,
  changeFrequency: "daily" | "weekly" | "monthly" = "weekly",
): MetadataRoute.Sitemap[number] {
  const at = (l: string) => `${SITE}/${l}${path === "/" ? "" : path}`;
  return {
    url: at(routing.defaultLocale),
    changeFrequency,
    priority,
    alternates: { languages: Object.fromEntries(routing.locales.map((l) => [l, at(l)])) },
  };
}

/** A same-site absolute URL for images the API serves (Open Graph needs absolute URLs). */
export const absolute = (url: string) =>
  url.startsWith("http") ? url : `${SITE}${url.startsWith("/") ? "" : "/"}${url}`;

/** JSON for a `<script type="application/ld+json">`: `<` escaped so no text can close the tag. */
export const ldJson = (data: object) => JSON.stringify(data).replace(/</g, "\\u003c");

/** Pages that are never indexed (account, create flow, admin, reader, share and voice links). */
export const PRIVATE_PATHS = [
  "/account",
  "/admin",
  "/create",
  "/cart",
  "/checkout",
  "/order/",
  "/track",
  "/books/",
  "/s/",
  "/r/",
  "/v/",
  "/invite/",
  "/portal",
  "/free-cover/result",
  "/login",
  "/register",
];
