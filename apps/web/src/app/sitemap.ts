import type { MetadataRoute } from "next";
import { getStoreCatalog, getThemes } from "@/lib/catalog";
import { entry } from "@/lib/seo";
import { ACTIVITY_LINES } from "@/lib/shop";

export const dynamic = "force-dynamic"; // the stories and books come from the admin, not the build

/** The public shop: home, stories (one page each), workbooks, quiz, kindergartens. Both languages. */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [themes, catalog] = await Promise.all([getThemes("ar"), getStoreCatalog()]);
  const stories = (themes ?? []).map((t) => entry(`/stories/${t.slug}`, t.status === "available" ? 0.9 : 0.5));
  const workbooks = (catalog?.products ?? [])
    .filter((p) => (ACTIVITY_LINES as readonly string[]).includes(p.line))
    .map((p) => entry(`/workbooks/${p.slug}`, 0.8));
  return [
    entry("/", 1, "daily"),
    entry("/stories", 0.9, "daily"),
    ...stories,
    entry("/shop", 0.8),
    ...workbooks,
    entry("/quiz", 0.6, "monthly"),
    entry("/kindergartens", 0.7, "monthly"),
    entry("/free-cover", 0.6, "monthly"),
    entry("/privacy", 0.2, "monthly"),
  ];
}
