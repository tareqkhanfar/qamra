/**
 * «قمرة كلاسيك» availability (Addendum 4 §1A): a Classic book needs a live template for its story, art style and
 * the child's look. The themes API lists them per theme as `classic: { [style]: variants[] }`.
 */

export type ClassicVariant = "girl" | "girl_hijab" | "boy";
export type ClassicAvailability = Record<string, string[]>;

/** The template look for a child: boys, girls, and girls who wear a hijab. */
export function classicVariant(child: { gender: "m" | "f"; hijab: boolean }): ClassicVariant {
  if (child.gender === "m") return "boy";
  return child.hijab ? "girl_hijab" : "girl";
}

/** The art styles with a live Classic template for this look (in one theme, or in any theme). */
export function classicStyles(
  themes: { slug: string; classic?: ClassicAvailability }[],
  variant: ClassicVariant,
  theme?: string | null,
): Set<string> {
  const styles = new Set<string>();
  for (const th of themes) {
    if (theme && th.slug !== theme) continue;
    for (const [style, variants] of Object.entries(th.classic ?? {})) {
      if (variants.includes(variant)) styles.add(style);
    }
  }
  return styles;
}

/** Whether a Classic book can be made for this theme, style and look. */
export function classicAvailable(
  theme: { classic?: ClassicAvailability } | null | undefined,
  style: string,
  variant: ClassicVariant,
): boolean {
  return !!theme?.classic?.[style]?.includes(variant);
}
