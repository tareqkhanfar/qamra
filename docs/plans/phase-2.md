# Phase 2 — Parent flow MVP (outline; full plan written when the phase starts)

Changes from Addendum 1:
- Create flow is 12 steps. New optional **step 4 «ارسم صاحبك»**: intro → camera → crop/clean → name + type → generating → choose (2 options, 3 free regenerations). Skipping uses the theme's default companion.
- `Companion` model (child, book or reusable, name, type_hint, drawing_key, cleaned_key, sheet_key, approved_at, provider, model). Companions are reusable: account tab «أصحابي».
- Themes declare `companion_slot` + per-page `companion_action`. All 3 MVP themes (first day, graduation, new sibling) updated.
- Page prompts pass child + companion references. Story LLM gets the companion's name and description.
- Keepsake last page «وهكذا وُلد صاحبي» (drawing + character, child name, date).
- The drawing follows the photo privacy rules: encrypted, original deleted after approval + 24h, cleaned version deletable by the parent. Safety check on the drawing and the generated companion.
- Add-on `drawing_companion` included free.
- All brand strings come from config (قمرة / Qamra). Order IDs use the `QM-` prefix (design README).
