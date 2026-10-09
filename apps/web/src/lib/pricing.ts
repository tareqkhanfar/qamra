/**
 * The pricing page (/pricing): each product family folded into a few price rows, all from the catalog API. A
 * family is one line («قمرة سحري» holds its story and the custom story); a row is a part (one volume or stage,
 * a set, a named bundle) in a format, at the lowest price it has (the levels of «دوسية التأسيس» cost the same,
 * so KG1 and KG2 make one row). Hidden variants never reach the catalog, so they never make a row.
 */
import type { CatalogProduct, CatalogVariant } from "@/lib/store";

/** The options that name a part of an activity book; a story or the family book has none. */
const PART_OPTIONS = ["volume", "stage"];
const FORMAT_ORDER = ["softcover", "hardcover", "spiral", "digital"];

export type PriceRow = {
  product: string; // the product's slug (a family with two products names each row by its product)
  unit: string | null; // null: the book itself; "one": a single part; "set" or a bundle's own key (e.g. "L1")
  format: string; // softcover | hardcover | spiral | digital
  price: number; // the lowest price of the row's variants
  from: boolean; // the row's variants don't all cost the same
  parts: number | null; // how many parts a set or bundle holds, when known
};

export type PriceFamily = { line: string; products: CatalogProduct[]; rows: PriceRow[]; from: number | null };

/** A variant's part: null (no part option), "one", "set", or a named bundle of `bundles`. */
export function unitOf(v: CatalogVariant, bundles: Record<string, string[]> = {}): string | null {
  for (const group of PART_OPTIONS) {
    const value = v.options[group];
    if (value) return value === "set" || value in bundles ? value : "one";
  }
  return null;
}

/** How many parts a set holds: its bundle's list, else the product's single parts (per level). */
function partsOf(product: CatalogProduct, unit: string, bundles: Record<string, string[]>): number | null {
  if (bundles[unit]) return bundles[unit].length;
  if (unit !== "set") return null;
  const singles = new Set<string>();
  for (const v of product.variants) {
    if (unitOf(v, bundles) !== "one") continue;
    for (const group of PART_OPTIONS) if (v.options[group]) singles.add(v.options[group]);
  }
  return singles.size || null;
}

const rank = (unit: string | null, bundles: Record<string, string[]>) =>
  unit === null || unit === "one" ? 0 : unit === "set" ? 1000 : 1 + Object.keys(bundles).indexOf(unit);

/** One product's rows: its priced variants grouped by part and format, printed first, then by part. */
export function priceRows(product: CatalogProduct, bundles: Record<string, string[]> = {}): PriceRow[] {
  const rows = new Map<string, PriceRow>();
  const highest = new Map<string, number>();
  for (const v of product.variants) {
    if (v.price === null) continue;
    const price = Number(v.price);
    const unit = unitOf(v, bundles);
    const format = v.options.format ?? "";
    const key = `${unit}|${format}`;
    const row = rows.get(key);
    const max = Math.max(highest.get(key) ?? price, price);
    highest.set(key, max);
    if (row) {
      row.price = Math.min(row.price, price);
      row.from = row.price !== max;
    } else {
      const parts = unit && unit !== "one" ? partsOf(product, unit, bundles) : null;
      rows.set(key, { product: product.slug, unit, format, price, from: false, parts });
    }
  }
  const digital = (r: PriceRow) => (r.format === "digital" ? 1 : 0);
  return [...rows.values()].sort(
    (a, b) =>
      digital(a) - digital(b) ||
      rank(a.unit, bundles) - rank(b.unit, bundles) ||
      FORMAT_ORDER.indexOf(a.format) - FORMAT_ORDER.indexOf(b.format),
  );
}

/**
 * The families of `lines` that have a price, in that order, each with its rows and the lowest price it starts
 * from. `bundles`: per line, its named bundles and the parts in each («قلبي يعرف الله»: L1, L2, set).
 */
export function priceFamilies(
  products: CatalogProduct[],
  lines: readonly string[],
  bundles: Record<string, Record<string, string[]>> = {},
): PriceFamily[] {
  const families: PriceFamily[] = [];
  for (const line of lines) {
    const own = products.filter((p) => p.line === line);
    const rows = own.flatMap((p) => priceRows(p, bundles[line] ?? {}));
    if (!rows.length) continue;
    families.push({ line, products: own, rows, from: Math.min(...rows.map((r) => r.price)) });
  }
  return families;
}
