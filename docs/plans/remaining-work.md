# Remaining work — the master checklist

Tareq, 2026-09-28: «انهي كافة التعديلات، ما تنسى شيء». Everything open across the build prompt and Addenda 1–9, in one place. An item is ticked only when it is built, tested, committed and, where it runs on the server, deployed to the test server.

Items marked **external** need something only Tareq or a third party can provide. The code for them is built as far as it can go, and each one says what is missing.

**State on 2026-09-30:** every workstream below is done except the activity-book volumes still to write (KG2 volume 3, KG1, journey stages 2–3). What remains is external. `docs/feature-matrix.md` shows the same per product.

## Addendum 4 — store, lines, studio
- [x] **W1 · Step 3, the Classic pipeline** (2026-09-29): templates per story × style × look, hero boxes, the identity portrait, the klein edit, QA, the 2₪ guard, vowelized texts. Live on the test server: first day and graduation for girl / girl with hijab / boy, new sibling for a girl (7 templates from the example books).
  - **External:** the real cost proof on 5 invented children (`scripts/classic_proof.py proof`) needs fal.ai balance (about $3); it ran with fakes only.
- [x] **W2 · Step 4, the template studio** (2026-09-29): theme versions with history and rollback, the page editor (hero box, texts with a live preview), bulk actions and scheduling, staff roles, the audit-log viewer.
- [x] **W3 · Create flow extras** (2026-09-29): «ارسم صاحبك» and the custom story. Open: Classic templates don't draw the companion yet, so the add-on is Magic-only.
- [x] **W4 · B2B price lists** in the catalog admin (2026-09-29, with the portal).
- [x] **Lead · Step 7** (2026-09-30): `docs/feature-matrix.md`; Playwright E2E for Classic softcover + 2 add-ons → COD, Magic hardcover → cart, the gift toggle and the sibling bundle with a coupon (`tests/e2e/`). Not covered by E2E: a Magic hardcover *with a custom story* and a B2B class book on a price list (both covered by API tests).
- [ ] **External:** Addendum 2 («قواعد تدقيق الإنتاج», the feature matrix) and Addendum 8 are not in the repo; the matrix is written from the addenda.

## Build prompt phases
- [x] **W5 · Phase 2 remainder** (2026-09-29): the reader and share links, email notifications, the card-gateway stub.
  - **External:** an SMTP account entered in Admin → الإعدادات; until then emails are only logged.
- [x] **W5 · Phase 3 remainder** (2026-09-29): print batches with the printer's links and CSV, now also the family book's inserts.
  - **External:** the printer's email (`printer_email`) and confirmation that 10-minute links work for them.
- [x] **W4 · Phase 4, the kindergarten portal** (2026-09-29): sign-up with approval, classes, CSV import, invite links, «كتاب الصف» drawn in one batch with bulk approval, one order and invoice, the print bundle (a class of 30 tested with fakes). Open: Classic class books still use generic children for the shared pages; `.xlsx` import (CSV works).
- [x] **W6 · Phase 5** (2026-09-29): «صوت أهلي», the WhatsApp interface (nothing is sent), SEO per story, sitemap and robots, a performance pass (`docs/plans/phase-5.md`).
- [x] **Lead · Phase 6** (2026-09-28): the production overlay, encrypted backups with a restore drill, monitoring, runbooks.
  - **External:** a production server, a domain, an R2 bucket and an alert webhook.

## Activity books
- [x] **W7 · «مغامراتي مع عائلتي», the full book** (2026-09-29): 112 pages at both sizes, the covers, the inserts with die lines, preflight; rendered per order from the child's character.
- [x] **W4 · Family book in the store** (2026-09-30): the family details form, «طلب عرض سعر» for organizations with the logo on the back cover, the illustrated-family add-on (off until Tareq switches `family_characters_enabled` on).
- [x] **W8 · «دوسية التأسيس» KG2 volumes 1 and 2** (2026-09-30): 128 + 124 pages with answer keys, preflight, the tracing on the letter paths, the pen-check page.
  - [ ] Volume 3 (vowels, syllables, reading, sentences, adding and subtracting, the certificate, ~96 pictures) and KG1.
