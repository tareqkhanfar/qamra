/**
 * «دفاتر التلوين والرسم» (the store's `colorbook` line): the four books' facts and their preview pages. The content
 * is fixed (packages/workbook/src/qamra_workbook/coloring): only the cover (the child's name, and their character
 * when they have one) and the title page «{صاحِبُ/صاحِبَةُ} هذا الدَّفْتَرِ» are personalized. The facts come from the catalog's
 * `features`; the table here is the fallback while a product carries none.
 */
import { COLORING_SLUGS, isColoringLine } from "@/lib/shop";
import type { CatalogProduct, CatalogVariant } from "@/lib/store";
import previews from "./coloring-previews.json";

export type ColoringTitle = "letters" | "palestine" | "ramadan" | "sketchbook";
export type ColoringBinding = "stapled" | "wire-o";

/** One exported image: the 720 px file (`src`, e.g. `/coloring/coloring-letters/01.webp?v=…`) and its size. */
export type ColoringImage = { src: string; w: number; h: number };
export type ColoringPage = ColoringImage & { caption_ar: string; caption_en: string };
/** A book's previews: its cover and a few inside pages (none yet: the pages draw a placeholder instead). */
export type ColoringPreviews = { cover: ColoringImage | null; pages: ColoringPage[] };

const PREVIEWS = previews as Record<string, ColoringPreviews>;
const NONE: ColoringPreviews = { cover: null, pages: [] };

export const coloringPreviews = (slug: string): ColoringPreviews => PREVIEWS[slug] ?? NONE;

/** The 360 px copy next to every 720 px page: `NN.webp` → `NN-sm.webp` (the `?v=` digest kept). */
export const smallSrc = (src: string): string => src.replace(/\.webp(?=$|[?#])/, "-sm.webp");

/** `src` and `srcSet` of an exported image: the small copy first, the full one as the 2× source. */
export const imageSources = (img: ColoringImage) => {
  const sm = smallSrc(img.src);
  return sm === img.src ? { src: img.src } : { src: sm, srcSet: `${sm} 360w, ${img.src} 720w` };
};

export type ColoringFacts = {
  title: ColoringTitle;
  pages: number;
  binding: ColoringBinding;
  size: string;
  interior: string;
};

/** The books as packages/workbook/src/qamra_workbook/coloring/titles.py prints them (all A4, B/W inside). */
export const COLORING_FACTS: Record<string, ColoringFacts> = {
  "coloring-letters": { title: "letters", pages: 32, binding: "stapled", size: "A4", interior: "bw" },
  "coloring-palestine": { title: "palestine", pages: 28, binding: "stapled", size: "A4", interior: "bw" },
  "coloring-ramadan": { title: "ramadan", pages: 24, binding: "stapled", size: "A4", interior: "bw" },
  sketchbook: { title: "sketchbook", pages: 48, binding: "wire-o", size: "A4", interior: "bw" },
};

/** Ages 3–7 for all four (the line's promise). */
export const COLORING_AGES: [number, number] = [3, 7];

const TITLES: readonly string[] = ["letters", "palestine", "ramadan", "sketchbook"];
const BINDINGS: readonly string[] = ["stapled", "wire-o"];

/** A book's facts: the catalog's features over the table above (a product just added may carry none). */
export function coloringFacts(product: Pick<CatalogProduct, "slug" | "features">): ColoringFacts {
  const base = COLORING_FACTS[product.slug] ?? COLORING_FACTS["coloring-letters"]!;
  const f = product.features ?? {};
  const pages = Number(f.pages);
  return {
    title: TITLES.includes(String(f.title)) ? (f.title as ColoringTitle) : base.title,
    pages: Number.isInteger(pages) && pages > 0 ? pages : base.pages,
    binding: BINDINGS.includes(String(f.binding)) ? (f.binding as ColoringBinding) : base.binding,
    size: typeof f.size === "string" && f.size ? f.size : base.size,
    interior: typeof f.interior === "string" && f.interior ? f.interior : base.interior,
  };
}

/** Whether a catalog product belongs to «دفاتر التلوين والرسم». */
export const isColoringProduct = (p: Pick<CatalogProduct, "line">): boolean => isColoringLine(p.line);

/** The coloring and drawing books of the catalog, in the line's order (letters, Palestine, Ramadan, sketchbook). */
export function coloringBooks(products: readonly CatalogProduct[]): CatalogProduct[] {
  const order = (slug: string) => {
    const i = (COLORING_SLUGS as readonly string[]).indexOf(slug);
    return i < 0 ? 99 : i;
  };
  return products.filter(isColoringProduct).sort((a, b) => order(a.slug) - order(b.slug));
}

/**
 * The variants on sale. A `null` price means "not sold in this currency"; while prices are hidden from customers
 * the API drops the field instead (undefined), and the variant is still on sale.
 */
export const soldVariants = (product: Pick<CatalogProduct, "variants">): CatalogVariant[] =>
  product.variants.filter((v) => v.price !== null);

/** Whether the book also sells as a PDF to print at home (the sketchbook is printed only). */
export const sellsPdf = (product: Pick<CatalogProduct, "variants">): boolean =>
  soldVariants(product).some((v) => v.options.format === "digital");

export type OptionGroup = { name: string; values: string[] };

/** The choices the book offers, from what it sells (the format first; a group with one value still shows). */
export function optionGroups(product: Pick<CatalogProduct, "variants" | "option_names">): OptionGroup[] {
  const sold = soldVariants(product);
  const names = [...product.option_names].sort((a, b) => Number(b === "format") - Number(a === "format"));
  return names
    .map((name) => ({
      name,
      values: [...new Set(sold.map((v) => v.options[name]).filter((x): x is string => !!x))],
    }))
    .filter((g) => g.values.length > 0);
}

/** Where the page starts: what its URL asks for (e.g. ?format=digital from the quiz), else a printed copy. */
export function startVariant(
  product: Pick<CatalogProduct, "variants" | "option_names">,
  query: Record<string, string>,
): CatalogVariant | null {
  const sold = soldVariants(product);
  const wanted = Object.entries(query).filter(([k]) => product.option_names.includes(k));
  const fits = (v: CatalogVariant) => wanted.every(([k, x]) => v.options[k] === x);
  const printed = (v: CatalogVariant) => v.options.format !== "digital";
  return sold.find((v) => fits(v) && printed(v)) ?? sold.find(fits) ?? sold.find(printed) ?? sold[0] ?? null;
}

/** The variant after choosing `value` for `group`: the one that keeps most of the other current choices. */
export function pickVariant(
  product: Pick<CatalogProduct, "variants">,
  current: Record<string, string>,
  group: string,
  value: string,
): CatalogVariant | null {
  const pool = soldVariants(product).filter((v) => v.options[group] === value);
  const kept = (v: CatalogVariant) => Object.entries(current).filter(([k, x]) => k !== group && v.options[k] === x);
  return [...pool].sort((a, b) => kept(b).length - kept(a).length)[0] ?? null;
}
