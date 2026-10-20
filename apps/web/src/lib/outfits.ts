/**
 * «ماذا يلبس؟» (owner, 2026-10-20): the outfits a character can be drawn in (`GET /api/create/outfits`, from
 * content/outfits.yaml) and their drawn swatches. A swatch is a small SVG figure in the outfit's colours, built
 * here (no AI image, no cost); a girl with a hijab sees it in the hijab colour that goes with the outfit.
 */

export type SwatchShape = "tee" | "shirt" | "hoodie" | "cardigan" | "stripes" | "pinafore" | "dress" | "thobe" | "vest";
export type Swatch = {
  shape: SwatchShape;
  top: string;
  bottom: string;
  shoes: string;
  accent?: string | null;
  pattern?: string | null;
};
export type Outfit = {
  id: string;
  name_ar: string;
  name_en: string;
  lines: string[];
  hijab_color: string | null;
  hijab_trim: string | null;
  looks: Partial<Record<"f" | "m", { swatch: Swatch }>>;
};
export type Outfits = { version: number; default: string; outfits: Outfit[] };

/** The outfits offered to this child on this line, in the file's order (none on Classic: its art is fixed). */
export function outfitsFor(catalog: Outfits | null, gender: "f" | "m", line: string | null): Outfit[] {
  if (!catalog || line === "classic") return [];
  return catalog.outfits.filter((o) => o.looks[gender] && (line === null || o.lines.includes(line)));
}

export function outfitName(catalog: Outfits | null, id: string | null | undefined, locale: string): string | null {
  const o = catalog?.outfits.find((x) => x.id === (id || catalog.default));
  return o ? (locale === "ar" ? o.name_ar : o.name_en) : null;
}

/**
 * The outfit preselected for this child: the one of their last-approved drawing when it is still offered, else
 * the default («الكلاسيكي»).
 */
export function initialOutfit(
  offered: Outfit[],
  fallback: string,
  characters: { approved: boolean; approved_at?: string | null; outfit?: string | null }[],
): string {
  const last = characters
    .filter((c) => c.approved)
    .sort((a, b) => (a.approved_at ?? "").localeCompare(b.approved_at ?? ""))
    .at(-1);
  const wanted = last?.outfit ?? fallback;
  if (offered.some((o) => o.id === wanted)) return wanted;
  return offered.some((o) => o.id === fallback) ? fallback : (offered[0]?.id ?? fallback);
}

const HEX = /^#[0-9a-fA-F]{6}$/;
const INK = "#2A2F4A";
const SKIN = "#E8B98F";
const HAIR = "#3A2A22";

function hex(value: string | null | undefined, fallback: string): string {
  return value && HEX.test(value) ? value : fallback;
}

/** A darker (f < 1) or lighter (f > 1) tone of a colour, for folds and pockets. */
export function shade(color: string, f: number): string {
  const c = hex(color, "#888888");
  const parts = [1, 3, 5].map((i) => {
    const v = parseInt(c.slice(i, i + 2), 16);
    const out = f < 1 ? v * f : v + (255 - v) * (f - 1);
    return Math.max(0, Math.min(255, Math.round(out)))
      .toString(16)
      .padStart(2, "0");
  });
  return `#${parts.join("")}`;
}

const line = (fill: string) => `fill="${fill}" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"`;

/** Sleeves and hands (the hands come after the garment, so they stay on top). */
function sleeves(color: string): string {
  return (
    `<path d="M31 46 L22 58 L19 86 L27 87 L31 64 Z" ${line(color)}/>` +
    `<path d="M69 46 L78 58 L81 86 L73 87 L69 64 Z" ${line(color)}/>`
  );
}
const HANDS = `<circle cx="23" cy="90" r="4.2" ${line(SKIN)}/><circle cx="77" cy="90" r="4.2" ${line(SKIN)}/>`;

function trousers(color: string, top = 80): string {
  return (
    `<path d="M33 ${top} L67 ${top} L66 128 L52.5 128 L50 92 L47.5 128 L34 128 Z" ${line(color)}/>` +
    `<path d="M50 ${top + 4} L50 92" stroke="${shade(color, 0.7)}" stroke-width="1"/>`
  );
}
function leggings(color: string, from: number): string {
  return (
    `<path d="M37 ${from} L48.5 ${from} L48 128 L37.5 128 Z" ${line(color)}/>` +
    `<path d="M51.5 ${from} L63 ${from} L62.5 128 L52 128 Z" ${line(color)}/>`
  );
}
function shoes(color: string): string {
  return (
    `<path d="M33 127 h15 v4 a3 3 0 0 1 -3 3 h-14 a3 3 0 0 1 2 -7 Z" ${line(color)}/>` +
    `<path d="M52 127 h15 a3 3 0 0 1 2 7 h-14 a3 3 0 0 1 -3 -3 Z" ${line(color)}/>`
  );
}
const TORSO = "M31 46 Q50 40 69 46 L68 82 L32 82 Z";

