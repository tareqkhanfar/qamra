# Decisions log

Newest first. Each entry: date — decision — why.

## 2026-09-29 — The template studio: theme versions, bulk actions, staff roles (Addendum 4 step 4, W8)

- **Theme versions live in `theme_versions`** (definition JSON, status, author, timestamps). `themes.definition` stays the live copy that every reader already uses, so nothing else had to change.
  - Statuses: draft → in_review → approved → live. A replaced live version becomes `retired`, and a rollback publishes it again (the same row and number, so the history keeps its meaning).
  - One open version per theme (draft, in review or approved), enforced by a partial unique index. Edits never fork.
  - The migration records each theme's current definition as its first live version (`source = file`).
- **A text edit lands in the open draft**, or makes one from the live version. A version in review or approved must go back to draft first. The whole definition is re-validated on every save (story rules and placeholders), so a draft is always publishable.
- **Deploys keep studio work.** `upsert_themes` publishes a content file only when its version is newer than every version of the theme, or corrects its own live file version in place (as before). A theme published from the studio is left alone until a file with a higher version arrives.
- **Classic templates keep their art and their pinned words.** When the live words differ, the template shows «texts out of date». The existing texts endpoint (`refresh`) takes the new words and now also records the template's `theme_version`. As before, it sends an approved or live template back to review.
- **Books keep their definition** (`books.generation.theme_def`, unchanged).
- **Scheduled go-live is a cron job** (`qamra_worker.jobs.studio.run_scheduled_publish`, every 5 minutes), not a check on read. The shop's reads stay as they are. A template that is no longer approved on its date is skipped, its date is cleared, and the audit log says why.
- **«ترجمة» is an English draft of one version**, made by the text model only after the editor sees the estimate (`GET …/translate`) and confirms. A failed draft is marked failed and not retried, because a retry would pay again. The cost goes to `generation_costs` with no book.
- **Staff roles:** admins (the `users` permission) add, change and remove staff. Only an owner grants or takes away the owner role, and nobody changes their own roles, so an owner always remains. The audit viewer (`users.audit`) returns only what the log holds. The page names staff actors from the staff list; anyone else shows as a short id.
- **Font size is not editable per page.** The renderer sets it from the child's age (20 pt for ages 3–5, 16 pt for 6–8) and shrinks it to fit (18 or 15 pt at least). The preview follows the same rule. The template's text box is shown, but the renderer places the panel by its area.

## 2026-09-29 — Phase 5: «صوت أهلي», the WhatsApp seam, SEO, performance

