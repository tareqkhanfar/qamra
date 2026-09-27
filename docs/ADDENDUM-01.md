# Addendum 1 — Brand rename + signature features

> Overrides `CLAUDE.md` where they conflict.

---

## 0. Brand rename (applies everywhere)

- The product name is now **قمرة** (Latin: **Qamra**). Replace every mention of "حكايتي", "Hikayati" and "KidPix" in code, UI strings, emails, PDFs, metadata, SEO tags, env names and docs.
- Meaning to reflect in copy: "ليالي القمرة" — moonlit evenings when families gathered to tell stories.
- Tagline (ar): «حكاية طفلك… تحت ضوء القمر». Tagline (en): "Your child's story, by moonlight."
- Use config for brand name, domain and support contacts (`BRAND_NAME_AR`, `BRAND_NAME_EN`, `BRAND_DOMAIN`) so a rename never touches code again.
- Log the rename in `docs/decisions.md`.

## 1. Signature feature A — «رسمة طفلك صارت صاحبه» (Child's drawing becomes the companion)

This is the product's main differentiator. Treat it as MVP (Phase 2), not later.

**Flow**
1. Optional step after the photo step: "ارسم صاحبك بالقصة" — parent uploads a photo of the child's drawing (paper photo or tablet drawing). Allow skipping; if skipped, the theme's default companion is used.
2. The drawing is pre-processed: crop to paper, fix perspective, remove background/shadows, boost contrast (OpenCV). Show the cleaned drawing to the parent.
3. Parent (with the child) names the companion and picks its type hint: creature / animal / robot / other (free text, max 30 chars).
4. The image model turns the drawing into a **companion character sheet** in the book's art style, **preserving the child's shapes, colors, number of eyes/legs and quirks** — faithful, not "improved" into a generic mascot. Generate 2 options; parent picks one or regenerates (max 3 free).
5. In every story page the companion appears next to the child (both references passed to the image model). The story text mentions the companion by name, and the LLM gets its name and description so it plays a real role in the plot.
6. **Last page of the book** ("وهكذا وُلد صاحبي"): the original drawing and the final character side by side, with the child's name and date.

**Rules**
- Themes must declare `companion_slot: true/false` and describe the companion's role per page (`companion_action`). Update the 3 MVP themes accordingly.
- Safety check the drawing and the generated companion (reject violent or inappropriate content with a gentle message).
- The drawing follows the same privacy rules as photos (encrypted, auto-delete original after approval + 24h; keep only the cleaned version used in the book, which parents can delete).
- Data model: `Companion` (child, book or reusable, name, type_hint, drawing_key, cleaned_key, sheet_key, approved_at, provider, model). A companion can be reused in future books.
- Tests: pre-processing on 5 sample drawings (fixtures), prompt building includes both references, last-page layout renders.
- Acceptance: on 10 real children's drawings, parents recognize their child's drawing in the companion in ≥ 8 cases.

## 2. Signature feature B — «كتاب الصف» (Class book for kindergartens)

Extends the B2B portal (Phase 4).

- A class book product where **every child in the class appears** in the story, plus a **personal cover** per child (their own photo-based character on the cover and their name as the hero of the copy they receive).
- Structure: shared story pages where groups of 3–5 children appear per page (scene templates declare how many child slots they have), + one "portrait page" per child (their character, name, a line from the teacher, and their drawing-companion if provided), + class group page (all characters together) + teacher message + school logo.
- Assignment: automatically distribute children across scene slots so every child appears at least N times (configurable, default 2) and nobody appears too often. Teacher can adjust in a drag-and-drop page planner.
- Multi-character consistency: pass each child's approved character sheet as a reference; limit children per image to what the chosen provider handles reliably (make it a config per provider; start with 3). Flag pages for regeneration when a child is not recognizable.
- Output: one print bundle per class = N copies of the same interior + N personalized covers + per-child portrait page inserted in each copy's position. PDF naming: `{school}-{class}-{child}.pdf` plus a combined print file.
- Status board for the teacher: per child — invited / consent / photo / drawing / character approved.
- Acceptance: a class of 25 generates a complete bundle; every child appears ≥ 2 times; human review queue shows per-child coverage.

## 3. Signature feature C — «صوت أهلي» (Family voice via QR)

Phase 5 (after MVP), but design the data model now.

- On each story page, a small QR code (bottom corner, inside the safe area) links to `/{brand-domain}/v/{book_token}/{page}` which plays the page audio.
- Recording: in the account, a "سجّل صوتك" screen shows the page text in large type, one page at a time, with record / listen / re-record. Supports multiple voices per book (ماما، بابا، ستّي، سيدي) — the listener can switch voices.
- Recordings are the family's real voice (NO voice cloning). Store encrypted; accessible only via the unguessable book token; parent can revoke the token or delete recordings anytime.
- Fallback: if no recording exists, play Arabic TTS narration (TTS adapter from the main prompt).
- Grandparents can record remotely: parent shares a private recording link (expires in 7 days) — no account needed.
- Print: QR codes must be generated at print resolution and tested to scan at 21×21 cm page size.
- Data model: `Recording` (book, page, voice_label, storage_key, duration, created_by), `ShareToken` (book, scope, expires_at, revoked).

## 4. Pricing and product changes

- Products: digital, softcover, hardcover (unchanged). Add-ons: `drawing_companion` (included free in MVP — it is the hook), `family_voice` (+15₪ once per book, later).
- B2B: `class_book` priced per child with volume tiers (configurable in admin).

## 5. Updated phase plan

- Phase 0 prototype: add `--drawing path/to/drawing.jpg --companion-name "بوبو"` and produce the companion + the final "drawing vs character" page. Report companion fidelity on at least 5 drawings.
- Phase 2: feature A is part of the parent flow MVP.
- Phase 4: feature B (class book) is the core of the kindergarten portal.
- Phase 5: feature C (family voice).

Start by updating `docs/plans/` for the affected phases, list what changes in each, then continue from the current phase.