/** The garment itself: everything between the neck and the shoes. */
function garment(s: Swatch): string {
  const top = hex(s.top, "#F1E6CF");
  const bottom = hex(s.bottom, "#26315F");
  const accent = hex(s.accent, "#FFFFFF");
  const pattern = hex(s.pattern, "#FFFFFF");
  switch (s.shape) {
    case "shirt":
      return (
        trousers(bottom) +
        sleeves(top) +
        `<path d="${TORSO}" ${line(top)}/>` +
        `<path d="M32 79 H68" stroke="${shade(bottom, 0.8)}" stroke-width="3"/>` +
        `<path d="M42 44 L50 53 L58 44 L55 42 L50 47 L45 42 Z" ${line(accent)}/>` +
        [57, 64, 71].map((y) => `<circle cx="50" cy="${y}" r="1.3" fill="${INK}"/>`).join("")
      );
    case "hoodie":
      return (
        trousers(bottom) +
        `<path d="M36 44 Q50 54 64 44 Q62 38 50 37 Q38 38 36 44 Z" ${line(shade(top, 0.82))}/>` +
        sleeves(top) +
        `<path d="${TORSO}" ${line(top)}/>` +
        `<path d="M38 66 H62 L59 78 H41 Z" ${line(shade(top, 0.86))}/>` +
        `<path d="M46 47 V56 M54 47 V56" stroke="${shade(top, 1.6)}" stroke-width="1.4" stroke-linecap="round"/>`
      );
    case "cardigan":
      return (
        trousers(bottom) +
        `<path d="M42 44 L58 44 L57 82 L43 82 Z" ${line(accent)}/>` +
        sleeves(top) +
        `<path d="M31 46 Q40 42 44 44 L48 82 L32 82 Z" ${line(top)}/>` +
        `<path d="M69 46 Q60 42 56 44 L52 82 L68 82 Z" ${line(top)}/>` +
        [56, 65, 74].map((y) => `<circle cx="46.5" cy="${y}" r="1.4" ${line(accent)}/>`).join("")
      );
    case "stripes": {
      const bands = [52, 62, 72]
        .map((y) => `<rect x="31.5" y="${y}" width="37" height="5" fill="${accent}"/>`)
        .join("");
      const arms = [56, 68, 80]
        .map(
          (y) =>
            `<path d="M${25 - (y - 56) / 6} ${y} l7 0 l-0.6 4 l-7 0 Z M${75 + (y - 56) / 6} ${y} l-7 0 l0.6 4 l7 0 Z" fill="${accent}"/>`,
        )
        .join("");
      return (
        trousers(bottom) +
        sleeves(top) +
        arms +
        `<path d="${TORSO}" ${line(top)}/>` +
        bands +
        `<path d="${TORSO}" fill="none" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>`
      );
    }
    case "pinafore":
      return (
        leggings(bottom, 100) +
        sleeves(accent) +
        `<path d="${TORSO}" ${line(accent)}/>` +
        `<path d="M40 44 L50 50 L60 44" fill="none" stroke="${INK}" stroke-width="1.2"/>` +
        `<path d="M37 52 H63 L70 108 H30 Z" ${line(top)}/>` +
        [38, 44, 50, 56, 62]
          .map((x) => `<path d="M${x} 53 L${x + (x - 50) * 0.28} 107" stroke="${pattern}" stroke-width="1.2"/>`)
          .join("") +
        `<path d="M37 52 H63 L70 108 H30 Z" fill="none" stroke="${INK}" stroke-width="1.4" stroke-linejoin="round"/>` +
        `<path d="M39 52 L37 44 M61 52 L63 44" stroke="${top}" stroke-width="3.2" stroke-linecap="round"/>`
      );
    case "dress":
      return (
        leggings(bottom, 108) +
        sleeves(top) +
        `<path d="M31 46 Q50 40 69 46 L68 70 L74 114 H26 L32 70 Z" ${line(top)}/>` +
        [
          [40, 58],
          [56, 62],
          [47, 74],
          [62, 84],
          [36, 90],
          [51, 98],
          [42, 108],
          [64, 104],
        ]
          .map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.7" fill="${pattern}"/>`)
          .join("")
      );
    case "thobe": {
      const stitch = (x: number, y: number) =>
        `<path d="M${x - 1.6} ${y - 1.6} l3.2 3.2 m0 -3.2 l-3.2 3.2" stroke="${pattern}" stroke-width="1"/>`;
      const panel = [41, 45, 49, 53, 57].flatMap((x) => [52, 56, 60].map((y) => stitch(x + 1, y))).join("");
      const hem = [30, 35, 40, 45, 50, 55, 60, 65, 70].map((x) => stitch(x, 121)).join("");
      return (
        sleeves(top) +
        `<path d="M22.5 80 L27.5 81 M77.5 80 L72.5 81" stroke="${pattern}" stroke-width="2.4"/>` +
        `<path d="M31 46 Q50 40 69 46 L68 72 L73 126 H27 L32 72 Z" ${line(top)}/>` +
        `<rect x="38" y="48" width="24" height="16" rx="1.5" fill="none" stroke="${pattern}" stroke-width="1.6"/>` +
        panel +
        `<rect x="31.5" y="70" width="37" height="4.5" fill="${pattern}"/>` +
        hem
      );
    }
    case "vest": {
      const edge = (x1: number, y1: number, x2: number, y2: number) =>
        [0, 0.2, 0.4, 0.6, 0.8, 1]
          .map((t) => {
            const x = x1 + (x2 - x1) * t;
            const y = y1 + (y2 - y1) * t;
            return `<path d="M${x - 1.5} ${y - 1.5} l3 3 m0 -3 l-3 3" stroke="${pattern}" stroke-width="1"/>`;
          })
          .join("");
      return (
        trousers(bottom) +
        sleeves(accent) +
        `<path d="${TORSO}" ${line(accent)}/>` +
        `<path d="M31 46 Q38 43 43 45 L47 82 L32 82 Z" ${line(top)}/>` +
        `<path d="M69 46 Q62 43 57 45 L53 82 L68 82 Z" ${line(top)}/>` +
        edge(41, 49, 44, 78) +
        edge(59, 49, 56, 78)
      );
    }
    case "tee":
    default:
      return (
        trousers(bottom) +
        sleeves(top) +
        `<path d="${TORSO}" ${line(top)}/>` +
        `<path d="M43 44 Q50 50 57 44" fill="none" stroke="${INK}" stroke-width="1.2"/>`
      );
  }
}

