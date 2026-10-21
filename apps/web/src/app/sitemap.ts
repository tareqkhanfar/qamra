import type { MetadataRoute } from "next";
import { getPricesShown, getStoreCatalog, getThemes } from "@/lib/catalog";
import { coloringBooks } from "@/lib/coloring";
import { entry } from "@/lib/seo";
import { WORKBOOK_LINES, productPath } from "@/lib/shop";

export const dynamic = "force-dynamic"; // the stories and books come from the admin, not the build

/**
 * The public store: home, stories on sale (one page each), activity books, coloring and drawing books, pricing,
 * how it works, kindergartens.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [themes, catalog, prices] = await Promise.all([getThemes("ar"), getStoreCatalog(), getPricesShown()]);
  const stories = (themes ?? []).filter((t) => t.status === "available").map((t) => entry(`/stories/${t.slug}`, 0.9));
  const workbooks = (catalog?.products ?? [])
    .filter((p) => (WORKBOOK_LINES as readonly string[]).includes(p.line))
    .map((p) => entry(productPath(p), 0.8));
  const coloring = coloringBooks(catalog?.products ?? []).map((p) => entry(productPath(p), 0.8));
  return [
    entry("/", 1, "daily"),
    entry("/stories", 0.9, "daily"),
    ...stories,
    entry("/workbooks", 0.9),
    ...workbooks,
    entry("/coloring", 0.9),
    ...coloring,
    ...(prices ? [entry("/pricing", 0.8)] : []), // no prices page while they are hidden
    entry("/how-it-works", 0.7, "monthly"),
    entry("/kindergartens", 0.7, "monthly"),
    entry("/shop", 0.6),
    entry("/quiz", 0.5, "monthly"),
    entry("/hello", 0.4, "monthly"),
    entry("/privacy", 0.2, "monthly"),
  ];
}
