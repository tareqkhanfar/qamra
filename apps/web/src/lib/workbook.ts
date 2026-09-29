/**
 * Activity-book product page (Addendum 9, WorkbookProduct): one template for «دوسية التأسيس», «رحلتي الأولى
 * للتعلّم» and «مغامراتي مع عائلتي». Option groups come from the product's variants (never hard-coded).
 */
import type { CatalogProduct, CatalogVariant } from "@/lib/store";
import previews from "./workbook-previews.json";

export type Preview = { src: string; title_ar: string; title_en: string };
export const PREVIEWS = previews as Record<string, Preview[]>;

/** The design's order of the choices; anything else a product adds comes after. */
const ORDER = ["level", "stage", "volume", "format", "interior"];

export type Picks = Record<string, string>;
export type Group = { name: string; values: { value: string; available: boolean }[] };

function fits(v: CatalogVariant, picks: Picks, skip?: string): boolean {
  return Object.entries(picks).every(([k, x]) => k === skip || v.options[k] === x);
}

/** The option groups in the design's order; a value is available if some variant has it with the other picks. */
export function groups(product: CatalogProduct, picks: Picks): Group[] {
  const priced = product.variants.filter((v) => v.price !== null);
  const names = [...product.option_names].sort((a, b) => (ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99));
  return names
    .map((name) => {
      const values = [...new Set(priced.map((v) => v.options[name]).filter((x): x is string => !!x))];
      return {
        name,
        values: values.map((value) => ({
          value,
          available: priced.some((v) => v.options[name] === value && fits(v, picks, name)),
        })),
      };
    })
    .filter((g) => g.values.length > 1 || g.name === "format");
}

/**
 * The variant for the picks. When a pick has no variant with the others (e.g. black and white as a PDF), the
 * newest pick wins and the others move to the nearest variant that has it.
 */
export function resolve(
  product: CatalogProduct,
  picks: Picks,
  last?: string,
): { variant: CatalogVariant | null; picks: Picks } {
  const priced = product.variants.filter((v) => v.price !== null);
  const exact = priced.find((v) => fits(v, picks));
  if (exact) return { variant: exact, picks: { ...picks, ...exact.options } };
  const pool = last ? priced.filter((v) => v.options[last] === picks[last]) : priced;
  const score = (v: CatalogVariant) => Object.entries(picks).filter(([k, x]) => v.options[k] === x).length;
  const best = [...pool].sort((a, b) => score(b) - score(a))[0] ?? priced[0] ?? null;
  return { variant: best, picks: best ? { ...picks, ...best.options } : picks };
}

/** Start from what the page's URL asks for (e.g. ?level=kg2 from the quiz), else a printed single copy. */
export function initialPicks(product: CatalogProduct, query: Picks): Picks {
  const priced = product.variants.filter((v) => v.price !== null);
  const wanted = Object.fromEntries(Object.entries(query).filter(([k]) => product.option_names.includes(k)));
  const printed = priced.find(
    (v) =>
      fits(v, wanted) &&
      v.options.format !== "digital" &&
      !Object.values(v.options).includes("set") &&
      (v.options.interior ?? "color") === "color",
  );
  const start = printed ?? priced.find((v) => fits(v, wanted)) ?? priced[0];
  return start ? { ...start.options } : {};
}
