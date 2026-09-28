# Curriculum plans — «دوسية التأسيس» (Addendum 5 §2)

One file per level: `kg1.yaml` (ages 4–5) and `kg2.yaml` (ages 5–6). Each holds three volumes (one per term). The workbook engine will build its pages from these files. Two readable documents are generated from them: the plan in `docs/workbook/plan-{level}.md`, and the Arabic version for the kindergarten educator in `docs/workbook/educator-{level}.md`.

Tareq's decisions of 28 September 2026 (`docs/workbook/decisions-2026-09-28.md`) override Addendum 5 where they differ; the checker cites them as "decision N".

```bash
uv run python -m qamra_workbook.plan check kg2    # the rules below; must report 0 problems
uv run python -m qamra_workbook.plan render kg2   # regenerates docs/workbook/plan-kg2.md and educator-kg2.md
```

The schema, the page-type library (with each type's Arabic name) and every rule live in `packages/workbook/src/qamra_workbook/curriculum.py`. A unit test fails when the docs are out of date with the YAML, so re-render after every edit.

## Format

```yaml
level: kg2
age: "5–6"
title_ar: دوسية التأسيس — المستوى الثاني
title_en: Foundation Workbook — KG2
letter_order: [أ, ب, ت, …]            # the Arabic teaching order: all 28 letters, alphabetical
independent_writing: [أ, ب, …]         # KG1 only: the letters the child writes alone; the rest are traced
progression_notes: |                   # how the plan goes from easy to hard (§2.4), in English
  …
interleaving_notes: |                  # how subjects rotate and how each week is mixed (§2.3), in English
  …
alignment_notes: |                     # general Palestinian / Jordanian KG expectations (§2.6), in English
  …
progression_notes_ar: |                # the same three notes in Arabic, for the educator's version
  …
interleaving_notes_ar: |
  …
alignment_notes_ar: |
  …
changes_ar:                            # what changed since the version the educator last saw, in Arabic
  - …
volumes:
  - volume: 1
    term: 1
    weeks: 12
    review_weeks: [7]                  # light weeks that only review; nothing new is introduced
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
- `params`: whatever the page type needs, for example `letter`, `letters`, `words`, `number`, `numbers`, `concept`, `sizes`, `mode`, `level`. Some rules read them:
  - `independent` (rows written alone) and `mode: independent | write | dotted | listen`;
  - `haraka` / `harakat` (English or Arabic names);
  - `tens_ones: pictures` on pages that show numbers above 10;
  - `checklist` and `tracing` on the pen-skills assessment.
- `one_sided: true` goes on cut & paste pages. The other side of that sheet (odd page = front, even page = back) must be a `blank` page.

## Rules the checker enforces

From Addendum 5:

- Each volume has 110–130 pages, an even count, numbered 1..N.
- Weeks start at 1 and go up one at a time. Every week with 6 or more pages mixes at least 3 subjects.
- No more than 4 pages of the same subject in a row.
- Every unit ends with a review. Every volume ends each of pen, Arabic, math, English and thinking with an `assessment` after that subject's last page. Volume 3 ends with the `certificate`.
- Arabic: `letter-intro` introduces each of the 28 letters once, in `letter_order`. Each letter then gets `letter-trace`, `letter-write` (only for the letters the level writes alone), `find-letter` and `match-letter-picture` pages, in that order.
- English: `en-letter` covers A–H in Volume 1, I–R in Volume 2 and S–Z in Volume 3. Each letter gets a practice page after it.
- Numbers: `number-intro` covers 1–5 and then 0 in Volume 1, and 6–10 in Volume 2. Each number gets a `number-trace` page and a practice page after its intro.
- Volume 1 has pen skills. Volume 3 has vowels (`harakat`), `word-read`, `word-write`, `picture-add`, `picture-subtract` and `vocab-unit` pages; KG2 also has `syllables` and `sentence-read`.
- No page repeats another page's exact content.

From the decisions of 28 September 2026:

1. `letter_order` is alphabetical (أ ب ت ث …).
2. In KG1, only the letters in `independent_writing` get a `letter-write` page, each with an independent row; the other letters are traced and recognized. Words, syllables and vowels are never written alone. A light review week comes after every 4–5 new letters, and each volume's last week reviews the rest.
3. KG1 meets only fatha, damma and kasra, as listening pages (`mode: listen`) in Volume 3's last 3 weeks, after all 28 letters, and never sukun (no page, no mark). KG2 teaches all four.
4. KG1 has no `sentence-read` pages.
5. Counting starts at 1: no zero before the intro of 5. Numbers stay within 10 in KG1 and within 20 in KG2, above 10 only in Volume 3, with tens and ones in pictures (`tens_ones: pictures`).
6. No tanween and no shadda in anything a child reads (instruction text may still spell أتعرّف). KG1 never reads «ال». KG2 reads a few familiar «ال» words (met earlier as pictures), only in Volume 3's last 3 weeks and only before moon letters, with no sun/moon lesson.
7. The replaced picture words (ظبي، لقلق، ذئب) never appear, and «طائرة» appears only as «طائرة ورقية».
8. Terms have 12, 11 and 11 weeks. A review week (`review_weeks`) introduces nothing new, reviews every letter met since the previous one, and has fewer pages than the volume's average week. KG2's Volume 2 lists its extra review week.
9. Each volume closes with a pen-skills `assessment` in its last week, among the final assessments: a `checklist` of grip, pressure and direction, and two `tracing` tasks.
10. Every English note has an Arabic version (`*_ar`) for the educator's document.
