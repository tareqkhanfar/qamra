import type { MetadataRoute } from "next";
import { getStoreCatalog, getThemes } from "@/lib/catalog";
import { entry } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";

export const dynamic = "force-dynamic"; // the stories and books come from the admin, not the build

/** The public store: home, stories on sale (one page each), activity books, pricing, how it works, kindergartens. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [themes, catalog] = await Promise.all([getThemes("ar"), getStoreCatalog()]);
  const stories = (themes ?? []).filter((t) => t.status === "available").map((t) => entry(`/stories/${t.slug}`, 0.9));
  const workbooks = (catalog?.products ?? [])
    .filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line))
    .map((p) => entry(`/workbooks/${p.slug}`, 0.8));
  return [
    entry("/", 1, "daily"),
    entry("/stories", 0.9, "daily"),
    ...stories,
    entry("/workbooks", 0.9),
    ...workbooks,
    entry("/pricing", 0.8),
    entry("/how-it-works", 0.7, "monthly"),
    entry("/kindergartens", 0.7, "monthly"),
    entry("/shop", 0.6),
    entry("/quiz", 0.5, "monthly"),
    entry("/privacy", 0.2, "monthly"),
  ];
}
