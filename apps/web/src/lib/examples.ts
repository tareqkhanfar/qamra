/**
 * Public examples (docs/decisions.md): real books made for invented sample children, published by an admin.
 * Pages are web-size, watermarked copies served by the API (same origin, so the CSP allows them).
 */

export type ExampleVariant = "girl" | "girl_hijab" | "boy";
export const VARIANTS: ExampleVariant[] = ["girl", "girl_hijab", "boy"];

export type ExamplePage = {
  beat: number; // 0 = the cover
  layout: "cover" | "full" | "split" | "spread";
  aspect: "1:1" | "3:2" | "16:9";
  text_area: string;
  numbers: number[];
  text: string | null;
  image: string; // ~1280 px
  thumb: string; // ~560 px
};

export type Example = {
  id: string;
  theme: string;
  variant: ExampleVariant;
  lang: "ar" | "en";
  line: "classic" | "magic";
  style: string;
  child_name: string;
  title: string;
  title_name: string;
  title_rest: string;
  dedication: string | null;
  page_count: number;
  cover: string;
  character: string | null;
  pages: ExamplePage[];
  parents: { lesson: string; questions: string[] } | null;
  published_at: string | null;
};

export const RATIO: Record<ExamplePage["aspect"], number> = { "1:1": 1, "3:2": 3 / 2, "16:9": 16 / 9 };

/** The look closest to a child (the wizard knows it; visitors pick it with the switch). */
export function variantOf(child: { gender: "m" | "f"; hijab: boolean }): ExampleVariant {
  if (child.gender === "m") return "boy";
  return child.hijab ? "girl_hijab" : "girl";
}

/** The example to show for a theme: the wanted look when published, else the first one there is. */
export function pickExample(
  examples: Example[] | null | undefined,
  theme: string | null | undefined,
  variant?: ExampleVariant | null,
): Example | null {
  const list = (examples ?? []).filter((e) => !theme || e.theme === theme);
  return list.find((e) => e.variant === variant) ?? list[0] ?? null;
}

/** The story pages (not the cover) a card or a strip can show. */
export function storyPages(example: Example | null, count: number, from = 0): ExamplePage[] {
  const pages = (example?.pages ?? []).filter((p) => p.beat > 0 && p.layout !== "spread");
  return pages.slice(from, from + count);
}

/** The visitor's chosen look, remembered in this browser only (a convenience; never required). */
export const rememberedVariant = {
  key: "qamra-example-variant",
  get(): ExampleVariant | null {
    try {
      const v = localStorage.getItem(this.key);
      return VARIANTS.includes(v as ExampleVariant) ? (v as ExampleVariant) : null;
    } catch {
      return null;
    }
  },
  set(v: ExampleVariant) {
    try {
      localStorage.setItem(this.key, v);
    } catch {
      /* private mode: the switch still works for this page */
    }
  },
};
