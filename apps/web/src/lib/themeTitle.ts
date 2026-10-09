/** A theme's book title for one child, as the API fills it (qamra_ai.pipeline.theme.fill_title). */

import { fillName } from "./arabicName.ts";

const VARIANT = /\{([^{}/]+)\/([^{}/]+)\}/g;

export type TitleGender = "m" | "f" | null;

/**
 * `{masc/fem}` by the child's gender, then the name in its case (`fillName`): "{name} {حارس/حارسة} النجوم" →
 * "سلمى حارسة النجوم", "يوم تخرّج {name:gen}" → "يوم تخرّج أبي بكر". With no gender yet both forms stay
 * («حارس/حارسة»), so the title never shows a brace.
 */
export function fillTitle(template: string, name: string, gender: TitleGender): string {
  const text = template.replace(VARIANT, (_, m: string, f: string) =>
    gender === null ? `${m}/${f}` : gender === "m" ? m : f,
  );
  return fillName(text, "name", name).trim();
}
