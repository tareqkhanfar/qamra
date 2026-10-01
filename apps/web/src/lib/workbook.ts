/**
 * Activity-book product page (Addendum 9, WorkbookProduct): one template for «دوسية التأسيس», «رحلتي الأولى
 * للتعلّم» and «مغامراتي مع عائلتي». Option groups come from the product's variants (never hard-coded).
 */
import type { CatalogProduct, CatalogVariant } from "@/lib/store";
import previews from "./workbook-previews.json";

export type Preview = { src: string; title_ar: string; title_en: string };
export const PREVIEWS = previews as Record<string, Preview[]>;

/** What a strip of preview pages comes from, e.g. {level: "kg2", volume: "3"} or {stage: "2"}; {} = the product. */
export type PreviewScope = Partial<Record<"level" | "volume" | "stage", string>>;
type PreviewSet = { pages: Preview[]; scope: PreviewScope };

/** «رحلتي الأولى»'s strip is one list; every caption starts with its stage («المحطة 2: …», "Stage 2: …"). */
const STAGE = /^(?:المحطة|Stage) (\d+): /;

function stagePages(pages: Preview[], stage: string): Preview[] {
  return pages
    .filter((p) => STAGE.exec(p.title_en)?.[1] === stage)
    .map((p) => {
      const en = p.title_en.replace(STAGE, "");
      return { ...p, title_ar: p.title_ar.replace(STAGE, ""), title_en: en.charAt(0).toUpperCase() + en.slice(1) };
    });
}

/** The preview sets of a product, one per level, volume or stage they show (in the catalog's order). */
function previewSets(slug: string): PreviewSet[] {
  const own = PREVIEWS[slug] ?? [];
  if (slug === "foundation-workbook") {
    return [
      { pages: PREVIEWS["foundation-workbook-kg1"] ?? [], scope: { level: "kg1" } },
      { pages: own, scope: { level: "kg2" } }, // drawn from KG2 volume 1, standing in for volumes 1 and 2
      { pages: PREVIEWS["foundation-workbook-v3"] ?? [], scope: { level: "kg2", volume: "3" } },
    ].filter((s) => s.pages.length > 0);
  }
  if (slug === "learning-journey") {
    const stages = [...new Set(own.map((p) => STAGE.exec(p.title_en)?.[1]).filter((x): x is string => !!x))];
    return stages.map((stage) => ({ pages: stagePages(own, stage), scope: { stage } }));
  }
  return own.length ? [{ pages: own, scope: {} }] : [];
}

/**
 * The preview pages for the reader's picks: the chosen level's, volume's or stage's when there are pages of
 * it, else the product's own set. A set ("all three") shows the pages of every part of it.
 */
export function previewsFor(slug: string, picks: Picks): { pages: Preview[]; scope: PreviewScope } {
  const fallback = { pages: PREVIEWS[slug] ?? [], scope: {} };
  const sets = previewSets(slug);
  if (slug === "learning-journey") {
    if (picks.stage === "set") return { ...fallback, scope: { stage: "set" } }; // every stage, captions keep theirs
    if (!picks.stage) return fallback;
    return sets.find((s) => s.scope.stage === picks.stage) ?? fallback;
  }
  if (slug === "foundation-workbook" && picks.level) {
    const level = sets.filter((s) => s.scope.level === picks.level);
    if (picks.volume === "set" && level.length > 1) {
      return { pages: level.flatMap((s) => s.pages), scope: { level: picks.level } };
    }
    const exact = level.find((s) => s.scope.volume === picks.volume) ?? level.find((s) => !s.scope.volume);
    if (exact) return exact;
  }
  return fallback;
}

/** A few inside pages for the product's card (the hub): one from each level, volume or stage it sells. */
export function samplePages(product: CatalogProduct, count = 3): Preview[] {
  const sold = soldOptions(product);
  const sets = previewSets(product.slug).filter(({ scope }) =>
    (["level", "stage"] as const).every((k) => !scope[k] || !sold[k] || sold[k].includes(scope[k])),
  );
  const out: Preview[] = [];
  for (let i = 1; out.length < count && sets.some((s) => s.pages.length > i); i++) {
    for (const s of sets) if (s.pages[i] && out.length < count) out.push(s.pages[i]!);
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
