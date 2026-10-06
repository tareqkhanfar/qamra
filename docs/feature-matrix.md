# Feature matrix

What each product line does today, and what is still open.

Written from the addenda, because Addendum 2 (the original matrix) is not in the repo. Updated 2026-09-30.

**Status:**
- ✅ built, tested and deployed to the test server;
- 🟡 built, but waiting on something outside the code (named in the row);
- ⬜ not started.

## Story books

| Feature | «قمرة كلاسيك» | «قمرة سحري» | Status |
|---|---|---|---|
| How pages are made | a ready illustrated template per story × style × look; only the hero is edited to the child (FLUX.2 klein 4B) | every page drawn for the child from the character sheet, with automatic checks | ✅ |
| Child's name, gender forms, full تشكيل | template text, vowelized once per story and gender | Claude adapts and vowelizes per book | ✅ |
| Looks | girl, girl with hijab, boy (a template for each) | any, from the photo | ✅ |
| Art styles | only where a live template exists (today: first day and graduation for all three looks, new sibling for a girl, all watercolor) | watercolor, cartoon, 3D, semi-realistic, coloring | 🟡 more templates need fal.ai balance (about $2 per example book) |
| Character from a photo, reused by every book and product | ✅ | ✅ | ✅ |
| Companion from the child's drawing («ارسم صاحبك») | not yet: templates don't draw it, so the add-on is Magic-only | included | ✅ (Magic) |
| Custom story («حكاية خاصة», product `magic-custom-story`) | — | brief → safety screen → Claude writes it | ✅ |
| Free watermarked preview before paying | cover + 2 hero pages | cover + first pages | ✅ |
| Text edits per page, dedication page | ✅ | ✅ | ✅ |
| Formats | digital 19 ₪, softcover 69 ₪, hardcover 99 ₪ | hardcover 139 ₪ | ✅ |
| Add-ons after the preview, with dependencies | ✅ | ✅ | ✅ |
| «أصوات العائلة» («صوت أهلي»): recordings, a grandparent link, a QR per page in print | ✅ | ✅ | ✅ (TTS fallback off: paid) |
| Reader, share link (7/30/90 days) | ✅ | ✅ | ✅ |
| Print PDF + cover with preflight, admin approval, print batches | ✅ | ✅ | ✅ |
| AI cost per order | ≤ 2₪ (guarded) | ≤ $2.50 (measured $1.49–2.01 on 9 example books) | 🟡 Classic measured with fakes; the real proof needs fal balance |
| Free cover («شوف غلاف طفلك») | from the Classic cover template, ≈ $0.012 | — | 🟡 built and deployed, off (`free_cover`) until fal works |
| Public examples on the site with a flip-through | 8 example books of invented children published | | ✅ |

## Store and ordering (Addendum 9)

| Feature | Status |
|---|---|
| Shop hub, story page with real examples and a live price, quiz with admin rules | ✅ |
| Cart: several items, add-on lines, «الكتاب الثاني −15%» as an admin rule, coupon or gift card, gift toggle + card message, packing slip without prices | ✅ |
| Cash on delivery only; card gateway is a disabled stub | ✅ |
| Email notifications (order, status, preview ready, book ready) | 🟡 needs an SMTP account in the admin; until then logged |
| WhatsApp / SMS | ⬜ interface only, waiting for Tareq's approval (paid) |
| Coupons, sales, bundles, zones, prices, print costs, reports, margins, gift cards: admin | ✅ |
| SEO per story, sitemap, robots, Open Graph from the example cover | ✅ |
| E2E (Playwright): Classic softcover + 2 add-ons → COD order; Magic hardcover → cart; gift toggle; sibling bundle + coupon | ✅ |

## Kindergartens (B2B)

| Feature | Status |
|---|---|
| Sign-up with approval, classes, CSV import, parent invite links, status board | ✅ |
| «كتاب الصف»: plan, batch with likeness checks, bulk approval, one order and invoice, print bundle | ✅ (a class of 30 tested with fakes) |
| B2B price lists per school (tiers per variant) | ✅ |
| Classic class books from Classic templates | ⬜ (generic children on the shared pages today) |
| Excel `.xlsx` import | ⬜ (CSV works; needs `openpyxl`, MIT) |
| Quote requests for many family books, with the school's logo on the back cover | ✅ (a request; 10+ copies are priced only once real printer prices exist) |

## Activity books

| Book | Pages | In the store | Status |
|---|---|---|---|
| «مغامراتي مع عائلتي» | 112 at 21×28 and A4, covers, stickers and 5 card-stock sheets with die lines; rendered per order with the child's character and the family's names; the illustrated-family add-on (off) | orderable (single copies; 10+ by quote) | ✅; 🟡 the printer's templates and real prices |
| «رحلتي الأولى للتعلّم» | stage 1: 118 pages, cover, answer key, audio QR per letter or word; rendered per order | page + «قريبًا» | ✅ stage 1; ⬜ stages 2–3; 🟡 the educator, the recordings |
| «دوسية التأسيس» | KG2 volumes 1 (128) and 2 (124) with answer keys, the pen check, tracing on our letter paths | page + «قريبًا» | ✅ v1–2; ⬜ v3 and KG1; 🟡 the educator's sign-off |
| AI per order | cover and guide character from the child's approved character; name tracing by code | — | ✅ ≈ 0 |

## Admin and operations

| Feature | Status |
|---|---|
| Approval queue with page redraw, text review and edit of every story before «تأكيد» (history, re-render, alert email), cost per line, settings, staff 2FA | ✅ |
| Template studio: theme versions, page editor, bulk actions, scheduling; staff roles; audit-log viewer | ✅ |
| Classic templates: sample → template, hero boxes, vowelized texts, publish | ✅ |
| Organizations, leads and quotes, journey audio uploads, print batches, gift cards | ✅ |
| Backups, restore drill, monitoring, runbooks, production overlay | ✅ on the test server; 🟡 production needs a server, a domain, R2 and an alert webhook |
