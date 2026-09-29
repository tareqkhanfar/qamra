import type { MetadataRoute } from "next";
import { routing } from "@/i18n/routing";
import { PRIVATE_PATHS, SITE } from "@/lib/seo";

/** Crawl the shop pages; never the private ones (every private page is also noindex). */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: ["/api/", ...routing.locales.flatMap((l) => PRIVATE_PATHS.map((p) => `/${l}${p}`))],
    },
    sitemap: `${SITE}/sitemap.xml`,
  };
}
