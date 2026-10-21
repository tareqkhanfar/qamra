# Decisions log

Newest first. Each entry: date — decision — why.

## 2026-10-16 — Prices hidden from customers, kept for staff (admin switch `show_prices`)

Owner (2026-10-16): «بدي توقف الاسعار لو سمحت من الموقع … وتخلي الاسعار داخلية للادارة فقط ع النظام، ما بدي الزباين يعرفوا الاسعار.»

- **One switch, off by default:** «إظهار الأسعار للزبائن» (`show_prices`, admin → Settings → الأسعار, public). Turning it on brings every price back without a deploy; nothing about the prices themselves changes. Orders still record their prices from the price list.
- **Enforced on the server, once:** every `/api/…` response except `/api/admin/…` (and the test-only `/api/e2e/…`) is customer-facing. While the switch is off, `qamra_api/price_visibility.py` strips the price fields from their JSON at any depth (`price*`, `*discount*`, `currency`, `subtotal`, `*_ils/_jod/_usd`, …; `total`, `amount`, `fee`, `shipping`, `base`, `percent`, `balance` only when they hold a decimal, so counts like a voice invite's `total: 3` stay). It fails closed: an early error on a customer path is stripped too. New endpoints are covered without code.
- **The catalog leaves out what has no price** (not sold in the currency) while prices are hidden, so the site's «on sale = listed» logic keeps working without the numbers.
- **Catalog wording that gives the price away** («نفس الكتاب بنص السعر تقريبًا», «نسخة رقمية مجانية مع المطبوع», the «توفير» badge, «بأسعار الروضات») is replaced in customer responses by `content/store/no_price_wording.yaml`, by slug. Staff screens and orders keep the admin's own words.
- **Not JSON:** the school's invoice PDF answers 404 to the school (staff print it from the admin); the order emails and the prepared WhatsApp messages say «الدفع نقدًا عند الاستلام» instead of the amount; the packing slip has no prices (it goes in the box).
- **The site:** no price, total, discount, «من X», price comparison or add-on amount anywhere a customer looks; no discount-code field; the prices page is out of the menu, the footer and the sitemap, and /pricing leads to the shop. Lines that spoke of a quote or class prices have a `…NoPrice` wording («تواصلوا معنا»). Checkout and the school's order say «نتواصل معكم لتأكيد التفاصيل». Server components read the switch per request (`getPricesShown`), client components through `useShowPrices()`; unknown settings count as off.
- **Kept on purpose:** «معاينة مجانية», «إعادة طباعة مجانية إذا الخطأ منّا», the free redraws and «غلاف مجاني» are promises about the service, not prices. Say the word if they should go too.
- **Tests:** the API suite runs with the switch on (its tests check prices); `test_price_visibility.py` covers it off and on. The E2E suite turns prices on for its run (`/api/e2e/settings/show-prices`), and `tests/e2e/test_prices_hidden.py` walks the public pages and an order from the format step to the order page with them hidden.

## 2026-10-10 — Every drawing kept and choosable; the parent's own words in «ما الذي لا يشبهه؟»

Owner (2026-10-10): «اذا بدي ارسم كمان مرة القديمة ما تنحذف خليك معرضها … عشان المقارنات بين الصور ونمط الرسم» and «بدي تضيف كمان حقل اسمح انه اقدر ادخل كتابة كمان».

- **The child's character is the drawing approved last.** Approving sets `approved_at` to now every time, also for a drawing approved before, so going back to an earlier drawing makes it the one every later book reuses (stories, activity books, the class book: all already pick `approved_at desc`). Older approved drawings stay approved: books and orders may point at them. The web's local fallbacks pick the same way (`lib/drawings.ts` `lastApproved`), and the API sends `approved_at` with each character.
- **The character step offers only drawings in a style this book can use** (the style step's list: the line's styles; Classic, the styles with a live template for the child's look). Approving one in another style moves the flow to that style (`?style=`), so the book is drawn in it.
- **A redraw is always a new drawing** (`redraw: true`, sent by the redraw button). Before, a redraw without chips could return the approved drawing in the same style.
- **The note never goes into an image prompt as written.** Claude (the fast model, `character_feedback` v1) keeps only what is about how the child looks and rewrites it as a short English instruction for `character_sheet` v4. The hijab, glasses and gender stay the family's settings. The instant local screen of the custom-story brief runs first (links, phone numbers, plainly unsafe words), so personal data never reaches the text provider. An unsafe or off-topic note, or a failed text step, is ignored without an error: the redraw uses the chips. Only the outcome is logged, never the note. 200 characters, counted after squashing spaces.
- **Drawings never approved are abandoned drafts:** after `draft_retention_days` (30) the cleanup deletes the picture and marks the row `discarded`. It still counts as one of the 3 free redraws. The parent's note goes with it, and from failed drawings too. Approved drawings stay until «احذفوا كل بيانات طفلي».

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
- **The consent text is versioned in the web messages** (`create.consent.version`, now `parent-2026-10`). The API accepts only the current version, so a page showing an old text gets a "reload" answer instead of recording the wrong consent.
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

## The journey's and the Islamic series' sticker sheets are included, made from the pages (2026-10-08)

- **Included, not an add-on:** the pages ask for the stickers, so every journey stage and every Islamic volume comes with its sheet (one A4 sticker sheet each). The `sticker-sheet` add-on stays hidden: it would be a second copy. The Islamic proposal's question «الجواز يعمل بالتلوين بلا ملصقات، وورقة الملصقات إضافة مدفوعة؟» is answered by this.
- **Derived, not listed:** what goes on a sheet is read from the pages being printed (`pages/reward_stickers.py`: `journey_needs`, `islamic_needs`), so a page added to a stage or a unit added to a volume changes its sheet. Rules: a sticker per journey-map page (the hero) and per opener circle; each picture of a train that asks to stick (the child still chooses); `ceil(slots / shapes) + 2` of each pattern shape; a unit stamp per circle of each passport page (V1–V5 have two: the front passport and the end card; each set is sized to its own ring); 7 stars (or leaves) for each unit whose closing or parent page asks the child to stick one on a board at home (a week).
- **A4 for both lines** (the printer's standard sticker paper, even for the 21 × 28 Islamic volumes), with a 9 mm safe margin instead of the books' 12 (a kiss-cut sheet needs less; V1's 43 stickers fit).
- **No sacred words on the Islamic sheet** (content guide: pages cut or thrown away carry none): not the name of Allah, ﷺ, a prophet, the Quran, a surah or a verse, so the footer names the volume, never the series «قلبي يعرف الله»; checked on every build (`sacred_words`). The child's own name is theirs and prints as given («عبد الله»).
- **Digital copies:** the sheet is the `stickers` extra of the digital download (cut to A4, the magenta cut lines show as a guide), not a page appended to the book's PDF: the print file stays one file for the printer and the parent can print it on sticker paper.


## The words the site uses for the same things (language pass, 2026-10-08)

A strict review of every customer-facing string added during the order-flow work (chunk 13 of `docs/plans/order-flows.md`) fixed the texts to these house terms. New text follows them.
- **Ages:** «سنوات» («KG1 · 4–5 سنوات», «3 سنوات أو أقل»), never «سنين»; one age with the ICU plural `one {سنة واحدة} two {سنتان} few {# سنوات} many {# سنة} other {# سنة}`.
- **Download / loading:** «تنزيل، نزّلوا» for a file the parent saves; «تحميل» only for loading («جارٍ التحميل…»).
- **The passports:** «قلبي يعرف الله» has «الجواز» / «جواز المسلم الصغير» (English "Young Muslim's passport"), never «جواز السفر»; «مغامراتي مع عائلتي» keeps its «جواز السفر».
- **The drawn companion of a story book:** described as «رفيق من رسمته/رسمتها» (English "companion"). The add-on's name «صاحبي من رسمتي» and the printed page «وهكذا وُلد صاحبي» stay.
- **«دوسية»** names only «دوسية التأسيس»; the four books together are «كتب الأنشطة» (English "activity books").
- **Parents** are addressed in the plural (اختاروا، طفلكم); the child step's words for a child of unknown gender use the generic masculine «طفلكم … اسمه».
- **English apostrophes:** the straight `'` in `messages/en.json`, as in the rest of the site.
- **Left for the owner:** the colloquial lines that came with the Addendum 9 design (e.g. «بدكم تزيدوا الفرحة؟», «بالخطوة الجاية», «تشوفوا المعاينة», the quiz's «قديش» and «شو», the add-on descriptions «سطرين منكم بأول الكتاب», «نفس الكتاب بنص السعر تقريبًا») are kept as they are: whether the whole site speaks MSA is Tareq's call. Older strings outside this pass that still say «صاحبه» for the companion (the companion step, the home headline, the landing page) or «دوسيات» as a category (the meta description, the landing lead, the footer) are listed in the chunk 13 report.

## Story covers redesigned: poster lettering, a back cover that sells, a spine in the art's color (2026-10-09)

Tareq: the covers did not look professional enough («وحتى بالحكايات بدنا التزبيط يكون»). Scope: the story books' front, back and spine (Classic, Magic, custom stories, class books); the activity books' covers are separate work. Same contract: `render_book` / `render_class_book` and their files are unchanged, every new field has a default.
- **The design is decided in Python, laid out in the template.** `qamra_pdf.cover` builds a `CoverDesign` from the book and its art; `_cover_parts.html.j2` only lays it out. Story and class books share it (`story_design`, `class_design`); the old plain class-cover template (`_cover.css.j2`) is replaced by the shared one.
- **Reading the art (`read_art`):** from a 48 px copy, the deep tone (the most common hue of the darkest quarter, at 17 % lightness: a mean drifted from a navy sky and brown wood to purple), a pale tint and a vivid accent; light or dark art; and where the scene begins (detail sustained over 10 mm, looked for below 36 mm, so a moon or lanterns at the very top may sit behind the title). Saturated blues and greens are pulled back (print-safe), nothing is pure black.
- **Title block:** from 7 mm under the trim, 44–62 mm tall (+6 mm on two lines), reaching at most 10 mm into the scene, then the ribbon tucked under it. A soft elliptical wash of the art's own deep (dark art) or pale (light art) tone sits behind it, stronger over busy art; the old fixed dark band is gone. The glow is full on dark art, a third on light art (a white halo muddies a light sky). The cover prompt keeps the top 30 % calm, so on new art the block never meets the hero's head.
- **Poster lettering:** a title up to 19 characters stays on one line with the child's name in the treatment's name gradient and 14 % larger («يوم تخرّج **ليان**»); a longer one gives the name its own leading line (up to 0.62 of the box, the rest at 0.38): «آدم» / «في أوّل يوم بالروضة». The name colors are a second gradient applied through a CSS variable inside the `<use>` copies (`.nm{fill:var(--nf)}`), so the outline, extrusion and glow copies keep their own colors. The letters are extruded (a 1.3 mm side in a darker hue, the outline wrapping face and side) and the sharp glow ring is dropped (its scallops showed in print); all text stays embedded TrueType.
- **Display text:** the cover lettering, the back title and the spine use light tashkeel: the short vowels, tanween, sukun and the dagger alif go, the shadda stays («تخرّج», «أوّل»), except the article's own («الذي») and a sun letter's after «ال»/«لل» («بالروضة», «للشمس», «الله»). The story text inside the book keeps every mark. Names on the cover are printed plain (a vowelized «آدَمُ» after «بِـ» would print a wrong case ending).
- **Series pill** (front, outer bottom corner, inside the safe area): moon mark, brand, product line: «قمرة | سحري», «… | كلاسيك», «… | حكاية خاصّة» (a custom story), «… | كتاب الصفّ». «سحري» is a label after the separator, never «قمرة سحري» in running text on the cover. The worker passes the line from `book.generation` (`cover_series`); an old book with no line shows the brand alone.
- **Back cover:** the art mirrored and blurred under a gradient of its deep tone (dark art, cream type) or pale tone (light art, the theme's accent for the title and the name), the title, the story's own blurb, three single-page pictures spread through the story (never half a panorama, each picture once), fact chips, «نُسْخَةٌ خاصَّةٌ بِـ{name}», the child waving and the companion, the logo and the domain. The QR card appears only with family voice.
- **Facts only:** the theme's `age_range` («لِلأَعْمارِ ٣–٧», carried on `BookPlan`/`BookSpec`), the interior page count with the number's agreement (`strings.page_count`), and «الحِكايَةُ مُشَكَّلَةٌ بِالكامِل» only when every story page has at least one short-vowel mark per two letters (one page a parent retyped without marks drops it). No chip is printed for anything not measured from the book.
- **The child on the back:** the middle (three-quarter, waving) view of the approved character sheet, cut out (`assets.hero_view`), sized so it never prints under 300 DPI (≈ 60 mm from a 1264 × 848 sheet) and stored at most 1100 px tall, in front of a soft moon disc so a cream outfit never melts into a light back. When the picture is not a clean three-view sheet (the Classic identity portrait is a head-and-shoulders), the back shows the round portrait in the moon frame. Class books cut out the child's front-view portrait.
- **Barcode:** no ISBNs yet, so the area is reserved (an empty 38 × 22 mm `data-reserved="barcode"` box on the spine side, 14 mm from the fold) and nothing is printed in it.
- **Spine:** the art's deep tone with darker edges; when it is at least 6 mm wide, the title with the name in gold (or «{title} · {name}» when the title lacks the name), and the brand with the moon at the tail. Text still runs top to bottom, as before.
- **Class books:** the same cover: «{name} {cover_subtitle}» as a poster title, the gendered ribbon (the worker now passes the child's gender; unknown → the school's name), «كتاب الصفّ» on the pill, the school, year (Arabic-Indic digits in Arabic books) and logo on the back, the theme's lettering and ages (`_theme_cover`).
- **Fonts:** no new font. Lalezar, Marhey and Aref Ruqaa (titles), Baloo Bhaijaan 2 (ribbon, pill), IBM Plex Sans Arabic (chips, domain), Noto Naskh Arabic (blurb): all SIL OFL, already in `packages/pdf/src/qamra_pdf/fonts` and `docs/licenses.md`.
- **Language review** (separate reviewer, 2026-10-09): all new strings checked; applied: light tashkeel fixed for «الله», «لل…» and «الذي» and the dagger alif dropped, the vowelized claim per page and scoped to the story, «حكاية خاصّة»/«كتاب الصفّ» with their shadda, the school year in Arabic-Indic digits, «·» on the spine; the unused English "vowelized" string removed.

## Activity-book covers: scenes, lettering, a back that shows the book, a wrap for the Islamic volumes (2026-10-09)

Tareq asked for covers that look professional and show what each part holds, with the child on both sides, after a reference he liked (a preschool workbook series with kids among giant letters, a cloud title panel and badges): "something different and nicer". Scope: «دوسية التأسيس», «رحلتي الأولى للتعلّم», «مغامراتي مع عائلتي», «قلبي يعرف الله». The story covers are separate work.
- **One system, four identities.** `qamra_workbook.render.covers` builds every cover from a `Front`/`Back` description; `_cover.html.j2` lays it out in mm inside a panel box (a page, or a panel of a wrap). Each series keeps its colors and gets its own title panel: a spiral-notebook page (دوسية), a trail sign with a dashed path (رحلتي), a house (العائلة), a pointed arch in cream and gold (قلبي يعرف الله).
- **Scenes are drawn once per part, never per child.** No people and no text in them: the child is composited, and every letter, number and word is set in code (an image model cannot be trusted with Arabic letters). The house style is stylized 3D, so the scenes sit well behind the 3D characters; the Islamic scenes follow the series' rule (no depiction of God, a prophet, an angel or a Companion; no Quran writing; prophets' stories shown through places and nature). Generated scenes live in `content/covers/scenes/<part>.jpg`; without one, the part shows its 2D plate from 2026-10-03. The scene is graded slightly (saturation ×1.12, contrast ×1.04) for matte card.
- **The part's real letters and numbers as toy blocks**, drawn in SVG beside the child: the reference's giant letters, but always correct glyphs in the book's numerals (١٢٣ or 123).
- **Lettering:** Baloo Bhaijaan 2 ExtraBold (already licensed, SIL OFL); one gradient per word (the child's name in its own color on the family title), a white keyline, a dark outline and a 1.6 mm extrusion, all as filled copies of vector text (an SVG stroke prints as a Type 3 font). Fitted in the browser (`COVER_FIT_JS`): wide as the panel allows, two lines within 1.25× of each other, more line height when the title is vowelized. Titles break between words and never inside the child's name; a second line prefers to start with «و».
- **What is vowelized:** the Islamic covers fully (child-facing, the series' convention), the volume subtitles and the family title as the books print them; product names («دوسية التأسيس», «رحلتي الأولى للتعلّم»), pills and parent-facing lines are plain. «الله» is written as units.yaml writes it (no shadda), so the back never shows both forms. The Islamic badge says «صُنِعَ لِـ{child}», not «باسم {child}», which would echo the basmala.
- **Facts only.** Badges and «يأتي مع الكتاب» name what the part holds (checked against the plans and renderers: the owner page and name tracing in every «دوسية» volume, the certificate only in V3, the journey map, stickers and QR, the family's sticker sheet, card stock, passport and certificate, the Islamic passport, sticker sheet, «للأهل» pages and certificate). Counts agree with the number (`covers.counted`, `pages_phrase`). No sticker counts are printed (they can change with the pages), no barcode box (no ISBNs, Addendum 11), nothing about audio on the Islamic covers, and the Islamic back no longer prints the scholar's credit (it stays on the title page and certificate).
- **Three real pages on the back**, rendered from the interior PDF the same job just made (`covers.with_thumbs`, by page type per series: a letter page, a counting page, a puzzle; the journey map; the family passport and a recipe). They print at 44 mm and are rendered 1.25× larger, because the preflight measures a tilted image by its upright bounding box. Islamic backs show only page types that may never carry sacred text (`islamic_volume.no_sacred_text`, plan.yaml `sacred: false`), so no verse is ever printed as a decoration.
- **Perfect binding:** the Islamic volumes print as one wrap [front | spine | back] (front on the left: the book opens from the right), like the story books, and `cover.pdf` is that one page. Spine = ceil(pages / 2) × 0.12 mm + 0.6 mm (placeholders until the print partner confirms its paper: `SOFTCOVER_LEAF_MM`, `SOFTCOVER_COVER_MM`); text only from 6 mm, then the moon alone; front and back text keeps 7 mm from the fold. The home-print download, the scholar's preview PNG and the web export already read a wrap (the export now crops its front panel).
- **A cover never stops an order.** Names shrink on the ribbon and the badges (`data-fit`), and a badge row that still overflows drops its middle badge; a back that overflows hides its optional pieces in a fixed order (the blurb's later lines, the three pages, the series list, the care note) before the build reports a problem.
- **An organization's copies** (the family book, A7 §8) carry its logo on a white card in the back's scene band, under the Qamra pill, so the logo never takes room from the parents' text.
- **Removed:** the old cover templates' CSS (`.wc-*`, `.jc-*`, `.icv-*`, `.cb-*`) and `islamic_frame.cover_art`.

## Honorifics in display titles, small titles, long names (2026-10-09)

- **Honorific signs are never lettered.** In a decorated title (sticker lettering, poster lettering, a back title with a shadow) an honorific sign is its own run in Noto Naskh Arabic Bold at 58 % of the title's size, raised 0.3 em, one solid colour, with no outline, rim, extrusion or glow: a Naskh ligature honours the sign and stays legible, and a display font either lacks it (Baloo Bhaijaan) or turns it into a blob under the outline. The signs: U+FDFA ﷺ, U+FDFB ﷻ, U+FDFE, U+FDFF, U+FDCF and U+FD40–U+FD4F (all in Noto Naskh Arabic). Spelled-out «عليه السلام» stays ordinary words. Colour: the series' outline colour on the activity covers' light panels; on story covers the face's light colour on dark art and the outline colour on light art.
- **The sticker effect scales with the letters.** Full (1.5 mm keyline, 0.75 mm outline, 1.6 mm extrusion) from an 18 mm font size up, which every front reaches, so the fronts are unchanged; in proportion below; under 10 mm the extrusion is 35 % of that and the soft shadow lighter. The layout reserves only the room the thinner effect needs.
- **A name is one word for the word limits.** The limits keep the book's own sentences short; the parent's typed words fill a slot (`{child}`, `{name_en}`, `{adult}`, `{member}`, `{family_name}`, `{city}`) and count once, so no name can push a page over its limit.
- **A long name shows as many whole parts as fit**, the rule the «اسمي» page already follows: the full name wherever it fits (at the box's smallest size), else the name with its last parts dropped, never cutting «عبد الرحمن», «أبو بكر», «نور الهدى». Only boxes and pages that hold the child's name do this; any other overflow still refuses the print. The game tables («ليلة الألعاب العائلية») show the name the family calls the child by (whole parts up to 12 letters, at least the first part).
- **No API limit changed:** the child's name stays up to 40 characters, family names and cities up to 30, members up to 20.

## A name's case: «يا أبا بكر» (2026-10-09)

- **The rule** (`qamra_pdf.arabic_names`, mirrored in `apps/web/src/lib/arabicName.ts`): a name whose first word is «أبو», «ابو» or «ذو» followed by another word takes «أبا», «ابا», «ذا» after «يا» and in an accusative slot; the parent's hamza and تشكيل are kept («أَبُو بَكْر» → «أَبَا بَكْر»). Every other name, and every other slot, prints as typed.
- **Templates mark the accusative, not the vocative.** «يا {child}» needs no mark (the helper sees «يا» as a word of its own, so «هَيّا {child}» is not a vocative); an object or a call without «يا» is `{child:acc}`, `{adult:acc}`, `{member:acc}`, `{name:acc}` (story themes). The web messages use `{nameAcc}` / `{labelAcc}`, which every call site passes.
- **Not changed, on purpose:** «أبوبكر» typed as one word (a name is never split or respelled); a name that does not start with «أبو» («محمد أبو بكر»: the first name takes the case, the rest is a surname); the family's name (`{family_name}`, «عائلة أبو غوش»: a surname, never inflected); genitive slots («لِـ{child}», «كِتابُ {child}», «مَعَ {adult}») printed the name as typed at first; they take «أبي» since the follow-up below (`{child:gen}`).
- **Classic texts keep their cache.** A theme text's `:acc` marks are removed before the text is vowelized and hashed, so marking a slot never invalidates a vowelized template or calls the model; the book's fill puts the marks back by slot order.
- **AI text:** the story prompts state the five-nouns rule (nominative «أبو», accusative and vocative «أبا», genitive «أبي»); after the model writes, «يا أبو …» on the child's own name is fixed deterministically. Other cases in AI text are the model's.


## A name's case: the genitive and the greetings (2026-10-09)

- **The genitive is marked, like the accusative:** `{child:gen}` / `{name:gen}` / `{adult:gen}` / `{member:gen}` / `{companion:gen}` after a preposition, as the second term of an iḍāfa, and for a name coordinated with or in apposition to a genitive one; the web uses `{nameGen}` (and `{childGen}`, `{labelGen}`). A greeting that calls a person by name without «يا» («مرحبًا …», «صباح الخير، …», «أهلًا …») is a vocative: `{name:acc}` / `{nameAcc}` / `{{ name | acc }}`.
- **«لـ» joins a genitive name in the template** (`{x:gen}` right after «لـ»/«لِـ»): before an alif it drops the «ـ» so the لا ligature forms («لِأبي بكر», «لِأحمد»), before «ال» it is written «لل» («لِلمعتصم», as `covers.fill` already did), before any other letter it keeps the «ـ» («لِـسلمى»). The web, whose messages cannot change their own letters, writes «ل{nameLam}» (`lamName`). «بـ» keeps its «ـ» (no ligature: «بِـأبي أحمد»). A «لِـ » followed by a space (the journey owner page) is left as it is.
- **Left as typed:** a title or label that stands alone (the Islamic cover ribbon, «اسْمي {child}», «الصَّحَفِيُّ: {child}», bingo owners, card sheets whose label is a definite noun such as «أَسْئِلَةُ العائِلَةِ»), the class book's «{names}» lists after a colon (filled raw; a list after «:» reads as its own phrase), and the family's name. With no family name the family book uses «عائلة» + the child's name in the genitive.
- **AI text:** only a preposition that cannot be a verb or open a clause is fixed after the model writes («مع، إلى، عن، مِنْ (with its kasra; a bare «من» may be «مَنْ»)، في، عند، على، لدى، نحو، أمام، خلف، وراء، فوق، تحت، بجانب، بقرب» and «لـ/بـ/كـ» written onto the name); «قبل، بعد، مثل، حول، بين، دون، عبر، قرب، حتى» and the iḍāfa are the model's (the prompts ask for them), so a fix never turns a correct subject into a wrong genitive.
- **A tashkeel fix keeps the vowelization cache** (`vowelize.CORRECTIONS`, `corrected_cache`, run by `qamra seed-themes`): the fix is made in the theme file, the stored theme and versions, and every Classic template's pinned definition and cached vowelized words, whose key is recomputed from the corrected words, and only when the corrected words still pass the words check. No paid call; a stale cache stays stale. Books already generated keep their text (they may be printed already).
- **The article is told from the name, not guessed from the letters alone:** a name whose first word is «ال» + two letters or more has the article (hamzat al-wasl: «لِلمعتصم», «هَمَسَتِ الجود»), except a short list of common names typed without their hamza (`NOT_ARTICLE`: «الين، الاء، الهام، الياس، الما، اليسا، اليسار، الينا، اليانا، الان، الينور، اليان»), which keep their letters after «لـ» («لِالين») and the sukun before them. A new such name joins the list when we meet it.
- **The helping vowel is made where the name is filled**, since the template cannot know the name: kasra, «مِنَ» before the article, «ـهُمُ/ـكُمُ/ـتُمُ», and a long vowel just drops its sukun. Templates keep their sukun (right for every other name). AI text is the model's.
- **One-word names get a hint, not a change:** «أبوبكر», «عبدالله», «عبدالرحمن», «ذوالفقار» → the create form suggests the two-word spelling with a button; the parent decides.
## A simple pricing page and the owner's contact numbers (2026-10-09)

- **One card per book, a few rows each.** A row is a part (none, one volume or stage, a set, a named bundle) in a format at its lowest price; the levels of «دوسية التأسيس» cost the same, so they are one row. If prices inside a row ever differ, the row says «من …». The rows come from the catalog, so a new variant or price shows up by itself; only the words for a part are in the messages (`pricingPage.unit.<line>.<part>`).
- **«ابتداءً من» on each card** is the lowest price of the book, the PDF included (that is what a parent can pay).
- **Delivery, cash on delivery and add-ons once, at the end.** The add-ons stay on the page only folded (`<details>`), with their names and prices and no notes.
- **One phone number for calls (+970) and one for WhatsApp (+972)**, both the owner's, as he asked. They live in the admin settings (`support_phone`, `support_whatsapp`, `sales_whatsapp`), so they change without a deploy; the migration sets them over whatever was saved. The copyright year is Latin digits like every number on the site.
- **Full-screen flows keep no footer** (create, cart, checkout, quiz): they have their own bottom bars; their order and tracking pages show the numbers instead.


## «شبه حقيقي» and the activity books' style step (2026-10-09)

Tareq asked for a new art style, «شبه حقيقي», for the activity books and the stories, and for the activity books
to ask the style again, with real examples. This reverses "no style question for activity books, a new one is
drawn in 3D" (2026-10-07). The full record is `docs/plans/order-flows.md`, «Owner's decisions of 2026-10-09».

- **The retired `semi-realistic` row comes back** (guide v2, migration `a58eeffa5362`), not a new `semireal`
  slug. One row means the admin never shows two semi-realistic styles, and a character drawn in it before stays
  valid. The name is the owner's: «شبه حقيقي» / Semi-realistic.
- **Likeness first, a painting always:** gouache-and-oil storybook painting, natural proportions,
  `likeness_min` 8 and `qa_threshold` 0.8 (the other styles have 7 and 0.75). Its negatives are about technique
  (no camera look, no washes or ink outlines, no waxy faces). Words about children's skin or "glamorized"
  children made the image model refuse the character sheet twice, so the guide avoids them.
- **Not in «قمرة كلاسيك»:** Classic needs pre-drawn templates per theme × style × look, and none exist in this
  style.
- **Fourth in the order (sort 3):** a parent who is never asked still gets 3D, and «الأكثر اختيارًا» stays on
  3D.
- **House style v5:** it names the new medium and lets a style ask for natural proportions. The other three
  styles keep their slightly large heads.
- **Where the style step goes:** after the photo, as in the story flow. The activity flow for a new child is now
  6 steps (the family book 7). A child with a ready character still takes 2 (3).
- **The who card offers «ارسموا شخصية جديدة بأسلوب آخر»** rather than a separate entry point. The plan pins
  the drawing steps, so «n من N» holds while the old character can still be reused.
- **No "ready in this style" badge on the style step:** the API reuses an approved character in the chosen
  style only when no newer photo exists, and the redraw path has just taken one. The step only preselects the
  first style the child has no character in.
- **The cart line keeps the style** (`style_slug` = the character's), so the order and the admin see the
  parent's choice. Price modifiers stay at zero for every style.
- **Activity examples are the same invented child (تالا) in every style:** her character sheet, and the
  «دوسية التأسيس» cover and owner page with her cut-out, rendered locally. Watercolor has none: its sheet's
  paper grain defeats the cut-out (`render/character.py` finds one figure spanning the whole sheet).
  Production watercolor sheets should be checked for the same problem.
- **Sample spend:** $1.26 of a $1.30 cap (`semireal:` rows in `out/design-images/ledger.jsonl`).
  - The bassinet page was rejected three times: the baby was under the text box.
  - The news page drew the companion twice. A retry with the same seed gave the same picture.
  - So the story samples are the cover and one page for now.

## Watercolor sheets: the cut-out handles grainy paper, and never pastes the whole sheet (2026-10-09)

Follows «Watercolor has none» above: real watercolor character sheets put the whole sheet on the activity
covers. Checked on every sheet in `out/` (the watercolor تالا sheet, the watercolor graduation sheet, the
seven published watercolor examples, and the 3D, cartoon and semi-realistic sheets as controls).

- **Two causes.** `render/character.figure_box` counted any pixel more than 22 off the paper colour as
  drawing; the paper's grain passes that in every column, so the sheet came back as one figure. And inside a
  crop, the cut-out's edge test (gradient over 6) fires on every grain pixel, so the flood never started. The
  style guide asks for "a little visible paper grain", so every watercolor sheet has it. The cartoon آدم
  sample sheet, drawn from a watercolor reference, has the same grain and failed the same way.
- **Measured, not guessed.** The grain is the 90th-percentile gradient on plain paper: paper at least 6 px from
  anything drawn, inside any flat margin the caller padded the crop with. Clean sheets measure 0–3.6 (the
  published watercolor examples too), the grainy ones 5.4–8.2. The threshold is 4.
- **Clean paper runs exactly as before.** At or under the threshold, the cut-out and the figure finding run
  the steps and thresholds of cut-out v2 (b4cec64) unchanged. The 3D, cartoon (تالا) and semi-realistic
  masks are identical to cut-out v2, checked with golden masks in the tests, and their activity cover, back
  and owner page renders are pixel-identical. Their existing flaws stay: the cartoon front view keeps its
  floor-shadow ellipse.
- **Textured paper:** the picture is smoothed with a Gaussian (grain / 5 px, at most 2), not a median: a
  median erases a 2-px outline, a Gaussian keeps it as a weaker line. The ink and edge thresholds come from
  the paper's own noise (99th percentile plus a margin). The rim is peeled through the grain, and the "pocket"
  step is skipped. Figures on a sheet are found from what is clearly drawn (twice the paper's noise), plus 6 px
  of real paper around each. One run wider than 60 % of a three-view sheet is split at the emptiest columns
  near its thirds. That way the cut-out never gets three children as one "figure".
- **Safety check:** a cut mask covering more than 78 % of its picture (the whole sheet was 91 %; real
  figures are 36–61 %), under 1 %, or touching all four edges is not a cut-out. The child is then printed as a
  framed portrait: the figure's region of the sheet in a rounded rectangle with a soft vignette, given the
  same white sticker edge as a cut-out. The PNG says so (`qamra-cutout` text), and the four activity-book jobs
  flag the book **`cutout_fallback`** for the reviewer. Any render that cuts cleanly clears it.
- **Not held for the family.** `cutout_fallback` is not in `HELD_FLAGS`: the framed portrait is a finished
  look, and a printed book is approved by a person anyway. The admin queue shows the raw flag name until
  `queue.flags.cutout_fallback` gets a label in the messages (another change owns those files now). Suggested:
  «الشخصية في إطار (تعذّر قصّها)» / "Character framed (cut-out failed)".
- **Story covers too:** the back cover's waving hero (`qamra_pdf.assets.hero_view`) of the watercolor تالا
  and the cartoon آدم sheets is now the cut figure, not the round-portrait fallback. Every other sheet is
  unchanged. The companion beside the hero is left out when it cannot be cut out (`assets.cutout` returns
  None): it is decoration, and the shared watercolor «قمّور» sheet (seven views, painted night-sky corners)
  came out as a ragged block of all seven views on paper.
- **Speed:** the border flood labels row runs instead of Pillow's per-pixel Python flood fill. Same result,
  about 30× faster, so a cut-out takes about 1 s instead of 2–4 s.

## Every story written and sold as Magic; the theme editor edits a theme's own words (2026-10-10)

Owner (2026-10-09): «في عندك حكايات إنت بعدك مش عاملها، مثلًا عن موسم الزيتون، ضرورية هاي جدًا… عندك محرر الثيمات ع البانيل مش شايفه شغال».

- **The five coming-soon stories are written (v2) and on sale as «قمرة سحري».** They were hidden because they had no pages, not because they had no Classic template. A story with no live template is sold as Magic only, and says so on its card («سحري فقط») and page; Classic appears per style only where a live template exists (`lib/story.ts` `classicStylesFor`).
- **Story choices:**
  - Grandpa is «سِيدِي» / "Sido" (as grandma is «سِتِّي» / "Teta"), the new shared `grandpa` cast id with the C14 description, so the existing sheets are used.
  - «قارب الأحلام» puts Baba in the dream boat (`{dad}` in a life jacket, on every boat page). The house style and the page QA forbid a child alone near water; with the child alone the image model would add an adult or the QA would fail most pages. The child still hears the call, decides, unties the net and has the lighthouse idea.
  - New side characters are theme-prefixed ids (`moon_planet`, `dream_turtle`, `dream_turtle_mother`, `hara_cat`, `hara_bird`, `hara_tortoise`, `little_star`). None has a sheet yet: they are drawn from their locked descriptions.
  - The companion's name stays «قَمّور» (shared by every theme); fully vowelized it would be «قَمُّور». To change, change it everywhere at once.
- **Olive season's art:** one 3D cover by the Magic pipeline for the invented sample girl (no hijab), $0.08 of the $0.40 allowed. Kept without lettering in `public/samples/3d/olive-season-art*.webp`; the site sets the title in code. Static, like the style samples (no API call).
- **The theme editor:**
  - «محرر الثيمات» opens the themes; each theme has its pages (`GET /api/admin/studio/themes/{slug}/texts`): edit the boy, girl and English words into the theme's draft, preview with a sample boy and girl, then review → approve → publish, with rollback. No Classic template is needed.
  - «قالب جديد» starts a Classic template (story × style × look, a cost cap, default $3), with a confirm before any paid drawing and a free dry run with placeholder pictures.
  - Not built (owner's call): moving the text box and the font size (the PDF places text by area), editing scenes, the cover, the catalog fields, adding or removing pages; the reviewer role can't approve versions or templates (it has only `.view`); rolling a written story back to its coming-soon v1 is allowed.
- **Preflight:** a zero-advance mark glyph (tashkeel, Ruqaa's dots) is not tested for the bleed on its own; its letter is. Its font box (an em up from a raised origin) says nothing about its ink.

## Boy or girl in the story books: the rules (2026-10-10)

Owner (2026-10-09): «انت بالحكايات والدوسيات ماخذ بعين الاعتبار سياق الكلام للمذكر أو المؤنث؟ … أصحك تخربط تفضحنا.»

- **The companion is always masculine** («صاحب»: «قالَ قَمّور», «هو»), whatever the child drew or named it, in every theme, prompt and web message. A feminine companion would need a gender for every companion and `{m/f}` pairs for it in every theme. That is not done.
- **The class book names its children without agreeing with them.** A page can name one child, two, girls only or a mix. The names follow a place («حَوْلَ البُرْجِ: …»), a «مَنْ» question or an elative on a non-human plural, never a plural noun. The alternative was six variants per scene (one, two or more, by gender) chosen by counting the page's children. The neutral wording is simpler and right for every group. A test keeps plural nouns away from `{names}`.
- **A gender slip in AI text never blocks a book.** Before, the safety review marked a misgendered story unsafe and the book failed. Now the review lists the words (`gender_issues`), a deterministic check reads them too (`qamra_ai.pipeline.gender_check`), and the book is flagged `gender_check` for the staff text review that every story book goes through anyway. The check prefers silence to noise: a mark decides only where it is written, a verb that can take the child as its object counts only when the name is marked as the subject, and a word that is also a noun counts only when its marks make it a verb. Its rules and lexicon are in the module.
- **Wording fixes in live themes ship with their cache patch** (`vowelize.TEXT_FIXES`). The theme keeps its version number. The deploy patches the stored definitions and the Classic templates' cached vowelization, so no paid re-vowelization is needed.
- **Generic texts with no child** (catalog descriptions, the home page) may keep the generic masculine «طفلكم» where a neutral wording would read worse. A text that names a child, or sits next to a known girl, follows her gender.

## Names with hamzat al-wasl: told by their pattern (2026-10-10)

- **A name is wasl when its first word is the article («ال», `has_article`) or the masdar of a derived verb typed with a bare alif:** افتعال (with ت → ط / د after ص ض ط ظ / ز), انفعال (not a plural in «…اء» such as «أنبياء») and استفعال (`_WASL_MASDAR`, the web's `WASL_MASDAR`). The patterns cover the common names (ابتسام، انتصار، ابتهال، اعتدال، امتثال، اعتماد، امتنان، اختيار، اشتياق، ارتقاء، ازدهار، انشراح، استقلال…) and any other name of these forms, which a fixed list would miss. Rarer shapes («استقامة», «اطمئنان») are not covered. No common Arabic name with hamzat al-qat' fits them, even typed without its hamza («اسراء», «انعام», «استبرق»). The few foreign names that do («انطوان», «انستاس», «استيفان») are exceptions (`NOT_WASL`).
- **`NOT_ARTICLE` grew** with names typed without their hamza that the article rule read as «ال»: «الفت، الفة، الماس، الطاف، الحان، اليف» (أُلفت، أُلفة، ألماس، ألطاف، ألحان، أليف) and the foreign «البير، البرت، الفريد، الكسندر، اليكس، اليس».
- **The parent's spelling decides:** a wasl name typed with a hamza («إبتسام») prints as typed, and the sukun before it stays, since the reader sees a hamzat al-qat'. We do not respell names.
- **«مِنْ» before hamzat al-wasl:** a fatha before the article («مِنَ الجود»), a kasra before any other wasl («مِنِ ابتسام»). «مَنْ» (who) always takes the kasra («مَنِ الجود»). Other sukun endings take the kasra, a plural «ـمْ» takes the damma («عَلَيْكُمُ»), and a long vowel drops its sukun («فِي»).
- **Not covered:** AI-written text (Magic stories). The model writes the name inside its own words, so the prompts' rules apply there and not this filling.

## The parent frames the child's photo (2026-10-10)

Owner (2026-10-10): «لما اجي ارفق صورة الطفل اعطيني صلاحيات اللي اقدر اغير من مكان الصورة عشان اسحب فيها يمين يسار فوق وتحت عشان يتطابق مع الدائرة … كمان بدي امكانية لتعديل الصورة بعد الارفاق وبعد الرسم.»

- **The framing is numbers on the photo, never a second copy.** `child_photos.crop` (JSONB): `{x, y, w, h}` fractions (0–1) of the stored original (upright, at most 2048 px) and `rotate` (0/90/180/270, clockwise, applied after the cut). `child_photos.crop_saved_at`: when the parent last moved it after the upload. Migration `3d041b8fdbf1` (down `a58eeffa5362`). A second, cropped JPEG of the child's face would be one more file to encrypt, list and delete; the numbers die with the photo (the 24-hour job and «حذف بيانات الطفل» clear them). The companion drawing's crop (`companions.params.box`) is the same idea; the photo's has its own columns because it changes the redraw rule (below).
- **The whole frame goes to the image model, not the oval.** The frame is 358 × 340 (design Create3); the oval only guides the face. The cut-out is head and shoulders, which keeps hair and clothes for the likeness. One helper (`qamra_worker.jobs.books.photo_bytes` → `qamra_ai.pipeline.photo_crop.crop_photo`) loads every photo that reaches an image model: the character sheet, the cover's likeness reference (Addendum 11), Classic's portrait and the free cover. So every provider gets the same reference. A photo without a framing (older uploads, the admin's test books, family members) is used whole, as before.
- **An upload without a framing is framed around the face found.** The face box (YuNet, brows to chin) takes 42 % of the frame's height, centred on the oval, so the face lands in the oval with no work for the parent. The parent's own framing always wins. When framing doesn't hold (rare), a photo that passed whole is kept whole. Because of this, a child a little far from the camera now passes (`face_small` on the whole photo, fine once framed) instead of being refused.
- **The check runs on the cut-out**, with a floor of 400 px on its short side (`MIN_CROP_SIDE_PX`; a whole photo still needs 512, where the face can be small). Zooming past it gets «كبّرتم الصورة كثيرًا …» (`crop_small`). The editor caps the zoom at the same floor (3× at most), so parents rarely see it. A face cut by the frame's edge is refused (`face_cut`): the detector still finds a half face, and it draws badly. The frame's shape is checked against the photo (±2 %).
- **Saving a new framing never redraws.** The next «أعيدوا الرسم» uses it (that button always draws a new character, `redraw: true`). Every other draw request with no fixes, note or `redraw` (e.g. the style step after a photo) hands back the approved character in that style, so `draw_character` treats a newer framing like a newer photo there. The redraw limits are unchanged, and so is the deletion time: framing again after the approval never postpones the 24 hours.
- **The original comes back to the guardian only through the API** (`GET /api/create/photos/{id}/image`, `Cache-Control: private, no-store`, an AuditLog row `photo.viewed` per view, never the bytes), like the character sheet. No signed URL: the browser never holds a storage link. The device that uploaded the photo shows its own copy from memory (`PICKED`, this visit only), so the original is downloaded back only on another device or after a reload. Once deleted, the API says `photo_gone` (410) and the editor asks kindly for a new photo.
- **The editor is a plain component, no library** (`PhotoEditor.tsx`, the maths in `lib/photoCrop.ts`): pointer events for mouse, touch and pinch; a slider and ± buttons; a quarter turn; reset; arrows and +/− on the keyboard. The photo always covers the frame. The web unit tests use the repo's `node --test` (no vitest in this app).
- **Not done:** the kindergarten invite's photo step (`InviteSteps.tsx`) and the free cover's form keep their simple upload. Both now get the framing around the face from the API, but no editor. Easy to add if the owner wants it.

## 2026-10-11 — «Qamra Display»: Baloo Bhaijaan 2 with a hamza that reads as «ء»

At 9–12 pt and on pale fills (the family book's name plates, «أبو عبد الرحمن»; small titles), Baloo Bhaijaan
2's hamza over or under a letter is a short slanted stroke that reads as a fatha. The books now use our OFL copy
of the font, «Qamra Display» (`scripts/build_display_font.py` → `QamraDisplay-{Medium,ExtraBold}.ttf`): the
marks `hamzaabove.ar` (أ ؤ ئ لأ and the hamza+vowel marks are built from it) and `hamzabelow.ar` (إ) are redrawn
as the font's own lone «ء», 1.4× the old mark's height, at the same place, and a vowel over (or under) it moves to
clear it (the hamza+vowel glyphs and the GPOS anchors); nothing else changes. Baloo's license
names no Reserved Font Name; the copy is renamed anyway, as the OFL asks, and keeps the license and copyright
notice (`OFL-QamraDisplay.txt`). The CSS keeps the family label "Baloo Bhaijaan 2" and serves it from the new
files, so every page and cover picks it up without template changes. The website still loads Baloo from Google
Fonts (`next/font`): its titles are large, where the hamza reads; revisit if a small one shows the problem.

## «شبه حقيقي» v3: a realistic painted portrait, not a storybook cartoon (2026-10-10, proposal)

Tareq: «الصورة الشبه واقعية … كانت أشبه بالكرتون.» Nothing was drawn for this (no fal spend): the guide, the
code and a comparison script are ready, and the comparison runs only with his budget.

- **Why v2 looked like a cartoon** (in order of weight):
  1. **The reference.** The site's samples were drawn from a crop of تالا's published *watercolor* sheet
     (`scripts/style_samples.py`), and an edit model keeps the rendering of its reference: FLUX.2 pro returned
     the sheet unchanged, Nano Banana 2's first tries were near-copies of the watercolor sheet, and the
     published one keeps its poses, outfit and proportions. The sheet then fixes every
     page ("keep exactly the same face … and body proportions", plus the cover as the page's style reference)
     and the activity books' cut-out. Customers' photos are a better start, but the prompt cues below still apply.
  2. **The house style comes first in every prompt** and says "a premium children's picture-book illustration",
     "friendly and rounded" characters, "slightly large heads and short limbs unless the art-style line asks for
     natural proportions" (the words are still in the prompt), "Not photorealistic" and "No photorealism".
  3. **v2's own words**: "children's-book illustration, like a classic hand-painted storybook portrait", "a head
     only slightly larger than life", "hair painted in soft, glossy clumps", "clean, readable silhouettes", and
     a negative "no photographic detail" that forbade the very detail that reads as real.
  4. **The sheet prompt**: "a picture-book CHARACTER REFERENCE SHEET" with three views side by side is the
     animation model-sheet format.
  5. **The model**: Nano Banana 2 at 1K for the sheet, as for every style.
- **v3** (`prompts/style/semi-realistic.md`; v2 kept in `prompts/style/history/`): a fine-art oil-portrait
  look carried through the scene, natural proportions and eye size, real tones in the face, hair in strands,
  real fabric folds, soft painterly light, visible brushwork, "never a photograph". It describes the face by
  its complexion and tones only, and avoids life-drawing words ("figure study", "painted from life",
  "anatomy"): words about skin or "glamorous" children made the model refuse sheets before.
- **The house merge is per style.** A guide may carry `## House style` and `## House negative`, which replace
  those two house sections for that style only (`HouseStyle.for_style`, `house_for`), and `## Sheet`, a line
  added to its character-sheet prompt (`character_sheet.v4`, otherwise the v3 text). `BookContext` merges on
  creation, so the pages, the cover and the page QA use it. The merged version is «5+semi-realistic.v3»: books
  record it, and the companion-sheet cache never mixes it with the plain house. Its house negative is the
  house's list without "No photorealism" (a test fails if the house list changes and the guide does not).
- **Every other style is byte-identical.** `packages/ai/tests/prompt_snapshot.py` builds every image prompt a
  style sends (sheets, every page and cover of two books, companion and family sheets, Classic, class book,
  page QA). The golden digests were committed before the change (0bd49a6); the other six styles still match
  them, and v2 from the history file still sends exactly what v2 sent.
- **Models (recommendation, not switched).** Models are global admin settings; nothing per style was added.
  - Character sheet: **Nano Banana Pro edit at 2K, $0.15** (fal: $0.15 at 1K and 2K) instead of Nano
    Banana 2 at 1K ($0.08): +$0.07 once per child, the strongest likeness of the two, and the printed cut-out
    gets twice the pixels (the activity cover prints it 125 mm tall at 300 DPI, 1476 px; a 1K sheet's figure
    is about 700 px).
  - Cover: Nano Banana Pro ($0.15), the existing `cover_image_model` setting (Addendum 11 §6.4).
  - Pages: stay on Nano Banana 2 (0.5K preview $0.06, 1K final $0.08 plus the upscale), painted from the
    realistic sheet. Pro pages would cost $2.40–3.00 a book.
  - Not FLUX.2 pro edit ($0.03 first MP + $0.015 per extra MP of input and output, about $0.06 a call here):
    it copied the reference back unchanged on 2026-10-09. Not GPT Image 2.5 on fal (sunburst edit $0.053 at
    1024² "high", plus input image tokens at $8/M): cheap, but our fal adapter does not set its size or
    quality and would price it at the $0.15 "unknown" rate; a candidate for a later round.
  - If the grid confirms it, the smallest change is to let a guide ask for the cover model on its sheet.
- **The comparison** (`scripts/semireal_compare.py`, dry run by default): rows v2/v3 × Nano Banana 2/Pro, plus
  v3 with the Pro sheet and a Nano Banana 2 page; columns sheet, story page (new-sibling beat 13, without the
  companion), activity cut-out (local). 9 calls, **$1.00** at fal's prices rounded up to the cent;
  `--max-usd` caps every run together, failed calls are logged at full price, and finished cells are reused.
  - **The reference is a photo, as in an order** (not تالا's watercolor crop, itself one cause of the cartoon
    look): the invented girl of the site's AI-made photo `photos/hero-reading.jpg`, head and shoulders, box
    (1175, 560, 1687, 1072). It goes through what an upload goes through (`clean_image`, then `check_photo`:
    one face, score 0.94, face 30% of the width), and the fal adapter re-encodes it as for every order.
  - The first box asked for, (1175, 560, 1625, 1060), is 450 × 500 px: the upload check refuses it
    (`too_small`, the minimum side is 512). The same corner at 512 × 512 keeps the mother's face out and
    passes. The open book's Arabic title is in the crop's lower edge; the prompts forbid copying text.
  - `--ref tala` keeps the current samples' reference, for the same grid on what the site shows today.
- **Left as they are** (shared with other styles, or not sold in this style): the page template's
  "picture-book page", the house Composition's "stage it like a picture book", the sheet template's first line
  (the v3 sheet line follows it), the Classic portrait prompt (Classic is not sold in this style), and the page
  QA's "false if photorealistic" (a soft `style` flag worth 0.05; watch it on the first v3 books). The theme
  companion «قمّور» is a dot-eyed mascot by design and will look stylized next to a realistic child.
- **After approval:** merge (the guide is live as soon as it deploys; migration `968a4be3c42d` updates the
  row's record to v3), redraw the site's semi-realistic samples (about $0.55), and decide what to do with
  characters already drawn in v2 (they are reused until the parent asks for a new drawing).

## Likeness trial: the child on the sheet must be the child in the photo (2026-10-10, findings)

The owner's live test with a real 5-year-old's photo gave, in every style, a generic, rounder, younger child
(Nano Banana 2 at 1K, `character_sheet.v3`). Trial on the production prompt path
(`scripts/likeness_trial.py`; the photo was a CLI argument only, nothing of it is in the repo), Nano Banana
Pro edit, four styles, two candidates:

- **N1**, one step: the sheet at 2K with the likeness-tuned `character_sheet.v5` (the style renders, never
  reshapes the face; no "must look N, not older"; hair, face shape and proportions, skin tone and real age
  spelled out, `prompts/likeness.v1.j2`).
- **N2**, portrait first: a large head-and-shoulders portrait in the style (`character_portrait.v1`, 1K),
  then the v5 sheet from [photo + portrait] at 2K.

Spend: $1.80 for 12 calls (`likeness:` rows), plus $1.00 for the semi-realistic grid: $2.80 of a $3.50 cap.

- **What we saw** (likeness out of 10, by eye):

  | style | live (NB2, v3) | N1 | N2 portrait | N2 sheet |
  |---|---|---|---|---|
  | 3D | 3 | 4 | 6 | 6 |
  | semi-realistic v3 | – | 7 | 8 | 7–8 |
  | cartoon | – | 3 | 5 | 5 |
  | watercolor | 3 | 4 | 6 (style drifted to sepia ink, looks older) | 5 |

- **The diagnosis holds, with one correction.**
  - (a) The toddler cues are real, but they live in the style guides as much as in the sheet prompt. The 3D and
    cartoon guides ask for "big expressive / friendly eyes" and "slightly large heads", and the house style
    asks for "rounded" characters with "slightly large heads". v5's "the style never changes the face" does
    not beat those: N1 is still round-faced and young in 3D, cartoon and watercolor.
  - (b) A small face holds little identity: N1 at 2K (faces of about 250 px) stays generic. A portrait whose
    face fills the frame holds clearly more, and the sheet painted from it keeps most of it.
  - (c) Pro is better than Nano Banana 2, but the model alone (N1) is not enough in the stylized styles.
  - The realistic style fights the face least: semi-realistic v3 was the closest in every column.
- **Side effects:** removing "not older" let some portraits age (cartoon and watercolor N2 read 7–8). The
  watercolor portrait drifted to a dark sepia ink sketch. One semi-realistic N2 sheet left the feet bare.
- **Recommendation (not switched):**
  - **Portrait first** for every style on Nano Banana Pro: portrait 1K $0.15, then the sheet 2K $0.15, so
    **$0.30 per child per style** against $0.08 today.
  - Show the parent the portrait first («هل هذا طفلكم؟»): a redraw then costs $0.15, and the portrait can also
    serve the cover, the portrait page and the activity books' owner page.
  - Before that, a v6 of the prompts: "exactly his age, neither younger nor older"; the portrait "in full
    warm color, never a monochrome or sepia sketch"; shoes kept in all three views.
  - Tone down the face cues in the 3D and cartoon guides: keep the stylized rendering, but the child's own
    face proportions and eye size. This changes those styles' look, so it is the owner's call.
  - Then pass the portrait as one more likeness reference to the pages (no extra cost on Nano Banana).
- **The auto-framing** (another branch) cannot frame a close-up photo whose face fills most of the width: the
  framed cut-out fails the face check, and the whole photo is used, as `frame_photo` does.

## Portrait first, in production (2026-10-10)

The owner approved the likeness trial's direction. What was built, and the choices made:

- **Two steps per character, each with its own model:**
  - the portrait first: `character_portrait.v2`, a head-and-shoulders portrait in the style, full warm color,
    the exact age;
  - then the sheet: `character_sheet.v6`, painted from the photo and the portrait, with shoes in all three
    views.
  - Admin settings: `character_portrait_model` and `character_sheet_model` (default
    `fal-ai/nano-banana-pro/edit`), `character_portrait_resolution` 1K and `character_sheet_resolution` 2K.
  - On fal, a failing Pro falls back to the page model, as covers do. Gemini and OpenAI draw both steps with
    their own model and the same prompts.
  - Both use the photo as the parent framed it; a close-up falls back to the whole photo, as the framing does.
- **Storage:** a nullable column, `characters.portrait_image_key` (migration `2351cdc1195c`, after
  `968a4be3c42d` → `3d041b8fdbf1`). A column rather than `params`, so the cleanup and the API can test it
  plainly. The key sits under the child's prefix, `children/{child}/characters/{id}-portrait.png`, so
  «حذف كل بيانات الطفل» removes it. The 30-day cleanup of drawings never approved deletes it with the sheet.
  Characters drawn before have none, and the web falls back to the sheet.
- **A redraw draws both again.** Free redraws and failures count as before: it is one character job.
- **Where the portrait is used:**
  - every story picture of the hero, covers included, next to the sheet (`page_image.v5`);
  - the free cover: after the Classic identity portrait, before the sheet.
  - Activity books print a cut-out of the sheet, with no AI call to pass it to. The four 2K sheets of the
    verification all cut out cleanly.
  - Class books and Classic are unchanged.
- **Parents:** the character step shows the portrait large with «هل هذا طفلكم؟ / هل هذه طفلتكم؟», the sheet
  below it, and the portrait as each drawing's thumbnail in the strip. A language reviewer suggested
  «هل تشبه هذه الصورة طفلكم؟» (a painting is not the child); the owner's wording was kept.
- **Style guides:**
  - house v6: no "rounded" characters or "slightly large heads and short limbs";
  - 3D, cartoon and watercolor v3: the child keeps their own face, eye size and age;
  - semi-realistic v3 adopted.
- **Cost per child per style:** $0.30 on fal (portrait $0.15 + sheet $0.15), against $0.08 before.
- **Production never pads a photo:** clean_image, crop_photo and the adapters only crop, scale and re-encode.
  The black bars in the trial's comparison came from the comparison tool alone (fixed).

## «قلبي يعرف الله»: the last open items (2026-10-16)
- **What counts as «a false statement about the Prophet ﷺ»:** every «خطأ» statement about him or any prophet, and
  every quiz option that, with its question, says something false about his deeds, sayings, traits, mission,
  revelation or the events of his life (and a prophet's conduct). These now state the true fact and ask about the
  child. Plain recall quizzes about the other prophets' stories (who/where/how many: «من أمر نوحًا…؟», «أين وضعت أم
  موسى طفلها؟») keep their wrong options: they are options to reject, not statements; and the name questions
  («ما اسم نبينا ﷺ؟»). `test_islamic_final.test_no_false_statement_about_a_prophet_is_printed` guards the rule.
- **The tashahhud:** the Prophet's ﷺ explanation inside Bukhari 831 is dropped from the words said (`dua.omit`),
  not moved to the parents' page: a paraphrase there would retype hadith wording.
- **The reader barefoot:** the child's character sheet is drawn with shoes and each order has its own; redrawing
  it barefoot would be a paid call per order. In the prayer hall and on a prayer mat the reader is cut at the hem
  of its legs and stands on bare feet drawn in its own skin tone (`islamic_figures.bare_feet`); when its legs cannot
  be found it is drawn as it is.
- **Page counts:** padded with drawing pages inside lessons (V2 u-prayer, V3 u-fasting, V4 u-nuh and u-yunus, R
  u-eid1): no new sacred text to review.

## The invite and the free cover reuse the parent flow's steps; staff see the portrait (2026-10-16)

- **The invite renders `PhotoStep` and `CharacterStep` themselves** (with `productLine` "class", `lib/drawings`
  `CLASS_BOOK`), not copies: the parent is the child's guardian once the link is claimed, so the create API's
  photo, framing, drawings, portrait, redraw and approve endpoints already apply. Only the first drawing goes
  through `POST /api/invite/{token}/character` (the class's style); a redraw is the create flow's, in the style
  of the drawing shown, and the strip offers only drawings in the class's style (`usable`), so the class book
  never gets another style. The step texts that differ for a class book have a `class` variant.
- **The consent stays before any upload:** the invite's photo step opens only after its consent. The free cover
  shows the picked photo in the editor from the device (an object URL) and uploads it only when the form is sent
  with the consent, with the framing; a refusal keeps the photo on the device to move and send again.
- **Staff's views of the child's likeness are audited:** the admin sheet and portrait routes are `private,
  no-store` (the sheet was cacheable for 5 minutes) and write `admin.character_viewed` (ids and which picture,
  never the image), like the guardian's `photo.viewed`. The detail loads them only when the book has them.
- **Sample reference:** the style samples keep the invented تالا, drawn from the crop of her watercolor sheet as
  the earlier samples were (never a real child's photo). A watercolor reference may pull a little of its look
  into other styles; the new semi-realistic portrait still came out as a painted, realistic face.

## The Classic hero edit only takes the head (2026-10-16)

- **The edit gets no style text.** The page it edits is the style. The style guides are written for new art
  (v3 watercolor asks for violet shadows and framing lanterns); the templates predate them, and klein followed the
  words over the picture. The identity portrait gets the medium line only, for the same reason: klein copies its
  reference's background too.
- **Only the head and hair come back.** klein repaints its whole crop, drifts in colour and sometimes zooms. The
  head crop is aligned (an affine ECC fit, accepted only when plausible: ≤ 45% zoom, no shear) and colour-matched
  in a ring around the head; the mask is the head box, grown over hair that changed and is hair-coloured before
  or after (an old ponytail, new curls), not over a companion's arm or a window. Clothes stay the template's
  even when klein recolours them. Hands keep the template's skin (only the neck is in the mask): a mismatch there
  showed less than a second pasted area would.
- **Boxes from the main model on a grid.** A head box is now needed, and Haiku's boxes were round guesses (one on
  the wrong child). Sonnet with a labelled 10% grid and the page's outfit, once per template page (≈ $0.012). A
  template without a head box still works: the head is taken as the top 42% of the figure box, which is only as
  good as that box.
- **The page QA stays as it is** (`classic_qa.v1`): it already flags seams, scene changes and broken faces, and one
  automatic redraw follows. The proposed Classic cap is 2.50₪ (a full redraw round fits); the default stays 2₪
  until the owner sets it.

## The browser gets only the messages its page needs (2026-10-16)

- **An allowlist, not a denylist:** `src/lib/clientMessages.ts` lists the namespaces client components outside
  /admin use; a new namespace is private until listed, and `clientMessages.test.ts` fails when a public component
  uses one that isn't (server components read every message from the request config, so they need nothing).
- **Price messages are emptied, not removed, while prices are hidden:** the screens already skip their prices
  then, and an empty string can never raise next-intl's MISSING_MESSAGE or show a raw key if one is still asked
  for (a catalog cached a few seconds after the switch, say). A price message: a currency or an amount
  placeholder (`{price}`, `{amount}`, `{unit}`…), plus the three `{total}` messages that are money.
- **The admin's messages need a verified admin session on the server:** the admin pages were gated only in the
  browser, so their source was open to anyone. A nested provider replaces the root one's messages, so the admin
  layout gives the whole file to a verified admin and the public set plus the gate's lines to anyone else.

## Parents may keep the child's photo for later books, opt-in only (2026-10-16)

Policy change asked by the owner: «اعطي خيار صلاحية للأهالي إنهم مثلًا إذا بدهم يخلّو صورة ابنهم ع الموقع، عشان إذا
بدهم يتم استخدام نفس الصورة لدوسيات أخرى لاحقًا.» CLAUDE.md §3.1's 24-hour rule stays the default; it now
applies only while this choice is off.

- **Opt-in, separate and never pre-ticked.** A box of its own on the photo step (once a photo is saved) and in
  «أطفالي» per child. Ticking it records its own consent row: `scope = photo_keep`, version
  `photo-keep-2026-10` (web messages `photoKeep.version`, `photoKeep.accept` + `photoKeep.hint`), with time, IP
  and user agent, and the retention the text named in the audit entry. It needs the photo consent first.
  Unticking it sets `consents.withdrawn_at` (audited as `consent.withdrawn`). Not offered on the kindergarten
  invite's photo step: the school's consent covers one class book; those parents can choose it in «أطفالي».
- **While on:** the original stays where it was (encrypted, private, under `children/{id}/photos/`, opened only
  through the guardian's private no-store route or ≤ 15-minute signed URLs for the image model). The cleanup skips
  it for both the 24-hour rule and the 30-day abandoned-draft rule. Its own limit:
  `kept_photo_retention_months` (admin setting, privacy group, default 12, at most 24, public so the privacy
  page names it) after its last use: `child_photos.last_used_at`, set when a drawing or cover is made from it
  (`photo_bytes` in the worker) and when the choice is turned on; the upload time when never used. At that limit
  the cleanup deletes it (`photo.kept_expired`) and ends the choice (`photo_keep.expired`), so a later upload asks
  again.
- **Turning it off** schedules the deletion within `photo_retention_hours` (24 h), even when the 24-hour date
  had already passed (a grace, so a mistaken tap can be undone). A photo whose character is not approved yet
  keeps the usual rules (24 h after the approval, or with the abandoned drafts).
- **«احذفوا الصورة الآن»** (`DELETE /api/create/children/{id}/photos`, «أطفالي»): the originals go from storage
  at once, the drawings and books stay, and the choice ends. «حذف بيانات الطفل» still removes everything,
  consents included, immediately.
- **Reuse:** `ChildOut.photo_kept`. A new drawing for that child (a new book, a workbook, another style) goes
  through the photo step showing the kept photo («نستخدم الصورة المحفوظة»), to use it as is, move it or change
  it; no new upload. A ready character is still reused without any photo step.
- **Texts that changed with it:** the parent consent's point 2 (version `parent-2026-09` → `parent-2026-10`), the
  invite consent's point 2 (`school-2026-09` → `school-2026-10`), the character step's keep line, the how-it-works
  privacy point and FAQ, and the privacy page (storage and deletion, plus a new «الاحتفاظ بالصورة لكتب قادمة
  (اختياري)» section). Shorter marketing lines («صور الأطفال تُحذف تلقائيًا بعد اعتماد الشخصية») describe the
  default and stay.
- **Backups still exclude every original photo** (`infra/scripts/backup.sh`), kept or not: a lost kept photo is
  re-uploaded, never restored.
- No new third party: the photo goes only to the image provider, as before, and only when a drawing is made.

## Free character drawings come back with time (2026-10-16)

The owner got stuck on the style step: each child had 4 drawings (the first + 3 redraws) for good, then «تواصلوا
معنا». He asked for drawings that come back after a while, e.g. every two hours. Each drawing costs ≈ $0.30
(Nano Banana Pro portrait + sheet), so some guard stays.

- **Rolling window, not a reset clock:** each drawing comes back `free_draws_window_hours` (default **2**) after it
  was asked for; at most `free_draws_per_window` (default **3**) in any such window. No midnight or "every
  2 hours on the hour" reset that rewards waiting for the boundary, and the time we show is exact (the oldest
  drawing in the window + 2 h).
- **Daily ceiling, per child and per account:** `free_draws_daily_cap` (default **12** in 24 h). 12 × $0.30 ≈ $3.6
  a day is the most one account can spend on drawings, about one book's AI cost. The account's count comes from
  `character.drawn` audit rows (ids only), so deleting a child and adding it again gives nothing back; the child's
  count comes from its characters. One number for both caps keeps the admin simple (three settings in «الجودة
  والتكلفة»).
- **Every drawing counts, the first one too** (the old rule counted 1 + 3). With 3 in 2 h a new child gets the
  first drawing and two redraws at once, and more as the hours pass. Reusing the approved character is not a
  drawing; a drawing that failed on our side never counts (as before); one the cleanup removed still does.
- **Staff are never limited, in any flow** (owner: «اذا انا بحساب الادمن دايما يقدر يعمل»): an `admin` account (the
  owner's among them) draws the child's character, the companion and the family as often as needed, has no
  previews-per-day cap and no hourly photo-upload cap. Past drawings don't matter for them, so the owner's test
  children are open right after the deploy. Parents' existing drawings do count in the window from the first
  minute (no one is blocked for longer than the window or the day).
- **One place:** `qamra_api.draw_limits`; the story and activity-book steps and the kindergarten invite all draw
  through `create.draw_character`. The refusal is `free_draws_used` (429) with `details.reset_at`; the
  companion's and the family member's own limits keep `redraws_used` (they don't come back with time).
- **The site:** the style step shows how many are left; with none left it shows «وستتاح لكم رسمة جديدة بعد
  {time} (عند الساعة {clock})» on the parent's own clock (lib/drawLimits) and continues with the child's newest
  drawing (in this style, else another one the book can use), where the strip of earlier drawings can be approved
  without a free drawing. The line says «رسمة جديدة», not «تتجدّد»: with a rolling window one drawing comes back at
  that time, not all of them (the language review's point). The button comes back on its own when the time
  passes; the API decides.
- **Not changed:** the companion's 4 rounds and the family member's 4 drawings stay per item (behind their own
  features); the class book's free page redraws stay per class.

## Phone numbers typed on Arabic keyboards; 422s name their fields (2026-10-16)

The owner kept getting «بعض البيانات غير صحيحة» at checkout (`POST /api/store/checkout` → 422). Cause, confirmed by
a test: the phone check was `^\+?[0-9 ()-]{7,20}$`, ASCII digits only, and an Arabic keyboard types ٠٥٩٩… (or
۰۵۹۹… on a Persian layout); the 422 named no field, and the site showed only the generic line.

- **One normalizer:** `qamra_core.phone.normalize_phone` (and its twin `apps/web/src/lib/phone.ts`): Arabic-Indic and
  Persian digits → ASCII; spaces, dashes, dots, brackets and direction marks ignored. Stored forms: local numbers
  keep their zero, digits only (`0599123456`, landline `022981234`; a bare `599123456` from Excel gets its zero
  back); international ones start with `+` and keep the country code as typed (`00970…`, `970…`, `+970 0599…` →
  `+970599…`; `+972…` stays `+972…`, since both serve Palestinian mobiles). Jordan (`07…`, `+962…`) and other
  countries' `+` numbers are accepted. A local `05…` number is **not** turned into `+970`/`+972`: we can't know
  which one the customer uses. `phone_key` (the last nine digits) is what all forms of one number share: order
  tracking and the coupons' first-order / per-customer checks match on it.
- **Everywhere:** checkout, kindergarten sign-up and school details, demo requests, family-book quotes, the school's
  children list (CSV), admin phone settings; also two-factor codes typed in Arabic digits (they used to fail) and
  numbers sent as text in Arabic digits (`children_count`, the quote's `quantity`).
- **Field messages:** every 422 from validation keeps `details.fields` (the sorted list of names, unchanged so
  existing pages keep working) and adds `details.field_errors`: field → `{ar, en}`, by field name and kind of
  problem (`qamra_api.errors.FIELD_MESSAGES`). The owner asked for the map under `details.fields`; that would have
  broken every page that reads the list, so the map has its own key. Refusals about one field with their own code
  (`unknown_city`, `unknown_zone`, `terms_required`, `weak_password`, `common_password`, `email_taken`,
  `wrong_password`, `invalid_setting`) carry the same two keys. When an `invalid_input` has field messages, its
  top-level `message` is the first field's message, so pages that mark nothing still say what is wrong.
- **The site:** checkout, sign-in/sign-up, change password, kindergarten sign-up, the demo request and the quote
  form check the obvious things first (required fields, the phone after normalizing, lengths, e-mail, whole
  numbers), show each message under its field (red border, `aria-invalid`, `aria-describedby`), focus the first
  one, and show «راجعوا الحقول المعلّمة بالأحمر.» on top; the server's own message stays the fallback when no field
  can be marked. Forms use `noValidate` so the browser's own bubbles (in the browser's language) don't take over.
  Number inputs are text with `inputMode="numeric"` (a `type="number"` input drops Arabic digits).
- **Addresses:** any text of 5 or more characters is accepted (the owner's «ضضضضضضضضض» included): no "gibberish"
  check. **City and zone:** the checkout's city must be one of the chosen zone's cities; the refusal now says so
  («هذه المدينة ليست ضمن منطقة التوصيل المختارة…») under the city; an unknown zone is marked on the city too.

## The activity books read in Scheherazade New (2026-10-17)

The owner found the workbooks' body text "too Arial" (IBM Plex Sans Arabic) and asked us to pick the best font for
3–6-year-olds reading fully vowelized Arabic. Compared on the same pages (ليان): A IBM Plex Sans Arabic, B Noto Naskh
Arabic, C Scheherazade New; Readex Pro and Vazirmatn were looked at too and dropped (both geometric sans, the same
"Arial" feel). Side-by-side images: `~/Downloads/qamra-font-compare/`.

- **Choice: Scheherazade New (SIL, OFL 1.1)** for every Arabic text the child or a parent reads in the four activity
  books: instructions, words and sentences to read, dialogues, labels, parents' boxes, footers, answer keys
  (`--body` and `--naskh` in `_base.css.j2`; «قلبي يعرف الله» uses them for `--kitab` and `--ui`). Why: school-book
  Naskh letter forms like the ones children meet in Palestinian and Jordanian KG/grade-1 books; the largest and
  clearest harakat of the three, placed well clear of the letters, shadda + vowel stacked cleanly, tanween and sukun
  easy to tell apart. Noto Naskh has the same forms but small, light marks; Plex is a sans.
- **Titles stay Qamra Display.** Latin letters, digits (١٢٣ and 123) and Western punctuation (! ? : . «») stay in IBM
  Plex Sans Arabic through the font's `unicode-range`, so English pages and numbers look as before and Scheherazade's
  wide-set colon and guillemets don't open gaps in Arabic lines. The Arabic comma, semicolon and question mark come
  from Plex too, for the same reason.
- **Sizing without touching the layout:** at the same point size Scheherazade looks about 10 % smaller than Plex and
  has very tall vertical metrics (2.0 em line box against Plex's 1.5 em), which made the engine's fit checks shrink and
  refuse boxes (the family book's parents' box was refused at 8.5 pt). The `@font-face` rules set `size-adjust: 110%`
  (same apparent size as Plex) and `ascent-override: 94%; descent-override: 42%; line-gap-override: 0%` (the same
  1.5 em line box as Plex), so every box keeps its height. The font files are unmodified, so no OFL rename is needed.
- **Footer skill line:** `max-width` 70 → 80 mm (still ≥ 6 mm clear of the centered page number) and
  `text-wrap: balance`: the Naskh is a little wider, and a wrapped line now never leaves one word alone.
- **Boxes that clip their text** (`_reading_font.css.j2`, loaded after every product's CSS, covers and answer keys
  included): Scheherazade's harakat and descenders reach further past the line box than Plex's, so boxes with
  `overflow: hidden` cut them («فى» for «في» in the parents' box, «سالم» without its kasra, the bottom of «بستّي»,
  the hamza of «أنشطة» on the covers' badges). One-line labels that clip only to cut a too-long line now clip
  sideways only (`overflow: clip visible`); boxes with a capped height (parents' box list, safety notes, fixed
  hadith boxes) clip 1.6 mm further out (`overflow-clip-margin`; the covers' subtitle 2.5 mm), enough for the marks,
  never for an extra line. «قلبي يعرف الله» answer keys: the engine's key fit (`_FIT_JS`) now also sets a card's
  text smaller when its last line runs into the card's padding (it sat on the card's edge, 1–4 mm in the page's
  safe margin, on 1–7 sheets per volume; three volumes already had one such sheet with Noto Naskh). «قلبي يعرف الله»: a story-grid caption that wraps to two lines takes the room it needs from its
  picture (its fixed strip ran the first line into the picture, already with Noto Naskh), and the character names
  of «مَنْ في الكِتاب؟» get 0.8 mm below them. The owner page's three lines sit 1 mm in from the safe edge
  (preflight saw «رَوْضَتي» 0.1 mm in the margin). The covers' design is untouched; they take the font through
  `--body`/`--naskh` and the same clip rules.
- **Checked:** every page of every volume (دوسية التأسيس KG1/KG2 × 3 with covers and answer keys, رحلتي الأولى stages
  1–3, مغامراتي مع عائلتي with its inserts, قلبي يعرف الله V1–V5 and R with covers, keys and sticker sheets) for
  «ليان» and «يوسف» (the boy's renders use the girl's sample picture: only the text is under test), audited after
  the engine's fit pass against the same pages in the old fonts: no page refused, no new text outside its box, no
  ink cut by a clipping box (measured with the shaped glyphs' real extents), no word broken across lines, fewer
  footers on two lines than before; every PDF passes preflight, and the only warnings left are the sticker sheets'
  (as before the change). The Islamic books' existing auto-fit (`.isl-body` zoom ≥ 0.8) now draws one interior page
  (R, «أزور وأهنّئ») at 96 % and two parent pages at 94 % instead of 96 %; answer-key cards (for grown-ups) are set
  at 85–95 % more often, a few at 70–80 %. Accepted.

## QR audio pace and tappable words from offline word times (2026-10-17)

The owner found the QR clips too fast (English most of all) and wanted to tap a word and hear it, then asked for
calm pauses between the words rather than a slowed voice.

- **Pauses, not playbackRate:** slowing a clip below ~0.9 smears speech, so the default plays the clip piece by
  piece with a pause between the pieces (1 s Arabic, 1.3 s English); «أبطأ» lengthens the pauses (1.7 s / 2 s) and
  plays at 0.9 with `preservesPitch`; «عادي» is the clip as recorded. One `<audio>` element seeks to a piece, plays
  it, stops at its end (checked each animation frame) and waits the pause (`lib/journeyPlayback.ts`, `StepPlayer`):
  no new audio and no Web Audio decode (which can't keep the pitch when slowed).
- **Word times instead of a clip per word:** the cheapest correct way. A clip is cut at its pauses (the n−1 longest
  quiet stretches for n pieces of the script; sound items where `journey_voices.py` joined their parts, since slow
  drum beats have pauses of their own), and every piece is heard back by Whisper running on this machine
  (`faster-whisper` large-v3-turbo: free; fal's Whisper would have cost about $0.20). A clip is accepted when at
  least 70 % of its pieces are heard as their text and at most one is heard as a neighbour (two or more = a
  shifted cut); a shown word is tappable only when its own piece was heard. Results: all 89 clips, 408 pieces,
  273 of 278 shown words and letters.
- **Served only with their clip:** the API gives `words` only when the stored clip is the shipped TTS clip with
  the same length as in `words.json`; a person's upload or the on-the-fly narrator plays whole. The deploy loader
  checks sha256 and length of every entry against the shipped clips and exits 1 on a stale one.
- **Rushed clips remade, $0.063:** clips whose words ran together (no pause to cut at: 32 English, 2 Arabic, and
  the alphabet's 28 names, 23.7 s in one breath) were remade word by word with the same voice, as earlier fixes
  were. A lone English letter is sent as `"A."` (heard back: «A» and «A.» were read «uh»). «Van» was taken three
  times and never heard back as «Van» (Whisper hears «Fun»/«from»); it plays in the word-by-word playback but is
  not offered on a tap. «R» and «Z» are said the British way («ar», «zed») and were heard as such on a second
  take. Words that are not said alone (stage 1 «كلمة شَمْس») are not tappable rather than playing extra words.
- **Shown entries said part by part:** the alphabet page shows one entry «أ ب ت …»; its times give the piece of each
  letter (`show[i]` is a list), and the page draws one button per letter.
- **No fake sounds:** a sound item's word plays that item's own sound effect, cut from its clip.
- **The last five (same day):** new takes for «تاء», «ثاء», «قاف» (said with their marks: without them the voice
  blurred them, heard «شكرا», «سات», «كاف») and «Van»; «كلمة شَمْس» split at its pause. «Van» is heard «van» in its
  take alone but «Fun» inside the clip, so it was checked by its waveform: one loud stretch of 0.82 s against
  0.31–0.76 s for the other letter pages' words, no inner pause: one clean word. It is accepted by hand for that
  clip's sha256 only. All 278 shown words and letters are tappable; a word that can't be played alone is shown
  greyed with no button rather than as a button that does nothing.

## Story text looks hand-lettered and painted into the picture (2026-10-19)

- **Owner, on «موسم الزيتون»:** «الخط بدنا إياه يكون مرتّب أكثر ومناسب للحكايات، زي اللي مرسوم رسم، مش خط كتابة
  Arial. يكون داخل حتى بالصور، وكأنه مرسوم وملوّن وعليه أشياء حلوة.»
- **Three treatments were tried on the published examples** (زينة and عمر in «موسم الزيتون», هيا in «يوم التخرّج»,
  rendered locally from the stored pages, read-only): A) Playpen Sans Arabic on a painted watercolor wash,
  B) Qamra Display (Baloo) on a torn paper scrap with washi tape, C) Marhey lettered straight onto a soft mist.
  Side-by-side boards (with the current Naskh-on-cream-cloud) went to `~/Downloads/qamra-story-type/`.
- **Chosen: A.** Tashkeel first: Playpen's marks are the clearest and largest of the faces tried (≈30 OFL Arabic
  faces were set with the same vowelized lines; Marhey's and Lalezar's marks crowd, Baloo's read well but its
  letters look typed, Ruqaa/Rakkas/Katibeh are display-only). Playpen is a rounded hand-drawn letter made for
  children learning to read, so it looks drawn, not typed, and it covers Latin: English books keep the same hand.
  B looked like a note stuck on the art (a sticker again) and C lost contrast on busy art.
- **The wash is painted in code, not a box:** an SVG blob that hugs the fitted text, edge wandering per page
  (seeded), filled through an SVG watercolor filter (ragged edge, uneven pigment, darker drying edge, grain), in a
  pale tint of the art's own color around the text. The words are set in a deep tone of the picture's own hue
  (≥ 7:1 where the wash is thinnest, 80% of its opacity), the child's name in the theme's accent darkened until it
  reads (≥ 4.5:1) and in the ExtraBold. Fades take the picture's tint too; paper pages take the picture's ink.
- **Decoration in moderation:** a small sprig on the wash's corner and a flourish on its edge, by theme
  (`Theme.text_motif`, else by slug, else by the cover lettering): olives (olive season), stars (star keeper, moon
  trip, dream boat, graduation), hearts (new sibling), flowers (first day, neighbourhood friends). The same sprig
  sits at the end of the cover's «بطولة» ribbon. The page-number star badge stays.
- **Never on a face:** faces are found in each picture with the YuNet detector we already ship (MIT, detection
  only) at a low threshold for painted characters. The fit shrinks the text (never under the age minimum), then
  narrows it and slides it to one side of its band, then tries the other bands; a page where the words still
  touch a face is flagged `text_over_face` for the staff review (crowded family scenes); `text_moved` notes a page
  whose words left the theme's text area.
- **Found on the way:** with Playpen's contextual alternates on, Chromium reused the wrong glyphs across a line
  break («…يَدَاكِ يَا اكِ يَا» instead of «…يَدَاكِ يَا زِينَةُ»). `calt` is off for the story text, and a test
  sweeps box widths and compares each wrapped paragraph with the same lines forced by `<br>`.
- **Sizes:** the age sizes stay (26/24 pt, 21/20 pt); `size-adjust: 90%` keeps Playpen at about the visual size
  of the Naskh it replaces. Story books are only 21 × 21 today (`PrintSpec` takes no trim from the settings);
  a 15 × 15 render of the layout library overflows and would need its own layout sizes before it is offered.
- Class books take the same lettering, wash and motif.

## The child's colours and likeness: a neutral reference, daylight prompts and likeness notes (2026-10-19)

Owner's live test with his test photo of a 5-year-old boy (a night photo under warm street light): the
watercolor portrait and sheet were muddy and brownish-yellow, almost sepia («ألوان مش كثير واضحة وسيئة»), and the
cartoon one was «طفل مختلف»: darker hair, a rounder face, a different smile, without his lighter tips swept up at the
front and his narrow smiling eyes.

- **The cause, measured.** The face in the photo is barely tinted: its cheeks read ln(R/G) 0.45, ln(B/G) −0.27 in
  linear light, against 0.44 / −0.35 for the daylight face of the test fixture. The warm light is in the hair's
  rim light and the background. So the sepia came mostly from our own words: the house palette («warm
  moonlit-and-golden … warm with a golden glow»), watercolor v3's «warm textured paper», «glowing honey-gold
  highlights» and «golden-hour light», and portrait v2's «full warm color» on a «warm cream background». The same
  photo with the new prompts gave clean, natural colour (below). The photo's cast still matters for darker or
  more strongly lit photos, which the colour step handles.
- **A: the reference's light made neutral** (`qamra_ai.pipeline.photo_color`). After the framing crop, every photo
  an image model gets (`photo_bytes`: portrait, sheet, cover likeness, Classic, free cover; and family members'
  photos) goes through `reference_photo`. The stored original never changes.
  - The light is read away from the head: YuNet finds the face, and the head, hair and neck are left out (skin
    and hair are warm by nature), as are strongly coloured pixels (a red T-shirt) and near-black and clipped
    ones. What is left gives the light: a p-norm (p = 4) "shades of grey" mean of linear RGB.
  - Only the part of the cast outside a tolerance box (ln R/G −0.06…0.10, ln B/G −0.15…0.06, so a warm room or
    a cool shade stays) is taken out, and only 80 % of it; each channel's gain stays within ×1.5 either way, and
    a grey's brightness is kept.
  - **The skin guard:** the cheeks, once corrected, must stay in a skin range (ln R/G ≥ ln 1.12, ln B/G ≤ ln 0.92,
    and not past ln 3 / ln 0.3); the correction is scaled back until they do, and skin already outside is never
    pushed further out.
  - Exposure: a face darker than luma 0.42 or brighter than 0.80 is moved gently toward the range (×0.8–1.6);
    then a mild levels stretch (≤ 1.25) when the picture doesn't span the full tonal range (never on a plain,
    flat picture).
  - Without a face, or with under 6 % of the picture left to read, the colour is left alone. A photo that needs
    nothing comes back byte for byte.
  - The owner's photo has almost nothing neutral away from the head (black sky, red T-shirt), so its colour was
    left alone (gains 1.0) and it only got a 1.13 levels stretch. Which is right: its face had no cast.
  - Tested on synthetic sodium, tungsten and blue-screen casts on the face fixture: the skin comes back at
    least 40 % (blue: 25 %) of the way to its daylight colour, a mild warm room is untouched, the gains stay
    clamped, pale skin never turns grey.
- **B: daylight prompts.**
  - `character_portrait.v3` and `character_sheet.v7` (through `likeness.v3`): "this is the child's reference
    portrait/sheet, not a scene: paint it in even, neutral daylight, whatever the palette says about the light
    of scenes".
  - A COLOR block: ignore the photo's light, colour cast and background; the child's true skin tone, hair colour
    and eye colour; never tinted brown, amber, yellow, sepia or grey.
  - The portrait is «in full, clear, natural color» on a «very light cream» background, and the sheet's
    background is «evenly lit, very light cream»; a negative against an overall tint.
  - The house style is unchanged: its golden palette is right for scenes, and pages, covers and QA are
    byte-identical in every style but watercolor (the golden snapshots prove it).
- **Watercolor v4** (v3 in `history/`, migration `5b7e2c9d4f10` keeps the row's record):
  - white textured paper; clean, bright, transparent washes with clear, rich colour; luminous highlights;
  - "the light is the scene's own (soft daylight, a golden evening or moonlight), and under it skin, hair and
    clothes keep their true, clear colors";
  - a new negative: no sepia, brown, amber or yellow cast over the whole picture, no muddy browns or greys.
  - It changes every watercolor prompt, pages included: the paper is white instead of warm. Golden scenes stay
    possible; a scene names its own light.
- **A new guide section, `## Character`:** a line each style can add to the character portrait and sheet prompts (watercolor:
  clean transparent washes in neutral daylight, true colours). `## Sheet` stays sheet-only, because the
  semi-realistic one speaks of three views.
- **C: likeness notes** (`qamra_ai.pipeline.likeness_notes`, `likeness_notes.v1` + `likeness_notes_user.v1`).
  - Before drawing, the main text model (Sonnet, vision) looks at the framed, neutralised photo(s) and writes
    short notes on how the child looks: hair (colour with lighter and darker parts, length, texture, direction,
    the front), face shape, eyes and how they look when smiling, eyebrows, nose, mouth and smile, skin tone in
    daylight, marks, and glasses only when the family said so (hair left out under a hijab).
  - They go into the portrait and sheet prompts of every style ("WHAT THIS CHILD LOOKS LIKE … keep every one in
    the drawing, in the style's own way") and are kept on the character, `params.likeness_notes`, with
    `likeness_notes_outcome`.
  - They are written once per drawing and saved before the drawing starts: a retried job doesn't ask again, and a redraw (a new
    character row) reads the photo again.
- **Privacy:**
  - appearance only: no name, no identity or resemblance, no ethnicity or origin, no age guess, nothing below
    the neck, no clothes or place;
  - the family's hijab and glasses choices win over the photo;
  - every note gets the local text screen (links, phone numbers, unsafe words) and is cut to 220 characters;
  - the log has the outcome only, never the notes;
  - the 30-day cleanup of drawings never approved removes the notes with the picture (and those of
    failed drawings), and «حذف كل بيانات الطفل» removes the character row.
  - An unclear photo or a failed call draws without notes, as before.
- **Cost:** about $0.01 per drawing (one Sonnet vision call, ~2.5k tokens in, ~300 out), logged as
  `character:likeness` in GenerationCost against the child. The portrait and sheet stay $0.30 on fal.
- **Verification on the owner's photo, $1.50** (`likeness-v2:` ledger rows, 10 Nano Banana Pro calls at $0.15;
  the cap was $0.55, then $2.00 once the owner's balance was known; `scripts/likeness_colour_trial.py`, portraits
  in parallel, then sheets). There is no Anthropic key here, so the trial's notes were written by hand from the
  photo, following the rules the model gets; the server writes its own. By eye, out of 10:

  | | live | new, try 1 | new, try 2 |
  |---|---|---|---|
  | watercolor portrait | 6, sepia | 6–7, clean colour | – |
  | watercolor sheet | 5, sepia | 5, clean colour, face rounder | 5–6, clean colour |
  | cartoon portrait | 3 | 5–6 | 4–5 (hair too light) |
  | cartoon sheet | 3 | 5 | 4–5 |
  | 3D portrait | – | 5 (hair too dark, face round) | 5 (closer hair, face round) |
  | semi-realistic portrait | – | 7 | – |

  - **Colour: fixed in every picture.** White or very light paper and background, natural skin, no sepia or
    amber; 3D and semi-realistic are neutral too, so the new wording does not hurt them.
  - **Likeness:** the notes bring back what a stylized drawing used to drop: his lighter tips, the quiff swept
    up at the front, the narrow smiling eyes and the closed smile. The face shape is still the weak point in
    cartoon and 3D: wider, rounder and a little younger than his. A second seed changes the hair colour more
    than the face. Semi-realistic remains the closest style.
  - Unspent: $0.50 of the cap, kept for live orders.

## A code for every book and «عن قمرة» in every book (2026-10-19)
- **Owner:** «بدنا صفحة لمعلومات قمرة على الكتاب… كل كتاب يتم إنشاؤه على النظام يكون إله كود… لما يجيني أكثر من طلب
  بنفس الاسم، مثلًا طلبين باسم يوسف، فبدي أميّزهم بالكود. اعمله على كل الدوسيات والحكايات.»
- **The code:** «QB-» + 5 symbols from `23456789ACDEFHJKMNPRTWXY` (24 symbols, about 8 million codes), e.g.
  «QB-7K4M2». No 0/O, 1/I/L, nor the pairs that a phone call or a quick look mixes up (B/8, G/6, S/5, Z/2, Q/O,
  U/V). No check digit (the owner said optional): a mistyped code finds no book. Staff can type it any way
  («qb 7k4m2», «7K4M2», Arabic digits) or a part of it (3+ symbols).
- **Given when the book is created**, by every code path (story, Classic, class copy, each activity-book volume):
  the session's `before_flush` claims a random code with `INSERT … ON CONFLICT DO NOTHING` in the registry
  `book_codes` and draws again when it is taken. The registry keeps every code ever given and has no link to the
  book, so a code is never reused, not even after «حذف كل بيانات طفلي». `books.code` is unique and required;
  migration `8c3f5a1d7e42` gives every existing book one.
- **Where it shows:** admin books list and approval queue (and search), book detail, order detail (each line's
  books, with their volume), order search, packing slip, print batch detail and the printer's manifest CSV
  (`book_code` column), invoices, the parent's order page, and the order and «book ready» emails.
- **«عن قمرة» page, always the book's last page**, in each product's colours and ornament (`qamra_pdf.imprint`):
  the code, large; «صُنِعَ هذا الكتابُ خِصّيصًا لِـ…» with the child's picture; the product and part; one warm line;
  phone, WhatsApp, email, website, Facebook, Instagram (the admin's contact settings, the owner's values by
  default); a QR to `https://qamra.app/b/<code>`; the month the book was made; «جميع الحقوق محفوظة © قمرة».
  - Stories (multiples of 4): the info page takes the last page of the last signature, after «للأهل» and the
    fillers. A book keeps its page count (it gives up one filler: «ذكرياتنا» without a companion page, «ارسم» with
    one), except when «للأهل» already ended a signature (only «أصدقاء الحارة» with a companion): then 4 pages are
    added (activity, memories, a blank page, the info page).
  - Class books: each copy's own last page (its own code), rendered per child like the portrait page.
  - «دوسية التأسيس», «رحلتي الأولى», «مغامراتي مع عائلتي» (wire-o, even page counts): the info page after the
    last page, and a plain page with the small moon behind it when the book was even (so the info page faces the
    reader after the certificate and the sheet stays whole). The cover's page count stays the content's.
  - «قلبي يعرف الله» V1–V5 (multiples of 4): the closing page «إِلَى اللِّقَاءِ» becomes the info page, its
    farewell and «the next book» above it; no page added. «رَمَضَانُ وَالْعِيدُ» had no closing page and was
    72 pages: it gets the same closing page plus two drawing pages and a family challenge (the padding the volume
    check recommends), 76 pages. These are AI-drafted like the rest and go through the scholar's review.
  - Back covers print «رمز الكتاب QB-…» small at the foot (stories: under the barcode area; activity books: in the
    foot beside «صُنعت خصيصًا لـ…»).
- **The QR page** (`/b/<code>`, `/hello` without a code) is public and `noindex`: the API answers only the child's
  first name and the product, and the same 404 for an unknown, malformed, deleted or sample code; 120 lookups
  an hour per IP.

## «تغيير الصورة»: a new photo for a child, any time (2026-10-19)

The owner: «اسمح لي إنه أقدر أغيّر الصورة، مش معقول خلص بس صورة واحدة وبس.»

- **Where:** the known-child card on the first step («تغيير الصورة», next to «تعديل البيانات», which links to it
  too) and each child in «أطفالي» (`/create?child=<id>&photo=new`). It is an action, not a toggle: it goes to the
  photo step at once (the consent step first when the child has none).
- **The flow** is the usual one with one flag in the URL, `photo=new` until the new photo is saved, then
  `photo=done` until a drawing is approved (lib/flows `FlowState.newPhoto`): the photo step shows even with a photo
  from the last 24 hours, and no ready character is reused. A story whose type isn't chosen yet asks the photo
  first, then the type (`stepsFor` orders `line` after `photo` then, so «n من N» reads right); «أطفالي» opens there.
  Approving a drawing ends it (the flag leaves the URL).
- **The current photo** (still kept: within 24 hours of the approval, or kept at the guardian's choice) can be
  moved instead of replaced; once deleted, the step asks for a new one and says why.
- **Privacy:** the API keeps only the newest original: a new upload deletes an earlier one still stored at once
  (audited `photo.replaced`, ids only), as it already did. The new photo's 24-hour clock starts at upload when an
  approval exists, at the approval otherwise (unchanged). Only the photo consent (`scope != keep`) lets a photo
  in; the keep choice alone does not.
- **The drawing records its photo** in `Character.params.photo_id` (no migration, no new column: the params are
  where a drawing's inputs already live, and several branches add migrations in parallel). The API sets the
  newest photo when the drawing is asked for; the worker, which now takes the newest photo first, writes the one
  it really used. `CharacterOut.photo_id` lets the strip mark drawings from an earlier photo («من صورة سابقة»);
  drawings made before have none and are not marked.
- **Free drawings:** a drawing from a new photo counts like any other (staff unlimited); the earlier drawings stay
  choosable without one.

## «ماذا يلبس؟»: the parent chooses the child's outfit (2026-10-20)

The owner: «إذا في مجال نختار براحتنا شو النمط ولون اللبس، أو يكون في قوالب جاهزة للبس… اعملي 5 أو 6 أنماط أو ألوان للبس. مهم جدًا.»

- **Catalogue, not code:** `content/outfits.yaml` (versioned) holds 8 outfits = 6 looks for girls and 6 for boys
  (classic, red top & jeans, school uniform and Palestinian embroidery are shared with a look per gender; girls also
  get the yellow cardigan and the pink dress, boys the green hoodie and the striped sweater). Each look has the exact
  sheet words (`prompt`), the portrait's `top`, and swatch colours; each girls' outfit names the hijab that goes
  with it (the hijab follows the outfit). Colours are distinct from each other and print-safe (no neon).
- **The default «الكلاسيكي»** is the cream top / night-blue trousers / brown shoes every child wore before. Its
  prompts are byte-identical to before (sheet v8 = v7, portrait v4 = v3; the golden prompt snapshots did not
  move), and books keep choosing their own everyday clothes for it, as before. The name stays «الكلاسيكي» as the
  owner asked, although the language review noted it shares the word with the Classic line; the two never show
  together (Classic hides the outfit choice). Rename later if it confuses parents (e.g. «الأساسي»).
- **Where the parent picks:** under the styles on the style step (a radiogroup of drawn SVG swatches, no AI, no
  cost), preselected as the child's last-approved drawing, else the default. On the character step the card and the
  drawings strip name the outfit, and «غيّروا ملابس …» redraws in another one (a free drawing like any redraw; staff
  unlimited). A plain redraw keeps the drawing's outfit. When the story page already chose the style (the style step
  is skipped), the child is drawn in the default or reused drawing; the parent can still change the outfit on the
  character step.
- **Classic** offers no outfit: its templates are drawn already; the style step says so. The API refuses an outfit
  on a line it is not offered on (`invalid_outfit`). Class books (the kindergarten invite) keep the default: the
  school chooses the look of a class book.
- **Stored** in `Character.params.outfit` (no migration, like `photo_id`). An approved drawing is reused only in the
  outfit asked for; with no outfit asked, any approved drawing in the style is reused (as before).
- **Books:** the outfit is worn on each theme's everyday scene groups, listed per theme in `outfits.yaml`
  (`themes:`; first-day, neighborhood-friends, new-sibling, moon-trip, olive-season and custom: `day`; graduation:
  only the `school` flashback). Costume groups keep the theme's clothes (graduation gown, pyjamas, sailor and space
  suits, festive clothes). When the cover's group wears it, the book's one hijab is the outfit's. The mapping lives
  in the outfit file, not in theme.yaml, so no theme version had to change and the studio's live definitions keep
  working. The book records the outfit it used (`generation.child_outfit`); books started earlier keep their stored
  bible. Activity books cut the child from the sheet, so they wear the chosen outfit with no other change.

## The child's own face shape in cartoon and 3D, and one direction per view on the sheet (2026-10-21)

The owner, after the likeness notes: in the cartoon and 3D styles the face comes out rounder, wider and younger
than his child's (the hair, smile and eyes are close now). And, often, a sheet whose side view has the head in
profile looking right while the body, arms and feet walk left.

- **The cause** (round, wide and young):
  - The style guides were already cleaned of "big eyes" and "large heads" (v3). What was left pulls the same way:
    cartoon's "soft two-tone cel shading" and "simple clean shapes" for everything (a face simplified to a round
    cartoon head); 3D's "appealing stylized rendering" in an "animated-film look" (the genre's appeal face:
    round, big-cheeked, short-chinned, big round eyes).
  - The prompts said "keep the face shape" but never what that shape is. The likeness notes (v1) asked for
    "the face shape (oval, round…), the cheeks, the jaw and chin" and invited any child's "soft full cheeks and a
    small rounded chin" (the trial's own notes of 10-19 said exactly that).
  - The age line ("not a toddler") named no face of that age.
  - Measured (YuNet face box, width to length): the photo 0.79; the live portraits 0.88 (3D) and 0.82–0.95
    (cartoon).
- **What changed** (all styles share the templates; the guides change only for cartoon and 3D):
  - `likeness.v4` (portrait v5, sheet v10): a FACE SHAPE AND AGE block. Work like a portrait artist (the outline
    of the head, face, jaw and chin, and the features' places from the photo first, then the style); keep the
    width against the length, jaw, chin, cheek fullness, eye spacing, the eyes-to-mouth and mouth-to-chin
    distances, and how high the eyes sit; never rounder, wider, fuller-cheeked, shorter-chinned or with larger or
    lower eyes; the age as "looks exactly N: the face of an N-year-old, with his own chin, nose and proportions;
    never a toddler's or a baby's face, and never older" (no "toddler" for ages under 4).
  - **The measured proportion** (`qamra_ai.pipeline.face_shape`): the YuNet box the photo check already runs
    (local, MIT, no recognition), only on a face looking at the camera (one face, score ≥ 0.85, eyes level,
    nose between them), in coarse bands («an oval, clearly longer than it is wide: about 4 wide to 5 long
    (width to length 0.79)»), as "Measured on the photo: …". Kept on the character (`params.face_shape`) and
    removed with the likeness notes after 30 days for drawings never approved. YuNet's eye points follow a tilt
    only loosely, hence the coarse bands.
  - `likeness_notes.v2`: the face note gives proportions (longer than wide or not, widest where, the jaw, the
    chin's width and length below the lip, the forehead); "round", "soft", "full", "chubby" and "rounded" only
    when the photo shows it; eye size relative to the face.
  - Cartoon v4: crisp (not soft) cel shading; the simple shapes are the background's; people are "a
    cartoonist's portrait of a real child" on the photo's outline. 3D v4: "a stylized 3D likeness of a real
    child, as if the head were sculpted from the photo", the eyes at the photo's own size and shape, the hair
    its true colour; negatives against a round, wide, chubby face, puffy cheeks, a button nose, a short chin and
    big round animated-film eyes. v3 of both in `history/`; migration `4e1c9a7b2d63` keeps the rows' record.
  - A parent's "looked older" fix no longer asks for "a rounder face", only "a little younger, keeping the
    photo's own face shape".
  - Watercolor and semi-realistic keep their guides; they get the new templates (the FACE SHAPE block and the
    sheet's directions). Their pages, QA and every other prompt are byte-identical (golden snapshots).
- **The sheet's directions** (`character_sheet.v10`): every style, the same: 1) front view, facing the viewer;
  2) three-quarter view turned toward the viewer's left, waving; 3) side view in full profile facing the viewer's
  left, walking left: "the nose and eyes, the chest, the swinging arms, the knees and the toes of both shoes all
  point to the left". Left because an Arabic book reads right to left. Each figure whole down to both shoes,
  with space below the feet.
- **The automatic sheet check** (`qamra_ai.pipeline.sheet_check`, `sheet_check.v1`): after the sheet is drawn,
  the main text model (vision, about $0.01) says per figure where the head, the body and the feet point and
  whether both shoes are on and inside the picture; the code decides (left and right in one figure, mixed
  feet, a bare or cut shoe, not three figures). On a problem the sheet is drawn once more with the problems in
  the prompt and its own seed (`character:N:redraw`, +$0.15 on Nano Banana Pro, only then, its own cost row),
  checked again, and the better of the two is kept (the redraw on a tie). A failed check keeps the sheet; it
  never blocks the drawing. `params.sheet_check` keeps the outcome (`ok`, `redrawn`, `redrawn_flawed`,
  `kept_flawed`, `failed`, `off`) and the problems; the worker logs the outcome and counts. Setting:
  `CHARACTER_SHEET_CHECK` (on). The parent sees only the kept sheet. The fake text provider answers a good sheet.
- **Trial on the owner's photo, $1.50 of a $1.50 cap** (`face-shape:` ledger rows, 10 Nano Banana Pro calls;
  `scripts/face_shape_trial.py`; notes written by hand to the v2 rules, no Anthropic key here; one seed per
  cell, so a single picture carries seed noise). By eye, out of 10, and the measured width/length:

  | | live | A: notes v2 only | B: + likeness.v4 + measure | C: + guide v4 | D: + 3D eyes |
  |---|---|---|---|---|---|
  | cartoon portrait | 4, round and wide | 4, round, hair too dark | 4–5, still round | **6**: his long face, slim jaw and chin; chin a little too pointed, hair too golden, lost the smiling crescents | – |
  | 3D portrait | 5 (0.88) | – not 3D: it came out a photo (0.84) | 4–5, big eyes, young (0.87) | 5–6, longer face, big round eyes (0.83) | 5–6: his narrow smiling eyes and closed smile, but the cheeks wider again, freckles added (0.89); little better than live |

  Sheets (the directions of v10, without the shoe line merged in later): cartoon from C 5 (the face narrower and the head-to-body proportion of a 5-year-old, against the
  live sheet's big round head; hair tips and smiling eyes lost); 3D from D 5 (big round eyes came back, about
  4–5 years old); semi-realistic from the 10-19 portrait 6 (rounder, about 4). **Directions: 3 of 3 sheets
  right**: every figure's head, body and feet turned one way, the three-quarter and side views to the left, all
  shoes whole (the owner's sample: the side view's head right, its body left).
- **Verdict:** the face shape is better, not solved. In cartoon the portrait now has his long face and slim
  chin; in 3D the eyes (D) or the length (C) improve, never both in one picture, and D is little better than
  the live portrait; the sheet drifts part of the way back
  toward the genre's face. Semi-realistic remains the closest style. Next, if the owner wants more: two portrait
  candidates per drawing and a likeness pick by the text model (+$0.15), or the sheet painted at a larger face
  scale.
- **Language:** prompts only (English, for the image and text models); no text a parent reads changed.
