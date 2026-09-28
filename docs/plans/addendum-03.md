# Addendum 3 plan — premium books at ≤ $2.50

Source: `docs/ADDENDUM-03.md` (overrides earlier prompts where they conflict). Started 2026-09-28.

## 1. Verified facts (checked 2026-09-28)

Prices and parameters below come from the providers' own pages and API schemas, not memory. They are also written to `packages/ai/src/qamra_ai/pricing.yaml` with the check date.

| What | Verified value | Source |
|---|---|---|
| Nano Banana 2, text-to-image | `fal-ai/nano-banana-2`: `prompt`, `resolution` 0.5K/1K/2K/4K (default 1K), `aspect_ratio` (1:1, 3:2, 16:9, 21:9 …), `seed`, `num_images` 1–4, `output_format`, `safety_tolerance` 1–6, `sync_mode`, `limit_generations` | fal OpenAPI schema |
| Nano Banana 2, references | `fal-ai/nano-banana-2/edit`: the same fields plus `image_urls`, up to 14 reference images | fal model page + schema |
| Nano Banana 2 price | $0.08 per image at 1K; 0.5K ×0.75 ($0.06); 2K ×1.5 ($0.12); 4K ×2 ($0.16); web search +$0.015; high thinking +$0.002 | fal model pages |
| Fallback | `fal-ai/flux-2-pro/edit`: up to 9 references (9 MP total), `image_size` {width, height}, `seed`, `safety_tolerance` 1–5. $0.03 for the first output megapixel + $0.015 per extra megapixel of input and output | fal model page + schema |
| Upscaler (default) | `fal-ai/seedvr/upscale/image` (SeedVR2): `upscale_factor` 1–10 or `target_resolution`, png/jpg/webp output. $0.001 per megapixel | fal model page + schema |
| Upscaler (alternative) | `fal-ai/recraft/upscale/crisp`: PNG input, $0.004 per image | fal model page + schema |
| Story model | `claude-sonnet-5`: $2 in / $10 out per MTok; cache write $2.50, cache read $0.20; minimum cacheable prefix 1024 tokens; adaptive thinking on by default | platform.claude.com pricing + model docs |
| QA/safety model | `claude-haiku-4-5-20251001`: $1 in / $5 out; cache write $1.25, cache read $0.10; minimum cacheable prefix 4096 tokens | same |
| Opus (selectable, not default) | `claude-opus-5` $5/$25; `claude-opus-5-5` $4/$20 | same |
| Anthropic data use | "Anthropic may not train models on Customer Content from Services." (Commercial Terms, effective 2025-06-17) | anthropic.com/legal/commercial-terms |
| Google (the model behind Nano Banana 2) | Paid Gemini API: "Google doesn't use your prompts … or responses to improve our products"; prompts are logged for a limited time for abuse monitoring (terms modified 2026-04-28) | ai.google.dev/gemini-api/terms |
| fal data use | The terms (updated 2026-09-08) let fal use *anonymized or aggregated* usage data to build products and models. The DPA (2026-07-31) limits personal data to our instructions and allows processing "Deidentified Data to improve the Services". There is no explicit "never trains on your inputs" sentence for non-enterprise accounts. | fal.ai/terms, fal.ai/legal/data-processing-addendum |
| fal retention controls | Request payloads (which contain our reference images) are kept 30 days unless `X-Fal-Store-IO: 0` is sent. Generated files follow `X-Fal-Object-Lifecycle-Preference: {"expiration_duration_seconds": N}`. `sync_mode` returns images inline. | fal docs "Platform headers", "Data retention" |

