# Addendum 4 — product lines, art styles, add-ons and the store: plan

Spec: `docs/ADDENDUM-04.md`. The store also carries the workbook line from `docs/ADDENDUM-05.md` §6, so the catalog is designed for both from the start. Work follows the addendum's order (§9). Each step ends with tests, docs, a commit on the `addendum-4` branch and a report (mobile screenshots and cost per book for each line).

## 1. Verified facts (checked 2026-09-28)

| Fact | Value | Source |
|---|---|---|
| Classic edit model | `fal-ai/flux-2/klein/4b/edit`: up to 4 reference images, 4 steps, custom `image_size`, `sync_mode` (output not stored), `output_format` jpeg/png/webp, seed | fal model page and API schema |
| Its price | about $0.01 per megapixel. The base 4B edit endpoint is billed "per megapixel of input and output", with inputs resized to 1 MP, so we budget input + output megapixels | fal model pages |
| Its license | FLUX.2 [klein] **4B**: Apache 2.0. Commercial use is allowed, including self-hosting the weights (§8) | Hugging Face model card, BFL blog |
| 9B alternative | `fal-ai/flux-2/klein/9b/edit` at $0.011/MP. fal marks it commercial-OK through their API, but the **weights are non-commercial** (FLUX Non-Commercial License), so it can never be self-hosted | fal, BFL licensing |
| JOD | pegged at 0.709 per USD | Central Bank of Jordan peg |
| ILS | floating; set in admin (`usd_ils`, default 3.70). The 2₪ Classic target is ≈ $0.54 at 3.70 | — |
| Current code | Prices live in admin settings (3 products × 2 currencies + delivery). `OrderItem.product` is an enum. The Phase 2 create flow is a placeholder, but the design has all 12 steps (`design/canvas/Create1–11`) plus checkout (`Create10`), tracking, admin orders and the kindergarten invoice | repo |
| Theme text | Pages already carry gendered templates, e.g. `{فتحَ/فتحَتْ} {name}`. Classic can fill them without an LLM once each theme's text is fully vowelized and reviewed | `content/themes/*/theme.yaml` |

## 2. Decisions

1. **One generic catalog for every line.**
   - A `Product` has a `line`: `classic`, `magic`, `coloring` or `workbook`. Class books are products of the classic or magic line with `audience = b2b`.
   - A `Variant` is a combination of options (`format`, `size`, `style`, `level`, `volume`, `interior`) with prices per currency and unit costs. The workbook's level × volume × interior × format needs no schema change.
2. **Art styles are data.**
   - An `art_styles` table holds the name, prompt block, sample images, price modifier, the lines it is sellable in, QA thresholds and the active flag. Seed files live in `packages/ai/prompts/style/<slug>.md`.
   - A book pins the style it started with (like `theme_def`).
   - The house style keeps setting, people, composition and safety. Look-specific negatives move into each style file: "no 3D-render look" can't apply to the 3D style, and "no harsh black outlines" can't apply to the coloring style.
3. **Initial styles:** watercolor (the signature look), bright 2D cartoon, 3D animated-film look (described, never a studio name), semi-realistic painted, and black-and-white coloring line art. The old crayon and paper-cut styles stay in the table, inactive.
4. **Money and margins.**
   - Prices are `Numeric(10,2)` in ILS and JOD.
   - Unit costs (print, packaging, shipping to us, payment fee %, AI estimate in USD) sit on variants, styles and add-ons.
   - Margin is computed in the sale currency with the admin exchange rates. Real AI cost comes from `generation_costs`. Items below the margin floor (default 35%) show in red.