/** The head: a girl's hijab in the outfit's hijab colour, else short (boys) or shoulder-length (girls) hair. */
function head(gender: "f" | "m", hijab: { color: string; trim: string | null } | null): string {
  const face =
    `<circle cx="44.5" cy="27" r="1.5" fill="${INK}"/><circle cx="55.5" cy="27" r="1.5" fill="${INK}"/>` +
    `<path d="M45 33 Q50 37 55 33" fill="none" stroke="${INK}" stroke-width="1.4" stroke-linecap="round"/>` +
    `<circle cx="41" cy="31.5" r="2.2" fill="#E99A8A" opacity="0.55"/><circle cx="59" cy="31.5" r="2.2" fill="#E99A8A" opacity="0.55"/>`;
  if (hijab) {
    const trim = hijab.trim
      ? `<ellipse cx="50" cy="28" rx="12.6" ry="14.2" fill="none" stroke="${hijab.trim}" stroke-width="1.6"/>`
      : "";
    return (
      `<path d="M50 6 C66 6 70 20 69 32 C69 40 66 45 72 52 Q50 58 28 52 C34 45 31 40 31 32 C30 20 34 6 50 6 Z" ${line(hijab.color)}/>` +
      `<ellipse cx="50" cy="28" rx="11.5" ry="13" ${line(SKIN)}/>` +
      trim +
      face
    );
  }
  const neck = `<rect x="46" y="36" width="8" height="8" fill="${SKIN}"/>`;
  const hair =
    gender === "f"
      ? `<path d="M34 28 C32 10 68 10 66 28 L67 46 Q61 48 59 42 L58 22 Q50 18 42 22 L41 42 Q39 48 33 46 Z" ${line(HAIR)}/>`
      : "";
  const fringe =
    gender === "f"
      ? `<path d="M36 24 C38 12 62 12 64 24 Q56 18 50 21 Q44 18 36 24 Z" fill="${HAIR}"/>`
      : `<path d="M35.5 25 C35 11 65 11 64.5 25 Q60 17 52 19 Q44 16 35.5 25 Z" ${line(HAIR)}/>`;
  return neck + hair + `<circle cx="50" cy="27" r="14" ${line(SKIN)}/>` + fringe + face;
}

/** The swatch: a child's figure in the outfit, as an SVG document (100 × 140). */
export function outfitSvg(outfit: Outfit, gender: "f" | "m", hijab: boolean): string {
  const look = outfit.looks[gender] ?? Object.values(outfit.looks)[0];
  const swatch: Swatch = look?.swatch ?? { shape: "tee", top: "#F1E6CF", bottom: "#26315F", shoes: "#7A5234" };
  const scarf =
    hijab && gender === "f"
      ? { color: hex(outfit.hijab_color, "#A7BC9C"), trim: outfit.hijab_trim ? hex(outfit.hijab_trim, INK) : null }
      : null;
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 140" width="100" height="140">` +
    `<ellipse cx="50" cy="133" rx="24" ry="3.5" fill="${INK}" opacity="0.12"/>` +
    garment(swatch) +
    shoes(hex(swatch.shoes, "#7A5234")) +
    HANDS +
    head(gender, scarf) +
    `</svg>`
  );
}

/** The swatch as an image source (an `<img>` needs no inner HTML). */
export function outfitSrc(outfit: Outfit, gender: "f" | "m", hijab: boolean): string {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(outfitSvg(outfit, gender, hijab))}`;
}
