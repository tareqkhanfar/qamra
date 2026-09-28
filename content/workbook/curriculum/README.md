# Curriculum plans — «دوسية التأسيس» (Addendum 5 §2)

One file per level: `kg1.yaml` (ages 4–5) and `kg2.yaml` (ages 5–6). Each holds three volumes (one per term). The workbook engine will build its pages from these files, and the readable plan in `docs/workbook/plan-{level}.md` is generated from them.

```bash
uv run python -m qamra_workbook.plan check kg2    # the rules below; must report 0 problems
uv run python -m qamra_workbook.plan render kg2   # regenerates docs/workbook/plan-kg2.md
```

The schema, the page-type library and every rule live in `packages/workbook/src/qamra_workbook/curriculum.py`.

## Format

```yaml
level: kg2
age: "5–6"
title_ar: دوسية التأسيس — المستوى الثاني
title_en: Foundation Workbook — KG2
letter_order: [أ, ب, ت, …]            # the Arabic teaching order, all 28 letters across the three volumes
progression_notes: |                   # how the plan goes from easy to hard (§2.4)
  …
interleaving_notes: |                  # how subjects rotate and how each week is mixed (§2.3)
  …
alignment_notes: |                     # general Palestinian / Jordanian KG expectations (§2.6), no copied text
  …
volumes:
  - volume: 1
    term: 1
    weeks: 12
    title_ar: …
    objectives:                        # per subject: pen, arabic, math, english, thinking
      arabic: [ … ]
    units:
      - {id: v1-ar-01, subject: arabic, title_ar: "حرف الألف", title_en: "Alif"}
    pages:
      - {n: 1, week: 1, subject: intro, unit: v1-intro, type: owner-page, skill: "هذا الكتاب لـ… وبصمة يدي", difficulty: 1}
      - {n: 9, week: 1, subject: arabic, unit: v1-ar-01, type: letter-intro, skill: "أتعرّف على حرف الألف", difficulty: 1, params: {letter: أ, words: [أرنب, أسد]}}
```

- `subject`: `intro` (front matter), `pen`, `arabic`, `math`, `english`, `thinking`, or `mixed` (cross-subject reviews).
- `unit`: every page belongs to a unit of the same subject. A unit ends with a `unit-review` page.
- `skill`: the page's one clear goal, in Arabic, so an educator can review it.
- `difficulty`: 1 (easiest) to 5.
- `params`: whatever the page type needs, for example `letter`, `letters`, `words`, `number`, `numbers`, `concept`, `sizes`, `mode`, `level`.
- `one_sided: true` goes on cut & paste pages. The other side of that sheet (odd page = front, even page = back) must be a `blank` page.

## Rules the checker enforces

- Each volume has 110–130 pages, an even count, numbered 1..N.
- Weeks start at 1 and go up one at a time. Every week with 6 or more pages mixes at least 3 subjects.
- No more than 4 pages of the same subject in a row.
- Every unit ends with a review. Every volume ends each of Arabic, Math, English and Thinking with an `assessment` after that subject's last page. Volume 3 ends with the `certificate`.
- Arabic: `letter-intro` introduces each of the 28 letters once, in `letter_order`. Each letter then gets `letter-trace`, `letter-write`, `find-letter` and `match-letter-picture` pages, in that order.
- English: `en-letter` covers A–H in Volume 1, I–R in Volume 2 and S–Z in Volume 3. Each letter gets a practice page after it.
- Numbers: `number-intro` covers 0–5 in Volume 1 and 6–10 in Volume 2. Each number gets a `number-trace` page and a practice page after its intro.
- Volume 1 has pen skills. Volume 3 has vowels (`harakat`), `syllables`, `word-read`, `word-write`, `picture-add`, `picture-subtract` and `vocab-unit` pages.
- No page repeats another page's exact content.
