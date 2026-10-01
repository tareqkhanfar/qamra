/** A theme's book title for one child, as the API fills it (qamra_ai.pipeline.theme.fill_title). */

const VARIANT = /\{([^{}/]+)\/([^{}/]+)\}/g;

export type TitleGender = "m" | "f" | null;

/**
 * `{masc/fem}` by the child's gender, then `{name}`: "{name} {حارس/حارسة} النجوم" → "سلمى حارسة النجوم".
 * With no gender yet both forms stay («حارس/حارسة»), so the title never shows a brace.
 */
export function fillTitle(template: string, name: string, gender: TitleGender): string {
  return template
    .replace(VARIANT, (_, m: string, f: string) => (gender === null ? `${m}/${f}` : gender === "m" ? m : f))
    .replaceAll("{name}", name)
    .trim();
}
