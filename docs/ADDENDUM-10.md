# Addendum 10 — «قلبي يعرف الله»: Islamic education book series for children (for Claude Code)

> Save as `docs/ADDENDUM-10.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-10.md — it overrides earlier prompts where they conflict."
>
> REUSE the workbook engine (Addenda 5, 6, 7): page-type library, picture library, PDF pipeline, curriculum editor, answer keys, audio QR, passport/stickers, store integration. Build it as a new product line. Do not duplicate code.
>
> Start with section 4 (proposal package) and STOP for my approval. **No religious text is final until a qualified scholar signs it off (section 3).**

---

## 1. The product

A complete Islamic education journey for children, not a book of dry facts to memorize. It should be:
- strong in content
- beautiful and fun to look at
- interactive
- gradual: the child learns to know and love Allah and His Messenger ﷺ, and lives the religion day to day

Each unit mixes: learning + story + dialogue + repetition + coloring + activities + games + daily situations + practice at home + review.

**Age:** kindergarten and the early school years (about 4–8). Parents play a central role.

**Structure: a series, not one huge book.** The full scope is too large for one comfortable book, so propose a split into **2 levels × volumes of ~96–120 pages** in the proposal, e.g.:
- **Level 1 (4–6):** knowing Allah, our Prophet ﷺ, intro to the pillars, my day with Allah, adhkar, manners.
- **Level 2 (6–8):** deeper pillars of Islam and Iman, prayer in full, Quran and short surahs, prophets' stories, Ramadan and Eid, halal and haram, «ماذا أفعل لو…؟».

The final split is for me to approve. Each volume can be sold alone or as a set.

**Name:** the working title is «قلبي يعرف الله». In the proposal, suggest 5 alternative names (short, warm, easy for a child to say). I will choose.

## 2. Required content (all from the customer brief)

1. **التعرّف إلى الله ❤️**
   - Who is Allah? Allah is our Creator and the Creator of everything.
   - Allah's blessings on us. How do I love Allah? How do I thank Him?
   - Activities to notice Allah's blessings in daily life.
2. **نبينا محمد ﷺ 🕊️**
   - Who he is; his name and lineage, simplified.
   - His beautiful qualities: his mercy to children, his honesty and trustworthiness.
   - Short authentic stories from his life.
   - How we follow his example every day.
3. **أركان الإسلام 🕌** — the shahadatayn, prayer, zakat, fasting and hajj, each with stories, activities and games.
4. **أركان الإيمان ✨** — belief in Allah, His angels, His books, His messengers, the Last Day, and qadar. Very simple examples from the child's world. **No fear-based content.**
5. **الصلاة 🧎** — why we pray, why it matters, prayer times, wudu, the order of wudu, the order of prayer, the main words a child says (simplified), step-ordering activities, review games.
6. **القرآن الكريم 📖**
   - What the Quran is; who revealed it and to whom.
   - How we respect it and take care of it.
   - Encouraging the child to read it and listen to it.
   - Short surahs suited to the age, with memorization activities.
7. **الأذكار والأدعية 🤲**
   - waking up, before sleep, before and after eating, entering and leaving the bathroom, leaving home
   - bismillah, alhamdulillah, salawat on the Prophet ﷺ, simple duas for parents
   - Every dhikr is tied to an illustrated situation: when we say it and why.
8. **الأخلاق الإسلامية 🌷 (large section)**
   - honesty, trustworthiness, kindness to parents, respect for elders, mercy
   - helping others, sharing, asking permission, forgiving and apologizing
   - guarding the tongue, not lying, not hurting others, cleanliness, respecting blessings
   - Each value comes as a story or daily situation, then «ماذا كنت ستفعل؟»
9. **الحلال والحرام ⚖️** — very simple and not frightening, with everyday examples: a Muslim chooses what pleases Allah and avoids what He forbade.
10. **قصص الأنبياء ⭐** — selected and simplified: Adam, Nuh, Ibrahim, Yusuf, Musa, Yunus (peace be upon them) and Muhammad ﷺ. Focus on the lesson and value, not long narration. Only what is established in the Quran or authentic sunnah.
11. **رمضان 🌙** — what it is, why we fast, fasting suited to the child's age, Quran in Ramadan, charity, helping others, Laylat al-Qadr, the atmosphere of Ramadan, Ramadan activities.
12. **العيد 🎈** — Eid manners, takbir, the Eid prayer, visiting family, sharing joy, charity and gifts, Eid games.
13. **بر الوالدين والأسرة 👨‍👩‍👧** — how I show love to mom and dad, help at home, speak politely, and be a useful child. Practical challenges the child does with the family.
14. **الآداب الإسلامية اليومية 🌸** — manners of eating and drinking, sleeping, speaking, asking permission, visiting, the mosque, cleanliness, dealing with others.
15. **«ماذا أفعل لو…؟»** — real situations:
    - if I lied
    - if I wronged my friend
    - if I got angry
    - if I found something that isn't mine
    - if mom said no to something I want
    - if I forgot the prayer
    
    The right action from an Islamic view, simply and gently.
16. **«يومي مع الله» 🌞🌙** — a full day: أستيقظ → أذكر الله → أصلي → آكل بأدب → أذهب للروضة → أتعامل مع أصدقائي → أساعد أهلي → أقرأ القرآن → أذكر الله قبل النوم. Religion as a way of life, not just information.

## 3. Religious accuracy — hard rules (P0)

1. **Never generate religious source text with AI.**
   - **Quran:** use a verified Uthmani text source with a license that allows commercial printing (e.g. Tanzil's verified text, under its license terms). Copy it exactly, never type it from model memory. Render it with a proper Quran font whose license allows embedding (e.g. KFGQPC Uthmanic Hafs; verify the terms). Record both licenses in `docs/licenses.md`.
   - **Hadith:** only from the major authentic collections, with the exact reference (book, number) and grading, in `content/islamic/sources.yaml`. Prefer hadith graded sahih or hasan by recognized scholars. **No weak or fabricated hadith**, and no "it is said that…" stories presented as true.
   - **Duas and adhkar:** only established wordings with their source (e.g. from Hisn al-Muslim, with the original hadith reference). Keep the exact wording; a simplified explanation goes beside it, never instead of it.
2. **Every religious statement in the book links to a row in `sources.yaml`.** A build check fails if a page has a hadith, dua, verse or ruling without a source id.
3. **Scholar review gate:**
   - A qualified scholar (I will provide one) reviews every unit page by page in the admin review workflow (reviewer role).
   - Status draft → scholar_review → approved.
   - Nothing prints or sells before approval.
   - The reviewer's name and approval date are stored. Show a «راجعه علمياً: [name]» line in the book only if the scholar agrees.
4. **Where scholars differ** (details of prayer positions, some adhkar wordings, rulings for children): use what is commonly agreed and simple. Flag the point in the review queue as `scholar_decision`. **Never pick a madhab silently.**
5. **Visual rules:**
   - Never depict Allah, the prophets, the angels or the Companions in any form: no faces, figures, silhouettes or symbolic stand-ins.
   - Prophets' stories are told through scenes, nature, places, objects, and the recurring child characters who hear the story. For example, a grandmother tells the story of Yunus while the illustration shows the sea and the whale.
   - Write the names with the proper honorifics: ﷺ and «عليه السلام».
6. **Quran handling:**
   - Verses are printed in a distinct, dignified frame.
   - Never on coloring pages or cut-out pages.
   - Never on pages likely to be thrown away.
   - Never as decoration.
   - Add a small note for parents on caring for the book.
7. **Audio:**
   - For Quran recitation, use only licensed recordings by a qualified reciter, or record our own with a qualified reciter. **Never TTS for Quran.**
   - Adhkar audio: a recorded human voice is preferred. TTS only for instructions, never for sacred text.
8. **Tone:** love before fear. No frightening imagery or threats (hellfire, punishment) for this age. Mistakes are met with repentance, apology and trying again.
9. **The AI may help with:** structure, activity ideas, simple explanations, stories of everyday children's situations (clearly fictional), and layout. All of it is marked AI-drafted and reviewed.

## 4. Proposal package — STOP after this

Produce `docs/islamic/proposal.md` + a rendered PDF with:

1. Concept, vision and 5 name options.
2. The series split (levels/volumes), with the age per volume.
3. Full table of contents: units → lessons, with page counts per unit and per volume.
4. **The retention system mapped in the plan.** Each core concept appears several times in different forms:

   story → activity → question → situation → review → home practice
   
   Show a matrix: concept × where it appears.
5. Per-unit ending structure (below) and where the parent sections fall.
6. The recurring characters: 2–3 original child characters (e.g. a brother and sister, a grandmother who tells stories) plus the reader's own personalized character. Short descriptions; no prophets or angels.
7. A visual identity per unit: color, icon and small motif, so the child remembers by symbols.
8. 10–12 sample pages, fully designed, covering:
   - a story page
   - a wudu step-ordering page
   - a dhikr-situation page
   - a «ماذا كنت ستفعل؟» page
   - a «ماذا أفعل لو…؟» page
   - a coloring page
   - a maze/search page
   - a unit-review page
   - a parent page
   - a passport page
   - the certificate
   - one Quran surah page with its frame
9. The list of every hadith, dua and verse planned, with sources, ready for the scholar (`sources.yaml` + a readable PDF).
10. Book size, paper, binding and price-by-quantity, reusing the Addendum 7 approach and the printer cost tiers.

## 5. Unit structure and retention

Each lesson rotates formats: short story, dialogue with the characters, interactive question, coloring, connect, choose the right answer, true/false, maze, find the objects, order the pictures/steps, role play, home challenge, stickers and stars.

**End of every unit:**
- «ماذا تعلّمت؟»
- «ماذا سأطبّق هذا الأسبوع؟»
- «دعاء أو ذكر الوحدة» (with its source)
- «تحدٍّ صغير مع أمي وأبي»

Every few units: a cumulative review, «ماذا تتذكّر؟» and «اختبر نفسك» pages.

**Parent section** (after each group of lessons, 1 page):
- what the child learned
- how to explain the idea
- a question to ask
- an activity to do together
- how to turn it into a daily habit

## 6. Ending of the series

- **«جواز المسلم الصغير» / «بطاقة رحلة الإيمان»:** stamps or stars for each completed unit and challenge (stickers on the sticker sheet).
- **Final fun assessment:** questions, games and practical situations, not a school exam. Parent observation stars per skill.
- **Certificate**, gender-aware: «أنا مسلم صغير / أنا مسلمة صغيرة أحب الله وأقتدي بنبيي محمد ﷺ», with the child's name, character and date.

## 7. New page types (add to the engine)

- `wudu-steps`, `prayer-steps` (order the cards)
- `dhikr-situation` (picture + when + the dhikr text from sources)
- `what-would-you-do` (choices)
- `what-do-i-do-if`
- `my-day-with-allah` (timeline)
- `blessings-hunt` (find Allah's blessings in the picture or at home)
- `surah-page` (framed Quran text, audio QR, memorization tracker)
- `pillar-card`
- `prophet-story` (scene-based, no depiction rules enforced)
- `true-false`
- `parent-guide`
- `unit-closing` (the 4 endings)
- `muslim-passport`
- `final-assessment`

Validation rules: the source-id check and the no-depiction check run at build time. The no-depiction check flags any page tagged `prophet_story` or `angels` that contains a character figure layer.

## 8. Personalization

- The child's character on the cover, the passport photo, unit openers and the certificate.
- Name in challenges and certificate, with gender-correct grammar throughout.
- The hijab choice for a girl's character follows the parent's choice.
- Characters in prayer scenes wear modest prayer clothing.
- AI cost per book: cover/character only (reuse an existing character). Target ≤ 1₪.

## 9. Store (admin-configurable)

- New product line «قلبي يعرف الله».
- Variants: volume / set, printed (spiral or perfect-bound, to decide in the proposal) / digital PDF.
- Suggested starting prices, to confirm after the printer quote:

  | Product | Price |
  | --- | --- |
  | printed volume | 79₪ |
  | set | per proposal |
  | PDF | 35₪ |
  | B2B (mosques, centers, kindergartens) | quantity tiers + logo on the back cover |

- **Add-ons:** sticker sheet, a printed parent guide, a gift box for Ramadan/Eid.
- **Seasonal:** the Ramadan and Eid units can also sell as a small standalone Ramadan book. It must be live 6 weeks before Ramadan.
- Add the product to the «أي كتاب يناسب طفلي؟» quiz as goal «تعليم ديني».

## 10. Quality checks (add to the production audit)

- `sources.yaml` complete; build fails on any unsourced religious text.
- Quran text diffed character-by-character against the licensed source.
- Scholar approval recorded for every unit before printing.
- No-depiction rule passes.
- A physical proof is reviewed by the scholar and tested with 2–3 families (with consent).

## 11. Order of work

1. Proposal package → **stop for my approval**.
2. `sources.yaml` + scholar review of the sources list.
3. Page types + validation checks.
4. Volume 1 content → scholar review → physical proof.
5. Store product + personalization.
6. Remaining volumes.

Report with sample page screenshots after each step.