- [x] **W9 · «رحلتي الأولى للتعلّم» stage 1** with the audio QR system (2026-09-30).
  - [ ] Stages 2 and 3 (they need single-stroke paths for every letter and form, and the educator's sign-off on the letter shapes first).
- [x] **W4 · Activity books in the store** (2026-09-29): product pages for the three books with real preview pages, the quiz «أي كتاب يناسب طفلي؟», personalization with the child's character; the educational books stay «قريبًا» (an admin switch) until the educator signs.
- [ ] **External:**
  - the educator's review and signature (plans, words, letter shapes, every text marked `# draft: educator review`);
  - the printer's templates and quotes (the family book's kit is 5 card-stock sheets in 2 files; the die line is RGB magenta, not a spot colour, until the printer asks otherwise);
  - physical proofs tested with children and families;
  - recordings for the journey's audio items (or a paid TTS provider).

## Addendum 10 — «قلبي يعرف الله»: the Islamic education series
Order of work from the addendum (§11). Nothing religious is final before the scholar's sign-off, and nothing prints or sells before it.
- [x] **Step 1 · The proposal package** (2026-10-01): `docs/islamic/proposal.md` and its PDF (`scripts/islamic_proposal.py --pdf`) from `content/islamic/` (plan, units, concepts, volumes, sources, proposal-text). 5 volumes + a seasonal Ramadan and Eid book, 639 pages; the retention matrix is computed from the plan (every concept reaches ≥ 5 of 6 forms); 192 planned references in the source register; 12 designed sample pages; price tiers marked ⚠ until the printer's quote (`docs/islamic/printer-quote-request.md`).
- [ ] **STOP: Tareq's approval and decisions** (name, split, Ramadan-first, scholar, the Tanzil file, binding and size, prices): `docs/islamic/proposal.md` §11.
- [ ] **Step 2 · `sources.yaml` and the scholar's review of the list:** fetch candidates (`scripts/islamic_sources.py fetch`), diff the Quran against the official Tanzil file (Tareq must place it in `content/islamic/quran/`), send `out/islamic/sources-for-scholar.pdf`.
- [ ] **Step 3 · Page types and build checks:** the sample pages' types exist; the remaining types of §7 (`prayer-steps`, `my-day-with-allah`, `pillar-card`, `true-false`, `unit-closing`, `final-assessment`), the source-id, no-depiction and no-sacred-text-on-disposable-pages checks in the print build.
- [ ] **Step 4 · Seasonal book first (live by ~28 Dec 2026), then volume 1:** content → scholar review page by page → physical proof (scholar + 2–3 families).
- [ ] **Step 5 · Store product and personalization** (line «قلبي يعرف الله», variants, add-ons, the quiz goal «تعليم ديني»).
- [ ] **Step 6 · Volumes 2–5.**
- [ ] **External:** the scholar (name, availability, review format), the Quran source file, a licensed reciter, the printer's quote and templates.

## Housekeeping (lead)
- [x] Every workstream deployed to the test server (2026-09-30).
- [x] README, CHANGELOG, `docs/decisions.md`, `docs/security.md` and `docs/feature-matrix.md` updated (2026-09-30).
- [x] The temporary `ops-bot` admin account deactivated at hand-over (2026-09-30).

## Paid services waiting for Tareq's approval (not switched on)
- Automatic WhatsApp or SMS sending, and phone-number sign-in (Twilio or the WhatsApp Business API).
- A card-payment gateway.
- A TTS provider for audio narration and letter sounds: the adapter is built, the provider is chosen in the admin.
- fal.ai balance: the example books used $14; the last two example books (new sibling with hijab and boy), the Classic cost proof and the free cover's first real run need about $5–8 more.
