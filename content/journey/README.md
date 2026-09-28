# «رحلتي الأولى للتعلّم» — journey plan (Addendum 6 §3)

`plan.yaml` holds the whole book: three stages («محطات») of 100–120 pages. Each stage walks the whole journey map in order. It is the second product on the workbook engine, and it shares the page-type library with «دوسية التأسيس» (`content/workbook/`). Tareq's decisions of 2026-09-28 (`docs/workbook/decisions-2026-09-28.md`) are applied: every section in every stage, one new letter per page, stage 1 numerals by sight only, Hindi numerals by default, and the replaced words.

```bash
uv run python -m qamra_workbook.journey check    # the Addendum 6 rules; must report 0 problems
uv run python -m qamra_workbook.journey render   # regenerates docs/journey/plan.md
```

The schema, the page types (the Addendum 5 library plus the Addendum 6 types) and every rule live in `packages/workbook/src/qamra_workbook/journey.py`.

## Format

```yaml
title_ar: رحلتي الأولى للتعلّم
title_en: My First Learning Journey
idea: |                 # §3.1
  …
skill_order: |          # §3.4: how each skill builds on the previous one
  …
difficulty_notes: |     # §3.6
  …
writing_notes: |        # §4.10: practice counts per writing level
  …
letter_order: [أ, ب, ت, …]        # all 28 letters across stages 2 and 3
sections:                          # journey order
  - {id: think, title_ar: أدرّب عقلي, icon: 🧠, journey_step: أفكر}
samples:                           # §3.7: the 12 sample pages
  - {stage: 1, n: 1}
stages:
  - stage: 1
    age: "3–4"
    title_ar: المحطة الأولى
    objectives: {think: [ … ]}
    pages:
      - {n: 5, section: think, type: odd-one-out, title: "مَن المختلف؟", instruction: "ضع دائرة حول المختلف", skill: "يميّز الصورة المختلفة بين أربع", goals: [observation, visual_discrimination], difficulty: 1, params: {items: [تفاحة, تفاحة, تفاحة, كرة]}}
```

- `section`: a section id, or `intro` for the opening pages.
- `merged: [a, b]`: a `section-opener` or `what-i-learned` page shared by two small neighbouring sections. The shared opener is the first page of `a`; the shared «ماذا تعلمت؟» is the last page of `b`.
- `title`: the mission's big title. `instruction`: at most 7 words, easy to read aloud. Put `{child}` where the child's name goes.
- `goals`: the development goals from Addendum 6 §2 (`attention`, `memory`, `observation`, `visual_discrimination`, `auditory_discrimination`, `logic`, `classification`, `sequencing`, `visual_motor`, `pen_control`, `fine_motor`, `writing_readiness`, `reading_readiness`, `arabic`, `numbers`, `english`, `independence`).
- `audio: true`: the page carries a QR code for the sound or word. Listening pages, a letter's `finger-trace` page and `en-letter` need it.
- Letters: `params.letter`, `letters`, `target` and a color `key` name the letters a page shows (`distractors` do not count). An Arabic letter's first page is its `finger-trace` page (meet it, hear it, link it to a picture, trace it with a finger).
- Numbers: `params.number` or `numbers`. `quantity-first` pages answer with dots, fingers or colouring (`answer_with`); `answer_with: numerals` makes the child pick the numeral, so the page counts as a numeral page.
- Numerals are written 1, 2, 3 in the plan. The printed page uses Hindi numerals (١٢٣) on Arabic and math pages, or 123 when the parent asks; English pages always use 123.
- `example: true`: the page prints a solved example.
- `one_sided: true`: for cut-out pages. The other side of that sheet must be `blank`.

## Rules the checker enforces

- Each stage has 100–120 pages, an even count, numbered 1..N.
- A stage starts with intro pages that include the journey map. **Every stage visits every section**, each as one block in journey order. A block starts with a `section-opener` and ends with `what-i-learned`; the stage's last section ends with its certificate.
- Two neighbouring sections may share their opener and their «ماذا تعلمت؟» (`merged`), only when both are small: at most 5 pages besides the opener and «ماذا تعلمت؟».
- Every mission has a title and an instruction of 7 words or fewer.
- No more than 2 pages of the same type in a row.
- `memory-look` is an odd page, and `memory-recall` is the next page (the back of the same sheet).
- Stage 1 has no letters and no quantities or numerals above 5. It counts quantities first, then meets the numerals 1–5 on `number-intro` pages and matches every numeral 1–5 to its quantity. It never writes a numeral: no `number-trace`, no `number-write`, no numeral on a writing page.
- Stages 2 and 3:
  - have name tracing in Arabic and English;
  - introduce all 28 Arabic letters once, in `letter_order`, 14 per stage, each on its own `finger-trace` page;
  - take each letter through `finger-trace` → `letter-trace` → `find-letter` in its stage;
  - cover English A–Z in order.
- Letters come one at a time: a page shows at most one new letter (new = from its first page to its `letter-trace` page, or its `en-letter` page), and no page shows a letter before its first page (`first-sound` pages only play the sound). Only review pages (`unit-review`, `what-i-learned`, `assessment`) put 4 letters or more together.
- The replaced words never appear on a page or in the notes: ظ uses ظِلّ and ذ uses ذَيل now (the old words are `RETIRED_WORDS` in `journey.py`); لسان and ضرس stay.
- Every number 1–10 appears on a `quantity-first` page (answering without numerals) before any page that prints its numeral.
- The writing progression (`write-progression`, levels 1–7): a level starts only after at least 3 pages of the level before it. Stage 1 stops at level 2 and stage 2 at level 5.
- Every stage has at least 2 missions with the child's name. Stages 1 and 2 end with a mini-certificate. Stage 3 has the observation checklist and ends with the certificate.
- Every development goal has at least 3 pages.
- The 12 samples point to real pages and cover at least 8 sections.
