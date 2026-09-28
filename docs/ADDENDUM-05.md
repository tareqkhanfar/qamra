# Addendum 5 — «دوسية التأسيس»: personalized KG foundation workbook (for Claude Code)

> Save as `docs/ADDENDUM-05.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-05.md — it overrides earlier prompts where they conflict." Start with section 2 (curriculum plan) and STOP for my approval before building pages.

---

## 1. The product

A complete, sequenced kindergarten foundation workbook that combines, **in the same book**:
- pre-writing / pen skills
- Arabic
- Math
- English
- thinking & focus
- activities
- reviews & assessments

It is personalized with the child's name and character. It is a real progressive curriculum (every page builds on the previous one), not a collection of worksheets.

**Structure: a 3-volume series** (one volume per school term). Each volume mixes the subjects so parents buy one book, not several. About 110–130 pages per volume, so it lays flat and is easy for small hands.

| Volume | Content |
| --- | --- |
| **Volume 1 (Term 1)** | pen skills, first Arabic letters, numbers 0–5, English A–H, basic concepts, thinking, reviews |
| **Volume 2 (Term 2)** | more letters, numbers 6–10, English I–R, shapes/patterns/position words |
| **Volume 3 (Term 3)** | remaining letters, vowels (فتحة، ضمة، كسرة، سكون), syllables, simple words/sentences, English S–Z + vocabulary units, simple addition/subtraction with pictures, final assessments + certificate |

Two levels: **KG1 (age 4–5)** and **KG2 (age 5–6)**. KG2 goes further in reading, writing and math.

Formats:
- **Printed:** wire-o/spiral binding so it lays flat for writing, thick paper, color or economic B&W interior with color cover.
- **Digital printable PDF:** for home printing.

## 2. Curriculum plan first (approval gate)

Create `content/workbook/curriculum/{level}.yaml` and a readable `docs/workbook/plan-{level}.md` with:

1. Learning objectives per subject and per volume.
2. Full **table of contents** and the **page-by-page sequence** (page number, subject, skill, page type, difficulty 1–5).
3. Interleaving rule: subjects rotate in short blocks, so the child doesn't do 20 pages of one subject in a row. Each week of the term gets a balanced mix; a "week" marker appears on pages.
4. Progression rules, from the brief:
   - pen skills → letters/numbers → tracing → writing → application → reading → advanced skills → review & assessment
   - easy to hard, never all skills at once
5. Review page after every unit; a simple assessment at the end of every subject block in each volume; certificate at the end of Volume 3.
6. Alignment notes for the Palestinian and Jordanian KG expectations (general, no copied curriculum text).

**STOP after this section.** Show me the plan and the total page count per volume, and wait for approval. A kindergarten educator will review it before any design work.

## 3. Content scope (from the customer brief — all required)

### Pen skills
- horizontal, vertical, diagonal, zigzag and curved lines
- circles, shapes, dot-to-dot, path tracing, mazes
- coloring inside borders, pen-control drills
- all with dotted guides

### Arabic, per letter (fixed sequence)
1. meet the letter (large and clear)
2. 1–2 pictures of words starting with it
3. color the letter and the picture
4. trace the big dotted letter
5. trace smaller sizes
6. writing practice: guided, then independent
7. find the letter among others
8. identify the correct one
9. match letter ↔ picture ↔ word
10. letter review

Then:
- letter positions: beginning, middle and end of a word
- vowels: فتحة، ضمة، كسرة، سكون
- syllables and building syllables
- reading simple words
- writing words: dotted, then independent
- very short sentences
- comprehensive reviews

### Math
- **Per number:** meet → dotted trace → practice → write → apply → review.
- **Concepts:**
  - counting, number ↔ quantity matching, choosing the right number
  - more/less, many/few, big/small, long/short
  - above/below, inside/outside, in front/behind, right/left
  - shapes, colors, patterns and sequences, ordering
  - simple addition and subtraction with pictures

### English
- **Per letter A–Z:** capital and small letter, recognize, dotted trace, write, find, match, a picture + word starting with the letter, coloring, review.
- **Vocabulary units:** Numbers, Colors, Shapes, Family, Body Parts, Animals, Fruits, Food, Toys, School Objects.
- Then simple words and very short age-appropriate sentences.

### Thinking & focus
matching, classifying, odd-one-out, completing patterns, ordering, mazes, observation, memory, connecting pictures, spot-the-difference, simple problem solving.

### Activities for variety
coloring, connecting, cut & paste (with printed cut lines on one-sided pages), drawing, mazes, visual, counting, letter and review activities.

## 4. Workbook engine (how to build it — mostly without AI)

Build a **page-type library** as parameterized HTML/SVG templates rendered with the existing Playwright PDF pipeline. Each page type takes data (letter, number, word, images, difficulty). Examples:

- `pen-lines` (type, count, spacing)
- `maze` (procedurally generated, difficulty levels)
- `dot-to-dot`
- `trace-path`
- `letter-intro`
- `letter-trace` (sizes)
- `letter-write` (guided/independent rows)
- `find-letter` (grid with distractors)
- `match-letter-picture`
- `letter-position`
- `harakat`
- `syllables`
- `word-read`
- `word-write`
- `number-intro`, `number-trace`, `count-and-circle`, `number-quantity-match`
- `compare` (more/less, big/small…)
- `position-words`
- `shapes`
- `pattern-complete`
- `picture-add`, `picture-subtract`
- `en-letter` (capital/small)
- `vocab-unit`
- `odd-one-out`, `classify`, `spot-difference`, `memory`
- `coloring`
- `cut-and-paste`
- `unit-review`
- `assessment` (with a small teacher/parent score box)
- `certificate`

**Tracing fonts and stroke guides**
- Arabic tracing needs correct single-stroke dotted letter forms with **start dots and direction arrows**.
- Use a dotted/tracing Arabic font **with a commercial license**, or build single-stroke SVG paths for all letters and forms once, and store them as assets.
- Same for English (print-style dotted font, commercially licensed) and digits (Arabic-Indic and Western, per level setting).
- Record every font license in `docs/licenses.md`.

**Writing space**
- Generous ruled lines sized for small hands (KG1 larger than KG2).
- Arabic lines are right-to-left with a clear start marker.

**Picture library (one-time AI cost)**
- About 300–400 simple vocabulary pictures (Arabic letter words + English vocab + math objects), generated once with our image provider in a **simple, clean, child-friendly style**.
- Each picture in two versions: color, and line-art for coloring.
- Stored in `content/workbook/images/` with tags (word_ar, word_en, first letter, category).
- Culturally appropriate words (e.g. أ: أرنب، ب: بيت، ت: تفاحة…); an educator reviews the word list.
- No text inside images.

**Design rules**
- child-friendly, clear and uncluttered, one clear goal per page
- cheerful but calm colors
- large clear Arabic font; very clear dotted tracing
- Qamra mascot moon/star used sparingly as a friendly guide with a one-line instruction per page (Arabic; English pages bilingual)
- page numbers, a subject color tab on the page edge (Arabic / Math / English / Thinking) so parents can navigate
- margins 12 mm safe area + 3 mm bleed; size A4 portrait (and A5 option later); 300 DPI; fonts embedded
- B&W interior version must stay clear (subject tabs become patterns, not only colors)

## 5. Personalization (what makes it Qamra)

- **Cover:** the child's character (Classic pipeline) + name + level + volume number.
- **«هذا الكتاب لـ …» page:** the child's name and a space for their handprint.
- **Name pages:** trace and write **your own name** in Arabic and English (generated tracing of the child's name). Children love this and competitors' workbooks can't do it.
- The child's character appears on unit opener pages and on the **certificate of achievement** (name, date, kindergarten name if B2B).
- Optional: the parent chooses the digit style (٠١٢٣ vs 0123) and whether English is included.

AI cost per workbook: only the cover character (and reuse the child's existing character if they already ordered a book). **Target ≤ 1₪ AI cost per volume.**

## 6. Store integration (uses Addendum 4 store)

- New product line **«دوسية التأسيس»** with variants:
  - level (KG1/KG2)
  - volume (1/2/3/set of 3)
  - interior (color/B&W)
  - format (printed spiral / digital PDF)
- Suggested starting prices (admin-configurable; confirm print costs with the printer first):

  | Product | Price |
  | --- | --- |
  | digital PDF per volume | 29₪ |
  | printed B&W per volume | 49₪ |
  | printed color per volume | 69₪ |
  | set of 3 printed color | 179₪ |
  | B2B per child per volume (20+) | 35–45₪ with the kindergarten logo on the cover |

- **Add-ons:**
  - reusable wipe-clean sleeve + dry-erase pen: +15₪
  - reward sticker sheet: +8₪
  - pencil/crayon kit: +15₪
  - audio QR codes for letter pronunciation (Arabic & English TTS): +10₪
  - teacher/parent guide PDF: free
- Cross-sell: after buying a story book, suggest the workbook with the same character — and vice versa.
- **B2B:**
  - kindergartens can adopt the series as their curriculum: class orders, their logo on covers, and delivery per term (Volume 1 in September, 2 in January, 3 in March).
  - This is recurring revenue: schedule the next volume automatically per class and remind the school.

## 7. Admin tools

- Curriculum editor: view/edit the page sequence per level/volume, drag to reorder, change page type parameters, and preview any page instantly.
- Picture library manager: tags, regenerate, approve, line-art/color pair check.
- Educator review workflow: page-by-page comments and approval (same reviewer role as themes).
- Generate a full sample volume PDF (with a sample child) for proofing and for the website preview (show 8–10 sample pages on the product page).
- Keep editable source data (YAML + SVG assets) versioned. Editable originals are part of what we can offer to schools if needed.

## 8. Quality checks (add to the production audit)

- Every page type renders correctly in RTL (Arabic) and LTR (English) with no overflow at A4 and in B&W.
- Tracing letters show correct forms, start points and stroke direction for all Arabic letters and positions (educator sign-off).
- No duplicated pages, sequence matches the approved plan, page numbers and table of contents are correct.
- Mazes are solvable (automated check); dot-to-dot numbers in order; counting pages have the right quantities (automated asserts).
- Print preflight passes; a physical proof of Volume 1 is checked by hand before selling.

## 9. Order of work

1. Curriculum plan + TOC for KG1 and KG2 → **stop for my approval**.
2. Fonts/stroke assets + page-type library (with visual tests).
3. Picture library generation + educator review of words.
4. Volume 1 (KG2 first — most demanded), full sample PDF → physical proof.
5. Store product + personalization + B2B term scheduling.
6. Volumes 2 and 3, then KG1.

Report with sample pages (screenshots) after each step.
