# «مغامراتي مع عائلتي» — the family adventure book (Addendum 7)

`plan.yaml` is the whole proposal: the concept and the print recommendations, the sections, every activity with its pages, the insert sheets, and the sample pages. It is the third activity book on the workbook engine, after «دوسية التأسيس» and «رحلتي الأولى للتعلّم».

```bash
uv run python -m qamra_workbook.family check              # the Addendum 7 rules; must report 0 problems
uv run python scripts/family_proposal.py                  # docs/family-book/proposal.md + the proposal PDF
uv run python -m qamra_workbook.render.family --book --size both   # the whole book, cover and inserts
uv run python -m qamra_workbook.render.family --pages 1-5,37 --name try   # a few pages, for a quick look
```

`--book` writes, for each size (21×28 and A4, one setting apart):

- `out/family-book/book-<size>.pdf`: the 112 pages, with `png-book-<size>/` previews, `book-<size>-spreads-NN.png` (the open book's spreads, right to left) and `book-<size>-preflight.json`;
- `out/family-book/cover-<size>.pdf`: the front and back cover (350 g card, no spine: wire-o);
- `out/family-book/inserts/<id>-<size>.pdf`: each insert's sheets with every cut line on the optional-content layer «CutContour», and `<id>-<size>-die.pdf` with the die lines alone (same page size, aligned with the art).

The sample child and family come from `samples.yaml`. An order renders the same files for its own child through `qamra_workbook.render.family_order.render_order` (the worker job `qamra_worker.jobs.family_book`).

The schema and every rule live in `packages/workbook/src/qamra_workbook/family.py`.

## Format

```yaml
title_ar: مغامراتي مع عائلتي
title_en: My Adventures with My Family
proposal:            # Addendum 7 §3, in Arabic
  concept: |         # the full concept and vision
  size: |            # recommended size, why, and the alternatives with their cost impact
  paper: |           # interior, cover, sticker sheet, card stock
  binding: |         # wire-o; digital vs offset and the break-even
front:               # pages before the first adventure (title page, «عائلتي», the passport, contents)
  - {type: passport, title: "جواز سفر المغامر {child}", instruction: "الصق ختمًا بعد كل مغامرة"}
sections:            # the adventures, in the book's order
  - {id: home, title_ar: بيتي مدرسة, icon: 🏠, hook: "…", badge: "مستكشف البيت"}
activities:          # grouped by section, in order
  - id: home-circles
    section: home
    title: صيد الدوائر في المطبخ
    goal: …
    skills: [observation, counting]       # from the list below
    child_part: …                         # what the child does alone
    parent_part: …                        # the grown-up's part («هيا نفعلها معاً!»)
    together: true
    where: home                           # home | outside
    materials: [ورقة, أقلام تلوين]         # common household items only
    minutes: 10                           # 5–20
    levels: {simple: "ابحث عن 3 أشياء دائرية", challenge: "ابحث عن 5 وصنّفها من الأصغر للأكبر"}
    safety: …                             # required for recipes and outdoor activities
    pages:
      - {type: scavenger-hunt, title: "صيد الدوائر", instruction: "ابحث عن ٣ أشياء دائرية", parent: ["…"], params: {…}}
back:                # after the last adventure: the 7-day challenge, then the certificate
inserts:
  - {kind: stickers, title: ورقة الملصقات, items: [أختام الجواز, ملصقات المكافأة, رموز الروتين]}
  - {kind: card-stock, title: بطاقات القصّ, items: [نقود قمرة للّعب, بطاقات الأدوار]}
samples:             # 8–10 pages for approving the look (book page numbers, or an insert title)
  - {n: 3}
  - {n: 0, insert: بطاقات القصّ}
```

**Page numbers** follow from the order: the front pages, then for each section its two-page opening spread (generated from the section's `hook`), its activities' pages, then the back pages.

**Skills** (Addendum 7 §1): `thinking`, `observation`, `memory`, `counting`, `speaking`, `emotions`, `problem_solving`, `creativity`, `responsibility`, `life_skills`, `cooperation`.

**Placeholders:**
- `{child}`: the child's name.
- `{adult}`: the grown-up doing the activity with the child.
- `{member}`: a family member from the family list.
- `{family_name}`, `{city}`.
- `{masc/fem}` pairs for the child's gender.

Never write a fixed «ماما» or «بابا» into instructions or parent boxes. Families differ, and a child may be raised by a grandparent or one parent (§9).

## Render params

A page's `params` complete what the page type draws (every builder falls back to a complete page when one is missing). The ones the whole book uses:

| Page type | Params |
|---|---|
| `drawing` | `frame`: plain · circle · tray · portrait · cup · landscape · room · words · rules · stage · id-card; `caption`; `layers`/`challenge_layers` (cup), `count`/`challenge` (words) |
| `scavenger-hunt` | a shape hunt (`shape`, `find`, `challenge`), a color hunt (`colors`), or a checklist (`items`, `challenge_items`: picture ids or `{picture, label}`; `count`, `compare`) |
| `counting` | `mode`: compare · tally · pictures (`picture`, `rows`) · things (`things`, `challenge_things`) · table (the child and the family around the table) · money · change |
| `sort-choose` | `groups` (see `SORT_GROUPS`; `simple` marks the ⭐⭐ groups after it), or `mode`: budget (`simple_purse`, `challenge_purse`, `prices`) · choice (`situations` with `options`) |
| `recipe-steps` | `ingredients`, `steps`, `shown` (the printed order, never already right), `variant`: steps · count · layers |
| `observation-journal` | `entries`, `challenge`, `lead`, `hints`, `chips`, `labels` (instead of numbers), `water`, `how` (steps), `notes` (one big entry) |
| `conversation-cards` | `roles` (lines, ⭐⭐ `challenge`) or `cards` (text, `face` or `icon`, `level`), `answers` |
| `sequence-cards` | `mode`: day (`cards` in order, some `level: 2`) · story (`panels` of pictures) · moves (`moves` with a `pose`, `simple`) |
| `picture-talk` | `mode`: before-after (`rows`) · scene (`questions`, `sentences`) · bubbles (`people`: a `face` or a `job`) · roles (`roles`, `places`) |
| `story-finish` | `mode`: sentences (`rows`) · story (`story`, `panels`, `end`) · problem (… and `feel`) |
| `routine-builder`, `chore-chart` | `steps`/`tasks` and `challenge`; the chart's `ideas` |
| `nature-bingo` | `items` (8 pictures), `hear` |
| `interview-template` | `questions` (text, `icon`, `level`) |
| `family-game-cards` | `mode`: memory (`pairs`, `challenge`, `steps`) · scoreboard (`rounds`) |

The passport's and the sticker sheet's stamps, the contents map's stops and the recipe cards are derived from the plan (`render/family.py`), so they never drift from the adventures. The cover's pages live under `cover:`, and each insert lists its printed `sheets` (insert-only page types, the colors from a `section` param) and an `id` that names its print file.

Texts still waiting for the educator are marked `# draft: educator review` in `plan.yaml`.

## Rules the checker enforces

- **Size:** the book has 96–128 pages, an even count.
- **Structure:**
  - Adventures are grouped by section, in order.
  - Each section's opening spread starts on an even page (the right-hand page of an Arabic book).
  - Each section ends with a «ذكرى اليوم» `memory-page`.
- **Front and back:** the passport is within the first 8 pages. The back pages include the 7-day challenge, and the last page is the family certificate.
- **Variety:** no page type repeats on consecutive pages (the opening spread aside).
- **Text:**
  - Every child instruction has 1–10 words.
  - A parent box has at most 3 lines.
  - Only the placeholders above are allowed.
- **Activities:**
  - Each has 1+ skills and takes 5–20 minutes.
  - A «هيا نفعلها معاً!» activity has a parent part and a parent box.
- **Safety:** recipes and outdoor activities carry a safety note. Recipes remind grown-ups about allergies and contain no nuts or raw eggs.
- **Coverage:**
  - Every skill has at least 3 activities.
  - At least half the activities have a ⭐⭐ challenge version.
- **Inserts:** insert-only types (play money, role cards, puppets, the sticker sheet, recipe cards, memory and question cards) never appear as book pages, and an insert's sheets are insert-only types on the right paper (stickers on the sticker sheet, the rest on card stock). There is a sticker sheet and at least one card-stock sheet.
- **Samples:** 8–10 of them, covering at least 6 parts of the book.
