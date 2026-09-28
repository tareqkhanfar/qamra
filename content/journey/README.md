# «رحلتي الأولى للتعلّم» — journey plan (Addendum 6 §3)

`plan.yaml` holds the whole book: three stages («محطات») of 100–120 pages. Each stage walks the journey map in order. It is the second product on the workbook engine, and it shares the page-type library with «دوسية التأسيس» (`content/workbook/`).

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
- `title`: the mission's big title. `instruction`: at most 7 words, easy to read aloud. Put `{child}` where the child's name goes.
- `goals`: the development goals from Addendum 6 §2 (`attention`, `memory`, `observation`, `visual_discrimination`, `auditory_discrimination`, `logic`, `classification`, `sequencing`, `visual_motor`, `pen_control`, `fine_motor`, `writing_readiness`, `reading_readiness`, `arabic`, `numbers`, `english`, `independence`).
- `audio: true`: the page carries a QR code for the sound or word. Listening pages, `letter-intro` and `en-letter` need it.
- `example: true`: the page prints a solved example.
- `one_sided: true`: for cut-out pages. The other side of that sheet must be `blank`.

## Rules the checker enforces

- Each stage has 100–120 pages, an even count, numbered 1..N.
- A stage starts with intro pages that include the journey map. Each section is then one block, in journey order. It starts with a `section-opener` and ends with `what-i-learned`; the stage's last section ends with its certificate.
- Every mission has a title and an instruction of 7 words or fewer.
- No more than 2 pages of the same type in a row.
- `memory-look` is an odd page, and `memory-recall` is the next page (the back of the same sheet).
- Stage 1 has no letters, no number writing, and no quantities above 5.
- Stages 2 and 3:
  - have name tracing in Arabic and English;
  - introduce all 28 Arabic letters once, in `letter_order`;
  - take each letter through `letter-intro` → `finger-trace` → `letter-trace` → `letter-write` → `find-letter`;
  - cover English A–Z in order.
- Every number 1–10 appears on a `quantity-first` page before any numeral page.
- The writing progression (`write-progression`, levels 1–7): a level starts only after at least 3 pages of the level before it. Stage 1 stops at level 2 and stage 2 at level 5.
- Every stage has at least 2 missions with the child's name. Stages 1 and 2 end with a mini-certificate. Stage 3 has the observation checklist and ends with the certificate.
- Every development goal has at least 3 pages.
- The 12 samples point to real pages and cover at least 8 sections.
