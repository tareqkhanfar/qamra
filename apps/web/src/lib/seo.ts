/** Search pages (Phase 5): absolute URLs on the brand domain, ar/en alternates, and safe JSON-LD. */
import type { Metadata, MetadataRoute } from "next";
import { brand } from "@/config/brand";
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
