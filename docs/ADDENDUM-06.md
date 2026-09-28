# Addendum 6 — «رحلتي الأولى للتعلّم»: readiness-first learning journey, ages 3–6 (for Claude Code)

> Save as `docs/ADDENDUM-06.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-06.md — it overrides earlier prompts where they conflict."
>
> This product REUSES the workbook engine from Addendum 5 (page-type library, tracing fonts/strokes, picture library, PDF pipeline, curriculum editor, store integration). Build it as a second product line on the same engine. Do not duplicate code.
>
> Start with section 3 (plan) and STOP for my approval before designing pages.

---

## 1. Positioning (so customers don't confuse the two products)

| | «دوسية التأسيس» (Addendum 5) | «رحلتي الأولى للتعلّم» (this addendum) |
| --- | --- | --- |
| Philosophy | school-term curriculum, subjects side by side | **readiness first**: think → observe → listen → hand → pen → trace → write → read → create |
| Age | 4–6 (KG1/KG2) | **3–6**, starts before letters |
| Best for | kindergartens (B2B), term-by-term | parents at home + nurseries/KG1, play-based |
| Feel | organized workbook | a **game/adventure book** where the child completes missions |

In the store, add a small helper **«أي كتاب يناسب طفلي؟»** (3 questions: age, holds a pen yet?, knows some letters?) that recommends the right product and stage.

## 2. Core idea

The book is a journey where the child is the explorer. The journey map:

**أفكر 🧠 → ألاحظ 👀 → أسمع 👂 → أحرّك يدي ✋ → أمسك القلم ✏️ → أتتبع → أكتب → أقرأ → أحل وأبدع 🌈**

- The journey map appears at the start and at each section opener, with the child's character moving along it (progress = motivation).
- Every page is a **mission** with one or two clear goals, a big title, a very short instruction (≤ 7 words, read-aloud friendly), a solved example when needed, large space, and big clear pictures.
- **Pictures are part of the learning, never decoration.** Every image on a page must be used by the activity.
- Never repeat the same activity format in a boring way. Rotate page types, and keep difficulty rising gradually.
- Development goals the plan must map to pages:
  - attention & focus, memory, observation
  - visual and auditory discrimination
  - logic, classification & matching, ordering & sequencing
  - visual-motor coordination, pen control, fine motor
  - readiness to write and to read
  - Arabic letters, numbers & math concepts, English letters & words
  - growing independence

## 3. Plan first (approval gate)

Create `content/journey/plan.yaml` and `docs/journey/plan.md` containing, exactly as the customer asked:

1. the general idea
2. table of contents
3. section breakdown
4. skill order
5. proposed page count per section
6. difficulty level per stage
7. a set of 12 sample pages (rendered PDF) covering different sections
8. **STOP → approval** → then the full book

**Stages.** The full content is too big for one comfortable book for a 3-year-old, so split the journey into 3 **stages** («محطات») of ~100–120 pages each. Each stage follows the same journey order but at a higher level. Sold separately or as a set.

| Stage | Age | Content |
| --- | --- | --- |
| **المحطة 1** | 3–4 | brain training, eye-leads-hand, hand training (pre-writing), patterns, smart coloring, shapes & colors, quantities 1–5, listening & sounds. **No letter writing yet.** |
| **المحطة 2** | 4–5 | harder thinking games, first Arabic letters with the full multi-step method, numbers 1–10 (quantity first), math concepts, first English letters, phonological awareness (first sound) |
| **المحطة 3** | 5–6 | remaining letters, letter positions, harakat, syllables, simple words, reading picture-words, the full writing progression, English vocabulary units + very short sentences, simple addition/subtraction with pictures, thinking challenges, **final assessment + certificate** |

The plan must show that each skill builds on the previous one, and that no stage moves to harder writing before enough practice.

## 4. Sections and required content (all from the customer brief)

**4.1 أدرّب عقلي 🧠**
- **Observation:** odd one out, what's missing, hidden picture, find two identical, match pictures, which belongs to the group.
- **Memory:** look then remember, remember the order, which picture disappeared, what was in the box, remember shapes & colors.
- **Logic:** what comes first/next, order the pictures, complete the picture story, complete the sequence, classify by shape/color/use.
- **Discrimination:** same/different, big/small, long/short, many/few, open/closed, complete/incomplete.
- Graded difficulty.

**4.2 عيني تقود يدي 👀✋**
- Connect the butterfly to the flower, the car to the house, help the rabbit reach the carrot, follow the train track, follow the right path, choose the shortest path, match the animal to its food, match the child to their shadow, varied paths, gradually overlapping paths.
- Very easy → complex.
- **Personalize** some missions with the child's name: «ساعد {child} للوصول إلى الحديقة».

**4.3 أدرّب يدي ✋✏️ (pre-writing)**
- Dotted drills: horizontal, vertical, diagonal, zigzag, curves, arcs, half circles, circles, spirals, waves, simple shapes.
- Themed pages: 🌧️ draw the rain (vertical), 🌱 grass (short verticals), 🌊 sea waves (waves), 🏔️ mountains (zigzag), and more of the same kind.
- Also: dot-to-dot, complete the shape, draw the missing part, trace inside the path, draw inside borders.

**4.4 الأنماط والتسلسل 🔵🔺**
- Two-element patterns (○ △ ○ △ __) → three elements → **the child creates their own pattern** (blank slots + stickers or drawing).

**4.5 التلوين الذكي 🎨**
- Coloring as a task: color all the circles, only the big things, color like the model, color 3 apples, color the school items, color the odd one, complete the coloring, color shapes by the required color.
- The model/reference must be printed in color, so this product's interior is **full color only**.

**4.6 الأشكال والألوان 🔵🟨**
- **Shapes:** circle, square, triangle, rectangle, star, heart. Each goes through: meet → trace → match → find → color → draw.
- **Colors:** red, yellow, blue, green, orange, purple, pink, black, white. Then color matching, finding, sorting, choosing, color patterns.

**4.7 الرياضيات 🔢 — quantity before numerals**
- Sequence: quantity (🍎 / 🍎🍎 / 🍎🍎🍎) → "how many?" → number → tracing → writing → applying.
- Numbers 1–10 with: counting, number↔quantity, choose the right number, dotted tracing, writing, ordering, number before, number after, more/less, many/few, same amount.
- **Concepts:** big/small, long/short, above/below, inside/outside, in front/behind, near/far, right/left.
- Then: patterns, classification, simple addition and subtraction with pictures.

**4.8 الاستعداد للقراءة 👂👄 (phonological awareness)**
- Listening, sound discrimination, animal sounds, object sounds, loud/soft, fast/slow, choose the picture whose name you hear, same/different words, first sound of a word (أ — أسد 🦁).
- **Audio is essential here**: every listening page gets a QR code that plays the sound or word.
  - Audio assets: TTS for words (Arabic/English, reviewed by a person for correct pronunciation).
  - Commercially licensed sound effects for animals/objects. Record every license in `docs/licenses.md`.
  - Audio is included free in this product.
  - Pages still work without audio: a parent can read the instruction.

**4.9 الحروف العربية 🔤 (أ → ي)**
For each letter, 11 steps (spread over several pages, not crammed):
1. meet the letter (big and clear)
2. hear its sound (QR)
3. link it to a picture (أ — أسد)
4. trace with my finger (big solid path with arrows)
5. trace with the pen (clear dotted letter, start dot + direction arrows)
6. practice writing several times
7. find the letter among others
8. identify the correct one
9. recognize it in words
10. color the letter and pictures
11. write the letter alone

Then: letter at the beginning / middle / end → فتحة، ضمة، كسرة، سكون → syllables → building syllables → simple words → reading picture-words → dotted word writing → independent word writing.

**4.10 الكتابة ✍️ (explicit progression, enforce in the plan)**

trace a line → trace a shape → trace the letter → complete the letter → write next to the model → write on the line → write with no model.

Don't advance a level before enough practice; the plan shows practice counts per level.

**4.11 English 🇬🇧**
- **A–Z:** capital, small, see, hear (QR), trace, write, match, distinguish, linked picture (A a — Apple 🍎), coloring.
- **Then vocabulary units:** Numbers, Colors, Shapes, Animals, Family, Body Parts, Fruits, Food, Toys, School Objects.
- Then simple words and very short sentences.

**4.12 ألعاب التفكير 🧩 (challenge section)**
complete the pattern, spot the differences, hidden objects, missing picture, order pictures into a story, which path is right, classify, match shadows, match the part to the whole, remember the pictures, picture riddles. Gradually harder.

**4.13 المراجعات ⭐**
- Review page after every group of skills.
- «ماذا تعلمت؟» at the end of each section, combining earlier skills.
- **Final assessment (Stage 3)**, a parent/teacher observation checklist + child tasks:
  - pen grip, line tracing, shapes, colors
  - focus, memory, discrimination, patterns
  - Arabic letters, numbers, math concepts, English, writing
  - Each skill rated with 3 simple faces/stars.
- **Certificate:** «أحسنت يا بطل! 🎓 لقد أنهيت رحلتي الأولى للتعلّم» with the child's name, character and date. Mini-certificates at the end of Stages 1 and 2.

## 5. New page types to add to the engine

Add these (parameterized, with automated correctness checks):

- `odd-one-out`, `whats-missing`
- `hidden-picture` (objects hidden inside a line-art scene)
- `find-identical-pair`, `belongs-to-group`
- `memory-look` + `memory-recall` (always a front/back pair: look on one page, recall on the next after turning)
- `sequence-story` (3–6 panels to order)
- `classify-by` (shape/color/use)
- `connect-pairs`
- `shortest-path`
- `overlapping-paths`
- `shadow-match`, `part-to-whole`
- `themed-pen-drill` (rain/grass/waves/mountains…)
- `complete-the-shape`, `draw-missing-part`
- `create-your-pattern`
- `smart-coloring` (rule-based, with color model)
- `shape-journey` (6 steps)
- `color-journey`
- `quantity-first` (how many?)
- `number-before-after`, `same-amount`
- `near-far`
- `listen-and-choose` (QR audio), `loud-soft`, `fast-slow`, `first-sound`
- `finger-trace`
- `write-progression` (7 levels)
- `picture-riddle`
- `observation-checklist`
- `mini-certificate`

**Generate the visual puzzles programmatically** from the picture library so they are always correct. Do not rely on an AI image model to create them, because AI can't be trusted to make "exactly 5 differences":
- spot-the-difference = one composed scene + controlled edits
- hidden objects = outline objects embedded at logged positions
- shadows = silhouettes generated from the picture
- part-to-whole = programmatic crops

Keep an answer key per page and run automated checks:
- mazes solvable
- the difference count matches the answer key
- the quantities on counting pages are exact
- sequences valid

**Answer key booklet:** generate a separate parent/teacher answer key PDF per stage (free download).

## 6. Design rules (on top of Addendum 5)

- One or two goals per page.
- Big title; ≤ 7-word instruction; solved example when needed; huge work space.
- Tracing dots bold and clear (not faint).
- Writing lines sized per stage (Stage 1 largest).
- Large, clear pictures; never crowded; activity variety on every spread.
- Every page can be worked on directly with a pencil or crayon: no dark backgrounds behind work areas, matte-friendly colors.
- Section colors and icons from the journey map (🧠 👀 👂 ✋ ✏️ …) on page edges for navigation.
- The child's character acts as the guide on section openers and gives short encouragement («رائع يا {child}!») at section ends.

## 7. Personalization

- Cover with the child's character + name + stage.
- Journey map page with the child's character.
- Some missions use the child's name.
- Name tracing pages (Arabic + English) in Stages 2–3.
- Personal certificate.
- AI cost per book: cover/character only (reuse the existing character if the child already has one). **Target ≤ 1₪.**

## 8. Store

- New product line «رحلتي الأولى للتعلّم».
- Variants: stage (1/2/3/set), format (printed spiral full-color / digital PDF). No B&W option, because smart coloring needs color models.
- Suggested prices (admin-configurable; confirm print costs first):

  | Product | Price |
  | --- | --- |
  | digital PDF per stage | 29₪ |
  | printed per stage | 69₪ |
  | set of 3 | 179₪ |
  | nurseries/KG (20+) | 45₪ per stage with their logo |

- Add-ons (reuse Addendum 4/5): wipe-clean sleeve + pen, sticker sheet for create-your-pattern and rewards, crayon kit, printed answer key.
- Cross-sell: story books with the same character, and «دوسية التأسيس» for school-age.
- The «أي كتاب يناسب طفلي؟» helper appears on both workbook product pages.

## 9. Quality checks (add to the production audit)

- All automated puzzle checks pass (answer keys verified).
- Every audio QR resolves and plays on iPhone Safari and Android Chrome; pronunciation reviewed by a person.
- Educator sign-off on:
  - the plan
  - letter forms and stroke direction
  - difficulty curve
  - age-appropriateness of every section
- A physical proof of Stage 1 is tested with 2–3 real children (with parents' consent) before selling. Note what was too easy/hard and adjust.

## 10. Order of work

1. Plan + TOC + page counts + difficulty per stage + 12 sample pages → **stop for approval**.
2. New page types + programmatic puzzle generator + answer keys + automated checks.
3. Audio assets + QR system.
4. Stage 1 complete → physical proof → child test.
5. Store product + helper quiz + personalization.
6. Stages 2 and 3.

Report with sample page screenshots after each step.
