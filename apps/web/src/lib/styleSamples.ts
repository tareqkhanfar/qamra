/**
 * Real example pages per art style (Tareq, 2026-10-07: «لازم المستخدم يشوف كيف الكتاب مع طبيعة الرسم»).
 *
 * Every picture is a page of a real book made by our pipeline for an invented sample child, laid out with
 * the theme's own text and the current page designs, exported to `public/samples/<style>/` as WebP
 * (`<id>.webp` 900 px for the lightbox, `<id>-sm.webp` 480 px for carousels) by `scripts/style_samples.py`.
 * Static on purpose: the store, the story pages and the order wizard can show them with no API call.
 *
 *   samplesForStyle("3d")                    → every 3D sample, the stories mixed, covers first
 *   samplesForStyle("3d", "first-day")       → this story's own pages first, then other stories in 3D
 *   samplesForStyle("3d", "first-day", { strict: true }) → only this story's own pages
 *
 * A sample whose `theme` differs from the one asked for must be labelled with its own story.
 *
 * The activity books' style step (owner, 2026-10-09) also shows, per style, the same invented child's character
 * sheet and the «دوسية التأسيس» cover and «هذا الكتاب لـ…» page with her cut-out: `samplesForStyle(style, null,
 * { activity: true })`. Those two kinds never appear with the story books' pages.
 */
import type { ExampleVariant } from "@/lib/examples";

/** The styles the books sell (catalog `ArtStyle` slugs, Addendum 11 §1; «شبه حقيقي» since 2026-10-09). */
export type SampleStyle = "3d" | "watercolor" | "cartoon" | "semi-realistic";
export const SAMPLE_STYLES: SampleStyle[] = ["3d", "watercolor", "cartoon", "semi-realistic"];

/**
 * `character`: the sample child's character sheet; `activity`: an activity-book page with her cut-out (the cover,
 * the owner page). Both are shown only for the activity books, contained in their tile (not square).
 */
export type SampleKind = "cover" | "page" | "companion" | "character" | "activity";

export type StyleSample = {
  id: string; // "<style>/<name>", unique
  style: SampleStyle;
  /** The story (theme slug); null for the companion's sheet, which belongs to every story. */
  theme: string | null;
  kind: SampleKind;
  /** The sample child's look, to put the closest one first (null: no child in the picture). */
  look: ExampleVariant | null;
  /** The same moment drawn in another style has the same scene (e.g. "graduation-stage"). */
  scene: string;
  src: string; // 900 px on the long side (900 × 900 for book pages)
  thumb: string; // 480 px on the long side
  width: number;
  height: number;
  alt_ar: string;
  alt_en: string;
};

type Row = [name: string, theme: string | null, kind: SampleKind, look: ExampleVariant | null, ar: string, en: string];

const STYLE_NAME: Record<SampleStyle, { ar: string; en: string }> = {
  "3d": { ar: "أسلوب سينمائي ثلاثي الأبعاد", en: "cinematic 3D style" },
  watercolor: { ar: "أسلوب مائي فاخر", en: "premium watercolor style" },
  cartoon: { ar: "أسلوب كرتون ملوّن", en: "bright 2D cartoon style" },
  "semi-realistic": { ar: "أسلوب شبه حقيقي", en: "semi-realistic style" },
};

/** The size of a sample's large file (`src`): book pages are square, the rest keep their own shape. */
const SIZE: Record<SampleKind, [number, number]> = {
  cover: [900, 900],
  page: [900, 900],
  companion: [900, 900],
  character: [900, 604], // a 3:2 sheet: front, waving, walking
  activity: [637, 900], // an A4 page
};

