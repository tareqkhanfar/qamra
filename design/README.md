# قمرة (Qamra) — Design handoff

Arabic-first, RTL web product: a child's photo (and drawing) becomes an illustrated, printed storybook where the child is the hero.
Source of truth: the "قمرة — Qamra" Design canvas (12 pages, 77 artboards). Tokens: `tokens.json`. Tailwind: `tailwind.config.js`. Logos: `logo/`.
Formerly حكايتي / KidPix 2.0 — every occurrence has been renamed; order IDs now use the `QM-` prefix.

## Global rules
- `<html lang="ar" dir="rtl">` everywhere. Use logical utilities (`ms-/me-/ps-/pe-/start-/end-`), never `ml/mr`.
- Directional icons mirror in RTL: "next" arrows point **left**, "back" arrows point **right**. Steppers and progress bars fill from the right.
- Numbers use Latin digits (0–9) for prices, phones, order IDs. Phone inputs are `dir="ltr"` with right-aligned text.
- Tap targets ≥ 44px. Mobile primary action = sticky bottom bar (min-height 56px, safe-area padding).
- Colour roles: **amber-500** = conversion moments only (start a book, approve character, "ready — draw the book", place order). **night-900** = normal "continue". Danger red only for delete.
- Motion: star twinkle, book float, skeleton pulse. All loops disabled under `prefers-reduced-motion`.
- Illustrations in the mockups are placeholders built from two parts (`Kid`, `Scene`). Replace with generated art; keep the square framing and "space at top for text" convention.
- Bracketed text like `[السعر]`, `[عدد]`, `[اسم الروضة]` = real value still to be decided. Never ship brackets.

## Screens (route → canvas artboard)
### Public
| File | Artboard | Notes |
|---|---|---|
| `landing.html` | landing — desktop / mobile | Hero before/after, 3 steps, themes, sample-pages carousel, privacy, testimonials (placeholders — use real quotes only), pricing ×3, kindergartens band, FAQ (`<details>`), footer. Mobile shows the sticky CTA bar after the hero. |
| `themes.html` | themes — catalog | Filters: age chips, occasion chips, sort select. 3-col grid of theme cards. |
| `theme-detail.html` | theme-detail — mobile | Hero scene, chips, values, 4-page peek (horizontal scroll), product prices, sticky CTA with "from" price. |
| `kindergartens.html` | kindergartens — desktop | B2B: 5-step class flow with owner tags (school / Hikayati / parents), book contents, trust, demo form. |

### Parent create flow (mobile-first, 11 steps; one desktop example)
`create-step-1-child.html` → `…-2-consent` → `…-3-photo` → `…-4-style` → `…-5-character` → `…-6-theme` → `…-7-review` → `…-8-generating` → `…-9-preview` → `…-10-checkout` → `…-11-success`. Desktop reference: `create-step-3-photo` desktop (horizontal 11-dot stepper, QR hand-off to phone).
- Step 2: "continue" disabled until guardian checkbox is ticked.
- Step 3: client-side checks (face count, blur, brightness, face size) show live ✓/! rows; rejected photos never upload (see States → Photo rejected).
- Step 5: "Regenerate" limited to 3 (show remaining). Optional "what doesn't look like her" chips feed the retry.
- Step 7: drafts; per-page text edit (180 char soft limit + counter), "redraw page", "restore original".
- Step 8: messages rotate every ~3.5s; progress is real pages-done/total; WhatsApp notify toggle; user may leave.
- Step 9: watermark "معاينة · حكايتي" on preview pages; product radio cards.
- Step 10: cash on delivery (card = "coming soon"); order summary with delivery fee per city.

### Parent account
`account-books.html` (children avatars + books grid + in-progress banner + bottom tab bar), `book-reader.html` (RTL spread: illustration on the right page, text on the left; audio button placeholder; night mode), `order-tracking.html` (5-step vertical timeline), `account-privacy.html` (what we keep, per-child delete, delete account with OTP confirm).

### Kindergarten portal (desktop-first)
`portal-dashboard.html`, `portal-import-children.html` (Excel → column mapping → validation table: ok / warning / error, errors excluded until fixed), `portal-classroom-invite.html` (class link + copy + WhatsApp share, per-child status: مدعو → وافق → رُفعت الصورة → معتمد, reminders), `portal-class-theme.html` (theme choice + school page: logo, class photo, teacher message, friends page, live 21×21 preview), `portal-batch-review.html` (batch progress + bulk review grid with multi-select approve / request redraw), `portal-order-invoice.html` (invoice preview + payment method + confirm).

### Admin
`admin-approval-queue.html` (queue list with auto-QA flags → page grid with face-similarity score per page, approve / regenerate selected), `admin-orders-print.html` (print batches with PDF + shipping labels, orders table), `admin-theme-editor.html` (page list, layout select, scene prompt, Arabic text template with gendered variables `{وصل/وصلت}`, live preview for girl/boy), `admin-cost-conversion.html` (KPIs, funnel, per-book cost breakdown, daily orders — sample data only).

### System states (mobile)
Empty, Loading (skeleton), Error (friendly + retry + support + error code), Photo rejected, Generation failed (auto-retry, retries not charged), Offline (banner + local draft saved + disabled CTA).

### Storybook print layouts (PDF)
Square 21×21 cm, 3 mm bleed → 816×816 px artboards. Trim inset 11 px, safe area 49 px (10 mm inside trim). Layouts: cover, title page (dedication), full-bleed illustration + text box, split (illustration top / text bottom), text-only with ornament, class page (graduation), back cover. Book body text ≥ 30px at artboard scale (well above 12pt at print size).

