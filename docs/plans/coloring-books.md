# «دفاتر التلوين والرسم» — coloring books and the sketchbook (2026-10-21)

The owner's request: new, profitable, low-cost products designed by us. Four fixed-content books, personalized
only on the cover (the child's name, and their character when the family already has one) plus the title page
and «عن قمرة» with the book code. A new store line `colorbook` and a new site section `/coloring`.

| Book | Store slug | Pages | Binding | Content |
| --- | --- | --- | --- | --- |
| «أُلَوِّنُ حُروفي» | `coloring-letters` | 32 | stapled | title, «اسْمي», 28 letters, «أَحْسَنْتَ!», «عن قمرة» |
| «أُلَوِّنُ فِلَسْطين» | `coloring-palestine` | 28 | stapled | title, 25 scenes, a free drawing page, «عن قمرة» |
| «أُلَوِّنُ رَمَضان» | `coloring-ramadan` | 24 | stapled | title, 21 scenes, a free drawing page, «عن قمرة» |
| «دَفْتَري» | `sketchbook` | 48 | wire-o | title, 46 drawing pages (blank framed, prompts, finish-the-drawing, date/age, favourite), «عن قمرة» |

All A4 portrait (210 × 297 mm, 3 mm bleed), interior **black only** (K) on 160 g uncoated paper (pencils,
coloured pencils and crayons; felt pens may show through a little), card cover in colour. Page counts are multiples of 4
(a saddle-stitched book is folded sheets of four pages; the wire-o sketchbook keeps whole sheets too); the
preflight checks it (`signature=4`).

## How the art is made: drawn in code, $0

The owner: «بدون AI، يعني إذا بتقدر ترسم رسومات». Every drawing is SVG built in code, in millimetres at print
size (`packages/workbook/src/qamra_workbook/coloring/`):

- `ink.py` — the kit: a `Pen` that keeps the printed line widths whatever the scale (outlines 2.6 mm, inner
  lines 2.0 mm, rounded joins and caps), `place()` to compose parts, shape helpers. The same drawing prints as
  line art (white areas, pure black lines) on the pages and painted (`mode="color"`) on the covers and the web.
- `parts/` — reusable parts: `common.py` (sky, ground, plants, friendly people), `palestine.py`,
  `heritage.py` (tatreez and keffiyeh patterns generated geometrically), `ramadan.py`, `qamra.py` (the moon
  friend, crayons, the medal).
- `scenes/` — one function per page of the scene books (`@scene("palestine", "olive-harvest")`).
- `letters.py` + `glyphs.py` — «أُلَوِّنُ حُروفي»: the letter is the display font's glyph as a path (outlined, never
  a stroked text), the pictures come from the existing code-drawn picture library, redrawn in black.
- `sketch.py` — the sketchbook's frames, decorations and half-drawings.
- `checks.py` — every drawing on a page must be pure black and white, with no text or raster inside; a page
  whose drawing fails is never printed.
- Preview while drawing: `uv run python -m qamra_workbook.coloring.preview --book palestine --mode both`.

Rules: closed shapes, large areas (nothing under ~6 mm), no text/letters/numbers/flags inside drawings, simple
friendly people (dot eyes and a smile), girls without hijab (an adult woman in a family or village scene may
wear a headscarf), mosques and Al-Aqsa/the Dome of the Rock from outside only, never the Quran's text or any
sacred text, no prophets, angels or religious figures.

### The near-zero-cost AI fallback (prepared, capped)

For a scene too complex to draw well in code, `scripts/coloring_ai.py` can generate line art with a cheap
model (FLUX.1 [schnell] on fal) and `coloring/lineart.py` cleans it into the same print line art (threshold,
specks removed, thinned to a skeleton, re-drawn at the uniform 2.6 mm width, vectorized). It has a hard
`--max-usd` cap, a `--dry-run` that lists the pages and the exact cost, and logs every call to
`/home/tareq/kids/out/design-images/ledger.jsonl`. See the report in the commit for what was used.

## Personalization and the order flow

Who is it for (the child: name, gender) → optional character for the cover → review → cart. The character is
optional for this line only: an existing approved character can go on the cover, or the family can have one
drawn from a photo (the usual paid path), or choose a cover without a character (a drawn centrepiece instead).
Inside, the title page («{صاحِبُ/صاحِبَةُ} هذا الدَّفْتَرِ» and the name in hollow letters to colour), the
letters book's «اسْمي» and «أَحْسَنْتَ!» pages, and the sketchbook's prompts follow the child's gender.

## Rendering

- `python -m qamra_workbook.render.coloring --title letters|palestine|ramadan|sketchbook [--gender m]
  [--no-character]` → interior.pdf, cover.pdf, preflight.json, PNGs and a contact sheet.
- The order job calls `qamra_workbook.render.coloring_order.render_order(child, slug, out, imprint=…)`.
- Web previews: `uv run python scripts/export_coloring_previews.py`.
