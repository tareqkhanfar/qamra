# «مغامراتي مع عائلتي» — the family adventure book (Addendum 7)

`plan.yaml` is the whole proposal: the concept and the print recommendations, the sections, every activity with its pages, the insert sheets, and the sample pages. It is the third activity book on the workbook engine, after «دوسية التأسيس» and «رحلتي الأولى للتعلّم».

```bash
uv run python -m qamra_workbook.family check   # the Addendum 7 rules; must report 0 problems
uv run python scripts/family_proposal.py       # docs/family-book/proposal.md + the proposal PDF
```

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
- **Inserts:** insert-only types (play money, role cards, puppets, the sticker sheet) never appear as book pages. There is a sticker sheet and at least one card-stock sheet.
- **Samples:** 8–10 of them, covering at least 6 parts of the book.