## Components
Buttons (primary amber, solid night, secondary outline, ghost, destructive; hover glow, pressed, disabled, loading; 56/48/44 heights), text input (default, focus ring amber-100, error), chips (toggle, `aria-pressed`), radio/checkbox, radio cards (selected = 3px amber border + check badge), photo uploader (dropzone, face-guide overlay, quality check list), stepper (mobile bar + label, desktop dots), cards (theme, book with spine shadow, order with mini tracker), status chips (8 states, each with a dot), tabs, toast (success/error with action), modal (night-950 55% scrim), table, friendly progress bar, empty state, skeleton.

## Logo
Two options on the canvas: A "كتاب ونجمة" (horizontal wordmark + open book with rising star) and B "ختم الحكاية" (rounded-square badge, works as app icon/favicon and on the back cover). Pick one before building the header.

---

# Addendum 1 — Qamra rebrand + new features

## Brand
- Name **قمرة / Qamra** («ليالي القمرة»). Tagline: «حكاية طفلك… تحت ضوء القمر».
- Palette unchanged in hex (it already reads as moonlight); the amber family is now called **moon-gold** (`moon-*` alias in Tailwind).
- Logo: 3 options on the canvas (foundations › Logo). **A «هلال على صفحة»** is used as the placeholder in every screen. B «بدر ونجمة», C «قمرة في نافذة». Files in `logo/`: mark in 4 versions (color, on-dark, mono-black, mono-white) + lockup per option. Lockup text must be outlined before production.
- Moon-phase motif: `Moon` component (`p` 0→1). Used in the create-flow header (`p = step/12`), companion generation, class-book setup and as a book ornament.

## Create flow is now 12 steps
1 child · 2 consent · 3 photo · **4 ارسم صاحبك (new, optional)** · 5 style · 6 character · 7 theme · 8 review · 9 generating · 10 preview · 11 checkout · 12 success. Existing files keep their names (`create-step-5-style` = old step 4, etc.); canvas titles are renumbered.

## New screens (route → canvas artboard)
### «رسمة طفلك صارت صاحبه» (canvas page: رسمة طفلك صارت صاحبه)
| File | Notes |
|---|---|
| `landing.html` (changed) | Hero = 3 frames: photo + crayon drawing → both on a book page. Headline «طفلك البطل… ورسمته صاحبه». Mobile hero updated too. |
| `create-step-4-companion-intro.html` | Before/after example, 3 bullets, primary «صوّر رسمة ليان», clear «تخطّي». |
| `create-step-4-companion-camera.html` | Camera-first, paper-frame corner guides, live tips chips (white paper / light / shadow), auto-capture when steady, gallery fallback. |
| `create-step-4-companion-crop.html` | Original / cleaned toggle, 4 crop handles, rotate, "remove paper colour & shadows". |
| `create-step-4-companion-name.html` | Name input, type (مخلوق/حيوان/روبوت/غير ذلك), optional traits. |
| `create-step-4-companion-generating.html` | Moon waxes as progress; rotating messages; user may continue the flow. |
| `create-step-4-companion-choose.html` | 2 options, each shown beside the original drawing; 3 regenerations. |
| `account-companions.html` | Reusable companion cards (character + drawing sticker), «حكاية جديدة معه». New tab "أصحابي" in the bottom bar. |
| Book: hero + companion page, **«وهكذا وُلد صاحبي»** keepsake last page (drawing + character, child name, date, framed). |

### «كتاب الصف» (canvas page: كتاب الصف, desktop-first)
`classbook-setup` (theme, appearances per child stepper, personal cover/portrait/companion toggles, logo, teacher message) · `classbook-readiness` (18 child cards, 5-step status: دعوة، موافقة، صورة، رسمة، شخصية معتمدة; filters; bulk WhatsApp reminder) · `classbook-page-planner` (pages as columns, drag child chips into slots, coverage meter per child, under-target warnings, auto-distribute) · `classbook-review` (page grid with flag/regenerate, per-child coverage check) · `classbook-covers` (carousel of personal covers + thumbnail strip) · `classbook-print-bundle` (copies, price tiers, delivery to school, invoice). Book layouts: class group page, per-child portrait page, teacher message page.

### «صوت أهلي» (canvas page: صوت أهلي)
`voice-record` (large page text, voice chips ماما/بابا/ستّي/سيدي, waveform, re-record/listen, 24-page progress) · `voice-invite` (choose who & pages, WhatsApp message preview, invite status) · `voice-elder` (no login; 30px text, 132px record button, 72px actions, one page at a time) · `voice-listener` (opened from printed QR; illustration, play, voice switcher, prev/next; static page, audio streamed). Print spec sheet: QR 18 mm + 2 mm quiet zone on a light card, outer bottom corner inside the 10 mm safe area, moon icon + «امسح واسمع» at 8pt, short URL `qamra.app/l/{book}/{page}`.

### Marketing (canvas page: التسويق)
3 Instagram posts (1080×1080), 2 stories (1080×1920), an 8-second looping reel storyboard (5 frames with timings), A5 flyer for kindergartens (559×794 px at 96 dpi — export PDF at 300 dpi).

## Interaction notes (new)
- Companion is optional everywhere; books without one simply omit the companion and the keepsake page.
- Drawing clean-up runs on device before upload; the original drawing is kept (it is printed on the keepsake page) and follows the same deletion rules as photos.
- Class book: only children with an approved character enter the planner; children without a drawing appear without a companion.
- Voice: max 3 voices per page; the QR works even if voices are recorded after printing.