/** The «يوم تخرّجي» proof exists in both 3D and watercolor: the same pages, the same order. */
const GRADUATION: Row[] = [
  [
    "graduation-cover",
    "graduation",
    "cover",
    "girl_hijab",
    "غلاف «يوم تخرّج ليان»",
    "Cover of “Layan’s Graduation Day”",
  ],
  [
    "graduation-mirror",
    "graduation",
    "page",
    "girl_hijab",
    "ليان أمام المرآة بثوب التخرّج",
    "Layan in front of the mirror in her graduation gown",
  ],
  [
    "graduation-teacher",
    "graduation",
    "page",
    "girl_hijab",
    "المعلّمة تصفّق لمحاولة ليان",
    "The teacher claps for Layan’s effort",
  ],
  [
    "graduation-stage",
    "graduation",
    "page",
    "girl_hijab",
    "ليان ترفع شهادتها عاليًا على المسرح",
    "Layan holds her certificate up high on stage",
  ],
  [
    "graduation-caps",
    "graduation",
    "page",
    "girl_hijab",
    "الأطفال يرمون قبّعاتهم في الهواء فرحًا",
    "The children throw their caps into the air for joy",
  ],
  [
    "graduation-sunset",
    "graduation",
    "page",
    "girl_hijab",
    "طريق العودة إلى البيت عند الغروب",
    "The walk home at sunset",
  ],
];

const COMPANION: Row = [
  "companion",
  null,
  "companion",
  null,
  "قَمّور، صاحب البطل، من عدّة زوايا",
  "Qamour, the hero’s companion, from several angles",
];

/** «آدم في أوّل يوم بالروضة»: drawn in every style for the same sample boy, the same scenes. */
const FIRST_DAY_ADAM = {
  cover: [
    "first-day-cover",
    "first-day",
    "cover",
    "boy",
    "غلاف «آدم في أوّل يوم بالروضة»",
    "Cover of “Adam’s First Day at Kindergarten”",
  ],
  gate: [
    "first-day-gate",
    "first-day",
    "page",
    "boy",
    "آدم عند بوّابة الروضة وصاحبه الصغير يطمئنه",
    "Adam at the kindergarten gate, his little companion reassuring him",
  ],
  blocks: [
    "first-day-blocks",
    "first-day",
    "page",
    "boy",
    "آدم وصديقان جديدان يبنون برجًا من المكعّبات",
    "Adam and two new friends build a tower of blocks",
  ],
  yard: [
    "first-day-yard",
    "first-day",
    "page",
    "boy",
    "آدم يركض في ساحة الروضة كالريح",
    "Adam runs across the kindergarten yard like the wind",
  ],
} satisfies Record<string, Row>;

/** «تالا وضيفنا الصغير»: the same sample girl (no hijab) and scenes in every style. */
const SIBLING_TALA = {
  cover: [
    "new-sibling-cover",
    "new-sibling",
    "cover",
    "girl",
    "غلاف «تالا وضيفنا الصغير»",
    "Cover of “Tala and Our Little Guest”",
  ],
  news: [
    "new-sibling-news",
    "new-sibling",
    "page",
    "girl",
    "تالا تقفز فرحًا بالخبر السعيد",
    "Tala jumps for joy at the happy news",
  ],
  bassinet: [
    "new-sibling-bassinet",
    "new-sibling",
    "page",
    "girl",
    "تالا تهمس للمولود: «مرحبًا يا ضيفنا الصغير»",
    "Tala whispers to the newborn: “Welcome, our little guest”",
  ],
  hug: [
    "new-sibling-hug",
    "new-sibling",
    "page",
    "girl",
    "ماما تضمّ تالا وتقول: «أنتِ بطلتي الكبيرة!»",
    "Mama hugs Tala and says, “You’re my big hero!”",
  ],
  smile: [
    "new-sibling-smile",
    "new-sibling",
    "page",
    "girl",
    "المولود يبتسم لتالا أوّل مرّة",
    "The baby smiles at Tala for the first time",
  ],
} satisfies Record<string, Row>;

/** تالا’s character sheet in each style (the same invented child as the new-sibling pages). */
const CHARACTER: Row = [
  "character",
  null,
  "character",
  "girl",
  "شخصية تالا في ثلاث رسمات: واقفةً، وتلوّح بيدها، وتمشي",
  "Tala’s character in three poses: standing, waving and walking",
];

