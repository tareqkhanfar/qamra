# Addendum 7 — «مغامراتي مع عائلتي»: family adventure activity book (for Claude Code)

> Save as `docs/ADDENDUM-07.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-07.md — it overrides earlier prompts where they conflict."
>
> REUSE the workbook engine from Addenda 5 and 6: page-type library, picture library, PDF pipeline, curriculum editor, answer keys, audio QR, store integration. Build this as a third activity-book product line. Do not duplicate code.
>
> Start with section 3 (proposal package) and STOP for my approval before designing the full book.

---

## 1. The product

A creative, interactive children's activity book where the child learns through **play, adventure, daily-life situations and doing things with their family**, not just by solving exercises. The child should feel the book is a series of real adventures with their family, not homework.

**Age:** 3–7. Each activity has a simple version (3–4) and a challenge version (5–7) where it makes sense, marked with ⭐ / ⭐⭐.

**Skills it must build** (map every activity to at least one):
- intelligence & thinking, observation & focus, memory
- counting & simple math, expression & speaking
- emotions & communication, problem solving, creativity & imagination
- responsibility, life skills, cooperation with parents

**Every activity** has a part the child does alone and, often, a small mission with a parent, marked «هيا نفعلها معاً! 👨‍👩‍👧».

## 2. Positioning in the store

| Product | Use |
| --- | --- |
| دوسية التأسيس | school curriculum, term by term |
| رحلتي الأولى | readiness skills from age 3 |
| **مغامراتي مع عائلتي** | family time, life skills, speaking, emotions, weekends, holidays, and a gift |

Add it to the «أي كتاب يناسب طفلي؟» helper, with a 4th question about the goal (school skills / family time).

## 3. Proposal package (what the customer asked for before design) — STOP after this

Produce `docs/family-book/proposal.md` + a rendered PDF with:

1. **Full concept and vision.**
2. **Proposed table of contents.**
3. **Sections and activities breakdown:** each activity with its goal, child part, parent part, materials needed (only common household items), time needed (5–20 min) and difficulty.
4. **Proposed page count per section and in total.** Target 96–128 pages + sticker sheet + cut-out inserts.
5. **8–10 sample pages**, fully designed, for approval of the look.
6. **Proposed book size:**
   - recommend 21×28 cm (or A4) portrait for writing/drawing space
   - justify the choice
   - alternative sizes with the cost impact of each
7. **Paper:**
   - interior 120–140 gsm uncoated/matte (good for pencil, crayons and markers without bleed-through)
   - cover 300–350 gsm with matte lamination
   - sticker sheet on matte sticker paper
   - cut-out pages on 200+ gsm card with perforation if the printer supports it
8. **Binding and printing:**
   - wire-o/spiral so it lays flat
   - full-color digital print for small runs, offset for large runs (explain the break-even)
9. **Price by quantity:** a table for 1 / 10 / 50 / 100 / 500 copies. It is computed from `print_cost_tiers` in admin (costs to be filled from the printer's quote) + our margin rules. Leave the cost placeholders clearly marked until I enter the printer's real prices.

## 4. Sections (all from the customer brief — keep the order as a journey)

Each section opens with a spread: title, the child's character with the family, a short story hook, and the passport stamp they can earn.

1. **بيتي مدرسة 🏠**
   - Treasure hunts at home for colors, shapes and objects («ابحث عن 3 أشياء دائرية في المطبخ»).
   - Count what you find; draw your favorite find.
2. **مغامرة السوق 🛒**
   - Shopping list to draw or write; count items; compare quantities (more/less); choose products (healthy / needed / not needed).
   - Role play: seller and buyer.
   - Price tags using the Qamra play money.
3. **الشيف الصغير 👩‍🍳**
   - Simple, safe recipes made with parents, e.g.:
     - زعتر وزيت sandwich
     - fruit salad
     - labneh balls
     - yogurt with fruit
   - Order the recipe steps (picture cards), count ingredients, name them.
   - A **safety box on every recipe**: adult handles the knife and heat; ask about allergies; wash hands.
4. **يومي الجميل ☀️🌙**
   - Order the day's events; morning/evening; before/after.
   - Build my own routine chart (sticker version).
5. **احكي لي 🗣️**
   - Conversation cards and questions between child and parent to grow speaking, expression and vocabulary: «شو أحلى إشي صار معك اليوم؟», describe a picture, tell a story from 3 pictures.
   - Parent tips on how to extend the conversation.
6. **مشاعري 💛**
   - Recognize emotions (faces), choose the right feeling for a situation, a feelings thermometer, "when I feel … I can …".
   - Talk with a parent about a situation.
   - Gentle, supportive tone. This is not therapy.
7. **أنا مسؤول ✅**
   - Simple home tasks (tidy toys, water plants, set the table), a weekly achievement chart with reward stickers.
8. **مستكشف الطبيعة 🌿**
   - Outdoor scavenger hunt (leaf shapes, colors, sounds, a stone, an olive leaf, a bird), observation journal, leaf rubbing, nature bingo.
   - Safety note: always with an adult.
9. **مهن عائلتي 👷‍♀️**
   - Learn professions; interview a parent about their work (question template); role play; «لما أكبر بدي أصير…» drawing.
10. **متجري الصغير 🏪**
    - A home shop game with Qamra educational money (cut-out coins and notes), counting, simple adding, choosing, making change (challenge level).
    - **The play money must be clearly fictional** (Qamra designs, "للعب فقط", never resembling real shekels or dinars).
11. **ليلة الألعاب العائلية 🎲**
    - Memory games, question cards, movement challenges, simple group games (cut-out cards), and a family scoreboard.
12. **نمثل ونحكي 🎭**
    - Unfinished stories and situations; the child completes the story or finds a solution; role cards; simple finger-puppet cut-outs.
13. **ذكرى اليوم 📸**
    - A memory page after each adventure: draw or write what we did, paste a photo, rate it with stars, a quote from mom/dad.
14. **تحدي العائلة الكبير 🏆**
    - A 7-day challenge, one different activity per day, with a checklist and a final family reward idea.
15. **جواز سفر المغامر الصغير 🛂**
    - An achievement passport where the child collects a stamp or sticker for each completed adventure. Badges:
      - مغامر
      - مفكّر
      - فنان
      - مستكشف
      - طبّاخ صغير
      - طفل مسؤول
      - صديق لطيف
      - (plus section badges)
    - Placed at the beginning of the book so the child sees it grow.
16. **شهادة المغامر 🎓** at the end, with the child's name and character, the family's name, and the date.

Sequencing: start with easy home adventures, then outside (market, nature), then responsibility and emotions, then family challenge and celebration. Vary activity types on every spread: drawing, counting, sticking, cutting, talking, moving, cooking, observing.

## 5. Page design

- Childlike, cheerful, full of movement and adventure; not a school book.
- Each page clear and uncluttered, with:
  - a catchy activity title
  - lovable characters (the child's character and family)
  - short simple instructions (≤ 10 words for the child)
  - enough space to write, draw or color
  - encouraging symbols/stickers
- A distinct **parent box** («للأهل» / «هيا نفعلها معاً!») with 1–3 short lines: what to do, what to ask, how to praise.
- Icons per activity: 🏠 at home / 🌳 outside / 👨‍👩‍👧 with family / ⏱ time / ⭐ level.
- Large friendly Arabic font, generous white space, printable in color.

## 6. New page types to add to the engine

- `scavenger-hunt` (checklist + drawing boxes)
- `shopping-list` (draw/write)
- `price-tags`, `play-money` (cut-out, fictional)
- `recipe-steps` (picture cards to order + ingredient count + safety box)
- `routine-builder` (stickers)
- `conversation-cards`
- `picture-talk`
- `feelings-faces`, `feelings-thermometer`, `situation-feeling-match`
- `chore-chart` (weekly)
- `nature-bingo`, `observation-journal`
- `interview-template`
- `role-cards`
- `family-game-cards` (cut-out) with scoreboard
- `story-finish`
- `memory-page` (photo slot + drawing + stars + parent quote)
- `seven-day-challenge`
- `passport` (stamp slots per badge)
- `badge-sticker-sheet`
- `certificate-family`
- `parent-box` component

**Cut-out and sticker inserts** are generated as separate print files:
- the sticker sheet: passport badges + rewards + routine icons
- a card-stock sheet: money, game cards, role cards, recipe step cards

All on the printer's templates, with cut lines.

## 7. Personalization (Qamra difference)

- The child's character on the cover and throughout; name in titles and missions («مغامرة سلمى في السوق»).
- **Family members:**
  - The parent enters the names and roles of up to 6 family members (ماما، بابا، إخوة، ستّي، سيدي).
  - These appear in missions and parent boxes.
  - **Optional add-on:** illustrated family characters generated from family photos (same pipeline and privacy rules as the child). The family then appears in the illustrations.
- Family city (from the cities list) used in the nature and market adventures.
- The passport shows the child's character as the passport photo.
- The certificate shows the child's name + «عائلة {family_name}».
- AI cost per book: only characters (≤ 1₪ without the family add-on; the family add-on is costed per extra character).

## 8. Store and pricing (admin-configurable)

**Suggested prices (retail)**

| Variant | Price |
| --- | --- |
| Printed book (wire-o, color, with sticker sheet and card-stock insert) | 89₪ |
| Digital printable PDF | 35₪ |

**Add-ons**

| Add-on | Price |
| --- | --- |
| Illustrated family characters (up to 4) | +30₪ |
| Extra sticker sheet | +8₪ |
| Crayon kit | +15₪ |
| Gift box | +15₪ |

**Bulk / B2B**
- Quantity price tiers (10/50/100/500) from `print_cost_tiers` + margin rules.
- A "request a quote" form for nurseries, schools, NGOs, and companies (e.g. family-day gifts).
- Option to add their logo on the back cover.

**Seasonal promotions:** summer holiday («صيف العيلة»), Ramadan/Eid family edition later.

Show price, cost and margin in admin like the other products.

## 9. Content quality and safety

- An educator reviews all activities for age-appropriateness and variety.
- Recipes:
  - no raw eggs
  - no nuts by default (list alternatives)
  - an allergy reminder on each recipe
  - adult supervision for knives and heat
- Outdoor activities: supervision reminder; no touching unknown plants or animals.
- Emotions section: supportive language, no diagnosing, no pressure.
- Play money visibly fake.
- Inclusive of different family shapes (e.g. a child raised by grandparents or a single parent): family members are editable and nothing assumes both parents.
- Culturally local and respectful (Muslim and Christian families).

## 10. Deliverables for the customer (editable originals)

- Final print-ready PDFs (interior, cover, sticker sheet, card-stock insert) with bleed and crop marks, per the printer's specs.
- If the customer purchases the "editable files" option (admin-priced), export the editable sources: SVG assets + page data + a layout package. Document what "editable" includes.

## 11. Quality checks (add to the production audit)

- Every activity mapped to skills; the variety check shows no identical page type on consecutive pages.
- Personalization renders correctly with 1 to 6 family members and with long Arabic names.
- Cut-out and sticker files align with the printer's die/cut templates (test print).
- Physical proof tested with 2–3 real families (with consent); adjust based on feedback.

## 12. Order of work

1. Proposal package (section 3) → **stop for my approval**.
2. New page types + parent box + inserts.
3. Full book content (educator review) + personalization.
4. Physical proof + family test.
5. Store product, add-ons, quantity tiers, quote form.

Report with sample page screenshots after each step.