**Action for Tareq:** ask fal for written confirmation of no training on our inputs (their enterprise page promises it for enterprise customers). Until then we minimize what fal keeps: `X-Fal-Store-IO: 0` on every call, 15-minute expiry on any generated file, `sync_mode`, and references sent inline (never uploaded to fal's CDN). The privacy page states this.

## 2. Decisions

1. **Image stack.** The default is fal Nano Banana 2 at 1K for finals and 0.5K for previews. The provider picks `/edit` automatically when references are passed. After 2 failed attempts on the primary it falls back to `fal-ai/flux-2-pro/edit` and logs the switch; the ledger and the book record it too.
2. **Generic fal provider.** It works with any fal endpoint. Known families (Nano Banana, FLUX.2, SeedVR/Recraft upscalers) get their exact argument shapes and prices. Any other endpoint gets a generic shape and a conservative price for the budget guard.
3. **The cover is the outfit anchor.** The cover is drawn first in the book's locked outfit and must pass QA. Every page then gets: character sheet (identity) + cover (outfit, style, palette) + companion sheet. This keeps outfits consistent at no extra image cost.
4. **Locations and lighting.** Themes define named locations with a fixed description, repeated word for word on every page set there. Each page also has a time of day. This keeps a room and its light the same through a sequence.
5. **The style guide is one file**, `packages/ai/src/qamra_ai/prompts/style/qamra_style.md`, split into sections that the page prompt assembles in the addendum's order. The addendum names `packages/ai/prompts/style/`; our prompts live inside the Python package so they ship in the Docker image. The chosen art style (watercolor default; crayon and paper-cut stay optional) only sets the painting medium. Palette, setting, people and composition rules come from the house style.
6. **Book structure** (Arabic, RTL, spine on the right). The interior is in reading order:
   - Page 1: title + dedication (a left-hand page, alone).
   - Story pages 2…N+1: spreads always start on an even page. In RTL the even page is the *right* half, so a spread's right half goes on the even page.
   - Then the «وهكذا وُلد صاحبي» page (when a drawing companion exists), the «للأهل» page, and "The End" + activity pages to fill up to a multiple of 4.
   - The cover is a separate wrap PDF, laid out front | spine | back (the mirror of an LTR wrap). The spine width is a setting.
7. **Layouts:**
   - `full`: full-bleed art with a cream panel at the top, bottom or outer side.
   - `split`: art on the upper part, text on cream below.
   - `spread`: one 16:9 image cropped to 426×216 mm across two pages.
   - `no_child: true` marks a background plate (no hero), cached per theme, version and style, and reused by every book.
8. **QA.** A Haiku vision call returns sub-scores: likeness, character count, anatomy, text in image, outfit, text space, safety, companion. A page passes at a weighted score ≥ threshold (default 0.75) with no hard fail. Hard fails are unsafe content, text in the image, a wrong count or broken anatomy. At most 2 automatic redraws per page, then the page is flagged for human review with its best attempt kept. The QA prefix is cached (system + reference images).
9. **Budget.** The cap applies per book (default $3.00, and a book's cap can be raised in review). Every paid call reserves its estimated cost first. When a reservation would cross the cap, generation stops and the book is flagged `budget_exceeded`. Pages already drawn are kept. Character and companion sheets are per child and are logged against the child, not a book.
10. **Resolution.** The default mode is `1k_upscale`: 1K, then the SeedVR ×2.5 upscaler, then an exact Lanczos fit to 2551 px (216 mm at 300 DPI). The A/B script compares it with `2k_upscale`. The decision is pending real keys; the cost math already favors 1K by $0.04 per image.
11. **Typesetting:**
    - Story text uses Noto Naskh Arabic (SIL OFL 1.1: commercial embedding allowed): 20 pt for ages 3–5, 16 pt for ages 6–8, line height 1.9.
    - Baloo Bhaijaan 2 is used only for titles and the cover. Page numbers are Arabic-Indic digits.
    - The panel is cream at 88% opacity. It goes to 96% when the art underneath is busy or the contrast falls below 7:1, and the page is flagged if it is still busy.
12. **Preflight** runs with pypdf and pdfplumber. It checks:
    - page size = trim + 2 × bleed, with TrimBox and BleedBox written;
    - fonts embedded (no Type 3);
    - every image ≥ 300 DPI effective;
    - no text outside the safe area;
    - page count divisible by the signature (default 4).
13. **Human gate.** Books reach `in_review` only after final generation and a passing preflight. Only an admin can move them to `approved`, and print batches accept approved books only.
14. **Samples before the create flow exists.** Admins can create a test book from `/admin/samples`: consent checkbox, 1–3 photos, optional drawing, theme, hijab and glasses. This runs the real pipeline, and the 5-volunteer acceptance test uses it.

## 3. Cost model (per 20-page book, verified prices)

The book has 17 story illustrations: 3 spreads and 14 single pages, one of which is a cached plate. There are also 16 book-specific images plus the cover, 2–3 redraws (15%), Haiku QA on every attempt, and a 4-page preview before purchase.

| Step | Calls | Unit | Cost |
|---|---|---|---|
| Final images, 1K | 17 (16 pages/spreads + cover) | $0.08 | $1.36 |
| Upscale to print | 14 single pages + 3 spreads | $0.0066 / $0.017 | $0.14 |
| Automatic redraws, 15% | ~2.6 | $0.08 + QA | $0.22 |
| Page QA (Haiku, cached prefix) | ~20 | ~$0.004 | $0.08 |
| Story + parents page + blurb (Sonnet 5) | 1 | ~5k in / ~6k out | $0.07 |
| Safety review (Haiku) | 1 | | $0.005 |
| Preview before purchase, 4 pages at 0.5K | 4 | $0.06 + QA | $0.26 |
| **Per purchased book** | | | **≈ $2.14** (≈ $1.88 without a preview, e.g. class books) |
| Once per child: character sheet + companion (2 options) | 3 | $0.08 | $0.24 |

Choosing 2K instead of 1K adds $0.04 × 17 ≈ $0.68, which puts the book at ≈ $2.82, over the cap.

## 4. Work items

- [x] **A. Providers:**
  - generic fal provider with privacy headers; fallback wrapper;
  - SeedVR/Recraft upscaler adapters;
  - verified `pricing.yaml`;
  - Sonnet 5 / Haiku 4.5 defaults with prompt caching (system blocks + cached reference prefix).
- [x] **B. Quality pipeline:**
  - style guide file and v2 prompts (page, cover, character sheet, plate, QA, story);
  - theme schema v2 (layouts, locations, time, outfits, cast, plates, parents page, blurb);
  - layout planner; outfit lock; QA scoring;
  - regeneration loop (≤ 2, then flag);
  - budget guard; plate cache; resolution tiers; preview mode.
- [x] **C. Themes:** first-day, graduation and new-sibling rewritten to 20 story pages each, with 3 spreads, a plate, split pages, ≤ 35 words per page (ages 3–5), a parents page and a blurb.
- [x] **D. PDF:**
  - premium templates (title/dedication, full/split/spread, companion, parents, end/activity, wrap cover with a QR code on the back);
  - RTL imposition; Arabic-Indic folios; age-based type;
  - contrast and busy-area check; text-fit check;
  - low-res web proof; TrimBox/BleedBox; preflight.
- [x] **E. Sketch provider:** offline, draws scenes in the design's illustration style. Used for demos, e2e and the sample book, so no keys are needed.
- [x] **F. Scripts:**
  - `scripts/sample_book.py`: full book, preflight report and projected cost;
  - `scripts/ab_resolution.py`: 1K+upscale vs 2K, side-by-side print crops and a cost table.
- [x] **G. Database and settings:**
  - migration: book generation context, costs, flags, QA and review fields; page layout/QA/status fields; child hijab/glasses; new statuses; TOTP;
  - settings registry: fal models, fallback, upscaler, resolution modes, QA threshold, budget cap, concurrency, print group; "FLUX model" renamed to "fal fallback model".
- [x] **H. Worker:**
  - jobs for character sheet, companion, book (preview/final) and single-page redraw, and render + preflight;
  - resumable (pages already done are kept); RQ retries with backoff;
  - costs written to `generation_costs`.
- [x] **I. API:**
  - admin samples (upload with type/size checks, EXIF stripped, consent recorded);
  - approval queue list and detail (spreads, QA, flags, costs); per-page redraw; text edit; raise cap; approve;
  - cost metrics; image/PDF proxy (S3 stays private).
- [x] **J. Web:**
  - `/admin/queue` and `/admin/queue/[id]` (AdminQueue design, as spreads);
  - `/admin/metrics` (AdminMetrics design);
  - `/admin/samples`; `/privacy` page;
  - 2FA setup and the login step.
- [x] **K. Security** (HTTPS and ufw are prepared as scripts and wait for a domain and Tareq's go-ahead):
  - admin TOTP 2FA with recovery codes, required for every admin endpoint;
  - optional admin IP allowlist;
  - HTTPS edge config and certbot service, ready for a domain;
  - `infra/scripts/firewall.sh` (not run until Tareq confirms).
- [x] **L. Wrap-up:** decisions, CHANGELOG, README, security doc; full checks; commit; deploy to the test server; report with sample PDFs and costs.

## 5. Results on the test server (real providers, 2026-09-28)

The test photo is a public-domain astronaut portrait (no real child). Both books are girls in hijab, watercolor.

| | Book 1: first day (age 5) | Book 2: graduation (age 6) |
|---|---|---|
| Path | 4-page preview, then final | straight to final (class-book path) |
| When | before the fixes below | after them |
| Story (Sonnet 5) + safety (Haiku) | $0.040 | $0.061 |
| Cover + story images | $2.24 (incl. $0.24 preview) | $1.60 |
| Upscale to print | $0.143 | $0.132 |
| Page QA (Haiku) | $0.142, 29 calls, not cached | $0.062, 20 calls, cached |
| **Book total** | **$2.56** (preview $0.29 + final $2.09 + 2 manual redraws $0.18) | **$1.85** |
| Automatic redraws | 6 of 18 images (33%) | 2 of 18 (11%) |
| Likeness ≥ 7/10 (QA) | 18 of 18 | 18 of 18 |
| Preflight | pass (min 299.8 DPI) | pass (min 299.8 DPI) |

- Book 1 exposed four problems, all since fixed and listed in `docs/decisions.md`:
  - a polluted plate cache;
  - classroom scenes inviting writing (most of the 6 redraws);
  - QA calls too short to cache;
  - SeaweedFS corrupting objects over 8 MB.
- Expected cost of a clean book with a preview is ≈ $2.10: book 2 ($1.85) plus a 4-page preview (≈ $0.25).
- Per-child costs, not charged to a book: character sheet $0.08 per child. The A/B cost $0.62 once.
- Total real spend for all Addendum 3 testing: $5.20.
- The 1K-vs-2K decision is 1K + upscale: `docs/decisions.md`, "Resolution".

## 6. What needs Tareq

- ~~A fal key and an Anthropic key, entered in `/admin/settings`.~~ Done; both are in use.
- 5 volunteer children with written consent (2 girls wearing hijab, 1 child with glasses). Upload through `/admin/samples`.
- The print partner's template (spine width, cover wrap, bleed, ICC profile) and a physical proof.
- A domain for HTTPS (Let's Encrypt).
- A go-ahead before enabling ufw on the shared test server. Other projects there listen on other ports, and Docker-published ports bypass ufw unless the `DOCKER-USER` chain is set.
- Written confirmation from fal that they do not train on our inputs (see §1).