/** «دوسية التأسيس» (KG1, part one) for تالا: the cover and the owner page, with her character cut out. */
const ACTIVITY: Row[] = [
  [
    "activity-cover",
    null,
    "activity",
    "girl",
    "غلاف «دوسية التأسيس» وعليه شخصية تالا",
    "Cover of the Foundation workbook, with Tala’s character",
  ],
  [
    "activity-owner",
    null,
    "activity",
    "girl",
    "صفحة «هذا الكتاب لـ…» وعليها شخصية تالا",
    "The “This book belongs to…” page with Tala’s character",
  ],
];

const ROWS: Record<SampleStyle, Row[]> = {
  // A story without a hijab comes first in every style: it gives the style its swatch (owner, 2026-10-09: little
  // girls in the sample imagery without a hijab). The 3D new-sibling cover is missing: both tries drew a parent's
  // arm with no one attached to it.
  "3d": [
    FIRST_DAY_ADAM.cover,
    FIRST_DAY_ADAM.blocks,
    FIRST_DAY_ADAM.yard,
    SIBLING_TALA.bassinet,
    SIBLING_TALA.smile,
    ...GRADUATION.slice(0, 2),
    [
      "graduation-album",
      "graduation",
      "page",
      "girl_hijab",
      "ليان تتصفّح ألبوم صور الروضة",
      "Layan looks through the kindergarten photo album",
    ],
    ...GRADUATION.slice(2),
    COMPANION,
    CHARACTER,
    ...ACTIVITY,
  ],
  watercolor: [
    FIRST_DAY_ADAM.cover,
    FIRST_DAY_ADAM.gate,
    FIRST_DAY_ADAM.blocks,
    FIRST_DAY_ADAM.yard,
    [
      "first-day-cover-girl",
      "first-day",
      "cover",
      "girl",
      "غلاف «ليلى في أوّل يوم بالروضة»",
      "Cover of “Layla’s First Day at Kindergarten”",
    ],
    [
      "first-day-walk",
      "first-day",
      "page",
      "girl",
      "ليلى في الطريق إلى الروضة تعدّ أشجار الزيتون",
      "Layla on the way to kindergarten, counting the olive trees",
    ],
    [
      "first-day-easel",
      "first-day",
      "page",
      "girl",
      "ليلى ترسم قمرًا أصفر كبيرًا في ركن الرسم",
      "Layla paints a big yellow moon in the art corner",
    ],
    SIBLING_TALA.cover,
    SIBLING_TALA.news,
    SIBLING_TALA.bassinet,
    SIBLING_TALA.hug,
    SIBLING_TALA.smile,
    ...GRADUATION,
    COMPANION,
    CHARACTER, // no activity pages: this sheet's paper grain defeats the cut-out (scripts/style_samples.py)
  ],
  cartoon: [
    FIRST_DAY_ADAM.cover,
    FIRST_DAY_ADAM.blocks,
    FIRST_DAY_ADAM.yard,
    SIBLING_TALA.cover,
    SIBLING_TALA.bassinet,
    SIBLING_TALA.smile,
    COMPANION,
    CHARACTER,
    ...ACTIVITY,
  ],
  // drawn 2026-10-09 (`semireal:` rows in the ledger); the bassinet and news pages were rejected (the baby under
  // the text box; the companion drawn twice), so the story has its cover and one page so far
  "semi-realistic": [SIBLING_TALA.cover, SIBLING_TALA.smile, CHARACTER, ...ACTIVITY],
};

export const STYLE_SAMPLES: StyleSample[] = SAMPLE_STYLES.flatMap((style) =>
  ROWS[style].map(([name, theme, kind, look, ar, en]) => ({
    id: `${style}/${name}`,
    style,
    theme,
    kind,
    look,
    scene: name,
    src: `/samples/${style}/${name}.webp`,
    thumb: `/samples/${style}/${name}-sm.webp`,
    width: SIZE[kind][0],
    height: SIZE[kind][1],
    alt_ar: `${ar} (${STYLE_NAME[style].ar})`,
    alt_en: `${en} (${STYLE_NAME[style].en})`,
  })),
);

