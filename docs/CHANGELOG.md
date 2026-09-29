# Changelog

## Addendum 9 order path: add-ons, the cart, gift cards, gift orders (2026-09-29)
- **The flow:** preview → «الإضافات» → «السلة» → address and cash on delivery (the Create9 → AddOns → Cart → Create10 designs).
- **Add-ons after the preview:** live totals from the server. Dependencies (`needs`), exclusions, the featured list and badges are admin data.
- **The cart:**
  - add-on lines, edit and remove;
  - «الكتاب الثاني −15%» as an admin bundle rule (kind `cheapest`: in every 2 books, the cheaper one);
  - one field for a coupon or a gift card;
  - the gift toggle with a card message (≤ 200 characters);
  - «شخصية ليان جاهزة»: a second story with the same approved character, never redrawn.
- **Gift cards:** issued by staff (Admin → الكتالوج → بطاقات الهدايا). They pay after every discount; the balance goes down atomically, with a DB check.
- **Gift orders:** a printable packing slip without prices, with the card message. The print-batch manifest carries `gift` and `gift_message`.
- **E2E tests:** Playwright flows in `tests/e2e/`, with test-only fixtures that the settings refuse in production (`docs/e2e.md`). Migration `ab04012fadad`.

## The activity-book pages (Addendum 9, WorkbookProduct) (2026-09-29)

- **`/workbooks/[product]`:** one template for «دوسية التأسيس», «رحلتي الأولى للتعلّم» and «مغامراتي مع عائلتي».
  - The choices (level, volume or stage, format, colors) and the live price come from the product's variants. A choice that doesn't exist with the others is greyed out.
  - Real pages drawn by the workbook engine for its invented sample child, exported once by `scripts/export_workbook_previews.py` into `apps/web/public/workbooks/`.
  - «خاصة بطفلك», the quiz link and the kindergarten card.
- **Who can order what:** a product flag (`features.orderable`), switched in the catalog admin (`PUT /api/admin/shop/products/{slug}/orderable`). «دوسية التأسيس» and «رحلتي الأولى» stay «قريبًا» with a "tell me when" link until the educator signs them off; the cart refuses them either way. The family book sells single copies; 10 or more copies still go through «اطلب عرض سعر».
- **The child's character is reused:** «أضف للسلة» asks which child («شخصية ليان جاهزة») and adds the book for that child (`POST /api/shop/workbooks/cart`: the item carries the child, the variant and the character). Without a ready character, the create flow draws one first, then puts the book in the cart.
- The seed adds the set as a PDF (75 ₪) and in black and white (129 ₪) for «دوسية التأسيس». The shop cards and the quiz now link to these pages.

## Phase 4: the kindergarten portal and «كتاب الصف» (2026-09-29)

- **Sign-up and approval.** A kindergarten signs up at `/portal/signup` and gets a school account at once. Staff
  approve or reject the organization at `/admin/organizations`, with an audit entry.
- **Classes and children.**
  - The school creates classes, then imports its children from CSV. The template includes Arabic headers, and a
    row-by-row preview gives reasons in Arabic and English before anything is imported.
  - Each child gets a private, expiring invite link for their parent, to copy or share on WhatsApp.
- **The parent's invite** (`/invite/{token}`). The parent signs in and accepts, then gives the class-book consent,
  uploads one photo (the same face check) and approves the drawing. The school's board shows the steps only,
  never a photo.
- **«كتاب الصف».**
  - One story and one line (Magic or Classic) per class, and the art style.
  - The school page: logo, class photo (only with the school's confirmation of the parents' permission) and the
    teacher's message.
  - An automatic, fair page plan: every child N times (2 by default), at most 3 per picture, never twice on a
    page. A planner lets the teacher move children, by tap or by drag and drop.
- **The batch.** One job draws the class:
  - shared pages with every child's character as a reference, each checked for every child;
  - a personal cover per child;
  - each copy's print files: school page, the child's portrait, the story, the group page.

  A live progress board, redraw requests and the school's bulk approval follow. Approved copies enter the admin
  review queue, and staff can print-approve a whole class at once.
- **The order.** Wholesale prices come from the kindergarten's price list; there is one order and one invoice per
  class, delivered to the school, cash on delivery.
- **The print bundle per class:** `{school}-{class}-{child}.pdf` interiors and covers, plus one combined print
  file, private and listed for staff with per-child coverage.
