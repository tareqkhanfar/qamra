# Addendum 3 — Premium book quality at the best cost (for Claude Code)

> Save as `docs/ADDENDUM-03.md` and add to the top of `CLAUDE.md`: "Read docs/ADDENDUM-03.md — it overrides earlier prompts where they conflict." Then: "Plan it in docs/plans/addendum-03.md, implement, and report with a sample book + cost breakdown."

Goal: every Qamra book must look like a premium, professionally illustrated and typeset Arabic children's book, while the AI cost stays **≤ $2.50 per 20-page book** (target $2.00).

---

## 1. Providers and models (admin settings)

**Images**
- Add a generic **fal** image provider that accepts any fal endpoint (not only FLUX).
- Default: **Nano Banana 2 on fal** — text-to-image `fal-ai/nano-banana-2` and its edit/reference-image variant for character-consistent generation. Verify exact endpoint IDs, parameters (reference images, resolution, aspect ratio, seed if supported) and prices from fal's model pages. Do not guess.
- Fallback provider: `fal-ai/flux-2-pro/edit` (rename the admin field "FLUX model" to "fal fallback model"). Auto-switch to fallback only after 2 failed attempts on the primary, and log it.
- Keep the direct Gemini and OpenAI adapters, but they stay inactive unless selected and keyed.

**Text (Anthropic API)**
- Story writing + vowelization: a Sonnet-class model (e.g. `claude-sonnet-5`).
- Safety review, image QA and short checks: a Haiku-class model (e.g. `claude-haiku-4-5-20251001`).
- Do not use Opus by default (too expensive for this job); keep it selectable in admin.
- Verify exact model strings on docs.claude.com before setting defaults.
- Use prompt caching for the long fixed parts (style guide, theme rules, JSON schema) to cut cost.

## 2. Cost strategy (implement all)

1. **Resolution tiers**
   - Previews: lowest resolution the model offers (watermarked).
   - Finals: generate at ~1K, then upscale with fal's image upscaler to print size (2480×2480 px + 3 mm bleed at 300 DPI).
   - Run an A/B on one book: "1K + upscale" vs "2K native". Pick the cheaper option whose print proof looks equally sharp. Record the decision in `docs/decisions.md`.
2. **Generate once, reuse**
   - Character sheet and companion sheet are generated once per child and reused for all books.
   - Cache per-theme background plates where a scene has no child in it.
3. **Automatic QA before any regeneration.** A Haiku vision check scores each page on:
   - child likeness vs character sheet
   - correct number of children/characters
   - extra fingers/limbs, distorted faces
   - text accidentally drawn in the image
   - outfit consistency
   - empty space kept for the text box

   Only pages below threshold get regenerated, max 2 auto-regenerations per page. After that, flag the page for human review.
4. **Budget guard**: hard cap per book (default $3.00, configurable). If exceeded, stop and flag in admin instead of continuing.
5. **Concurrency**: 4–5 pages in parallel, with queue retries and exponential backoff. Never regenerate the whole book because one page failed.
6. **Cost dashboard**: show average cost per book, per page, and regeneration rate per theme. Themes with a high regeneration rate get their scene prompts improved.

## 3. Illustration quality rules

Create `packages/ai/prompts/style/qamra_style.md` (from `/design/ART_STYLE.md` if present) and inject it into every image prompt:

- **Style**: soft watercolor/gouache children's book illustration, warm moonlit-and-golden palette, gentle paper texture, clean readable shapes, expressive happy faces, no photorealism.
- **Local setting cues** (unless the theme says otherwise):
  - Palestinian/Levantine village and city life: limestone houses, stone terraces, olive groves, prickly pear cactus, grapevines, old souq arches, tiled floors, family living rooms.
  - Avoid Tuscan/European cues: no cypress rows, no Italian villas.
- **People**: modest everyday clothing; hijab only when the parent selected it; respectful, non-stereotyped grandparents and families.
- **Composition**: every page prompt reserves clean negative space for the text box. The theme's `layout` field decides where (top / bottom / side). No text, letters or signs inside the illustration; all text is added in the PDF.
- **Consistency**:
  - Lock the child's outfit per book: the outfit is chosen once from the theme and stored in the book's generation context.
  - Keep the same lighting and time of day within a scene sequence.
  - Pass the character sheet (and companion sheet) as references on every page.
- **Page prompt template**: `[style guide] + [setting cues] + [scene description from theme/story] + [characters present with reference labels] + [outfit lock] + [composition/text-space instruction] + [negative instructions]`.
- **Safety**: nothing scary, violent, or unsafe (e.g. a child alone near water or fire). Every image passes the safety check.

## 4. Book design and typesetting (the part that makes it feel premium)

Format: **21 × 21 cm square**, 3 mm bleed, 10 mm safe margin, 300 DPI, CMYK-safe colors, fonts embedded.

**Arabic book rules**
- **Right-to-left binding**: the spine is on the right, page order runs right to left, and the cover/back cover and spreads are imposed accordingly. Test this with the printer's template.
- Page numbers in Arabic-Indic digits (١، ٢، ٣).
- Story text font must render full diacritics perfectly: use a high-quality Naskh font (e.g. Noto Naskh Arabic or Amiri, verify the license allows commercial embedding).
  - Size 18–22 pt for ages 3–5, 15–17 pt for ages 6–8.
  - Line height ≥ 1.8 so the tashkeel never collides.
- Brand display font only for titles and the cover.
- Text box: soft rounded cream panel with slight transparency over the illustration's reserved space. Never place text over busy areas. Auto-check contrast.
- Max ~35 words per page for ages 3–5.

**Book structure (every book)**
1. Cover: child as hero, title with the child's name, Qamra moon logo on the back only.
2. Dedication page: «إلى {child}… » with an optional message from the parent (max 120 chars).
3. Story pages: 16–20. Mix full-bleed illustrations with 2–3 spread layouts per book so it doesn't feel repetitive.
4. «وهكذا وُلد صاحبي» page (if a drawing companion exists).
5. «للأهل» page: the lesson + 2 questions to ask the child.
6. Back cover: short blurb, small moon logo, and a QR code (reserved for family voice later).

**Proofing**
- Generate a low-res web proof and a print PDF.
- Add an automated preflight: bleed present, images ≥ 300 DPI effective, fonts embedded, no text in the bleed zone, page count divisible by the printer's signature (usually 4).

## 5. Human review (last gate)

The admin approval queue shows the whole book as spreads, with QA scores and flags, one-click regenerate per page (counts toward budget), text edit, and approve for print. Nothing goes to print without approval.

## 6. Security (do this before any real child photo)

1. Don't expose the app port publicly. Bind the app to localhost and put Nginx in front with HTTPS (Let's Encrypt) on the domain.
2. Protect `/admin` with a strong password, 2FA (TOTP), login rate-limiting, and an optional IP allowlist.
3. Firewall (ufw): allow only 22, 80, 443.
4. API keys encrypted at rest; the browser only ever sees the last 4 characters.
5. Confirm fal's and Anthropic's API terms (no training on our inputs) and reference them in the privacy policy page.

## 7. Acceptance criteria

- One full sample book per MVP theme generated end to end on 5 test children (family volunteers with written consent), including 2 girls with hijab and 1 with glasses.
- Child recognizable on ≥ 90% of pages after auto-QA; no text artifacts in images.
- Average AI cost ≤ $2.50 per 20-page book, shown in the cost dashboard.
- Print PDF passes preflight and a physical proof from the printer looks sharp.
- Report back with: sample PDFs, cost per book breakdown, regeneration rate, and the 1K-vs-2K decision.
