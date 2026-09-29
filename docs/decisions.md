# Decisions log

Newest first. Each entry: date — decision — why.

## 2026-09-29 — Addendum 9 store pages: routes, quiz rules, and where the pages differ from the design

- **Routes:** the story page is `/stories/[slug]` and the list is `/stories`. `/themes` and `/themes/[slug]` answer 308 to them (next.config redirects), and every internal link was updated.
- **Quiz rules are one JSON row in `app_settings` (key `quiz_rules`), not a new table.**
  - They are an ordered list, edited as a whole, so a table and a migration buy nothing, and other work adds migrations at the same time.
  - The row sits outside the settings registry: the settings screen ignores it, and the rules have their own editor in the catalog admin (permission `prices`).
  - `qamra seed-store` seeds it once from `content/store/quiz.yaml`. The quiz reads the YAML until then.
  - Matching runs in the API (`qamra_api.store.quiz`, unit-tested): the first rule whose conditions hold wins, and a save must cover every answer.
- **Everything the store page shows comes from data.**
  - Line prices ("from" = the cheapest printed copy), formats and their prices, and the style price modifiers come from the catalog.
  - Style availability per line comes from `ArtStyle.lines`, narrowed by the themes API's per-story Classic templates when that field is present.
  - The free digital copy shows only while the `digital-copy` add-on is 0 ₪.
  - The class-book price comes from `GET /api/shop/summary`.
- **Where the pages differ from the design, and why:**
  - «تصفّحوا الكتاب» is added after the description on the story page (Tareq: "why are there no examples?").
  - Each line card has a small real page when an example is published.
  - The hero shows the real cover (square) instead of the 390×320 scene.
  - Styles are listed from the catalog, 5 instead of the design's 4, with Classic-capable styles first.
  - The activity-book cards say «قريبًا» and link nowhere until `/workbooks/[product]` exists (`WORKBOOK_PAGES` in `lib/shop.ts`).
  - The free-cover banner stays hidden until a `free_cover` public setting is on.

## 2026-09-29 — Classic texts vowelized once, the character reused, metrics per line, the free cover