- **Catalog admin → «أسعار الروضات»:** B2B price lists, the default and per kindergarten, with tiers per variant
  and the margin per tier.
- **Acceptance:** a class of 30 is drawn in one batch with the offline providers and exported as one print
  bundle, in `apps/worker/tests/test_classbooks.py`.

## Real examples on the site, and the Addendum 9 store pages (2026-09-29)

- **Public examples:** an admin publishes an approved sample book of an invented child (approval queue → «انشره نموذجًا على الموقع»). Its pages appear on the site as web copies watermarked «نموذج»: the real cover, a flip-through of every page with its words, and the character sheet. Real children's books can never be published. API: `GET /api/examples`, the page and character images, `POST|DELETE /api/admin/books/{id}/example`.
- **The story page is now StoryProduct at `/stories/[slug]`** (`/themes/…` redirects with 308):
  - the real cover, then «تصفّحوا الكتاب» (swipe, arrows, keyboard, tap to enlarge; girl / girl with hijab / boy);
  - «1. اختر نوع الكتاب» (Classic «الأكثر طلباً» / Magic «الأفخم», each with a real page and its checklist), «2. أسلوب الرسم» (styles a line can't sell yet: «متوفر في سحري») and «3. شكل الكتاب»;
  - the live price in a sticky bar. «اصنع الحكاية» carries the story, type, style and format into the create flow, which skips what is already chosen.
- **`/stories`:** real covers, the price each story starts from, and the stories still being written in their own «قريبًا» section.
- **`/shop`:** the two story lines, the activity books («قريبًا» until their pages exist), the quiz, kindergartens (with the class-book price), the trust strip and the cart bar.
- **`/quiz` «أي كتاب يناسب طفلي؟»:** age, goal and (for learning) the pen answer lead to a book and an alternative. The rules are data (seeded from `content/store/quiz.yaml`, edited in Admin → الكتالوج → «أسئلة الاختيار»). A save that leaves any answer without a suggestion is refused.
- **Home page:** the real cover in the hero, a real book to flip through, the three steps with real pictures (photo → character → book), the stories with their covers, and the two book types as in the shop.
- **Create flow:** the book-type step uses the story page's cards with real pages in the child's look. The format step uses the same format cards, shows preview pages for either line, and starts on the format chosen on the story page.
- Everything falls back to the illustrated placeholders, with a note, while a story has no published example.

## Phase 2 and 3 remainders: the reader, share links, email, the card stub, print batches (2026-09-29)

- **The web reader** («كتبي» → a finished book or its preview): page flip, right to left for Arabic books, swipe and keyboard, full screen and night mode, mobile first (design: Reader). Pictures come through the API with the parent's session.
- **Share links:** the parent creates a private link to a finished book (a week, a month or 3 months), copies or sends it, and can turn it off at any time. The public page shows the book only, is never indexed and is rate-limited.
- **Emails** (SMTP from the admin settings; without SMTP they are only logged): order placed, confirmed, at the printer, shipped, delivered; preview ready; book ready with its reader link. Arabic and English, each sent once per order and status.
- **Payments:** cash on delivery behind a `PaymentProvider` interface, unchanged; the card gateway is a disabled stub («الدفع بالبطاقة — قريبًا»).
- **Admin → دفعات الطباعة** (permission `print`): collect the approved books of printed orders into a batch per day, or per kindergarten; send to the printer, which freezes the list, moves the orders to «في الطباعة» and emails the printer one link per file (each click opens a 10-minute download); then printing → done → handed to delivery (the orders become «شُحن»). The batch list downloads as CSV.
- New settings: `printer_email`, `printer_link_days`, `smtp_security`, `mail_from_name`, `email_notifications_enabled`. Migration `5125d903ce3f`: the `notifications` table and the printer fields on `print_batches`.

## Classic follow-ups and the free cover (2026-09-29)

- **Classic texts with full تشكيل:** each template's Arabic words are vowelized once per gender by the text model (checked letter for letter, placeholders kept, cached by the words' hash, ≤ $0.1 per theme one time). Books fill in the name at no AI cost. Admin: `POST /api/admin/classic/templates/{id}/texts` (with `refresh`, the theme's current words first); approving a template needs them.
- **One character per child:** a second book reuses the approved character (no redraw, no cost) unless the parent asks for fixes or uploads a newer photo.
- **Metrics per line:** `/api/admin/metrics` keeps Magic's figures on top and adds `lines` (cost per book and page, preview → purchase) for Classic and Magic.
- **The free cover** (Addendum 9, off by default: setting `free_cover`): `/free-cover` (name, look, consent, photo and story, through the create flow's endpoints) → one small watermarked cover edit from the story's Classic cover → `/free-cover/result` with WhatsApp, story-size and download, and the way on to Classic or Magic for the same child. One per account and story, 5 per IP per day, capped by `free_cover_budget_usd`; the photo is deleted 24 hours after upload.

## Addendum 4, step 3: «قمرة كلاسيك», the Classic pipeline (2026-09-29)

- **Classic templates** per story × art style × look (girl, girl with hijab, boy): drawn once with the premium pipeline around a placeholder hero, or copied from an approved sample book of an invented child. Hero boxes found by the fast vision model; review, per-page redraw, locks, approve and publish (`/api/admin/classic/templates…`, permission `templates`). One-time costs logged.
- **Classic books:** one identity portrait per child and style, then only the hero of each page is edited with FLUX.2 [klein] 4B (crop, edit, feathered paste), checked for likeness, seams and stray text; pages without the hero reuse the template. Texts from the theme with the name and gender forms. A **2₪ budget guard** per book (`classic_budget_ils` ÷ `usd_ils`).
- **In the shop:** Classic is offered only where a live template exists (the themes API lists them; the style step shows only those styles; otherwise a friendly «جرّبوا قمرة سحري»). The preview (cover + 2 hero pages, watermarked) is drawn right after the story step; confirming the order draws the whole book, which then waits in the approval queue. Old Classic drafts start once their template is live.
- **Settings:** `classic_fal_model` (default `fal-ai/flux-2/klein/4b/edit`); `classic_image_provider` (fal or our GPU, with fal klein as the fallback) and `classic_budget_ils` are used.
- **Cost proof tooling:** `scripts/classic_proof.py` (templates from samples, publish, and 5 invented children → 5 Classic books with their ₪ cost and PDFs); admin endpoints for Classic test books and invented faces.

## Phase 6: production-ready (2026-09-28)

- **`compose.prod.yaml`** on top of `compose.yaml`:
  - HTTPS mode and secure cookies;
  - Cloudflare R2 for object storage;
  - the stack refuses to start without real secrets;
  - rotated container logs, and only the edge published, on localhost behind the TLS proxy.
- **Nightly encrypted backups** (`infra/scripts/backup.sh`): the database, and the object store without children's original photos. 14 daily + 8 weekly copies, and an optional off-site copy.
- **A restore drill** (`restore.sh --check`) and disaster recovery (`--replace`).
- **A 5-minute health check** (`monitor.sh`): site, API, containers, disk, backup age and queues, with webhook alerts on state changes.
- **One installer** for the schedule (`install-ops-cron.sh`), tested on the test server.
- **Runbooks:** production install and deploy, backups and restore, monitoring and incidents.

## Addendum 4, step 5: catalog, margins, price simulator and reports (2026-09-28)

- **Admin → الكتالوج والأسعار:**
  - every product (on sale or not), extra and delivery zone, with its price, what it costs us and the margin in ₪ and %, in red under the margin floor;
  - edit prices, costs and on/off;
  - create coupons and seasonal sales, switch offers off, change bundle discounts;
  - every edit is audited.
- **Price simulator:** any basket (books, extras, delivery, coupon, ₪ or JD) through the store's own pricing, with our cost and margin.
- **Admin → التقارير:**
  - orders, revenue, average order, margin and orders under the floor;
  - sales by product line, product, story, extra and art style;
  - the extras attach rate, preview-to-purchase per line, parents vs kindergartens, and the daily AI cost;
  - orders and items as CSV files that open in Excel with Arabic intact.

## Addendum 4, step 6: the self-hosted GPU option, prepared and off (2026-09-28)

- **`ComfyImageProvider`:** talks to our own ComfyUI server over HTTP (upload the references, queue the workflow, fetch the image, forget the job).
  - It is for Qamra Classic edits only, chosen in the admin, and falls back to fal automatically when the server is down.
  - It runs only a workflow whose model license is approved in `docs/licenses.md`. None is yet.
- **Admin:**
  - new settings group «خادم الرسم الخاص (GPU)»;
  - a cost-dashboard card with the server's health (GPUs, free memory) and the Classic image spend on the API vs the GPU's monthly cost, with a recommendation.
- **Docs:** `docs/licenses.md` (every model, font and self-hosted program with its license) and `docs/runbooks/self-hosted-gpu.md` (server, privacy, deployment, health, fallback, rollback).

## Addendum 7: the proposal approved; printer prices in the admin (2026-09-28)

- The plan follows Tareq's answers: the new adventure order, the market-to-kitchen link, and the play-money levels.
- **Admin → أسعار المطبعة:**
  - enter the printer's price per copy by run length;
  - see the price-by-quantity table live, with ⚠ while the numbers are estimates.
- The store holds orders of 10+ copies of the family book until real printer prices are saved, then prices them from the tiers.
- A printer quote request is ready to send (`docs/family-book/printer-quote-request.md`).

## Addendum 7: «مغامراتي مع عائلتي», the proposal package (2026-09-28)

- **The plan** (`content/family-book/plan.yaml`), checked by `python -m qamra_workbook.family check`:
  - 112 pages, 12 adventures and 75 activities, each with a simple level ⭐ and a challenge ⭐⭐;
  - a sticker sheet and two card-stock sheets;
  - 9 designed sample pages plus 2 insert sheets.
- **The proposal:**
  - `docs/family-book/proposal.md` and a designed PDF (`scripts/family_proposal.py --pdf`);
  - it covers the concept, contents, activities, page counts, samples, size, paper, binding and a price-by-quantity table.
- **Store:**
  - a new `family` line with the printed wire-o book (89 ₪) and the printable PDF (35 ₪), inactive until approved;
  - printer cost tiers per variant;
  - the family-characters extra;
  - the gift box, sticker sheet and crayon kit are now offered with it too.
- **PDF helper:** `qamra_pdf.html_to_pdf()` for any A4 document; the invoice uses it.

## Addendum 4, step 2 (part 2): the parent create flow (2026-09-28)

- **Create a book on a phone** (`/create`, design Create1–Create9):
  1. the child;
  2. the guardian's consent;
  3. one photo, checked on the spot;
  4. Classic or Magic;
  5. the art style;
  6. the drawn character (approve, or redraw saying what was wrong);
  7. the story and an optional dedication;
  8. writing and drawing progress;
  9. the preview pages with editable words;
  10. the format and its extras, then the cart and checkout.
- A reload, the back button and the account page resume the book where it was.
- **"Delete all my child's data"** on the account page: photos, character, books and files, immediately. Orders keep no child details.
- Theme cards now carry the book title (`{name} في رحلة إلى القمر`), shown as the name is typed.

## Addendum 4, step 2 (part 1): storefront, checkout and orders (2026-09-28)

- **Store API:**
  - the catalog in ₪ or JD;
  - a cart for guests and parents with a live quote (add-ons, sale, bundle, coupon, delivery, COD fee);
  - checkout with cash on delivery;
  - order tracking by code and phone.
- **Storefront pages (mobile-first):**
  - Classic vs Magic side by side on every story page, with live prices;
  - cart (extras folded under «أضيفوا لمسة مميّزة», coupon field, full summary);
  - checkout (design Create10);
  - order placed, and order tracking with a status timeline;
  - a cart link in the header.
- **Order admin** (`/admin/orders`):
  - status tabs and search;
  - an order's books, extras, price, our cost and margin against the floor;
  - allowed status moves, internal notes, ready-to-send WhatsApp messages, partial reprints, and a full history with names.
- **Arabic invoices:** numbered per year, issued at confirmation, rendered by the worker. Books and extras are listed at list price, with the discount in the totals.
- Friendly Arabic and English messages for every new error.

## Addendum 4, step 1: the store's data model (2026-09-28)

- **Catalog:**
  - products, variants and prices (ILS and JOD) for Classic, Magic (with a custom-story product), coloring books, class books, «دوسية التأسيس» (KG1/KG2 × volumes × color/B&W × printed/digital) and «رحلتي الأولى للتعلّم» (stages × printed/digital);
  - unit costs for print, packaging, handling and AI.
- **Art styles as data:** watercolor, bright 2D cartoon, 3D film look, semi-realistic painted and coloring line art, each with its own guide file and QA thresholds.
- **Add-ons** with prices, costs, the lines that offer them, the lines that include them for free, requirements, exclusions, limits and daily capacity. All from Addenda 4, 5 and 6.
- **Pricing rules:** bundles, coupons (with redemptions), seasonal sales, B2B price lists with volume tiers, and shipping zones with free thresholds and COD fees.
- **Pricing engine** (`qamra_core/pricing.py`): one fixed order of steps, tested rule by rule.
- **Orders:**
  - the Addendum 4 statuses;
  - price, name and cost snapshots on order items;
  - an order event log;
  - Arabic invoices numbered per year (tables ready);
  - server-side guest carts.
- **Staff roles** (owner, admin, editor, reviewer, production, support), with a permission on every admin route. Existing admins are owners. `qamra create-user --staff-roles`.
- `qamra seed-store`: an insert-only seed from `content/store/catalog.yaml`, run on every deploy.
- New admin settings: USD→ILS and JOD→ILS rates, the margin floor (35%), the courier's COD cost, and the Classic AI budget (2 ₪).
- «دوسية التأسيس» and «رحلتي الأولى للتعلّم» plan tooling: YAML schemas, rule checkers and generated readable plans (`packages/workbook`).

## Addendum 3: premium books at ≤ $2.50 (2026-09-28)

- **Providers:**
  - Generic fal provider (any endpoint) with fal Nano Banana 2 as the default; `/edit` is used automatically with references.
  - `fal-ai/flux-2-pro/edit` fallback after 2 failed attempts, logged and counted.
  - SeedVR print upscaler.
  - Claude Sonnet 5 writes the story; Haiku 4.5 runs QA and safety checks. Prompt caching is on for the story rules and QA references.
  - Verified prices are in `pricing.yaml`.
- **Privacy on fal:** no request history stored (`X-Fal-Store-IO: 0`), generated files expire within 15 minutes, and images are sent inline, never uploaded to their CDN. Error logs never include our images.
- **Quality:**
  - House illustration style (`prompts/style/qamra_style.md`) in every image prompt, in the addendum's order.
  - Levantine setting cues; per-book outfit lock, with the cover as the outfit and style anchor; locations and lighting kept consistent.
  - Hijab and glasses follow the parent's choice.
  - Haiku vision QA with weighted scoring, at most 2 automatic redraws, then human review.
  - Per-book budget cap (default $3.00); cached background plates; 0.5K previews; finals at 1K + upscale.
- **Themes:** first day, graduation and new sibling rewritten as 24-page books (20 story pages, 3 spreads, split pages, a plate), with a «للأهل» page and a back-cover blurb. At most 35 words per page.
- **Print:**
  - Premium RTL book: title and dedication, full, split and spread layouts, «وهكذا وُلد صاحبي», «للأهل», activity and memories pages.
  - Cover wrap laid out front | spine | back with a QR slot.
  - Arabic-Indic page numbers; Naskh type sized by age, with shrink-to-fit.
  - Contrast- and busy-aware text panels.
  - Low-res web proof; exact TrimBox/BleedBox; automated preflight (bleed, 300 DPI, fonts, text in bleed, page count).
- **Server generation:**
  - Worker jobs for books (preview or final), single-page redraws and re-rendering.
  - Resumable, with costs written as they happen and child-scoped storage.
- **Admin:**
  - Sample books with guardian consent and photo checks; photos are re-encoded without metadata.
  - Approval queue showing the book as spreads, with QA scores and flags, per-page redraw, text edit, budget cap and approval gated on preflight.
  - Cost dashboard: per book, per page and per theme, with redraw and fallback rates.
- **Security:**
  - Admin two-step verification: TOTP with replay protection and recovery codes, required for every admin endpoint. `qamra reset-2fa` for recovery.
  - Optional admin IP allowlist.
  - HTTPS setup script (host nginx + Let's Encrypt).
  - Dry-run firewall script.
  - The edge trusts forwarded IPs only from Docker.
  - A privacy page lists the providers' data terms.
- **Tools:** `scripts/sample_book.py` (offline sketch art or real providers; report with preflight, QA and projected cost), `scripts/ab_resolution.py` and `python -m qamra_worker.ab` (1K vs 2K).
- **Fixed after the first real books** (details in `docs/decisions.md`):
  - The plate cache key includes the image model, so offline placeholder art can't reach a real book.
  - Books are pinned to the theme definition they started with.
  - Classroom scenes no longer invite writing (themes v3, house style v2): automatic redraws fell from 6 to 2 per book.
  - Page QA caches its prefix (prompt v2): QA cost per book fell from $0.14 to $0.06.
  - The regeneration rate counts only automatic redraws after failed QA, not preview-to-final upgrades, provider retries or admin redraws. Each attempt records why it was drawn.
  - "Text shrunk" is no longer reported for untouched 16 pt text (a px → pt rounding error).
  - Print files over 8 MB are stored reliably (SeaweedFS SSE bug; multipart uploads).
  - Image prompts no longer name the page, which the model painted into corners (page prompt v3, house style v3).
  - Page QA v3 catches a duplicated hero (look-alike children) and digits in the corners.
  - The dedication no longer repeats «إلى {name}…» when the parent's message already starts that way.
  - The approval queue and cost dashboard show theme names without the `{name}` placeholder, and the dashboard leaves placeholder-art ($0) books out of its averages.
- 256 Python tests.

## Admin settings, music, animations, security hardening (2026-09-28)

- **Admin settings** (`/admin/settings`, admins only):
  - Groups: prices (ILS + JOD, delivery), contact details, site switches (sign-up, music, animations, Google sign-in), AI keys, AI models, email/WhatsApp, and privacy retention (bounded by policy).
  - Seeded with example values that are marked in the UI.
  - Secrets are encrypted at rest (Fernet), masked, and every change is audited. Saves are validated all-or-nothing.
  - Endpoints: `GET /api/settings/public`, `GET|PUT /api/admin/settings`. The website reads prices and contact details from settings live, with no rebuild needed.
- **Background music:** an original lullaby rendered from code (`scripts/make_music.py`), played gaplessly via Web Audio. It starts on the visitor's first tap, can be muted (the choice is remembered), pauses in background tabs, and never plays in the admin area.
- **Animations:**
  - Twinkling star field and shooting stars in the hero; floating book and cards; flowing arrows; glowing main CTA.
  - Staggered scroll reveals; page-turn transition in the sample pages; child bobbing on hovered cards.
  - The admin can switch animations off, and they are always off for reduced-motion users.
- **Security:**
  - Nonce-based strict CSP on every page, plus security headers at the edge and on the API.
  - Nginx rate/connection limits, timeouts, method allow-list and dotfile blocking.
  - Container hardening: `no-new-privileges`, `cap_drop ALL`, memory limits; Redis password.
  - Sign-up rate limit and common-password blocklist.
  - Password change that signs out other sessions (with an account-page form).
  - `bandit`, `pip-audit` and `npm audit` all clean. See `docs/security.md`.
- 141 Python tests.

## Design import + public site (2026-09-28)

- Full design canvas imported into `design/canvas/` (77 artboards) and rendered for reference.
- Web, built from the design:
  - illustration parts ported (`Kid`, `Scene`, `Drawing`, `Companion`, `MoonPhase`);
  - new landing page (desktop + mobile): hero, 3 steps, story worlds, sample-page carousel, privacy, pricing, kindergarten band, FAQ, footer, mobile sticky CTA;
  - story-worlds catalog with age/occasion filters and sort;
  - story detail page (mobile design + desktop);
  - Kindergartens page with a working demo-request form;
  - account page per MyBooks (children, tabs, books, empty state, mobile tab bar);
  - site header (dark/light) with mobile menu, and footer.
- Content:
  - two new MVP stories (graduation, new sibling), 12 pages each, gendered Arabic + English;
  - catalog metadata for all worlds;
  - five coming-soon worlds from the design.
- API:
  - `GET /api/themes`, `GET /api/themes/{slug}` (preview, real sample pages), `GET /api/pricing`;
  - `POST /api/leads`;
  - `GET /api/children`, `GET /api/books`;
  - migration `add leads`;
  - themes seeded on deploy.
- Tests: 105 Python tests. The browser e2e now also covers the catalog and the kindergarten form.

## Phase 1 — foundations (2026-09-28)

- **Monorepo:** uv workspace (`packages/core`, `packages/ai`, `packages/pdf`, `apps/api`, `apps/worker`) and the Next.js app in `apps/web`.
- **Data model:** 19 tables covering spec §6 and Addendum 1 (companions, recordings, share tokens), plus refresh tokens, in one reviewed Alembic migration. Autogenerate is post-processed by `scripts/make_migration.py`.
- **API (FastAPI):**
  - register / login / logout / refresh / me;
  - argon2id passwords;
  - JWT access cookie plus a rotating refresh cookie with reuse detection and a 30-second multi-tab grace window;
  - login rate limits in Redis;
  - CSRF header check;
  - Google OIDC sign-in, enabled by config;
  - role guard;
  - friendly ar/en error bodies, JSON logs with request ids, optional Sentry;
  - `/api/health` checks the database, Redis and storage;
  - `qamra` CLI (create-user, seed-themes).
- **Worker (RQ 2):** privacy cleanup job (expired photos and original drawings, 30-day drafts, audit trail) scheduled every 15 minutes by `rq cron`.
- **Storage:** S3 adapter (put/get/delete, prefix delete per child, signed URLs capped at 15 minutes, optional SSE).
- **Web (Next.js 16.3, Tailwind 4, next-intl):**
  - RTL-first Arabic with English;
  - design tokens from `design/tokens.json`, fonts Baloo Bhaijaan 2 + IBM Plex Sans Arabic;
  - home, register, login and account pages;
  - silent session refresh;
  - locale switcher.
- **Docker:** `compose.yaml` with postgres 16, redis 7, SeaweedFS (local S3), migrate, api, worker, cron, web and an nginx `edge`. The edge is the only public entry point: it overwrites `X-Forwarded-For` so login rate limits can't be bypassed with a spoofed IP. `QAMRA_BIND=0.0.0.0` opens it to the network; every other port stays on 127.0.0.1.
- **CI:**
  - Python lint, types and tests against a Postgres service;
  - web prettier, eslint, tsc and build;
  - compose image build.
- **Tests:** 95 Python tests: 52 from Phase 0 and 43 new (auth, Google, roles, health, migrations == models, cascades, storage, cleanup, cron). `scripts/e2e_auth.py` (browser) passed against the full `docker compose` stack on the Qamra test server, both through an SSH tunnel and over its public IP: register → account → logout → login → silent refresh → English.

## Phase 0 — prototype (2026-09-28)

- Monorepo skeleton (uv workspace): `packages/ai` (`qamra_ai`), `packages/pdf` (`qamra_pdf`), `content/`, `scripts/`, `docs/`. Design handoff moved into `/design`.
- Brand is قمرة / Qamra, read from config (`BRAND_NAME_AR/EN`, `BRAND_DOMAIN`).
- AI providers behind interfaces:
  - images: Gemini (`gemini-3.1-flash-image`), FLUX.2 via fal (`fal-ai/flux-2-pro/edit`), OpenAI (`gpt-image-2.5-sunburst`), and a fake provider;
  - text: Claude via structured outputs (`messages.parse`, Pydantic), with server-side refusal fallback, and a fake provider.
- Versioned prompt templates (`qamra_ai/prompts/*.v1.j2`).
- Pipeline:
  - photo check (YuNet);
  - drawing clean-up (OpenCV);
  - character sheet;
  - companion from the child's drawing (review + 2 options + fidelity score);
  - story adaptation with gender agreement and full تشكيل for ages ≤ 7, followed by a safety review;
  - cover + 12 pages generated in parallel with a concurrency limit, retries and backoff, a Claude vision review (safety, hero recognizable, companion present, no text) and automatic redraws;
  - cost ledger per step.
- Theme «أول يوم في الروضة» (`first-day`, 12 pages): gendered Arabic + English templates, `companion_slot`, `companion_action` per page, default companion «قَمّور».
- Three original art styles: watercolor, crayon, paper cut.
- Print PDF (Playwright):
  - 216 × 216 mm pages (210 trim + 3 mm bleed), images at 300 DPI;
  - static embedded OFL fonts (Baloo Bhaijaan 2, Noto Naskh Arabic, IBM Plex Sans Arabic);
  - title/dedication page, story pages with text box, keepsake page «وَهٰكَذا وُلِدَ صاحِبي»;
  - separate cover PDF (front + back);
  - optional preview watermark.
- `scripts/prototype.py` (full book) and `scripts/companion_eval.py` (drawing fidelity on a folder of drawings).
- 52 tests with fake providers (no network). ruff + mypy strict. GitHub Actions CI.