export function isSampleStyle(style: string | null | undefined): style is SampleStyle {
  return SAMPLE_STYLES.includes(style as SampleStyle);
}

/** Covers, then pages in story order, the asked look first; stories taken in turns so none crowds out. */
function interleave(list: StyleSample[], look?: ExampleVariant | null): StyleSample[] {
  const lookFirst = (a: StyleSample, b: StyleSample) => Number(b.look === look) - Number(a.look === look);
  const byTheme = new Map<string, StyleSample[]>();
  for (const s of list) byTheme.set(s.theme ?? "", [...(byTheme.get(s.theme ?? "") ?? []), s]);
  const queues = [...byTheme.values()].map((q) =>
    [...q].sort((a, b) => (look ? lookFirst(a, b) : 0) || Number(b.kind === "cover") - Number(a.kind === "cover")),
  );
  const out: StyleSample[] = [];
  for (let i = 0; queues.some((q) => i < q.length); i++) for (const q of queues) if (q[i]) out.push(q[i]);
  return out;
}

/** The kinds that are pictures of a story book (the rest: the companion's sheet and the activity-only kinds). */
const BOOK_KINDS: readonly SampleKind[] = ["cover", "page"];

/**
 * The example pages of a style. With a story: its own pages first (cover first), then the other stories'
 * pages in the same style, unless `strict`. The companion's sheet always comes last (never with `strict`).
 * `activity`: for an activity book, the activity pages with the cut-out first, then the character sheet, then
 * the story pages (no companion: activity books have none); `theme` and `strict` are ignored.
 */
export function samplesForStyle(
  style: string,
  theme?: string | null,
  options: { look?: ExampleVariant | null; limit?: number; strict?: boolean; activity?: boolean } = {},
): StyleSample[] {
  if (!isSampleStyle(style)) return [];
  const all = STYLE_SAMPLES.filter((s) => s.style === style);
  const books = all.filter((s) => BOOK_KINDS.includes(s.kind));
  if (options.activity) {
    const own = [...all.filter((s) => s.kind === "activity"), ...all.filter((s) => s.kind === "character")];
    const list = [...own, ...interleave(books, options.look)];
    return options.limit ? list.slice(0, options.limit) : list;
  }
  const own = theme
    ? interleave(
        books.filter((s) => s.theme === theme),
        options.look,
      )
    : [];
  const rest = interleave(
    books.filter((s) => !theme || s.theme !== theme),
    options.look,
  );
  const extras = options.strict ? [] : all.filter((s) => s.kind === "companion");
  const list = theme ? (options.strict ? own : [...own, ...rest, ...extras]) : [...rest, ...extras];
  return options.limit ? list.slice(0, options.limit) : list;
}

/**
 * The one picture that stands for a style (a swatch): this story's cover in it, else any cover; with
 * `prefer: "page"` a story page instead (a wide crop of a cover cuts through its title); with
 * `prefer: "character"` the sample child's character sheet (the activity books' style step), else a cover.
 */
export function styleThumb(
  style: string,
  theme?: string | null,
  look?: ExampleVariant | null,
  prefer: "cover" | "page" | "character" = "cover",
): StyleSample | null {
  if (prefer === "character") {
    const list = samplesForStyle(style, null, { look, activity: true });
    return list.find((s) => s.kind === "character") ?? list.find((s) => s.kind === "cover") ?? list[0] ?? null;
  }
  const list = samplesForStyle(style, theme, { look });
  return list.find((s) => s.kind === prefer) ?? list[0] ?? null;
}

/** Whether a sample is shown whole in its tile (sheets and A4 pages), not cropped to a square. */
export const containedSample = (s: StyleSample) => !BOOK_KINDS.includes(s.kind);

/** How many real book pages (not the companion's sheet) a style has, for one story or for all. */
export function bookSampleCount(style: string, theme?: string | null): number {
  return samplesForStyle(style, theme, { strict: !!theme }).filter((s) => s.kind !== "companion").length;
}

export const sampleAlt = (s: StyleSample, locale: string) => (locale === "ar" ? s.alt_ar : s.alt_en);