5. **Pricing engine, in a fixed and tested order:**
   1. variant price + style modifier;
   2. add-ons (percent add-ons such as "extra copy −50%" use the book's price);
   3. seasonal sale;
   4. bundle;
   5. coupon;
   6. shipping (zone fee, free-shipping threshold, COD fee).

   B2B orders use the organization's price list and volume tiers instead of retail prices and sales. The cart shows every step.
6. **Staff roles.**
   - A `user_roles` table holds `owner`, `admin`, `editor`, `reviewer`, `production` and `support`. A user can have several.
   - `users.role = admin` keeps meaning "staff: may enter the admin with 2FA". Permissions come from the roles through one permission map in code.
   - Existing admins become owners.
   - Every staff write is audited: who, what, when, and before/after for catalog, prices and templates.
7. **Guest checkout.**
   - The cart lives server-side, keyed by an httpOnly cookie token. Guests check out with name, phone and address; an account is optional and a guest cart merges into the account at login.
   - COD first. `PaymentProvider` is ready for a card gateway.
8. **Order statuses** follow the addendum: new → confirmed → generating → review → printing → shipped → delivered, plus cancelled and reprint.
   - Existing rows are migrated: pending → new, in_production → printing.
   - Every change is written to an order event log with notes and the customer message sent (WhatsApp/email templates).
   - A reprint can cover some items only.
9. **Invoices:** Arabic PDF through the existing Playwright renderer, numbered per year (`INV-2026-00001`) from a counter row taken under a row lock.
10. **The Classic pipeline edits only the hero.**
    - Each template page stores a hero box. Per order, the box is cropped from the print-resolution template, edited at ≤ 1 MP with klein 4B (the crop plus the child's identity portrait), and pasted back with a feathered edge.
    - The rest of the art stays at print quality, and each edit costs about $0.015.
    - Fallback if seams show: edit the whole page, then upscale (about $0.03 per page).
11. **Identity portrait.**
    - Each child gets one cheap portrait in the book's style: a klein edit from the photo, about $0.015. It is reused for every Classic page, the class-book cover and the workbook cover (Addendum 5: "reuse the child's existing character").
    - A Magic character sheet is reused when one exists.
12. **Template variants.**
    - Start with boy, girl and girl-with-hijab at a middle skin tone, in the watercolor style, for the three MVP themes.
    - The per-order edit adapts skin tone and hair. More variants are added only where the 5-child test shows the edit can't close the gap. This keeps the one-time template cost near $5 per theme and style.
13. **Classic text.**
    - Each theme's templates are fully vowelized once (Sonnet, then human review) and stored as the Classic text.
    - Per order: the name is inserted and the gender forms are chosen, with no AI call.
    - Parents may edit within the page's length limit, and edited text goes through the Haiku safety check.
14. **Custom story (Magic + custom story).**
    - The parent writes a short brief: the idea, 3 moments they want, family names.
    - Sonnet expands it into the theme schema (17 beats with scenes, locations, outfits and texts) with the Addendum 3 rules and safety review. From there it's a normal Magic book.
    - It sits behind an admin switch until tested.
15. **Test children.** The Classic cost proof uses 5 synthetic child portraits generated by us (2 girls in hijab, 1 with glasses). No real child is involved. The acceptance test with volunteer children stays with Tareq and needs consent.
16. **Self-hosted (§8).** Only klein 4B (Apache 2.0) qualifies today. No InsightFace or other non-commercial weights. `docs/licenses.md` records every model and font, and new models need Tareq's approval.

## 3. Cost model per book (verified prices; the rates in admin are what counts)

| Line | Main costs | AI cost |
|---|---|---|
| Classic | identity portrait $0.015 (once per child) + ~14 hero edits × $0.015 + Haiku QA 14 × $0.003 + ~15% redraws | **≈ $0.29 ≈ 1.1₪** (target ≤ 2₪). About $0.48 ≈ 1.8₪ if whole-page edits are needed |
| Magic | Addendum 3 pipeline | ≈ $1.95 without a preview, ≈ $2.20 with one (target ≤ $2.50) |
| Coloring version (add-on) | one line-art klein edit per page (~17 × $0.02) | ≈ $0.35 |
| Workbook cover (Addendum 5) | identity portrait (reused) + one cover edit | ≈ $0.02–0.04 (target ≤ 1₪) |
| Classic templates (one time) | 18 images × 3 variants × $0.086 + QA | ≈ $5 per theme per style |

## 4. Work items

- [x] **Step 1 — Data model**
  - Tables: products, variants, variant prices, art styles, add-ons (prices, costs, lines, requires/excludes, capacity), bundles, coupons + redemptions, sales, price lists + tiers, shipping zones, carts + items, order changes (statuses, snapshots of prices and costs), order events, invoices + a yearly counter, and staff roles.
  - Migrations with a data move (price settings → catalog; order statuses; admins → owner).
  - Seed from the tables in Addenda 4 and 5.
  - Pricing engine module with unit tests for each step.
  - Permission map and `require_permission`.
- [ ] **Step 2 — Store UI (mobile-first, design canvases)**
  - catalog by line and style;
  - product page with a style picker, sample pages and Classic vs Magic side by side;
  - add-on toggles shown at the right moment;
  - cart (several books, edit, saved; guest);
  - checkout (shipping zone, COD) and order summary;
  - the create flow steps the design already has (child → consent → photo → style → character → story → page review → preview → format), attached to cart items;
  - order tracking;
  - invoice PDF;
  - order admin (statuses, notes, messages, partial reprint).
- [ ] **Step 3 — Classic pipeline**
  - templates (tables + generation script for 3 variants of one theme);
  - hero boxes;
  - identity portrait;
  - crop-edit-paste with klein 4B;
  - Haiku QA (likeness, seams, text);
  - cost logging and a budget guard of 2₪;
  - Classic text filling;
  - custom story builder for Magic.
  - **Proof: 5 synthetic children, ≤ 2₪ AI cost each**, with sample PDFs.
- [ ] **Step 4 — Template studio**
  - theme versions (draft → in review → approved → live) with history and rollback;
  - per theme × style × variant page list with the template image, hero box and text box;
  - RTL page editor (drag/resize the text box, font size within range, m/f/en texts with `{child}`, `{companion}`, `{family.mom}`, live preview with a sample child);
  - template generation, per-page regeneration and locking, with one-time costs logged;
  - bulk actions (duplicate a theme to a style, translate, publish, schedule);
  - roles in the UI; audit log viewer.
- [ ] **Step 5 — Margins and reports**
  - catalog admin: products, variants, prices, costs, add-ons, bundles, coupons, sales, shipping, price lists;
  - price, cost and margin (₪ and %) per product and order, with red warnings;
  - price simulator;
  - reports: sales by product, theme, style and add-on; average order value; attach rate; preview → purchase per line; AI cost trend; B2B vs B2C;
  - CSV and Excel export.
- [ ] **Step 6 — Self-hosted provider (inactive)**
  - `SelfHostedProvider` for ComfyUI over HTTP (Classic edits only), selectable in admin, falling back to fal;
  - health check;
  - API-versus-GPU cost comparison in admin;
  - `docs/runbooks/self-hosted-gpu.md`;
  - `docs/licenses.md`.
- [ ] **Step 7 — Feature matrix and E2E**
  - `docs/feature-matrix.md`;
  - Playwright E2E: Classic softcover + 2 add-ons; Magic hardcover with a custom story; sibling bundle with a coupon; B2B Classic class book on a price list.

## 5. What needs Tareq

- **"Production audit rules"** (§9.2) and **"the feature matrix"** (§9.7): neither is in the repo. Likely a missing Addendum 2; please send it. Until then I use `docs/security.md` and CLAUDE.md §10.
- The exchange rate to use for ₪ ↔ $ (the default is 3.70, editable in admin).
- Print, packaging and shipping costs from the printer, so margins are real. The seed uses clearly marked placeholders.
- Approval of klein 4B (Apache 2.0) as the Classic model, and of synthetic test faces for the cost proof.
