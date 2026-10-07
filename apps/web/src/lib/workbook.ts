/**
 * Activity-book product page (Addendum 9, WorkbookProduct): one template for «دوسية التأسيس», «رحلتي الأولى
 * للتعلّم», «مغامراتي مع عائلتي» and «قلبي يعرف الله». Option groups come from the product's variants (never
 * hard-coded); the pages shown come from scripts/export_workbook_previews.py, per part the store sells.
 */
import type { CatalogProduct, CatalogVariant } from "@/lib/store";
import previews from "./workbook-previews.json";

/** One exported page: the 720 px image (`src`), its 360 px copy (`sm`), its size and its captions. */
export type Preview = { src: string; sm?: string; w?: number; h?: number; title_ar: string; title_en: string };
/** A part the store sells (a level's volume, a stage, a volume, the family book): its cover and chosen pages. */
export type Part = { key: string; cover: Preview; pages: Preview[] };
type ProductPreviews = { default: string; scopes: Record<string, { cover: Preview; pages: Preview[] }> };

export const SHOWCASE = previews as Record<string, ProductPreviews>;

/** Product → [cover, …pages] of the part it shows first (cards, link previews, JSON-LD). */
export const PREVIEWS: Record<string, Preview[]> = Object.fromEntries(
  Object.entries(SHOWCASE).map(([slug, p]) => {
    const first = p.scopes[p.default] ?? Object.values(p.scopes)[0];
    return [slug, first ? [first.cover, ...first.pages] : []];
  }),
);

/** «قلبي يعرف الله»'s sets and the volumes in each (content/store/catalog.yaml). */
const ISLAMIC_SETS: Record<string, string[]> = {
  L1: ["V1", "V2"],
  L2: ["V3", "V4", "V5"],
  set: ["V1", "V2", "V3", "V4", "V5"],
};

/**
 * The keys of the parts the picks show (the export's scope keys): «دوسية التأسيس» `kg1-2` (level-volume), a
 * stage `2`, a volume `V3`, the family book `book`; a set gives all of its parts. A part the export doesn't have
 * is dropped, and nothing left falls back to the product's first part.
 */
export function partKeys(slug: string, line: string, picks: Picks): string[] {
  const own = SHOWCASE[slug];
  if (!own) return [];
  let keys: string[] = [];
  if (line === "workbook") {
    const level = picks.level ?? own.default.split("-")[0]!;
    const volume = picks.volume ?? "1";
    keys = volume === "set" ? ["1", "2", "3"].map((v) => `${level}-${v}`) : [`${level}-${volume}`];
  } else if (line === "journey") {
    keys = picks.stage === "set" ? ["1", "2", "3"] : [picks.stage ?? own.default];
  } else if (line === "islamic") {
    const volume = picks.volume ?? own.default;
    keys = ISLAMIC_SETS[volume] ?? [volume];
  } else {
    keys = [own.default];
  }
  const known = keys.filter((k) => own.scopes[k]);
  return known.length ? known : [own.default].filter((k) => own.scopes[k]);
}

/** The parts the picks show, each with its cover and pages (several for a set). */
export function partsFor(slug: string, line: string, picks: Picks): Part[] {
  const own = SHOWCASE[slug];
  return own ? partKeys(slug, line, picks).map((key) => ({ key, ...own.scopes[key]! })) : [];
}

/** Whether an option value is a set (all three, «المستوى الأول», the five volumes) rather than one book. */
export const isSetValue = (value: string) => value === "set" || value in ISLAMIC_SETS;

/** Whether the picks are a set (several volumes or stages in one order). */
export function isSet(picks: Picks): boolean {
  return Object.values(picks).some(isSetValue);
}

/**
 * A few inside pages for the product's card (the hub): from parts spread over what the store sells (KG1 and
 * KG2, stages 1–3, volumes 1, 3 and 5), a different kind of page from each.
 */
export function samplePages(product: CatalogProduct, count = 3): Preview[] {
  const own = SHOWCASE[product.slug];
  if (!own) return [];
  const sold = soldOptions(product);
  const line: string = product.line; // the catalog's lines include «قلبي يعرف الله» (islamic)
  const isSold = (key: string) => {
    if (line === "workbook") {
      const [level, volume] = key.split("-");
      return (sold.level ?? [level]).includes(level!) && (sold.volume ?? [volume]).includes(volume!);
    }
    if (line === "journey") return (sold.stage ?? [key]).includes(key);
    if (line === "islamic") return (sold.volume ?? [key]).includes(key);
    return true;
  };
  const keys = Object.keys(own.scopes).filter(isSold);
  if (!keys.length) return [];
  const out: Preview[] = [];
  for (let i = 0; i < count; i++) {
    const part = own.scopes[keys[Math.floor((i * keys.length) / count)]!]!;
    // «قلبي يعرف الله»: each volume's first page is its illustrated unit opener; elsewhere a different kind each
    const page = part.pages[line === "islamic" ? 0 : i % Math.max(part.pages.length, 1)];
    if (page && !out.includes(page)) out.push(page);
  }
  return out;
}

/** The design's order of the choices; anything else a product adds comes after. */
const ORDER = ["level", "stage", "volume", "format", "interior"];

export type Picks = Record<string, string>;
export type Group = { name: string; values: { value: string; available: boolean }[] };

function fits(v: CatalogVariant, picks: Picks, skip?: string): boolean {
  return Object.entries(picks).every(([k, x]) => k === skip || v.options[k] === x);
}

/**
 * The option groups in the design's order; a value is available if some variant has it with the other picks.
 * Only variants the catalog sells are listed (the API omits inactive ones), so a level, volume or stage that
 * doesn't exist yet is simply absent; a group with one value still shows, as one selected chip.
 */
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
    .filter((g) => g.values.length > 0);
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

/**
 * Start from what the page's URL asks for (e.g. ?level=kg2 from the quiz), else a printed single copy. A pick the
 * store doesn't sell (an old link to a volume or stage that isn't listed) is ignored.
 */
export function initialPicks(product: CatalogProduct, query: Picks): Picks {
  const priced = product.variants.filter((v) => v.price !== null);
  const wanted = Object.fromEntries(Object.entries(query).filter(([k]) => product.option_names.includes(k)));
  const printed = (picks: Picks) =>
    priced.find(
      (v) =>
        fits(v, picks) &&
        v.options.format !== "digital" &&
        !Object.values(v.options).includes("set") &&
        (v.options.interior ?? "color") === "color",
    );
  const start = printed(wanted) ?? priced.find((v) => fits(v, wanted)) ?? printed({}) ?? priced[0];
  return start ? { ...start.options } : {};
}

/** The values each option group sells now, in the catalog's order (e.g. volume → ["1", "2"]). */
export function soldOptions(product: CatalogProduct): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const v of product.variants.filter((x) => x.price !== null)) {
    for (const [k, x] of Object.entries(v.options)) {
      const list = (out[k] ??= []);
      if (!list.includes(x)) list.push(x);
    }
  }
  return out;
}

/** The school levels and the ages they are for (the foundation workbook sells by level). */
const LEVEL_AGES: Record<string, [number, number]> = { kg1: [4, 5], kg2: [5, 6] };

/** The ages the levels sold now cover, as [min, max]; null when the product has no levels (use its fixed ages). */
export function soldAges(product: CatalogProduct): [number, number] | null {
  const ranges = (soldOptions(product).level ?? []).map((l) => LEVEL_AGES[l]).filter((r): r is [number, number] => !!r);
  if (!ranges.length) return null;
  return [Math.min(...ranges.map((r) => r[0])), Math.max(...ranges.map((r) => r[1]))];
}