- **Classic texts get full تشكيل once, not per book.** Each template's Arabic words (title, dedication, pages, parents' page, blurb) are vowelized by the text model for the template's gender, with `{name}` and `{companion}` kept as placeholders, and cached in the template (`generation.texts`) under a hash of the source words. A sibling template of the same theme and gender lends its copy, so a theme costs one call per gender (Sonnet: about 2k tokens in and 2–4k out, ≈ $0.02–0.05 per gender, ≤ $0.1 per theme; logged as `tpl:vowelize:<gender>`, and the real figure shows in the template's cost). The model may only add diacritics: every text is compared letter for letter (diacritics removed) and placeholder for placeholder with its source, and a text that differs keeps its unvowelized source and is listed as `kept`. Template jobs vowelize automatically; `POST /api/admin/classic/templates/{id}/texts` redoes it, and with `refresh` first takes the theme's current words (only while its pages still line up with the art). Approving a template needs vowelized texts from its current words. A book whose template has none (or stale ones) prints the plain theme text and is flagged `text_not_vowelized` for the reviewer. The child's name itself stays as the parent typed it.
- **An approved character is reused by every book** (Addendum 9 §6): asking to draw a character in a style where the child already has an approved one returns it (no job, no cost), unless the parent asked for fixes or uploaded a newer photo since.
- **`/api/admin/metrics` per line:** the top-level cost figures and the per-theme rates are Magic's (they are judged by Magic's $2 target and $2.50 cap); `lines` gives each line's books, cost per book and per page, and preview → purchase (books made in the create flow in the period, bought = in an order that was not cancelled).
- **The free cover** (Addendum 9): the parent uses the create flow's own child, consent and photo endpoints; `POST /api/free-covers {child_id, theme}` makes one small hero edit on the theme's live Classic cover (watercolor, 1024 px, no redraw), then the worker burns in the title and the preview mark («معاينة · قمرة», Pillow with libraqm; Latin marks if a machine lacks it) and makes a 1080 × 1920 story copy. Reference: the child's identity portrait, else the approved character sheet, else the photo (no extra call). Guarded by `free_cover_budget_usd` (default $0.05; one edit + one check ≈ $0.01–0.015). One per account and story (the same child gets the same cover back), 5 per IP per day, only while the `free_cover` setting is on (off by default; public, so the shop's banner can follow it). Requesting one sets the photo's deletion to 24 h after upload; the existing cleanup job deletes it. The images live under the child's prefix; the API streams them privately; sharing sends the painted cover (the phone's share sheet, or a WhatsApp text link), never the photo.

## 2026-09-29 — Phase 2 and 3 remainders: the web reader, share links, email, the card stub, print batches (W5)

- **The reader is its own route and component** (`/[locale]/books/{id}` for the child's guardian, `/[locale]/s/{token}` for a share link, `components/reader/`). The public examples viewer (another workstream) is built around published example data (variants, watermarked web copies) and did not exist yet; the two can share a primitive later. Pictures stream through the API, so no storage URL reaches a browser. A preview shows its drawn pages; a finished book (`in_review`, `approved`, `ordered`, `printed`) shows every page; a page that failed the safety check is never shown. Page turns: buttons, keyboard (in an Arabic book ArrowLeft goes forward) and swipe (to the right goes forward in RTL). The flip is a Web Animations turn from the spine, so no inline `<style>` is needed and the strict CSP stays; it is off with reduced motion or the admin's animation switch.
- **Share links reuse `ShareToken` (scope `read`)**, stored as-is like the QR tokens, so the owner can copy the link again. One live link per book: a new link revokes the old one, and the owner can revoke at any time. Links last 7, 30 or 90 days (30 by default), never forever, and only finished books can be shared. The public answer holds the title, language, page texts and picture paths only: no book or child ids, no parent, no order. It is `no-store`, `no-referrer` and `noindex`. Limits: 120 views and 3,000 pictures per IP per hour, 20 new links per parent per hour. Unknown, revoked and expired links get the same 404.
- **Email adapters live in the worker** (`qamra_worker/notify/`): `SmtpEmailSender` (stdlib `smtplib`: STARTTLS, SSL or none), `LogEmailSender` and `FakeEmailSender` for tests. `LogEmailSender` is used whenever no SMTP host is set; it only notes that a message would have gone out, without the address, subject or body. New settings (additive): `smtp_security`, `mail_from_name`, `email_notifications_enabled`, `printer_email`, `printer_link_days`. The messages are in `content/emails/messages.yaml` (Arabic and English) with one HTML frame; values are escaped in the HTML.
- **When emails go:** checkout (`placed`); the order status change and print batches (`confirmed`, `printing`, `shipped`, `delivered`); the book job's render (`preview_ready`, and `book_ready` with the reader link). They are jobs on the `default` queue with 3 retries; a queue outage never fails a checkout or a status change. The recipient is the account behind the order or book, in its language. Guest orders have no email address, because checkout asks for a phone only, so they get none. Admin sample books never get emails.
- **Each email goes once:** the `notifications` table (migration `5125d903ce3f`) has one row per key (`order:<id>:<event>`, `book:<id>:<event>`, `batch:<id>:send:<n>`), claimed with `INSERT … ON CONFLICT DO NOTHING`. A failed or stuck attempt can be claimed again, up to 4 times. No addresses, names or bodies are stored.
- **Payments:** `PaymentProvider` (`qamra_api/store/payments.py`) with `CashOnDelivery`, which works exactly as before (the order starts unpaid and staff mark it paid), and a disabled `CardGatewayStub` («الدفع بالبطاقة — قريبًا»). Choosing the card is refused (409 `payment_unavailable`) before any order exists. `GET /api/store/payment-methods` lists both. Addendum 9 confirms: cash on delivery only for now.
- **Print batches:** an order is ready when it is confirmed, generating or in review, and not in a batch yet. Every printed item in it needs an admin-approved book with both PDFs. Printed means softcover, hardcover or spiral, and the hardcover upgrade counts. An item with no personalized book keeps its order out, because it has its own production. «اجمعوا الجاهز» puts ready orders into today's open batch: one per kindergarten, one for all families.
- **Sending a batch** freezes its manifest: copies = quantity × (1 + extra copies), with the extras listed. It moves each order to `printing` along the existing transitions; a confirmed order walks confirmed → generating → review → printing, one event per step, never through cancelled or reprint. Books become `ordered` («قيد الطباعة» on the parent's shelf), the customers are emailed and the printer email is queued. Then the printer's progress: sent → printing → done (books become `printed`), and «سُلّمت للتوصيل» moves the orders to `shipped`. An open batch can drop an order; a cancelled order blocks sending until it is removed. Reprints stay on the order page for now.
- **The bundle is a manifest with links, not a zip:** a class of 30 hardcovers is gigabytes of PDFs, which the worker would have to hold in memory and store twice. The worker stores the manifest CSV beside the batch: order code, SKU, format, size, copies, extras and file names, with no names or addresses. It issues a printer token; only its sha256 is on the batch. The token lasts `printer_link_days` (14 by default), and a resend replaces it at once. The email has one link per file, `/api/printer/{token}/files/{n}/{interior|cover}`, which redirects to a signed URL of 10 minutes (the privacy cap is 15). With no printer address the batch is still prepared and the admin sees «لم يُرسل».
- **Permissions:** print batches need `print` (production, owner). The batch page's file links use the existing `books.view` endpoints.

## 2026-09-29 — «قمرة كلاسيك»: templates, the hero edit and the 2₪ guard (Addendum 4 step 3)

- **Tables** (`qamra_core/db/classic.py`, migration `7b04ca0efdb2`): `classic_templates` (theme × art style × variant, `draft → in_review → approved → live`, a job state, the pinned theme definition, the one-time cost), `classic_template_pages` (print-resolution image, preview, `has_hero`, hero box and text box as normalized `{x, y, w, h}`, lock, manual redraws, one-time cost) and `child_portraits` (one identity portrait per child and style, under the child's prefix, cascade-deleted with the child). The variant is a string (`girl`, `girl_hijab`, `boy`) so skin and hair variants need no migration.
- **Two ways to make a template.** (1) The premium page pipeline draws every page once around a neutral placeholder hero (a text-to-image character sheet for the variant), with the usual QA, upscaling and plate cache, capped per run by `book_budget_usd`; costs are `generation_costs` rows `tpl:<step>` plus the template's and page's totals. (2) An approved sample book of an **invented** child (no drawn companion) is copied page for page ("sample → template"); the admin must confirm the child is synthetic. Either way the template lands `in_review`; approving needs every page drawn and every hero page's box, and locks all pages. Changing an approved or live template sends it back to review. Only live templates serve parents; sample (proof) books may use one still in review.
- **Hero boxes come from the fast vision model**, once per template page, on the print image the edit will crop: the image models return no layout data, a second placeholder pass to diff would double the art cost, and a prompt that pins the hero's position is unreliable. The model gets the hero's reference sheet (to tell the hero from classmates) and answers fractions; percent or pixel answers are normalized, boxes are clipped, slivers rejected. The crop's 15% margin absorbs a few percent of error, and editors can correct any box in the API (the studio, step 4). A hero page without a box is edited whole and flagged.
- **The edit:** crop the box + margin from the print page, resize it to 0.35–0.6 MP (multiples of 16, its own shape), edit with FLUX.2 [klein] 4B on fal (`classic_fal_model`) with the crop and a 512 px copy of the identity portrait, paste back resized with a feathered edge (hard where the crop touches the trim) after a small colour match on the border band (≤ 24 levels). About $0.010–0.015 per page (klein bills input + output megapixels). Pages without the hero are the template's own page. English books use the template mirrored, so text panels and calm areas swap sides with the reading direction.
- **QA** (fast model, per edit): likeness to the portrait, same scene, seams, hero count, anatomy, stray text, style, safety; a pass needs likeness ≥ 7. Every page gets its first edit before any page is redrawn, and the cover goes first, so a tight budget is spent evenly and never leaves a book without its cover. One automatic redraw per page, then `needs_review`.
- **Identity portrait:** a klein edit of the approved character sheet (or, for samples, the photo), 768 px, checked once for likeness; reused by every Classic book of that child and style. After it exists, the originals get the usual deletion time.
- **Budget guard: 2₪ per book** = `classic_budget_ils ÷ usd_ils` (0.54 USD at 3.70), counted from the first paid call of the book, portrait included. Drafts made before a template existed carried the Magic cap; the worker replaces it once (`budget_pinned`).
- **Text:** the theme's page templates with the name and gender forms (`render_template`), no AI call; the parent's edits and dedication get the fast model's safety review before print.
- **Flow:** Classic is offered only where a live template exists for the story, the style and the child's look (`classic` in the themes API; StyleStep shows only those styles; otherwise `classic_unavailable` suggests Magic). The create flow draws a watermarked preview (cover + two hero pages) right after the story step; confirming the order draws the rest (a book still drawing its preview continues on its own). A Classic draft from before its template went live starts on the parent's next visit or the admin's "generate". Admin redraw, re-render and approval work as for Magic (the worker dispatches by line).

## 2026-09-29 — Public examples: real books on the site, only from invented sample children

- **Only sample books can be public examples.** An admin with `books.review` publishes an *approved* book (Admin → the approval queue → «انشره نموذجًا على الموقع»). The API refuses any book whose book or child is not `is_sample`, and the admin must confirm that the child is invented (a generated face), as for Classic templates: a volunteer child's book stays private even with written consent. Unpublishing is one click.
- **The flag lives in `Book.generation["public_example"]`** (no migration). A published book is listed only while it stays approved in an active theme: a redraw or a text edit sends it back to review, which hides it until it is approved again.
- **Public images are web copies, watermarked «نموذج»** ("SAMPLE" in English books): at most 1280 px (560 px thumbnails), diagonal marks plus a corner tag, JPEG without metadata. They are made once from the stored art at publish time (or on first request) and kept under the sample child's prefix, so deleting the sample child deletes them. The key and the URL carry a hash of the source and the page's last change, so the responses can be `Cache-Control: public, max-age=86400` and a redrawn page still shows at once. The responses carry no names, child ids or storage keys.
- **API:** `GET /api/examples?theme=&lang=` (the variant girl / girl with hijab / boy comes from the child's gender and hijab; pages in reading order with their words, layout and printed page numbers), `GET /api/examples/{id}/pages/{beat}/{s|m}.jpg`, `GET /api/examples/{id}/character/{s|m}.jpg`, `POST|DELETE /api/admin/books/{id}/example`.
- **The site falls back to the illustrated placeholders** (with a note) wherever no example is published yet, so every page looks finished before the first example goes live.

## 2026-09-28 — Addendum 7: «مغامراتي مع عائلتي» (proposal only)

**Approved by Tareq with changes** (verbatim in `docs/family-book/decisions-2026-09-28.md`):
- The adventures now run home → market → chef → nature → day → responsibility → feelings → talk → jobs → shop → games → acting. The chef opener starts «ما اشتريناه من السوق نطبخه معًا!».
- The book stays at 112 pages, with a full «ذكرى اليوم» page after every adventure. Titles, passport stamps and the certificate follow the child's gender.
- **Size: A4 if the printer's wire-o and cutting templates are A4, otherwise 21×28 cm.** The engine switches between them with one setting.
- **Paper:** we ask for quotes at 120 and 140 gsm interior and take 140 if it costs under 3 ₪ more per copy. `docs/family-book/printer-quote-request.md` is ready to send.
- **Play money:** ⭐ uses 1, 2 and 5; ⭐⭐ uses all notes with change exercises. The digits follow the order's numeral setting (Hindi by default).
- **Printer prices stay estimates, marked ⚠, until Tareq saves the quote in the admin** (`/admin/print-costs`).
  - The seeded tiers carry `estimated: true`, and saving a quote clears it.
  - Until then, 10 or more copies of the book can't be ordered: the cart and checkout answer «تواصلوا معنا لعرض سعر».
  - After it, 10+ copies are priced from the tiers and the bulk margin, in ₪; bulk orders in JD are quoted by hand.
  - Below 10 copies the book sells at retail.
- The next deliverable is the first two adventures in full, as a PDF, before the rest of the book.

- **The third activity book reuses the workbook engine.** `qamra_workbook.family` holds only the plan schema, its rules and the proposal text; pages, pictures, the PDF pipeline and the samples all come from the shared engine. The unit is the *activity* (a goal, the child's part, the family's part, materials, time, levels, safety), and each activity has one or more pages.
- **The book is 112 pages** (the range is 96–128): 5 front pages, 12 adventures and 3 back pages.
  - Each adventure is a two-page opening spread, its activities, then «ذكرى اليوم». Every adventure has an even length, so each opening spread starts on an even page.
  - The passport is on page 3, and the 7-day challenge and the certificate close the book.
  - «ذكرى اليوم» is the memory page after each adventure (item 13 of the brief), not a separate section.
  - The adventures keep the brief's order. Moving the nature adventure earlier is an open question for Tareq.
- **The checker enforces the addendum**, including:
  - no identical page type on consecutive pages;
  - child instructions of 10 words or fewer and parent boxes of 3 lines or fewer;
  - every skill in at least 3 activities;
  - a safety note with an allergy reminder on every recipe and no nuts or raw eggs;
  - a supervision note outdoors.
  - **Families differ:** instructions and parent boxes never contain a fixed «ماما» or «بابا». Missions say «مع {adult}» or name `{member}`, from the family list the parent fills in.
- **Insert sheets are separate print files:** a sticker sheet and two card-stock sheets. Play money, role cards, finger puppets and the badge stickers never appear as book pages.
- **Price by quantity comes from the store.** The printed variant has `print_cost_tiers` (price per copy by minimum quantity, placeholders until the printer's quote), and `quantity_prices()` in `qamra_core.pricing` builds the table:
  - one copy sells at retail;
  - from 2 copies, the price is the tier cost plus the other unit costs, divided by (1 − bulk margin); `bulk_margin_pct` is 45% in the settings;
  - the result is rounded up to a whole shekel, never above retail, and never under the margin floor.
- **The product is seeded inactive** (`active: false` in the catalog) until Tareq approves the proposal and the printer's prices are in.

## 2026-09-28 — Addenda 4–6: the store, and the workbook engine

Full reasoning is in `docs/plans/addendum-04.md` §2.

**Store data model (Addendum 4, step 1)**
- **One generic catalog.** A product has a line: `classic`, `magic`, `coloring`, `workbook` (Addendum 5) or `journey` (Addendum 6). Variants are option combinations (format, size, level, volume, interior, stage) with prices per currency and unit costs. The two workbook products fit without schema changes.
- **Styles are data.** They live in an `art_styles` table seeded from `qamra_ai/prompts/style/<slug>.md`. The five new styles never name a studio or artist, and a test checks that. The old crayon and paper-cut styles are kept but inactive.
- **The seed is insert-only.** `qamra seed-store` runs on every deploy and adds only missing rows, so prices, costs and prompts edited in the admin are never overwritten. Starting data is in `content/store/catalog.yaml`. Its costs are marked placeholders until the printer quotes arrive, and its JOD prices are suggestions at 1 JD ≈ 5.2 ₪.
- **Pricing runs in one fixed order:** price-list tier or retail price + style modifier → add-ons → sale → best single bundle → coupon → shipping and COD fee. It is pure code with a test per rule (`qamra_core/pricing.py`).
  - B2B tiers use the order's total quantity of each variant.
  - Sales never apply to price-list prices.
  - A fixed coupon is spread over the items to the cent.
- **Staff roles** (`user_staff_roles`: owner, admin, editor, reviewer, production, support). A user can have several.
  - A role grants a permission name and everything under it (`orders` covers `orders.view`). The map is in `qamra_core/permissions.py`, and every admin route declares its permission.
  - Existing admins became owners in the migration. `qamra create-user --role admin` grants `owner` unless `--staff-roles` says otherwise.
- **Order statuses follow Addendum 4:** pending became new and in_production became printing. Order items now snapshot the variant, names, options, add-ons and unit costs, so later catalog edits never change a past order.

**Storefront and orders (Addendum 4, step 2)**
- **Guest carts live on the server.** An httpOnly cookie holds a random token and the database stores only its hash. Signing in adopts the guest cart. The cart's currency follows the delivery zone: Palestine pays in ₪, Jordan in JD.
- **Checkout re-checks everything and freezes it on the order:** prices, add-on names and unit prices, and unit costs. So later catalog edits never change a past order, and invoices list exactly what was sold.
  - The express add-on has a daily capacity.
  - Coupons check dates, uses, first order (by phone or account) and uses per customer.
  - Checkout, coupon attempts and tracking are rate-limited per IP.
- **Tracking needs the order code and the phone number.** A wrong code and a wrong phone get the same 404, so codes can't be enumerated. The phone is kept in the tab's sessionStorage only, never in the URL.
- **Order statuses change only along the allowed moves.** Cancelling is possible until printing, and a reprint needs the items it covers. Every change, note and customer message is an order event with the staff member's name.
- **Invoices** are numbered per year with no gaps (a row-locked counter) and issued when an order is confirmed. The worker renders them, because only its image has Chromium. They sit in private storage, and admins open them through the API.
- **Customer messages are ready-to-send WhatsApp links for now.** Staff tap once and WhatsApp opens with the message filled in, and the send is logged on the order. The templates are content (`content/store/messages.yaml`). An automatic sender (Twilio or the WhatsApp Business API) is a paid service and waits for Tareq's approval.
- **Personalized books need a signed-in parent at the consent step.** A consent row belongs to a guardian account (the privacy rules: consent records and "delete my child's data"). Browsing, the cart and checkout still work as a guest. Phone-number sign-in would remove the friction, but it needs a paid SMS or WhatsApp provider.
- **`/api/pricing` now reads the catalog.** The settings-based prices are no longer used by the site.

**The parent create flow (Addendum 4, step 2d; design Create1–Create9)**
- **One full-screen wizard at `/create`.** The step and the ids (child, character, book) live in the URL, so a reload, the back button and the account page's links all resume in the right place. Everything else lives in the API. Checkout and the order page are the store's own pages (design steps 11 and 12).
- **Step 4 is the book type (Classic or Magic),** side by side, with Magic suggested gently (Addendum 4 §7). The styles offered next are the ones that type can draw. An approved character that the type can draw is reused, so a second book costs no new drawing.
- **The consent text is versioned in the web messages** (`create.consent.version`, now `parent-2026-09`). The API accepts only the current version, so a page showing an old text gets a "reload" answer instead of recording the wrong consent.
- **"Change the photo" replaces it.** The earlier photo is deleted from storage at once, so the next drawing never mixes an old photo with the new one. A photo uploaded after a character was already approved gets its 24-hour deletion time immediately.
- **Redraws can say what was wrong** (skin tone, face, hijab or hair, looks older). The choice is saved on the character and reaches the image model through character prompt v3. v3 is identical to v2 when nothing was ticked. Each redraw also gets a new seed. A drawing that failed on our side doesn't use up one of the parent's 3 free redraws.
- **The optional "something special" note** (design Create1) is stored with the interests, and the story prompt weaves it in the same way.
- **A Classic dedication adds the 5 ₪ dedication-page extra by itself** when the book goes to the cart. It is free in Magic.
- **"Delete all my child's data"** is on the account page (CLAUDE.md §3.1). It deletes at once all stored files under the child's prefix: photos, character sheets, companions, books and PDFs. It then deletes the child's rows (consents, photos, characters, companions and books go with them) and removes their unbought cart lines. Orders are the shop's records, so they stay, but without the child's name, age or dedication. An open order gets a note so the team stops making that book. The audit log records only that it happened. **Issued invoices are kept as they are** (tax records), including the book line's child name. Say if they should be reissued without it.

**Workbook engine (Addenda 5 and 6)**
- **One engine package** (`packages/workbook`, `qamra_workbook`) serves both workbook products, as Addendum 6 requires.
- **Plans are data with automated rules.**
  - «دوسية التأسيس»: `content/workbook/curriculum/{level}.yaml`, checked by `python -m qamra_workbook.plan check`.
  - «رحلتي الأولى للتعلّم»: `content/journey/plan.yaml`, checked by `python -m qamra_workbook.journey check`.
  - The readable plans in `docs/` are generated from the YAML, so what the educator reviews is exactly what the engine will build.
- The checkers encode the addenda's rules: page counts, interleaving or journey order, reviews and assessments, the per-letter steps, quantity before numerals, the writing progression, memory pages on the two sides of one sheet, and instructions of 7 words or fewer.
- The drafts were written by parallel agents, and both addenda stop for Tareq's approval before pages are designed.

## 2026-09-28 — Addendum 3: premium books at ≤ $2.50

Verified prices and parameters are listed in `docs/plans/addendum-03.md` §1, with sources.

**Models**
- **Default image model: fal Nano Banana 2** (`fal-ai/nano-banana-2`). With reference images the provider switches to `/edit` automatically, which takes up to 14 references. It is $0.08 per image at 1K and $0.06 at 0.5K.
- **Fallback: `fal-ai/flux-2-pro/edit`**, used only after 2 failed attempts on the primary (setting `fallback_after_failures`). Every switch is logged, recorded on the attempt, and counted on the cost dashboard. The admin field "FLUX model" became "fal fallback model"; a migration renames stored rows.
- **Content blocks count as a failed primary attempt.** A false positive in one provider's filter shouldn't leave a child's page blank. Our own Haiku QA safety check still judges whatever comes back, and unsafe pictures are never kept, not even for review.
- **Text models:**
  - `claude-sonnet-5` writes the story at `effort: medium`.
  - `claude-haiku-4-5-20251001` runs page QA, the safety review and drawing checks.
  - Opus stays selectable in admin.
  - Server-side refusal fallbacks are sent only to the models that support them (Opus 5/5.5, Fable). Haiku 4.5 gets no `effort`.

**fal privacy**
- **Every fal call sends `X-Fal-Store-IO: 0`** (no 30-day payload history) and a 15-minute expiry on generated files.
- References go inline as data URIs and results come back inline (`sync_mode`), so nothing is uploaded to fal's CDN.
- fal error payloads echo the request (which includes our reference images), so only the error type and message are ever logged.
- fal's terms allow de-identified or aggregated usage data to improve services. There is no explicit "never train on inputs" clause outside enterprise contracts. Tareq should get written confirmation from fal before real children's photos go through it.

**Prompt caching**
- The story system prompt (rules + the theme's beats and lesson) contains no child data, so class batches of one theme reuse it. The minimum for Sonnet 5 is 1024 tokens.
- QA calls cache the book's reference images: character sheet, cover and companion. Haiku 4.5 needs a 4096-token prefix, and the first real book showed the prefix was ~3.5K tokens, so QA never cached (29 calls, $0.14). **Fix (page QA prompt v2):** the QA system prompt now carries the full house style, people, safety and negative rules plus the book's locked outfits. Those are the rules the judge needs anyway, and they add enough tokens to cross the minimum. The cover reference is now the print cover downscaled to 1536 px instead of the small preview.

**Look and consistency**
- **The cover is the outfit anchor.** It is drawn first, in the book's locked outfit, and QA'd. Every page then gets the character sheet (identity) and the cover (outfit, style, palette) as references. This gives consistent outfits without paying for a separate outfit sheet.
- **Locations and lighting:** each theme defines named locations whose description is repeated word for word, plus a time of day per page. This keeps rooms and light the same through a sequence.
- **House style path:** the addendum names `packages/ai/prompts/style/qamra_style.md`. Our prompts live inside the Python package so they ship in the Docker images, so the file is `packages/ai/src/qamra_ai/prompts/style/qamra_style.md`.
- **The art-style choice now sets only the painting medium.** Watercolor is the default; crayon and paper-cut stay optional. Palette, setting, people, composition, safety and negatives come from the house style.
- **Names never go into image prompts.** A written name (especially Arabic) invites lettering in the picture, which would fail the no-text rule.

**QA and budget**
- **QA scoring is weighted** (likeness 45%, outfit 15%, text space 15%, count 10%, companion 10%, style 5%) and passes at 0.75, set in admin.
- **Hard fails:** unsafe, text in the image, broken anatomy, the hero missing or duplicated, likeness below 4/10. Likeness below 7 is flagged "face".
- **At most 2 automatic redraws**, then the best safe attempt is kept and flagged for a human.
- **The budget cap is per book (default $3.00).** Character and companion sheets are per child and reused across books, so they are not charged to a book's cap. A book's cap can be raised in review. Manual redraws count toward it and are pre-checked by the API.
- **Background plates:** child-free pages (`no_child: true`, one per MVP theme) are cached per theme, version, style, house-style version, resolution and language.

**Resolution: 1K + upscale (A/B done with real keys, 2026-09-28)**
- Previews are drawn at 0.5K. When the book is ordered, the preview pages are redrawn at final resolution with the approved preview as an extra reference, so the final matches what the parent saw.
- **The final default is 1K + SeedVR upscale** (`fal-ai/seedvr/upscale/image`, $0.001 per megapixel). A local Lanczos resize then fits the image exactly to 2551 px (216 mm at 300 DPI).
- **A/B** (`scripts/ab_resolution.py`, beats 1, 6 and 16 of a real first-day book, same prompt and references in both arms):
  - Cost: 1K + upscale is $0.0862 per page and 2K native is $0.12, about $0.60 more per 18-image book, which would push a book past the $2.50 cap.
  - Quality: compared on 800 px crops at 300 DPI (≈ 68 mm, i.e. true print size), they are equally sharp. 1K + upscale has slightly crisper line edges; 2K keeps slightly more paper grain. Faces, hands and hijab folds are the same in both.
  - **Decision: 1K + upscale.** It gets the same print sharpness for 72% of the cost. It is still to be confirmed on a physical printer proof (paper grain may read differently on uncoated stock). Switching is one admin setting (`final_mode = 2k_native`).

**Book structure**
- Books are 24 pages: title + dedication, 20 story pages (17 beats: 3 spreads, 2 split pages, 1 plate), the «وهكذا وُلد صاحبي» page when there's a drawing, «للأهل», then the activity and memories pages to reach a multiple of 4.
- **RTL imposition:**
  - Page 1 is a left-hand page; spreads start on even pages.
  - A spread's even page is read first and is the right half, so the text panel goes there.
  - The cover wrap is laid out front | spine | back (the mirror of an LTR wrap), and the spine width is a setting.
- **Typesetting:**
  - Noto Naskh Arabic (SIL OFL 1.1: commercial embedding allowed) for story text: 20 pt for ages 3–5, 16 pt for 6–8, line height 1.9. It shrinks in 0.5 pt steps to 18/15 pt when text doesn't fit, and anything still overflowing is flagged.
  - Baloo Bhaijaan 2 only for titles and the cover. Folios use Arabic-Indic digits.
- **Text panel:** cream at 88% opacity. It goes to 96% when the art underneath is busy (edge measure) or the ink contrast falls below 7:1, and busy areas are flagged.
- **Preflight** uses pypdf + pdfplumber (BSD/MIT). It checks exact MediaBox/TrimBox/BleedBox, embedded non-Type-3 fonts, every image ≥ 300 DPI effective, no text outside the trim (error), text inside the safe margin (warning), and page count % signature. Chromium rounds page sizes to CSS pixels, so the renderer rewrites the boxes to the exact millimetre size.
- **Offline "sketch" provider:** the design's illustration parts rendered with Chromium, with no network and $0. It's used for demos, e2e and the sample PDFs until real keys run, and the admin sample form can choose it ("placeholder art").

**Fixes found by the first real books**
- **The plate cache key includes the image model.** The first real book got the offline sketch provider's plate for its child-free page, because the key did not say which model drew it. Keys are now `plates/<model>/<theme>/v<version>/…`. The polluted plate was deleted and the page redrawn.
- **Books are pinned to the theme definition they started with** (`generation.theme_def`). A theme edit or version bump mid-generation cannot mix two versions in one book, and redraws use the same scene text as the original pages.
- **Classroom scenes invited writing.** 6 of 18 pages in the first book were redrawn, most for text in the image (alphabet posters, labelled shelves, book titles). The first-day and graduation classroom descriptions now say what is on the shelves (wooden toys, stacking cups, baskets of blocks) and that nothing in the room has writing. The house style (v2) adds: book spines and covers are plain blocks of color; no posters, charts, calendars, labels or price tags. The themes went to version 3.
- **SeaweedFS SSE-S3 corrupts objects over 8 MB** (4.47: reads fail with "wrote more than the declared Content-Length"). Print PDFs are 20–60 MB. We turned off per-object SSE (`S3_SSE=none`). Volumes are still encrypted at rest by SeaweedFS (`-s3.encryptVolumeData`), so photos and books stay encrypted. Uploads over 8 MB are now multipart, and the S3 container has 1 GB of memory. We verified 4/9/30/60 MB round trips. Production uses R2, which encrypts everything at rest and is not affected.
- **Found by reading the graduation book's print PDF** (the automatic QA had passed all of these):
  - **Painted page numbers.** The page prompt named the page ("page 3"), and on 2 of 17 pages the model painted that number into a corner like a printed folio. Page prompt v3 describes the page without a number, and house style v3 forbids page numbers and corner marks.
  - **A duplicated hero.** One page showed two identical girls hugging where the text has one child. QA v2 scored it 0.955. QA v3 counts children by face, not by outfit (whole classes wear the same gown), and counts look-alikes as a duplicated hero. It also asks QA to check the corners for digits.
  - **A repeated dedication opening.** Parents naturally write «إلى ليان… مبارك», which printed as «إلى ليان… إلى ليان… مبارك». The opening is now added only when the message doesn't already address the child.
  - This is why every book still gets a human review before print. The automatic QA lowers the review load; it does not replace the review.
- **The regeneration rate counts only automatic redraws after a failed QA check.** The addendum uses this rate to find themes whose scene prompts need work. The first count took every extra attempt, so a book with a preview showed 4 phantom redraws (the pages redrawn at print resolution after ordering), and admin redraws counted too. Each attempt now records why it was drawn: "qa", "error" (a provider retry) or "manual". The two real books were backfilled from their cost log.
- **The cost dashboard leaves placeholder-art books out.** They cost $0 and would pull down the average the $2.50 cap is judged by.
- **A/B and other tooling spend is not charged to a book.** It is logged against the child with `book_id` empty, so it shows on the dashboard without inflating a book's cost or tripping its budget.

**Review and security**
- **Nothing reaches print without approval.** Final books end in `in_review`. Approval requires both print files and a passing preflight. Text edits and redraws re-render the PDFs.
- **Admin 2FA:**
  - Every admin endpoint requires a session that passed TOTP (RFC 6238, ±1 step). Codes are never accepted twice, because the last used step is stored.
  - 10 single-use recovery codes are stored as sha256 hashes. Admins can't turn 2FA off; recovery is `qamra reset-2fa --email …` on the server.
  - An optional admin IP allowlist sits in admin → security.
- **HTTPS on this server:** port 80 belongs to another project's host nginx, so `infra/scripts/setup-https.sh` adds a host-nginx site + Let's Encrypt for our domain in front of the edge, which is then bound to localhost. The edge trusts `X-Forwarded-For` only from Docker bridge addresses; internet clients keep their real IP, which was re-tested with spoofed headers.
- **ufw is prepared, not applied.** `infra/scripts/firewall.sh` is dry-run by default. On this shared server it would close other projects' public ports (4000, 8080, 5432), so it needs Tareq's go-ahead.

## 2026-09-28 — Admin settings, music, security

- **All operator-facing configuration lives in the admin** (Tareq's requirement): prices, contact details, AI keys and models, notifications, site switches and privacy retention. Infrastructure secrets (DB URL, JWT secret, `SETTINGS_ENCRYPTION_KEYS`) stay in the environment; they can't safely be edited from inside the system they protect. The registry is in `qamra_core/app_settings.py`.
- **Example values ship as defaults** and carry an "example" badge until an admin saves a real value:
  - Prices: 49/89/119 ₪ and 9/16/22 JD.
  - Phones: +970590000000 and …001.
  - Emails: `@example.com`, a reserved domain, so nobody's real inbox is used.
  - AI keys: empty, since there's no such thing as an example key.
- **Music is generated, not licensed:** an original composition rendered by `scripts/make_music.py`, so there are no rights issues. Playback starts on the first user gesture because every browser blocks audible autoplay. Muting is remembered per browser.
- **CSP nonces require per-request rendering of every page** (`connection()` in the root layout). Pages are light, and the settings/pricing reads hit the API's 10-second cache.
- **Admin 2FA and HTTPS are the top remaining security items.** See `docs/security.md`.

## 2026-09-28 — Design import + public site

- **The full design canvas is in `design/canvas/`**: 77 `.dc.html` artboards and `canvas.json`, taken from the Claude Design artifact Tareq shared. Screens are implemented from these files. The design's illustration parts (`Kid`, `Scene`, `Drawing`, `Companion`, `Moon`) are ported 1:1 to React SVG components (`apps/web/src/components/art`) and stand in for art until real generated characters exist.
- **No bracket placeholders ship** (design README rule):
  - Prices come from `PRICE_*_ILS`; when unset, the site says "الأسعار قريباً" (prices coming soon).
  - Testimonials stay hidden until there are real quotes.
  - Contact numbers and emails and the company name come from `NEXT_PUBLIC_*` and are hidden when unset.
  - The privacy card states the real rule: photos are deleted within 24 hours of character approval.
  - FAQ answers only claim what the product actually does.
- **Story worlds:**
  - Available: the three MVP stories from the spec. «أوّل يوم في الروضة» (first day) and two new ones, «يوم تخرّجي» (graduation) and «ضيفنا الصغير» (new sibling), each with 12 pages and masculine/feminine variants. The new-sibling story calls the baby «الضيف الصغير» throughout, so the book never needs the baby's gender.
  - Coming soon: the five other worlds in the design catalog (moon trip, olive season, dream boat, star keeper, neighborhood friends) are catalog-only entries. Their stories are not written yet.
  - Each theme's `catalog` block in `theme.yaml` holds the name, tagline, description, occasions, values, tag, rank and illustration settings. Themes are seeded into the DB on every deploy (`migrate` runs `qamra seed-themes`).
- **Landing samples are real product text**: "صفحات من حكاية يوسف" shows pages 1/4/8/12 of the first-day story, rendered for the sample child.
- **Kindergarten demo requests** are stored in a `leads` table, rate-limited to 5 per IP per hour. An admin view comes in Phase 3.
- **`/create` is a placeholder page** until the create flow (Phase 2) lands. Every "start" button already points to it.

## 2026-09-28 — Phase 1

- **Job queue: RQ 2** (not Celery). It needs only Redis, has few moving parts and is easy to debug. RQ 2.12 has a built-in `rq cron` scheduler, which covers the periodic privacy cleanup without Celery beat. Jobs are plain functions: the api enqueues them and `apps/worker` runs them. Queues, in priority order: `generation`, `pdf`, `maintenance`, `default`.
- **Local S3 is SeaweedFS (`chrislusf/seaweedfs`, Apache-2.0), not MinIO.** MinIO no longer publishes pullable container images: Docker Hub denies every tag and quay.io requires authentication (checked 2026-09-28). This affects local development only. Production stays on Cloudflare R2, and the code only speaks the S3 API. SeaweedFS runs in `weed mini` mode with `-s3.encryptVolumeData` (data encrypted at rest), and it accepts SSE-S3 (`S3_SSE=AES256`, the compose default; verified with put + head). The bucket is created at startup, and credentials are generated from env vars.
- **Shared package `packages/core` (`qamra_core`).** It holds the settings, SQLAlchemy models, Alembic migrations and the storage adapter, and is used by both the api and the worker. This is an addition to the spec's repo layout.
- **One driver (psycopg 3)** for async FastAPI, the sync worker, and migrations.
- **Enums are VARCHAR + CHECK** (`native_enum=False`), not PostgreSQL enum types, so values can be added without type migrations. `scripts/make_migration.py` post-processes autogenerate output for two known quirks: duplicated CHECK constraints, and `use_alter` foreign keys emitted inline.
- **Deletion model:** tables owned by a child cascade from `children`, and objects live under `children/{child_id}/` in storage, so "delete all my child's data" is a prefix delete plus one row delete. Order items and generation costs keep their rows, with the foreign key set to NULL. Audit logs carry ids and action names only.
- **Model changes vs spec §6:**
  - `Book.share_token` is replaced by a `share_tokens` table (scopes read / listen / record, expiry, revoke; Addendum 1 §3).
  - Orders get an `order_items` table.
  - `users.organization_id` links school admins to their kindergarten.
  - New `refresh_tokens` table.
  - `book_pages.original_text` backs "restore original".
- **Auth:**
  - Access token: JWT, 15 minutes, in an httpOnly cookie (`qamra_at`, path `/`).
  - Refresh token: opaque, 30 days (`qamra_rt`, path `/api/auth`), stored only as a sha256 hash and rotated on every use.
  - Reuse detection: presenting a rotated or logged-out token revokes that whole login. A 30-second grace window for *rotated* tokens stops two tabs that refresh at the same moment from logging the parent out.
  - Passwords use argon2id (pwdlib).
  - Login is rate-limited in Redis per email+IP and per IP.
- **CSRF:** SameSite=Lax cookies, plus a required `X-Qamra-Client` header on POST/PUT/PATCH/DELETE. Browsers can't set custom headers cross-site without a CORS preflight, and the API allows no cross-origin requests.
- **Google sign-in:** hand-written OIDC code flow (httpx + PyJWT JWKS). State and nonce live in a signed 10-minute cookie. A verified Google email links to an existing account with the same email. The feature is enabled by `GOOGLE_CLIENT_ID/SECRET`, and the web button by `NEXT_PUBLIC_GOOGLE_LOGIN=1`.
- **Web → API:** `src/proxy.ts` rewrites `/api/*` to `API_INTERNAL_URL` at *runtime*; `next.config` rewrites would be fixed at build time. Cookies therefore stay first-party on the web origin. In production Nginx can route `/api` directly (Phase 6).
- **i18n:** next-intl with `/ar/...` and `/en/...` prefixes, Arabic by default. Browser-language detection is off, so Arabic-speaking parents with English phones still get Arabic until they switch.
- **Web stack versions:** Next.js 16.3 (the proxy replaces middleware; `next/root-params`), React 19.2, Tailwind 4 with CSS `@theme` tokens transcribed from `design/tokens.json`, and next-intl 4.14.
- **Test database:** local runs use `qamra_test` on the Qamra test server (Postgres 18, reached through an SSH tunnel). CI and `docker compose` use Postgres 16. The fixtures refuse any database whose name doesn't end in `_test`, because each session drops and rebuilds its schema through the migrations.
- **Nginx `edge` is the only public entry point** (`QAMRA_BIND` / `QAMRA_WEB_PORT`); every other service stays on 127.0.0.1 or the Docker network. When a client sends its own `X-Forwarded-For`, Next.js passes it through unchanged; tested with a spoofed `6.6.6.6`. Exposing the web or API container directly would therefore let anyone bypass the per-IP login limits with a fake header. The edge *overwrites* `X-Forwarded-For` with the real peer address and routes `/api/*` straight to the API. Verified on the test server: 12 logins with 12 different spoofed IPs were blocked at attempt 11 and keyed to the real client IP. Rule: never publish the `web` or `api` ports publicly.
- **`compose.yaml` lives at the repo root** (not under `/infra`), so `docker compose up` works from a fresh clone as the acceptance test says. Dockerfiles and database init scripts stay in `/infra`.

## 2026-09-28 — Phase 0

- **Brand is قمرة / Qamra** (Addendum 1). The name, domain and support contacts come from config (`BRAND_NAME_AR`, `BRAND_NAME_EN`, `BRAND_DOMAIN`), not code. `CLAUDE.md` was renamed too. `design/README.md` still says "حكايتي" in two places (the preview watermark text and the B2B owner tag). `/design` is read-only, so I left it; the code renders the watermark from config.
- **Design handoff is partial.** The `/design` canvas holds the design system (tokens, dark mode, logo options, components, illustration parts). It does not hold the 77 screen artboards or the print-layout artboards that `design/README.md` lists. The Phase 0 PDF follows the README print spec and `tokens.json`. The screens will need the per-screen HTML exports before Phase 2.
- **Logo placeholder: option A «هلال على صفحة»**, matching the design README.
- **Python tooling: uv workspace** (`packages/ai`, `packages/pdf`). It is fast and gives a single lockfile. It is also already installed.
- **Default image model: Gemini `gemini-3.1-flash-image` at 2K** ($0.101 per image; the paid tier does not train on our data). The alternatives are behind the same interface: fal `fal-ai/flux-2-pro/edit` (FLUX.2 has replaced FLUX.1 Kontext as fal's multi-reference editor, with up to 9 refs) and OpenAI `gpt-image-2.5-sunburst` (the "editing precision" variant). Model IDs live in `.env`.
- **fal: no CDN uploads.** Reference images go to fal as base64 data URIs, and results come back with `sync_mode` as data URIs. A child's photo therefore never gets a public fal.media URL.
- **Text model default: `claude-opus-5`** for story adaptation and vowelization, where Arabic quality matters most. Safety and judge calls use a separate setting (`TEXT_MODEL_FAST`), which also defaults to `claude-opus-5`. Moving those to a cheaper model is a cost decision for Tareq.
- **Print size: 216×216 mm pages** (210 mm trim + 3 mm bleed on each side). Images are generated square and upscaled to 2551 px (300 DPI at 216 mm) with Lanczos in Phase 0. A real upscaler is a Phase 2 decision.
- **CMYK:** Chromium writes RGB PDFs. Phase 0 keeps the palette CMYK-safe by avoiding saturated RGB-only colors in the layouts; the images are left untouched. Converting to the printer's ICC profile (Ghostscript) is deferred until we know the print partner's profile.
- **Book body font:** Baloo Bhaijaan 2 (the design's display font) for titles. Story text uses Noto Naskh Arabic because its تشكيل placement is clearer for early readers than a rounded display face. This is a deviation from the design body font (IBM Plex Sans Arabic); see the PDF samples to decide.
- **Photo check uses YuNet** (`FaceDetectorYN`, MIT license, OpenCV zoo, 230 KB model in `qamra_ai/models_data`). OpenCV 5 no longer ships Haar cascades, and YuNet handles non-frontal kid photos far better. It is a detector only; no face recognition or embeddings. No InsightFace or other research-only models are used.
- **Fonts are embedded as static instances.** Chromium embeds *variable* fonts as Type 3, which print RIPs often reject. `BalooBhaijaan2-{Medium,ExtraBold}` and `NotoNaskhArabic-{Regular,Bold}` were instanced with fontTools from the OFL variable fonts. A test asserts that no Type 3 fonts are present.
- **PDF page box is 612 × 612 pt (215.9 mm)**, not exactly 216 mm, because Chromium quantizes to CSS px (816 px, the design's artboard size). That is 0.1 mm under the bleed box. Confirm with the print partner; if they need exact sizes, post-process the MediaBox with pypdf.
- **Prompt templates render with `trim_blocks=False`**, and `render()` collapses runs of blank lines. With `trim_blocks` on, an inline `{% endif %}` swallowed the following newline and glued prompt lines together (caught in the story prompt).
- **Drawing shadow removal fits a quadratic lighting surface to paper pixels only** (low saturation, bright). The first version used local dilate + median-blur background estimation, which erased large crayon fills to white.
- **Cover and page composition:** page prompts ask for a calm top quarter (a third on the cover) for the text box. Faces stay out of the outer 6%, which is roughly the bleed plus a margin.
- **Interior page count is not yet padded to a multiple of 4** (it is currently title + 12 + keepsake = 14). Padding rules depend on the print partner's binding.
- **Recognizability metric (Phase 0):** a Claude vision judge compares each page with the approved character sheet. This is a proxy until a commercially licensed face-similarity model is chosen for the admin QA screen.
