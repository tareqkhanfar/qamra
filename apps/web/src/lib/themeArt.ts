/**
 * A story's own cover illustration for the catalog when no example book is published yet (owner, 2026-10-09:
 * a story page never shows an empty box). The art is the cover our Magic pipeline drew for an invented sample
 * child, without the title (the page sets the title in code on top of it), exported as WebP to
 * `public/samples/<style>/<theme>-art.webp` (900 px) and `-art-sm.webp` (480 px).
 *
 * Stories with neither an example nor an entry here show the illustrated placeholder (`components/art/Scene`).
 */
export type ThemeArt = {
  style: string; // the catalog `ArtStyle` slug it is drawn in
  src: string; // 900 × 900
  thumb: string; // 480 × 480
};

const art = (style: string, theme: string): ThemeArt => ({
  style,
  src: `/samples/${style}/${theme}-art.webp`,
  thumb: `/samples/${style}/${theme}-art-sm.webp`,
});

export const THEME_ART: Record<string, ThemeArt> = {
  // drawn 2026-10-09 by `scripts/style_samples.py draw` for the invented sample girl (no hijab), one call,
  // $0.08 (`olive:` in out/design-images/ledger.jsonl)
  "olive-season": art("3d", "olive-season"),
};

/** The story's cover illustration, or null (then the placeholder). */
export function themeArt(theme: string | null | undefined): ThemeArt | null {
  return (theme && THEME_ART[theme]) || null;
}
