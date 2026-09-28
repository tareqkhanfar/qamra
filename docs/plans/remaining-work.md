# Remaining work — the master checklist

Tareq, 2026-09-28: «انهي كافة التعديلات، ما تنسى شيء». Everything still open across the build prompt and Addenda 1–7, in one place. Each item names who owns it: a parallel workstream (W1–W9) or the lead (me). An item is ticked only when it is built, tested, committed and, where it runs on the server, deployed.

Items marked **external** need something only Tareq or a third party can provide. The code for them is still built as far as it can go, and each one says what is missing.

## Already done and verified live (2026-09-28)
- [x] Create flow on a phone against the test server: child → consent → photo check → Classic/Magic → style → real character drawing → story → format → cart → COD checkout (order QM-FN9UW4) → «حذف بيانات الطفل».
- [x] Full test suite green against the test database: 760 API/core/worker tests and 455 workbook tests.
- [x] Addendum 4 steps 1, 5 and 6; Addendum 7 proposal and printer-price admin; Addenda 5–6 decisions applied; letter tracing paths; educator PDFs.

## Addendum 4 — store, lines, studio
- [ ] **W1 · Step 3, the Classic pipeline**
  - template tables;
  - template generation for 1 theme × watercolor × 3 variants (girl, girl with hijab, boy);
  - hero boxes and the identity portrait;
  - crop, klein 4B edit and paste back;
  - Haiku QA (likeness, seams, text);
  - cost logging and a 2₪ budget guard;
  - Classic text filling;
  - the proof on 5 synthetic children, with sample PDFs and the measured cost.
- [ ] **W2 · Step 4, the template studio** (after W1's tables):
  - theme versions (draft → in review → approved → live) with history and rollback;
  - the page list per theme × style × variant;
  - the RTL page editor (text box, font size, m/f/en texts, live preview);
  - template generation per page with locking;
  - bulk actions (duplicate to a style, translate, publish, schedule);
  - staff roles in the UI and the audit log viewer.
- [ ] **W3 · Create flow extras**
  - the «ارسم صاحبك» drawing-companion step for parents;
  - the Magic custom-story builder (product `magic-custom-story`).
- [ ] **W4 · B2B price lists** in the catalog admin (tiers per variant, per organization).
- [ ] **Lead · Step 7**: `docs/feature-matrix.md` and Playwright E2E tests for the four purchases the addendum names:
  - Classic softcover + 2 extras;
  - Magic hardcover with a custom story;
  - a sibling bundle with a coupon;
  - a B2B Classic class book on a price list.
- [ ] **External:** Addendum 2 («قواعد تدقيق الإنتاج», the feature matrix) is not in the repo. Until Tareq sends it, the matrix is written from the addenda.

## Build prompt phases
- [ ] **W5 · Phase 2 remainder**
  - the web reader (page flip, RTL) and share links;
  - email notifications (SMTP adapter; order placed, status changes, preview ready, book ready);
  - the card-payment gateway stub behind `PaymentProvider`.
- [ ] **W5 · Phase 3 remainder:** print batches in the admin (collect approved printed books, the bundle PDF, the printer email with links, statuses).
- [ ] **W4 · Phase 4, the kindergarten portal**
  - organization sign-up with admin approval;
  - classrooms;
  - children imported from Excel/CSV;
  - a per-parent invite link (consent and photo by the parent);
  - one theme per class;
  - the class photo, teacher message and school logo page;
  - «كتاب الصف» with per-child slots;
  - batch generation with progress and bulk approval;
  - wholesale pricing on price lists;
  - one invoice, and delivery to the school;
  - the teacher's status board.
- [ ] **W6 · Phase 5**
  - «صوت أهلي»: recordings, a QR per page, a remote elder link, the TTS fallback adapter;
  - gift cards;
  - the WhatsApp adapter interface (the Twilio adapter stays off until approved);
  - SEO pages per theme;
  - a performance pass.
- [ ] **W6 · Phase 6, production-ready without touching production**
  - the production compose/stack file;
  - Nginx and Cloudflare notes;
  - backups (Postgres and object storage) with a restore test on the test server;
  - monitoring and alerts;
  - runbooks.
  - **External:** a production server and domain.

## Activity books
- [ ] **W7 · «مغامراتي مع عائلتي», the full book**
  - adventures 3–12, and the front and back pages;
  - every page type in the plan;
  - the card-stock sheets complete (money and price tags, recipe step cards, game and role cards, finger puppets);
  - the sticker sheet;
  - die lines on a separate layer;
  - the complete 112-page PDF at both sizes, with preflight.
- [ ] **W4 · Family book in the store:** the «طلب عرض سعر» form for organizations (logo on the back cover), and the illustrated-family-characters extra (same pipeline and privacy rules as the child).
- [ ] **W8 · «دوسية التأسيس» KG2 volume 1 in full** (the addendum's order: KG2 first)
  - every page type it uses;
  - the pictures for its words;
  - the tracing pages on the new letter paths (more room below the line for tails);
  - the pen-check page;
  - the full PDF and answer key, with preflight;
  - then volumes 2 and 3 and KG1 as the plan allows.
- [ ] **W9 · «رحلتي الأولى للتعلّم» stage 1 in full**, the audio QR system (links per letter or word, a player page, audio stored privately), then stages 2 and 3.
- [ ] **W4 · Activity books in the store:** product pages for the three books, the «أي كتاب يناسب طفلي؟» helper (age, holds a pen, knows letters, goal: school skills or family time), personalization and B2B term scheduling.
- [ ] **External:**
  - the educator's review and signature (plans, words, letter shapes);
  - the printer's templates and quotes;
  - physical proofs tested with children and families.

## Housekeeping (lead)
- [ ] Deploy every finished workstream to the test server and walk it on a phone.
- [ ] README, CHANGELOG, `docs/decisions.md` and `docs/security.md` updated.
- [ ] Deactivate the temporary `ops-bot` admin account on the test server at the very end.

## Paid services waiting for Tareq's approval (not switched on)
- Automatic WhatsApp or SMS sending, and phone-number sign-in (Twilio or the WhatsApp Business API).
- A card-payment gateway.
- A TTS provider for audio narration and letter sounds: the adapter is built, the provider is chosen in the admin.
