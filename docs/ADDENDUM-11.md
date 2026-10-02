# Addendum 11 — Book visual redesign: covers and pages that sell (for Claude Code)

> Save as `docs/ADDENDUM-11.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-11.md — it overrides earlier prompts where they conflict."
> I put reference images in `/design/references/` (competitor covers and ads). They are for **quality level and energy only**. Never copy their characters, layouts, logos or brands.
> Model: plan with `/model opus` + `/effort xhigh` in plan mode, then implement with `/effort high`.

---

## 0. The problem

I reviewed `graduation-proof.pdf` («يوم تخرّج ليان»). The illustrations are pleasant, but the book does not look like a premium product a parent would pay 99–139₪ for. The competitors' covers look like movie posters. Ours looks like a page from inside the book.

### 0.1 Findings to fix (all P1)

**Cover**
1. The cover is just an interior illustration with plain white text on top: no designed title, no hierarchy, no "wow".
2. The child is small and static in the middle of a pale room. No heroic pose, no magical lighting, no depth.
3. Colors are muted and washed out. On a phone thumbnail (where parents decide) it disappears.

**Interior layout**
4. Text boxes are generic white rounded rectangles stuck on top of the art. On p.3 and p.12 a huge semi-transparent panel covers half the illustration and holds 3 short lines. Wasted space; it hides the art.
5. Story text is too small for ages 3–6, and every page uses the same layout. It feels like a template, not a designed book.
6. p.5 has **no text at all**, and p.11 crops the main character at the page edge.

**Consistency**
7. The hero's hijab changes color (white → sage → light blue) and the outfit changes between gown, red dress and pyjamas within the same day sequence.
8. The companion «قمور» changes form: a round blob on most pages, a crescent moon on p.12 and p.21.
9. The teacher and side characters change between pages.

**Closing pages**
10. Dedication, parents page, «ارسمي» page, memories page and back cover are plain and empty-looking. The back cover has a placeholder QR box with «قريباً» text.

### 0.2 What "good" means (from the references)

- Vivid, saturated, cinematic lighting.
- The child as a hero in a dynamic pose at the center.
- A rich, deep background with a magical atmosphere.
- **Designed title lettering**: big, bold, outlined, with a glow/shadow and an "بطولة: {name}" line.
- Shown as a real hardcover book mockup.

We match that level, **in our own style**, with original characters and **no brands, clubs, logos or celebrities** (the competitor ad uses a football club kit and sponsor logos; we never do that).

## 1. Art direction: three styles, done properly

Update `packages/ai/prompts/style/` and the `ArtStyle` table:

1. **«سينمائي ثلاثي الأبعاد» (new default for covers and the Magic line)**
   - Polished 3D animated-film look, soft subsurface skin, big expressive eyes, cinematic rim light and volumetric glow, rich saturated palette, depth of field, magical particles.
   - Describe the look; never name a studio.
2. **«مائي فاخر» (upgrade the current watercolor)**
   - Keep the warmth, but add contrast, deeper shadows, richer color, golden-hour or moonlit lighting, foreground framing elements and atmospheric depth.
   - No flat pale backgrounds.
3. **«كرتون ملوّن»** — bright 2D, clean outlines, bold color blocks.

**Rules for all styles**
- The child is always the visual focus: larger in frame (≥ 35% of page height on hero pages), clear face, expressive emotion matching the text.
- Every scene has foreground / midground / background depth and one light source that matches the story time.
- Local setting cues (Addendum 3) stay. The 3D and watercolor looks must still feel Palestinian/Levantine: arches, stone, olive trees, tatreez textiles, lanterns.
- **Likeness:** use the approved character sheet as the reference on every page, plus the child's photo for the cover only (higher reference weight). Run the Haiku likeness check; regenerate below threshold.

## 2. Cover system (the most important page)

Build the cover as a **layered composition in code**, not one flat image:

1. **Background plate** (AI): an epic, theme-specific scene with depth and glow. It leaves the top 30% calmer for the title.
2. **Hero layer** (AI, same style): the child in a dynamic heroic pose, plus the companion if present, lit to match. Generate it separately when the model allows, or as one image with a clear title area.
3. **Title lettering** (code/SVG, never drawn by the image model):
   - A display Arabic font with a commercial license (record it in `docs/licenses.md`), large, 2–3 lines max, with gentle arc or tilt.
   - Thick outline in a dark tone, inner gradient fill (e.g. gold → warm white), soft outer glow and drop shadow.
   - A ribbon/badge line «بطولة: {name}» (gender-aware: «بطولة البطل الرائع» / «بطولة البطلة الرائعة») with the name highlighted.
   - Make 4–5 reusable **title treatments** (gold-magic, candy-bright, night-glow, nature-fresh, heritage-tatreez). Each theme picks one in `theme.yaml` (`cover_title_style`).
4. **Small Qamra moon mark** on the front (corner) and full logo on the back.
5. **Back cover:** the same background continued (blurred), a short blurb, the child's small portrait in a frame, a barcode/ISBN area placeholder only if we get ISBNs, the logo and `qamra.app`. **Remove the «قريباً» QR block.** The QR appears only when family voice is enabled.
6. **Spine** for hardcover (title + name + moon), sized from the page count and the printer's spine formula.
7. **Mockup renders for the website and ads:** generate a 3D hardcover mockup image (front, slight angle, soft shadow on a cream surface) and a "book + open spread" mockup, from the real cover, automatically for every order and every catalog theme.

**Acceptance:** at 300×300 px (phone thumbnail) the title is readable and the child's face is clear. Test by rendering thumbnails.

## 3. Interior layout system

Replace the single "white box on top" pattern with a **layout library** (`packages/pdf/layouts/`), 8 layouts minimum, chosen per page by `layout` in the theme and rotated so no layout repeats on consecutive pages:

1. `full-bleed-cloud` — full illustration; text in an organic cloud/scroll shape that sits in the image's reserved calm area (not a rectangle).
2. `full-bleed-fade` — the text sits on a soft gradient fade at the top or bottom, no box.
3. `spread-panorama` — one illustration across two facing pages (RTL order), short text on the calm side.
4. `vignette-text` — a cream page with a spot illustration (cut-out character or object, no background) and larger text. A rest page.
5. `split-frame` — the illustration in a decorative frame (tatreez or moon border) on one side, text on the other.
6. `big-moment` — one-line text in huge display type over a dramatic full-bleed scene (climax pages).
7. `dialogue` — speech bubbles for 1–2 short lines of dialogue.
8. `ornament-text` — a text page with a decorative drop cap and corner ornaments.

**Typography rules**
- Story text 24–28 pt for ages 3–5, 20–22 pt for ages 6–8. Line height ≥ 1.8, full tashkeel.
- The child's name is always in the accent color and semi-bold.
- Max 2–3 short sentences per page. If the theme text is longer, split it across pages or shorten it with the editor.
- Text containers fit the text with comfortable padding. **Never a container that is mostly empty.**
- The page number sits in a small moon/star badge, consistent and away from art focal points.

**Composition rules in image prompts**
- Each page prompt states where the calm area for text is (matching the chosen layout).
- Characters never cropped by the trim or bleed. Keep heads and hands inside the safe area. Add an automated check: detect people in the image and flag any figure touching the safe-area edge.

## 4. Consistency locks (fix the bugs from the proof)

1. **Per-book style bible**, stored in the generation context:
   - hero outfit **per scene group** (e.g. "graduation day: navy gown + gold sash, white hijab"; "night: blue pyjamas, light-blue hijab" only if the story changes the time)
   - hijab color
   - hair
   - companion design
   - teacher / family / friends designs
2. **Companion reference sheet** generated once and passed on every page. Its form never changes. Add a QA check comparing the companion to its sheet.
3. **Side-character sheets** for recurring adults and friends in a theme (teacher, mom, dad, grandma), generated once per order or per template and reused.
4. **Text completeness check:** every story page must have text, unless the theme marks it as `wordless: true`. Fail the build otherwise.
5. The page QA (Addendum 3) adds checks for: outfit match to the scene group, hijab color match, companion match, character cropped at edge, text area free of busy detail.

## 5. Front and back matter, redesigned

- **Title/dedication page:** decorative frame, the child's portrait in an ornate moon frame, the dedication in a handwritten-style Arabic font (licensed), and small scattered stars.
- **«للأهل»:** two-column card design with icons, the child's character in a corner, and soft color blocks. Not a plain text page.
- **«ارسم أجمل لحظة»:** a playful frame with the companion peeking from the corner and crayon doodles around it.
- **«ذكرياتنا»:** a polaroid frame with tape, date and "first day / last day" prompts.
- **Back cover:** see section 2.

## 6. Proof workflow before touching all themes

1. Redo `kg-graduation` («يوم تخرّج ليان») with the new system in **two styles**: Cinematic 3D and Premium watercolor.
   - 3 cover concepts per style (different title treatments and poses).
   - The full interior with the layout library.
   - Front and back matter.
2. Produce `out/redesign/graduation-before-after.pdf`: old page vs new page side by side, plus the hardcover mockups and the phone-thumbnail test.
3. **STOP for my approval.** Then apply to the 3 MVP themes, then all live themes, and regenerate catalog covers and mockups.
4. Report the AI cost per book for each style. Covers may use the higher-quality image model (e.g. Nano Banana Pro). Interior pages stay on the cheaper model unless the quality gap is clear.

## 7. Do not

- Don't copy the competitors' compositions, characters or wording.
- No brands, logos, sports clubs, sponsor marks, celebrities or real places' trademarks in any image.
- No text drawn by the image model. All text is set in code.
- Don't change the story texts, except splitting or shortening for layout, with the edit logged.

## 8. Tareq's notes (2026-10-02)

- The text pages (activity books, workbooks, «قلبي يعرف الله») must be designed to the same level, not only the story books.
- General images for the website and the Islamic series: Tareq generates them himself from prompts Claude writes (`docs/image-prompts.md`), sends them back finished, and Claude decides where they go. No fal.ai spend on those.
- fal.ai was topped up with $10 for the redesign proof.