- **The add-on switches the feature on.** A book has family voice when a live order line for it carries `family-voice` (a cancelled order doesn't count). Without it there is no QR in the PDF, and recording answers «هذا الكتاب بلا إضافة» (403).
- **One printed link per book, fixed for good:** a `listen` share token of 20 URL-safe characters (120 bits), made when the final PDF renders or the parent first opens the record screen.
  - Each story page's QR is `https://{BRAND_DOMAIN}/v/{token}/{page}` (the theme beat), and the back cover's QR opens the first page.
  - The parent can pause and resume listening, but not rotate the token: a new one would orphan the printed book.
  - **A QR goes on every story page**, not only the pages recorded before printing (the BookQR design note): families record after the book arrives, and a page without a voice shows its words.
  - The design's `/l/` path is `/v/`, as Addendum 1 and the task say.
- **Placement (design BookQR):** an 18 mm code with a 2 mm quiet zone on a paper card with 3 mm corners and «امسح واسمع» in 8 pt. Its edges sit on the 10 mm safe line in the outer bottom corner (left on left-hand pages, right on right-hand pages), and text boxes on that side move away. The code is a vector (`qrcode`, already in the lockfile, BSD) at error correction M, and a test decodes it from the print PDF rendered at 300 DPI.
- **Recordings are real voices only.** The browser's MediaRecorder tries MP4/AAC first (it plays everywhere, Safari included), then WebM/Opus and Ogg.
  - The API checks the file's own bytes, ≤ 8 MB and ≤ 3 minutes a page, and up to 3 voices a page, named by the family.
  - They are stored encrypted under `children/{child}/books/{book}/voice/`, so «حذف بيانات الطفل» removes them; their rows go with the book.
- **Audio links are same-origin API URLs signed with an HMAC that expires in 10 minutes**, not bucket URLs. The site's CSP allows media from 'self' only, and a grandparent's phone never talks to the bucket. The API streams the bytes and answers range requests (Safari needs them).
- **A grandparent's link** is a `record` share token: 7 days, revocable, and optionally limited to chosen pages.
  - New columns `share_tokens.pages` and `opened_at` (migration `19ebf7d578eb`).
  - No account; the voice's name is the invite's label.
  - The parent sends it from their own WhatsApp (a `wa.me` share), never through our sender.
- **The TTS fallback** is `qamra_ai.tts`: `TTSProvider.speak(text, lang)` has no voice-sample parameter, so it can't imitate anyone. The admin setting `tts_provider` is `none` (default) or `fake`. A paid provider waits for Tareq's approval; until then a page without a recording shows its text.
- **The listen and grandparent pages fetch from the browser**, not the server, so each visitor counts against their own per-IP rate limit.
- **Link tokens stay out of the request log:** the access line masks the token in `/api/shared/…`, `/api/voice/invites/…` and `/api/voice/listen/…` paths. Query strings, where the audio signatures travel, were never logged.
- **WhatsApp:** `qamra_api.whatsapp` has a `WhatsAppSender` interface with three senders.
  - `links` (the default) sends nothing: the status messages stay ready-to-send links.
  - `log` writes only the template and the order code.
  - `twilio` is built but disabled: it refuses unless `approved=True`, which nothing passes.
  - Addendum 9 keeps email as the only automatic channel.
- **SEO for the story pages:**
  - title and description in each language;
  - canonical and hreflang (ar, en, and x-default → ar);
  - the published example's cover as the Open Graph picture;
  - Product + Book JSON-LD with the lowest price a parent can order at;
  - `/sitemap.xml` built per request from the API, and `/robots.txt` with the private paths disallowed.
  - Private pages stay noindex; the account page was missing it.
- **Performance** was measured with Lighthouse 13 (mobile, simulated 4G) on a local production build. The first load is fonts (13 files, about 380 KB) and framework JS (about 160 KB).
  - Preloading only the Arabic font files was tried and reverted: Latin digits and punctuation appear on every page, so those files load anyway, just later (FCP 1.4 → 2.1 s).
  - Kept: a week of browser caching for the files in `/public`, which had `max-age=0`.
  - Fewer font weights would help most, but that is a design decision.

## 2026-09-29 — Activity-book pages: orderable flag, previews, and the child's character

- **"Can it be ordered now" is a product flag, `features.orderable`**, not a new column: no migration, and it is edited in the admin next to the product. The API decides it (`qamra_api.store.workbooks.orderable`):
  - A missing flag means orderable, except the educational lines («دوسية التأسيس» and «رحلتي الأولى»). Those wait for the educator's sign-off, per Tareq's rule.
  - The seed writes `orderable: false` for both.
  - `check_item` refuses a closed product in every cart path.
  - The pages read the flags from `GET /api/shop/summary`.
- **The previews are static files:** real engine pages of the invented sample child (AI-drawn, no real child's data), exported once by `scripts/export_workbook_previews.py` to `apps/web/public/workbooks/`, and listed in `apps/web/src/lib/workbook-previews.json`.
  - «دوسية التأسيس» shows the design's illustrations, with a note, until its renderer is complete (it is still being built).
- **A workbook is bought for a child with an approved character.**
  - The page asks which child. `POST /api/shop/workbooks/cart` stores `child_id`, the variant (its options) and the character used, so the order-time render can find everything.
  - Without a character, the create flow runs with `product=<sku>`. It uses the house style and reuses any approved character, then adds the book to the cart.

## 2026-09-29 — Phase 4: the kindergarten portal and «كتاب الصف»

Plan and file map: `docs/plans/phase-4.md`.

**Accounts and privacy**
- **A school's sign-up gives an account at once; the organization waits.** The `school_admin` user can sign in
  right away and sees a «pending» page until staff approve the organization in `/admin/organizations`. The
  approval is audited. Every portal query filters by the caller's organization, and another school's class
  answers 404, like a missing one.
- **The invite link makes the parent the child's guardian.** The school's child row has no guardian. The parent
  opens a per-child link (a random token, stored as-is so the school can copy it again; it expires after
  `portal_invite_days`, 30 by default), signs in, and accepts.
  - From then on the child is the parent's, with all the create flow's rights. Deleting the child removes them
    from the class too.
  - A link works for one account, and school or staff accounts can't accept one.
  - Before a parent accepts, the school can remove the child (the row is deleted). Afterwards, removing only takes
    the child out of the class.
- **The school sees states, not photos.** The board shows invited → consent → photo → drawing → approved.
  - A photo counts as uploaded even after its 24-hour deletion.
  - The school may view the parent-approved drawing, because it appears in the class book anyway. It never sees
    the photo, and no endpoint gives a school a photo or a photo's storage key.
  - The consent text of the invite (version `school-2026-09`) says so, and says that classmates' copies show the
    drawing.
- **The create flow's code is reused, not copied.** Consent is recorded by `qamra_api.consent.record_consent`, now
  used by `create.give_consent` too. The photo upload and the character approval are the create flow's own
  endpoints. The invite's drawing step calls `create.draw_character` with the class's art style.
- **The class photo is the school's upload, with its confirmation.** It is accepted only with the checkbox "the
  kindergarten has the parents' permission to print it". The confirmation, its time and the user are stored and
  audited. The photo is re-encoded without metadata and kept privately under the class prefix. The school can
  delete it; there is no automatic deletion yet (open point).
- **Parents' contacts are the school's data.** They are stored on the invite row, shown masked on the board
  (0599 ••• 456), and never logged. WhatsApp sharing opens `wa.me/?text=…` without a number, so the school picks
  the contact itself. We send nothing: automatic WhatsApp or SMS still waits for Tareq's approval.

**The class book**
- **Class templates are content** (`content/class-books/<theme>.yaml`).
  - Core scenes are always in the book. `extra` scenes join in their story position until the class's
    appearances fit, and repeats are the last resort.
  - Texts never make a verb agree with the names («… : {names}»), so any mix of boys and girls reads correctly
    without a language model.
  - Only `graduation` has a template for now.
- **The plan gives every child exactly N appearances** (N = `class_book_min_appearances`, 2; the school can
  raise it). Appearances are spread over the book, never twice on one page, and pages are as evenly filled as
  their places allow.
  - Places per picture are capped per image provider (`class_book_refs`, "fal:3, gemini:3, openai:3"; unlisted
    providers get 3).
  - A teacher's edits make the plan "manual". A later class change then asks for a new plan instead of silently
    replacing the teacher's work.
- **The class group page is composed, not drawn.** No model keeps 30 faces consistent in one picture, so the page
  is a grid of every child's approved character (the front view of their sheet) with their name. Each copy has
  its own portrait page as page 2; for this, the front view is used as-is (no extra AI cost).
- **Classic class books** (Addendum 4 §1C) draw the shared pages once, with generic children and no named
  children. Children appear on their personal cover, their portrait page and the group page. When W1's Classic
  templates are live, these pages should come from the templates instead. Magic class books put named children
  into the story.
- **One batch job per class, resumable.** The job draws the shared pages, then the covers, then the files.
  - A page is redrawn only when its children changed or the school asked for it. The school has 6 free redraws per
    class.
  - The batch budget is the per-book cap × pictures ÷ 20, because a book's cap covers about 20 pictures.
- **Each child's copy is an ordinary `Book`** (`generation.line = "class"`). The admin review queue, print
  approval, print batches and "delete my child's data" all apply unchanged. The per-child files live under the
  child's storage prefix.
  - The review queue's generate, redraw and re-render actions on a class copy are routed to
    `jobs.classbooks.copy_action` (the same dispatch as Classic books in `jobs.books`). So a copy is never
    redrawn as a single-hero book, and a cover redraw reruns only that picture and the files.
  - In a re-run, copies whose pictures didn't change keep the school's and our approvals. When the class's
    shared pages change, every copy goes back to the school.
  - Deleting a child also deletes the class's shared pictures that show them and the combined print file. Those
    pages are redrawn without the child.
- **Print files.** The shared interior is rendered once, then the portraits and covers per child (one Chromium
  session). The copies are assembled with pypdf.
  - The combined print file puts each child's cover then their interior, and reuses the shared pictures, so the
    file doesn't grow with 30 copies of every page.
  - Preflight runs on the shared interior once, and on each portrait and cover.
  - Files are named `{school}-{class}-{child}.pdf` at download (storage keys stay ASCII ids).
  - Prepared images (logo, class photo, faces) are sized up to at least 300 DPI at their print size.

**Orders and prices**
- **The class order reuses the store:** the pricing engine with the price list's tiers, the order snapshot, and
  `issue_invoice`.
  - The school's own active list wins over the default kindergarten list.
  - Each approved copy is its own order line, so the invoice lists every child.
  - The invoice is issued when the school places the order, because schools pay against it. Cash on delivery to
    the school's address.
  - The product's `min_qty` of 20 is not enforced for portal orders: a class of 17 still orders. Below the lowest
    tier, the variant's list price applies.
- **B2B price lists live in the catalog admin** (the «أسعار الروضات» tab): the default list and per-kindergarten
  lists, tiers per variant with the margin per tier, and every edit audited.

**Dependencies**
- **No new dependency for Excel.** `openpyxl` isn't in the workspace, so the portal reads CSV only. It reads
  both encodings Arabic Excel writes, and gives an `.xlsx` a friendly "save as CSV UTF-8" message.
  - Adding `openpyxl` (MIT, pure Python) would read `.xlsx` directly. It is a one-line dependency change plus
    about 20 lines in `portal/importer.py`, left for Tareq's decision.

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

## «مغامراتي مع عائلتي», the whole book (W7, 2026-09-29)

- **Passport and stickers:** the passport has a slot for each of the 12 adventure stamps (round seals, numbered in the book's order) and each of the 7 adventurer badges (rosettes with ribbons, so the two kinds never look alike; an adventure and a badge may share a name, e.g. «طبّاخ صغير»). The sticker sheet has exactly one sticker per slot, sized to cover it, plus 21 chore stars, 7 day stars and 10 routine icons; the six word stickers («رائع!»…) were dropped for room.
- **Card stock:** the kit is five card-stock sheets in two print files (money and price tags, recipe cards; memory cards, question cards, role cards, finger puppets), not two sheets: the cards stay big enough for small hands. The printer's quote should count five sheets.
- **Die lines:** one layer «CutContour» (magenta #EC008C) in each insert PDF, plus the die alone as `…-die.pdf`. The printed dashed guides stay on the card stock for home cutting; the stickers print none.
- **Grown-ups:** the job interview and «حكايات زمان» ask `{adult}` (a grown-up), not `{member}`, so a young sibling is never asked about their work or childhood.
- **Order-time render:** a family book gets a `Book` row (on a hidden, inactive theme `family-book`, since every book has a theme) so it goes through the same print approval and print batches as the story books. An order without family details is drawn for the child with one neutral grown-up («أحد الكبار») and «عائلة <child's name>», never an assumed mother and father.

## «ارسم صاحبك» and «حكاية خاصة» in the parent flow (W3, 2026-09-29)

- **Where the companion step sits:** optional sub-steps of step 6, after the character is approved and before the story («الخطوة 6 من 12»). The design numbers it 4 in an older step order; the wizard's 12-step header stays as it is. The URL keeps `step=companion`, `companion=<id>` and `cstep=upload|name`; the other screens follow the companion's status on the server.
- **Data:** `companions` gets `status` (draft → generating → ready → approved, or failed), `options` (each drawn option's storage key, round, provider, model and fidelity score) and `params` (crop box, rotation, clean-up flag, art style, failure reason). Migration `d022f9307892` (on `918b650a07fc`). Companions of the admin sample books are marked approved.
- **Privacy (the photo rules):** the upload needs the guardian's consent, is re-encoded without EXIF/GPS (`clean_image`) and is stored under the child's prefix. The original photo is deleted `photo_retention_hours` (24 h) after the parent chooses the companion, or after `draft_retention_days` (30) when it is never chosen; the existing cleanup job does it. The options not chosen are deleted at the choice. The cleaned drawing stays for the keepsake page. The parent can delete a companion in «أصحابي» once no unfinished book uses it, and "delete my child's data" removes everything at once.
- **Crop and clean-up run on the server** (the existing OpenCV `clean_drawing`), not on the device as the design suggests: the parent's crop box (fractions of the photo), a clockwise turn and the paper/shadow clean-up can be changed until the drawing goes to the artist. The camera opens through the phone's own camera input (`capture=environment`): there is no live viewfinder or auto-capture.
- **Drawing:** the worker job `jobs.companions.generate_companion` reuses the companion pipeline: the drawing review, 2 options, then a fidelity and safety check per option (an unsafe option is dropped). Costs go to the child, not to a book. A redraw gets new seeds (`1000 × round + option`). Four rounds: the first and 3 free redraws. A round that failed on our side, or a rejected drawing, is not counted.
- **Reuse:** a chosen companion belongs to the child (`book_id` stays empty) and is offered again on the companion step of their next books and in «أصحابي». `POST /api/create/books` takes `companion_id` (approved, the same child).
- **Pricing:** the step shows when the catalog's `drawing-companion` add-on is offered for the line (admin data). Magic includes it. For Classic the cart line gets the add-on automatically (+20₪), like the Classic dedication. **Open:** the Classic pipeline (W1) still draws its template's default companion and prints no keepsake page. Until it edits the chosen companion into the template pages, take `classic` out of the add-on's lines in the admin so Classic parents are not charged for it.
- **The generating screen keeps the parent there** (about a minute). The design's «أكمل الكتاب وسنخبرك» (continue while it draws) is left out: the story needs the chosen companion before it is written.
- **«حكاية خاصة» (Magic):** a hidden base theme `custom` (content/themes/custom, no catalog block): 14 beats (16 story pages, 2 spreads) and no child-free plates, because plates are cached per theme. Claude writes the text *and* every page's picture (scene, place, time of day, outfit, other people, the companion's action) from the brief, with the versioned prompts `story_custom.v1` and `story_custom_user.v1`. The book pins the rewritten theme in `generation.theme_def`, so previews, finals, redraws and re-renders all draw the story's own scenes.
- **The brief:** the occasion and the place (≤ 60 characters each), 2–3 things the child loves or did (≤ 60), a wish or lesson (≤ 120), and up to 6 family members in the family's own words, each with an optional name. Nobody is assumed: with no one named, the prompt says so and the story speaks of "the family".
- **Checks:** the API checks the lengths, then screens at once for links, e-mails, phone numbers (6+ digits, Arabic-Indic too) and a short list of plainly violent words (whole words, also after و/ال), with a friendly Arabic error per field. The worker runs the existing story safety review (`story_safety.v2`, the fast model) on the brief before writing, and on the story after. A brief rejected there stops the book (`brief_unsafe`, not retried); the parent sees why and edits it (the brief is kept in the browser tab).
- **Sold as `magic-custom-story`** (169₪): the cart refuses a custom book as `magic-book` and a theme book as `magic-custom-story`.

## «قلبي يعرف الله»: the Islamic series, step 1 (the proposal), Addendum 10 (2026-10-01)

- **Nothing religious is typed by us.** `content/islamic/` holds *references and structure only*. A Quran verse is a range (sura, first ayah, last ayah) resolved from the Tanzil Uthmani file that Tareq places at `content/islamic/quran/quran-uthmani.txt` (tanzil.net's TLS handshake fails from this machine, and we do not bypass certificate checks). A hadith is a collection and a number; its wording comes from a verified source, never from a model. A dua is a span cut *by code* between two letters-only markers inside a hadith's verified text (the markers are never printed). Until a verified text exists a page prints a placeholder block, and the print build fails on a placeholder or on a source that is not `scholar_approved`.
- **Source status ladder:** `proposed` → `text_candidate` → `text_verified` → `scholar_approved`. Only the scholar's decision moves a source to the last step; the reviewer's name and date are stored with it and «راجعه علمياً: [الاسم]» is printed only then. A scholar who disagrees leaves the page in `scholar_review`.
- **Hadith candidates:** only from the open dataset `fawazahmed0/hadith-api` (its code is Unlicense; the status of the texts is a scholar's call, recorded in `docs/licenses.md`), over jsdelivr, for the editions of the six major collections. A candidate is a *candidate*: the fetch sanity-checks each hadith number against keywords from the plan and writes `content/islamic/candidates.json`; a mismatch is reported, never silently kept. The grading for anything outside Bukhari and Muslim is marked «للتحقق».
- **Where scholars differ we flag `scholar_decision`, we do not pick:** the hands in prayer (s-prayer-hands), pictures of people and animals (s-illustrations: we draw children, a grandmother and animals in a simplified style and never Allah, prophets, angels or Companions in any form; the scholar is asked whether that is accepted and whether to add limits, e.g. faceless people), and the characters' clothes in prayer scenes (s-prayer-clothing), the takbir of Eid (s-eid-takbir), and the age at which a child is told to pray (h-abudawud-495). The page is written so that either answer works until the scholar decides.
- **Series shape (proposal):** five volumes in two levels (V1, V2 for 4–6; V3, V4, V5 for 6–8) of 98–120 pages and a seasonal Ramadan and Eid book of about 70 pages: 639 pages, 43 units, 93 core concepts that cover all 16 areas of the brief. `python -m qamra_workbook.islamic check` computes pages, units and the retention matrix *from the plan itself*, and fails on an unknown unit/type/concept/source, a religious page with no source id, a dhikr page without a dua or Quran source, a surah page without a Quran source, a volume outside 96–120 pages (the seasonal book 48–80) or a concept that reaches fewer than five of the six retention forms (story, activity, question, situation, review, home). Today: 0 problems, 93/93 concepts.
- **Unit structure is automatic:** opener 1 + lessons + closing 2 + parent page 1, plus cumulative `self-test` pages after chosen units and the final assessment at the back. A concept first taught in unit N comes back (`r:` revisits) in later units, so the retention matrix is a promise the checker can read.
- **Ramadan first, by date, not by taste:** Ramadan 1448 starts about 8 February 2027 (moon-sighting decides), so the seasonal book must be live about 28 December 2026 (6 weeks before). It is the smallest volume and the one with the fewest scholar rulings, so the proposal recommends that it goes through every step (sources, pages, scholar, a printed proof) *before* V1, then V1 and V2–V5.
- **Binding:** perfect-bound is recommended over wire-o, because pages with the Quran should not be loose or tear out. Wire-o stays an option for the activity-heavy volumes. The proposal reuses the Addendum 7 price method: the printer column is an ⚠ estimate (placeholder tiers 40/35/29/25/18 ₪ for 1/10/50/100/500 copies, packaging 3 ₪, AI 0.30 USD) until the printer replies to `docs/islamic/printer-quote-request.md`; 10+ copies stay blocked until real prices exist.
- **Quran font:** Amiri Quran (SIL OFL, bundled in `qamra_pdf/fonts/` with its licence). KFGQPC Uthmanic Hafs is used only after its terms are read and recorded in `docs/licenses.md`.
- **AI cost:** Addendum 10 §8 allows AI for the cover and the character only (an existing character is reused), target ≤ 1 ₪ per book. The estimate in the proposal is 0.30 USD for a new character; the religious text is fixed content and no model rewrites it for a child.
- **Open for Tareq (proposal §11):** the name, the split (5+1 or 4+1), Ramadan-first, who the scholar is and when they can start, the Tanzil file, the reciter for audio, the binding and size, the real prices, and the sticker policy (the passport works by colouring a star, with no stickers; a sticker sheet is a paid add-on).

## The launch site: structure, availability and what the pages never say (2026-10-01)

- **One structure, in one sentence a parent can repeat:** story books where the child is the hero (Classic and Magic), three activity books («دوسية التأسيس»، «رحلتي الأولى للتعلّم»، «مغامراتي مع عائلتي»), and books for kindergartens. The menu is الحكايات · كتب الأنشطة · للروضات · الأسعار · كيف نعمل (+ cart, sign-in); the footer adds each book, «كل الكتب» (`/shop`, not in the menu), privacy and contact. The word «العوالم» is gone everywhere; `nav.themes` reads «الحكايات».
- **Pages:** `/` (promise, the four offers with real covers and "from" prices, a real book to flip through, three steps, why Qamra, the activity books, a short FAQ, one closing call), `/workbooks` (the three books side by side: real cover, age, what's inside, "from" price, real pages, a button to each page), `/workbooks/[product]`, `/pricing`, `/how-it-works` (story flow, privacy promises, activity-book flow, «صوت أهلي», the full FAQ), `/shop`, `/stories`, `/kindergartens`. Each answers "what is this, what does it cost, what do I do next" on the first screen of a 390 px phone; the screenshots are in `out/samples/launch/` (full pages, and `folds/` for the first screens).
- **Nothing is "coming".** Only what the catalog API returns is listed: a volume or stage that does not render yet is an inactive variant (`variant_matrix.rendered` in `content/store/catalog.yaml` and migration `a3c1f0b7e2d4`), so it is absent from the product page's chips, the cards, `/pricing`, the JSON-LD and the cart, and the page never says it is expected. Switching it on is the SQL in the migration's docstring (or Admin → الكتالوج → the variant's «active»). The ages on a card follow the levels sold (KG2 only → «5–6 سنوات»), and a note like "each stage builds on the one before" shows only when more than one stage or volume is sold (`many` in `WorkbookProduct`). Product copy that could name volumes (the catalog description says "three volumes") comes from the messages (`workbook.desc.*`), not from the catalog text.
- **Messages that were removed or rewritten:** the card-payment row in checkout (cash on delivery only, no mention of cards), `workbooksHub.available` («المتوفّر الآن» implies more is coming), the free-cover «not available» page (it now redirects to `/stories` while the switch is off), the empty cart ("pick a story" → "a story or an activity book"), and two portal messages that said "soon". **Left on purpose:** `admin.soon`, the badge of an admin menu item that is never ready (every item is, so it never renders), and the portal wording about the team reviewing a request.
- **`/pricing` is the catalog, nothing typed:** story formats per line, add-ons, activity-book prices per volume/stage/set, the class-book price per child, and delivery per zone with cash on delivery. `?country=jo` shows the same page in dinars with the Jordan zones (the cart's currency follows the zone); the switch shows only when the catalog has zones in more than one country.
- **Lifestyle photos** are slots (`public/photos/README.md`, `components/site/Photo.tsx`): each shows its file when it exists and the current art when not, and the phone view hides the ones that would push the content down (activity hub header, how-it-works header).
- **Search:** `pageMetadata()` (`lib/seo.ts`) gives every public page "title | brand", a clipped description, canonical + hreflang and share cards; JSON-LD for the site (Organization, WebSite), the FAQ, the activity-book list and each activity book (AggregateOffer from the active variants). The sitemap lists the pages and the products on sale; `/free-cover` is noindex and not listed.
- **Tests:** `tests/e2e/test_public_site.py` (anonymous visitor, no fixtures): every public page fits 390 px and says nothing is coming; the menu and footer; the home's offers; the hub's three orderable books; the pricing sections; the English structure.

## One tap adds any product to the cart (2026-10-02)

- **Tareq: "I choose a book and it is not added to the cart."** «أضيفوا للسلة» on every story page and every activity-book page now adds the chosen variant at once (`POST /api/store/cart/items`), for guests too, and opens `/cart`. A story line carries its theme and the chosen format, and the style only when the parent tapped one; the family book carries the optional family details, now asked on its page. The create flow stays on story pages as «جرّبوا المعاينة أولًا».
- **The line then waits for the child** (`needs_details`: no child, or a story without its book). The cart says «ينقصه: بيانات الطفل وصورته» and «أكملوا بيانات الطفل» opens the create flow with `item=<line>`; at its end the flow fills that line (`item_id` on `POST /api/create/books/{id}/cart` and `POST /api/shop/workbooks/cart`, checked against the caller's cart and the line's product) instead of adding a new one. An approved character is reused unless the line asks for another style.
- **Checkout refuses a waiting line** (`details_missing`, with the lines in `details.items`), so workers and print batches never get an order item without a child or a book. Coloring books have no page or production yet and stay unsellable.
- **Carts and signing in:** a signed-out request never reads a cart that belongs to a parent (the cookie alone is not enough), and the first cart request after signing in moves the guest cart's lines into the parent's cart (no dedupe, listed in the order they were added) and closes the guest cart.

## Consistency locks: style bible, fixed sheets, cover plate (Addendum 11 §2.1–2.2, §4) (2026-10-02)

- **Scene group = the scene's `outfit` key.** The cover's group is the main one: its pages take the cover as their outfit reference. Every other group (graduation's school flashback, the evening pyjamas) gets its locked text and, once drawn, the group's first accepted page as its outfit reference; `generate_pages` draws those anchor pages right after the cover. `page_image.v4` no longer says "match the cover's clothing" on pages of another group (v3 stays for old books).
- **One head covering per book.** The hijab comes from the cover group's chosen option (`hijab_en`) and is the same on every page; other options' `hijab_en` are not read (removed from the three MVP themes). The bible (`book.generation["bible"]`: groups → outfit, hijab, hair, companion design, cast, cover plate) is written on the first run and reused unchanged on resume and redraw. The seed picks the same options as before, so an older book keeps its clothes.
- **Fixed sheets are content files, never per child:** `content/themes/<slug>/cast/<id>-<style>.png`, else the shared `content/cast/<id>-<style>.png` (Tareq's C-images: `C1-qamour-3d.png` → `content/cast/qamour-3d.png`, `C3-teacher-3d.png` → `teacher-3d.png`, `C5-classmates-3d.png` → `classmates-3d.png`, `C8` → `mom`, `C10` → `dad`, `C12` → `grandma`, `C14` → `grandpa`, `C16` → `baby`; `-watercolor` / `-cartoon` likewise). A theme's own companion sheet is `themes/<slug>/cast/companion-<style>.png`. With no file, the theme companion is drawn **once** from its locked description (`companion_default_sheet.v1`) and kept in the plate store under a key of model + style + house style + design, so every book and theme with the same «قمّور» shares it. Side characters without a sheet keep their locked text only (no generation: Tareq supplies them).
- **Cast ids live in `others`** as `{teacher}`, `{classmates}`…; the same id has the same description in every theme (a test checks). Cast sheets are the first references dropped when a provider's limit is reached (fal: Nano Banana 14, FLUX.2 9; the fallback wrapper takes the smaller).
- **No look-alikes:** classmate (2)'s hijab is lavender (was white, the hero's graduation hijab), the graduation school outfit is teal and first-day's coral option is plum (a classmate wears coral). `docs/image-prompts.md` C5/C6 changed with it.
- **Cover plate:** `content/themes/<slug>/plates/<style>-<n>.png`, one picked by the seed and recorded in the bible. The child's photo goes with the cover only while it is kept (not past `delete_after`), to the image model only; QA (Anthropic) never sees it.
- **Cover model:** admin setting `cover_image_model` (empty = the page model), fal only, falling back to the page model. Nano Banana Pro (`fal-ai/nano-banana-pro[/edit]`, $0.15 at 1K/2K, 4K double, no 0.5K tier → sent as 1K) was checked on fal's pages on 2026-10-02.
- **QA v5:** new fields `cropped` (who is cut by the edge) and `hijab_ok`; outfit, hijab, companion-vs-sheet and a cropped hero are "lock misses": redrawn like hard fails but preferred over them when the best attempt is kept; someone else cropped is a soft flag (`crop_other`). A redraw prompt lists what the last review found. New page flags for the admin queue: `hijab`, `crop`, `crop_other`.
- **Text completeness:** a story page without text fails the story step and the PDF build (`text_missing`) unless the theme marks it `wordless: true`; `theme_problems` reports both directions.

## Book presentation: cover lettering, layout library, front/back matter (Addendum 11 §2, §3, §5) (2026-10-02)

- **Title lettering is code, never the image model:** an inline SVG per line on a gentle `<textPath>` arc/tilt, drawn as glow (blur, rasterized at 300 DPI) → drop shadow → dark outline → light rim → gradient fill. The outline is a ring of filled copies, not an SVG/CSS stroke: Chromium prints stroked text as Type 3 fonts, filled copies stay embedded TrueType (tested). Five treatments (`gold-magic`, `candy-bright`, `night-glow`, `nature-fresh`, `heritage-tatreez`); each theme sets `cover_title_style`. Lines: 1 up to 13 letters, 2 up to 28, else 3; never inside a word or the child's name; sizes fitted in the browser.
- **Ribbon:** «بُطُولَةُ الْبَطَلِ الرَّائِعِ / الْبَطَلَةِ الرَّائِعَةِ» + the name highlighted, under the title. Our titles already contain the name, so it appears twice; the addendum asks for the ribbon on every cover.
- **Fonts (OFL, docs/licenses.md):** Lalezar and Marhey Bold (display), Aref Ruqaa (handwritten dedication, polaroid captions), Noto Naskh SemiBold (the child's name in the story). Variable sources were cut to static instances.
- **Layouts:** eight in `packages/pdf/layouts/` (`qamra_pdf.page_layouts`). A theme page's `layout` takes a library name (kept as `design`, the geometry stays full/split/spread) or the old value (rotated). The text area the prompt keeps calm is unchanged (it comes from `layout` + `text_pos`), so prompts, `checks.AREAS` and Classic templates stay valid; every layout sets its text inside that area. Dialogue only when the text ends with a quote; big-moment only up to 9 words; vignette/ornament up to 24 words and at most twice a book.
- **Containers fit their text** and report how much they are filled; a book flags `empty_text_box` below 60 %. Story text 26 pt (ages ≤ 5, shrinks to 24) and 21 pt (6–8, to 20), line height 1.85.
- **Arabic «drop cap» is a drop word:** a single drop letter would break the joining; a one/two-letter first word («في»، «ثمّ») takes the next word with it.
- **Print quirks found:** `transform: translateX(-50%)` on an element with spilling children made Chromium shrink whole PDF pages (centering now uses auto margins); CSS masks print onto white (the vignette is a paper-colored gradient over the picture); filters on a box rasterize the picture inside it (shadows are separate layers).
- **Back cover:** the front picture mirrored (its edge meets the front at the spine) and blurred in PIL at print resolution, a tint in the theme's ink color, the portrait in the moon frame, the blurb, logo and domain. The «قريباً» QR block is gone: a QR shows only when family voice exists.
- **Spine:** `print_spine_mm` = 0 (new default) means paper caliper × sheets + board allowance (`print_paper_caliper_um` 150, `print_board_allowance_mm` 6.0: placeholders until the print partner confirms); a number keeps the old fixed width. Text and moon only from 6 mm.
- **Decor images (E1–E5)** are optional: `packages/pdf/layouts/decor/manifest.json` (file, crop, white key-out) and the folder beside it, or `design/incoming/` while testing. Without them the code-drawn SVGs are used.

## «قلبي يعرف الله»: the store, the scholar's review and the orders (Addendum 10 §3.3, §9, §10) (2026-10-03)

- **The scholar's approval is computed, never copied into a switch.** A unit is `draft` → `scholar_review` → `approved`, or `changes_requested` with the scholar's note (tables `islamic_unit_reviews`, `islamic_review_events`; migration `cf0e711e7919`). The units of a volume are the ones `content/islamic/units.yaml` lists for it plus one unit for its front and back matter (`matter-v1`…: the passport, the final assessment, the certificate carry religious wording too). A volume is approved while every one of those units is approved (`qamra_core.islamic_review`); a unit added to the content later has no approval, so its volume stops selling by itself.
- **How a volume goes on sale:** the product `islamic-series` (line `islamic`, `content/store/catalog.yaml`) is seeded like any other, active, but `load_catalog` (`store/catalog.py: scholar_gate`) drops every islamic variant whose volume(s) are not approved (a set: L1 = V1+V2, L2 = V3–V5, set = the five) and the product itself when nothing is left. So the cart, checkout, quiz, `/pricing`, the hub and the JSON-LD never see it; nothing says "soon". The admin's switches still close an approved volume (the variant's `active`) or the line (`orderable`); approval never opens what the admin closed. When the scholar sends a unit back, or staff reopen it after editing its pages (a note is required), the volume leaves the store at once and its books can't be approved for print (`scholar_not_approved` in `admin_books.approve`).
- **Only the scholar decides:** a new staff role `scholar` (permissions `islamic.view`, `islamic.scholar`). Approving, requesting changes, answering a `scholar_decision` point and the printed name need the role itself: the owner's `*` does not stand in for it. Editors get `islamic.view` + `islamic.edit` (send to the scholar, reopen, notes, render previews); admins and reviewers read. A unit can't be approved while a `scholar_decision` point its pages cite (or a dua's hadith / a ruling's basis behind them) has no answer (`islamic_scholar_decisions`: the question as asked, the answer, who, when; the content follows it everywhere the source is used). Points no page cites (e.g. `s-illustrations`) are listed as general questions.
- **The scholar's name:** `islamic_reviewers` keeps the name as printed and the consent to be named (with its date). The export's `credit_name` is set only for an approved volume whose every approving scholar agreed; otherwise «راجعه علميًّا: …» is not printed.
- **The export the engine reads (simplest robust option):** `build_export` → JSON `{version: 1, generated_at, volumes: {V1: {approved, units, approved_on, credit_name}}, units: {u-…: {volume, status, reviewer, approved_on, preview_run}}, decisions: {source: {question, decision, by, on}}}`. The worker writes it next to every render and points `QAMRA_ISLAMIC_REVIEW_FILE` at it for that render (the containers' `content/` is read-only and owned by root, so nothing is written there in production). For local renders `qamra islamic-review-export [--out …]` writes `content/islamic/review-status.json` (gitignored: the database is the record); `GET /api/admin/islamic/review/export` returns the same JSON. The engine reads `$QAMRA_ISLAMIC_REVIEW_FILE`, else that file, else treats nothing as approved.
- **Review previews:** staff ask for them per volume; the worker renders the volume for the sample child (a preview build: placeholders allowed) and stores one PNG per page under `islamic/review/<volume>/<run>/` in private storage; the admin streams them. Page n of the interior is page n of the plan (`pages_mismatch` warns otherwise). An approval records the preview run the scholar saw.
- **Orders:** confirming an order with an islamic item enqueues `islamic_book.render_order_islamic_items`: one Book per volume (a set: one per volume), drawn by `qamra_workbook.render.islamic_volume.render_volume(..., print_build=True)` with the child's approved character (no new AI cost), the PDF copy too. A volume that is not approved when the job runs is not rendered: its book stays `failed` with the units still waiting and the flag `scholar_review`, and the admin's retry (`LINE_JOBS["islamic"]`) renders it once approved.
- **Store details (placeholders until the printer's quote):** printed = perfect-bound softcover 21×28 (proposal §10: pages with the Quran must not tear out), 79 ₪ per volume, 35 ₪ PDF, sets 139/199/329 ₪, the Ramadan book at a volume's price for now; JOD at 5.2, rounded to 0.5; print cost tiers are the proposal's ⚠ estimates, so 10+ copies wait (as the family book). Add-ons reuse the sticker sheet and the gift box; the printed parent guide is new and prints the engine's parents' file (`answer_key`). The quiz gets the goal «تعليم ديني» (V1 up to 5, V3 from 6, the Ramadan book as the alternative); the site shows the goal only while a volume is on sale, and the API never recommends a volume that can't be ordered.

## Delivery: the West Bank and Jerusalem only (2026-10-05)

- **2026-10-05: delivery limited to the West Bank and Jerusalem; Jordan deactivated, not deleted** (Tareq). The zones `amman` and `jordan-other` are switched off (migration `9d4f2b7c1e60`; `active: false` in `content/store/catalog.yaml`, which the seed now reads). `load_catalog` lists only active zones, so the checkout and `/pricing` no longer offer a Jordanian city or JOD, and `PUT /api/store/cart/zone` rejects a Jordan zone (`unknown_zone`); `?country=jo` falls back to shekels while no Jordan zone is active.
- **Kept for when Jordan comes back:** every JOD price, the Jordan zones and their fees, the currency-follows-zone code, the `JO` messages and the portal's `JO` country. The country choice in the checkouts and the kindergarten signup is derived from the active zones (`deliveryCountries` in `lib/store.ts`), so it reappears automatically when the admin switches a Jordan zone on (Admin → الكتالوج والأسعار → التوصيل).
- **Copy:** the FAQ answer to «أين توصّلون؟» and the kindergarten lead form's city list no longer name Jordan or Amman. The social kit and the Meta ad targeting already named only the West Bank cities and Jerusalem. Deliberately left unchanged: the workbook's note on alignment with Palestinian and Jordanian KG expectations (about the curriculum, not delivery) and the story prompts' audience line (not shown to customers).

## Staff review every story's text before «تأكيد» (2026-10-06)

- **2026-10-06: one gate, the existing approval** (Tareq: «لازم يبقى معي صلاحيات اني اعمل لها مراجعة او تعديل للنص المكتوب فيها قبل ما اعمل تاكيد لها»). The admin queue's «اعتماد» became «تأكيد النص واعتماد الكتاب»: it is the review of the words and the release, not a second flow. Plan and findings: `docs/plans/admin-story-text-review.md`.
- **What the confirmation now holds back:** print (as before: print batches take `approved` books only), and also the parent's reader, share links and the "book ready" email. `in_review` is no longer "final" in `routers/reader.py`; the email is sent by the API at «تأكيد» (story lines Magic/Classic; class copies and samples never got it). The parent can't edit page text once the final files are being made or wait in review (`text_locked`), so the words staff confirmed are the words the family reads.
- **Story books only:** Magic (with custom stories), Classic and class copies. The activity books (family, journey, «قلبي يعرف الله») have no generated story text and keep their own gates (the scholar's review for the Islamic series).
- **Edits save at once, the files follow once:** before, every saved page set the book to `generating` and re-rendered the PDFs (minutes), so a second edit had to wait. Now a save only writes the text and flags the book `text_changed`; «إعادة إخراج الملفات» renders once; `approve` refuses with `text_not_rendered` while the flag is on; the worker's render clears it. Editing a confirmed book puts it back to `in_review`.
- **History outside `audit_logs`:** old/new text holds the child's name, and `audit_logs` keeps ids only (it survives «احذف كل بيانات طفلي»). The words go to `book_text_edits` (migration `e5dd2afbd62c`, ON DELETE CASCADE with the book); `audit_logs` gets `admin.page_text_edited` / `admin.story_text_edited` / `admin.book_rerender` / `admin.book_approved` (with `text_edits`) without text.
- **Safety check on staff edits = the instant screen, not the AI review:** the same screen as the custom-story brief (`screen_text`: links, phone numbers, the unsafe-word list). A hit returns `text_unsafe`; staff may keep the words with a note (stored with the edit). The paid Haiku review is not re-run on staff edits: staff are the human gate CLAUDE.md §3.3 asks for, and Classic's AI review of the parent's words still runs on the final render.
- **«استرجاع النص المولَّد»:** pages go back to `BookPage.original_text` (the generated words, before the parent's or staff's edits; the parent's wording stays in the history's "before"). Story fields keep their first value in `generation.text_originals` at the first edit.
- **Not built:** per-page AI text regeneration (the pipeline writes the whole story in one call; there is no per-page text step to call), and editing a class copy's words (they are the class's shared pages, rewritten from the class template on every render: shown read-only).
- **Optional staff alert:** setting `review_alert_email` (البريد والواتساب; empty = off). When a story's final files are ready the worker emails it once per book (`text_review_waiting`), instead of emailing the parent.

## «قلبي يعرف الله»: the owner's review replaces the scholar gate for this release (2026-10-07)

- **Decision (owner, 2026-10-07):** the six volumes (V1–V5 and R) go on sale on the owner's own page-by-page review on the review site (2026-10-03..07, 639 pages; the V1 notes were applied in ef3548f), without waiting for a scholar's sign-off.
- **How:** migration `0c695b89fde0` marks every review unit of the six volumes (49 units) `approved` with the note «owner decision 2026-10-07» in each unit's history (`islamic_review_events`). No reviewer is named: `reviewer_name` stays empty, so the review export gives no name and no book prints a «راجعه علميًّا» line. Downgrade puts the units back to `draft`.
- **Nothing public says who reviewed the books.** The sentence «كل مجلد يراجعه مشرف علمي قبل طباعته» / "A scholar reviews every volume before it is printed" is removed from the product description (catalog, live row, site text), and nothing replaces it.
- **The scholar workflow stays in the code** (roles, review page, `scholar_decision` points, the consent-based credit line) for later use. The 31 open `scholar_decision` points are not answered; the store gate does not read them.
- **The sources too (owner, 2026-10-07, explicitly):** all 193 sources in `content/islamic/sources*.yaml` (Quran, hadith, adhkar, sira, rulings) are `owner_approved` — a new status between `text_verified` and `scholar_approved` — with `reviewed_on: 2026-10-07`, `approval_note: "owner decision 2026-10-07"` and, for hadith and dua, the `approved_sha256` of the wording the owner saw (a later fetch that changes it fails loudly). No `reviewed_by`: nobody is named. The print gate (`APPROVED` in `islamic_sources.py`) accepts `owner_approved` or `scholar_approved`; `Source.decided` stays scholar-only, so the `scholar_decision` points stay open. All six volumes pass `islamic_volume --check --print` and print with preflight passing.
- **Character cut-outs are wide enough for print:** `character.pose` now also scales a narrow figure to 66 mm at 300 DPI (the «هَذَا أَنَا» portrait frame crops by width; it printed at 264 DPI after the shadow-free cut-out made figures narrower).
- **Audio QR codes are off for this release (2026-10-07).** No reciter's or human recording exists yet, so the 29 QR codes of the surah and dhikr pages are hidden (`AUDIO_QR = False` in `qamra_workbook/render/islamic_content.py`). The pages print with no QR, no «listen» label and no empty box, and the «how to use» and parent-page lines that mentioned the sound code are gone. Set the flag back to True once every code plays a real recording. Quran recitation is never text-to-speech.
- **«الاستعاذة عند الغضب» (`d-anger-refuge`)** is now cut from Sahih Muslim 2610 (`h-muslim-2610`), whose wording includes «الرَّجِيمِ». The Bukhari 3282 text in the dataset ends at «الشَّيْطَانِ». The `expect` keywords of Bukhari 3282, 3149, 4770 and 6245 now name words that are in those hadiths, so all four pass the reference check. The title of 4770 now quotes its real wording («ما جرّبنا عليك إلا صدقًا»).

## Digital delivery: the parent downloads the PDF they bought (2026-10-08)

- **The gap:** the store sold files (`classic-digital` 19 ₪, the activity books' «ملف PDF» 29–75 ₪) and nothing gave them to the parent. Plan and contract: `docs/plans/digital-delivery.md`.
- **What a line gives:** a digital line gets the whole book with its cover (each volume of a set) and the extra files its job renders (answer keys; the family book's sticker and card sheets, since a digital buyer gets no printed insert). A printed «رحلتي الأولى» stage gets only its answer key, free (Addendum 6 §5). Every other printed line gets nothing: the free «نسخة رقمية مع المطبوع» stays the web reader (owner's audit, 2026-10-07).
- **When:** a story once staff confirmed its words (approved/ordered/printed; never `in_review`); an activity book once its render passed (`in_review`, every preflight passed, no reviewer flag) or an admin approved it, so a file doesn't wait for the print approval; the order confirmed and not cancelled; a set's line is "ready" when every volume is, each volume downloadable as soon as it is.
- **Who:** the child's guardian, on their own order or a guest order; anyone else gets 403 `download_not_yours` (the task asked for 403, unlike the reader's 404). Every download is in `audit_logs` (`download.file`) with ids only.
- **The home copy:** the print files have a 3 mm bleed and exact TrimBox but no crop marks, so the worker cuts each page to its TrimBox with pypdf (`qamra_pdf.home`); no renderer change, no re-render, under a second for 120 pages. A story's cover wrap is split into front and back panels (front on the left for Arabic). The book keeps its own size; the page says to print on A4 with «ملاءمة للصفحة». Cached at `children/{child}/books/{book}/home/{kind}/{ETag hash}.pdf`, so a re-render makes a new copy and «حذف كل بيانات طفلي» removes it with the child's prefix. No new column: the version is derived from the print files' ETags, the "being made / failed" state lives in Redis.
- **Streamed, not a signed URL:** the file streams through the API in 1 MB chunks (`ObjectStorage.stream`), so the bucket stays private and it works with the local SeaweedFS too.
- **Email:** a 5-minute cron (`scan_ready_lines`) finds digital lines that became ready, makes their copies and sends one `download_ready` email per line, linking to `/account#downloads`, never to the file.
