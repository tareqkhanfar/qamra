# End-to-end tests of the order path (Addendum 9 §3, order flows chunk 12)

`tests/e2e/` drives a real browser (Python Playwright, already a dependency) through the order path on a
390 px phone, in Arabic. No test draws anything or calls a paid API (see "No AI" below).

## What is covered

**`test_order_flows.py`: one flow per product** (docs/plans/order-flows.md §c), from the product or story page
to a confirmed cash-on-delivery order and, for a file, its download:

| Test | Flow |
| --- | --- |
| `test_islamic_v1_new_child` | «قلبي يعرف الله» V1, one tap → cart «أكملوا بيانات الطفل» → who → consent → photo → character (drawn in 3D, no style step) → review with «أنا مسلمة صغيرة» (5 steps, never a story step) → the same cart line, filled → a confirmed order |
| `test_islamic_set_known_child` | the set for a child with a ready character: «ابدؤوا كتاب طفلكم الآن» → who → review (2 steps) |
| `test_foundation_kg1_v2_english_name` | «دوسية التأسيس» KG1 V2: the child step asks the English name and checks both names («Luay» as the Arabic name is refused with the friendly message, «لؤي» is traced, an English name in Arabic letters is refused); the review and the cart show the level, the volume and «Luay» |
| `test_foundation_digital_set_download` | the KG2 set as PDF for a child with a ready character: who (asks the English name) → review (2 steps) → order → staff confirm with placeholder renders → the order page lists every volume's files and «تنزيل PDF» downloads the worker's home copy |
| `test_journey_stage_3_and_stage_1` | «رحلتي الأولى»: stage 3 asks the English name, stage 1 doesn't; the age note warns and never blocks |
| `test_family_one_tap_and_start` | «مغامراتي مع عائلتي»: one tap → who → family → review (3 steps); «تعديل» keeps the family; «ابدؤوا» and skipping the family step |
| `test_classic_story_from_its_page` | «قمرة كلاسيك» from its story page: who (no likes, no note) → consent → photo → character → story → writing → format → add-ons (8 steps; only add-ons that can be made, with their pictures) → cart |
| `test_magic_story_new_child` | «قمرة سحري» from `/create`: who → type → consent → photo → style (real sample pages) → character → companion → story (likes) → writing → review → format → add-ons (12 steps) |
| `test_only_active_add_ons` | the add-ons switched off by the owner and the black-and-white «دوسية التأسيس» are never offered: not in the catalog, not on the product page, not for any cart line |

**`test_one_tap_cart.py`:** a guest adds a story and every activity book in one tap each; every activity line
completes through its own product (`/create?product=<sku>`), never the story flow; a known child completes an
Islamic line with no story step.

**`test_order_path.py`:**

| Test | Flow |
| --- | --- |
| `test_classic_softcover_with_two_add_ons_to_a_cod_order` | preview → softcover → «الإضافات» with 2 add-ons → «السلة» → address + cash on delivery → order |
| `test_magic_hardcover_to_the_cart` | Magic preview → hardcover → add-ons step → cart (and the «شخصية … جاهزة» cross-sell) |
| `test_the_gift_toggle_and_card_message` | cart → «هذا الطلب هدية» + card message (kept by the server across a reload) → gift order |
| `test_a_sibling_bundle_with_a_coupon` | two children's books → «باقة الإخوة» → discount code → order with both discounts |
| `test_activity_lines_say_what_they_print_and_offer_their_add_ons` | an activity line shows its cover title, variant and English name; its add-ons are offered by cart line |

**`test_public_site.py`** is the launch site seen by an anonymous visitor (no fixtures, no orders, no AI; it
needs only a running site with the store seeded): every public page fits a 390 px phone and says nothing is
"coming soon"; the menu and footer are the launch structure (الحكايات · كتب الأنشطة · للروضات · الأسعار · كيف نعمل);
the home shows the four offers with prices; the activity-books hub lists the three books, each with a price and
an orderable page; the pricing page has every kind of price; the English site has the same structure.

**`test_qr_codes.py`** scans the printed QR codes (owner, 2026-10-09: every QR must work): a page is rendered
as it prints (a «رحلتي الأولى» sounds page and letter page; a story page with «أصوات العائلة»), its QR is read
from a screenshot with OpenCV, and the decoded `https://qamra.app/...` link is opened on the stack. The journey
codes show their item and play its reviewed clip; the story code says kindly that the family hasn't recorded
the page yet (a visitor gets a sign-in link, the owner «سجّلوا صوتكم لهذه الصفحة», which opens the recording
page at that page), and plays the owner's recording once it exists; the back cover's code opens page 1.

**`test_story_catalog.py`** (owner, 2026-10-09: every story on sale): `/stories` lists all eight stories, each
card saying what it is sold as («سحري فقط», or «كلاسيك وسحري» once a live Classic template exists), with the
Magic price for a story with no template, also on the Classic list; the «موسم الزيتون» page shows its art,
summary, values, ages and pages, explains «سحري فقط», keeps «قمرة كلاسيك» unavailable and adds the Magic book to
the cart in one tap; and the whole Magic flow from that page (child, consent, photo, character, story with the
likes, preview, format, add-ons) ends with «… في موسم الزيتون» in the cart.

**`test_photo_framing.py`** (owner 2026-10-10: drag the photo so the face fits the oval, on upload and after the
drawing): a far-away child is framed around the face on upload; «تعديل موضع الصورة» drags, zooms, turns and uses
the keyboard, «إلغاء» keeps the saved framing and «احفظوا الموضع» saves a new one; a photo with two children is
refused, then framed to one and accepted; after the drawing, «تعديل الصورة» opens the kept original after a
reload and saving returns to the character with its note; once the original is deleted
(`/api/e2e/photos/{id}/expire`, the 24-hour job at once) the editor says so and takes a new photo.

**`test_admin_studio.py`** (the template studio, owner 2026-10-09: «محرر الثيمات … مش شايفه شغال»): a staff user
(`/api/e2e/staff`: roles, two-step verification passed) edits a theme's page text (boy, girl, English) into a
draft, previews it, sends it for review, approves, publishes and rolls back; edits a Classic template drawn with
placeholder art (`/api/e2e/studio-templates`): the hero box, approve, publish, bulk actions; starts a new
template, which asks before spending and makes a free dry run; and checks the roles (an editor edits, an admin
is told why not). Each test fails on a script error, a 5xx, or a raw message key on the Arabic screen.

The shop → quiz flow of §3 is not covered here.

## No AI, no paid calls

The tests never draw anything. What a paid step would make comes from test-only fixtures, `/api/e2e/*`
(`apps/api/src/qamra_api/routers/e2e.py` and `e2e_qr.py`), all with placeholder art:
- for the QR codes: a journey item's reviewed clip from content/journey/clips (`/journey-audio/{code}`, as the
  server's loader stores it), and a book ordered with «أصوات العائلة» (`/books/{id}/family-voice`);
- a child with the guardian's consent, an approved character and a book at its preview;
- the character the flow asked for after the photo (`/characters/{id}/ready`; the parent then approves it in
  the flow), the story preview (`/books/{id}/preview`) and a live «قمرة كلاسيك» template (`/classic-templates`);
- the staff's order confirmation, with the activity books "rendered" as placeholder PDFs
  (`/orders/{code}/confirm`), so the parent's download can be tested;
- `/rate-limits/reset`: a whole run signs up and orders more from one address than the API allows in an hour,
  so each test first clears this machine's own counters.

Everything else is the real site and API: the steps, «الخطوة n من N», the cart, add-ons, codes, checkout, the
order page and the download.

The router is mounted only when **`E2E_FIXTURES=true`**, and the API refuses to start with it in prod.

## The worker: the `pdf` queue only, never `generation`

The order flows go through the real photo, drawing and story steps, and those steps still put jobs on the
worker's `generation` queue. The fixtures finish them with placeholders and take the jobs off the queue. A
worker that listens on `generation` would pick them up first and call the real image and text providers
(money, and a race with the fixtures). The parent's download, though, needs the `pdf` queue (the home copy).

So run the stack's worker on **`pdf` only**. The compose `worker` listens on `generation pdf maintenance
default`, so stop it and start a `pdf`-only one in its place:

```sh
docker compose stop worker
docker compose run -d --rm --name qamra-e2e-pdf worker sh -c 'exec rq worker --url "$REDIS_URL" pdf'
# after the run
docker stop qamra-e2e-pdf && docker compose start worker
```

## Run

1. A running stack whose API has `E2E_FIXTURES=true` (for docker compose, put it in `.env`; the app services
   read it), with the themes and the store seeded (`qamra seed-themes`, `qamra seed-store`; the `migrate`
   service does both on `up`).
2. The worker on the `pdf` queue only (above).
3. Chromium for Playwright, once: `uv run playwright install chromium`.
4. Point the tests at the site (the web app; it proxies `/api`):

   ```sh
   E2E_BASE_URL=http://localhost:3000 uv run pytest tests/e2e -p no:cacheprovider
   ```

   One file or one test: `uv run pytest tests/e2e/test_order_flows.py -k islamic -p no:cacheprovider`.

Each test signs up a new parent (`e2e-…@example.com`), so they can run again on the same database. They
create orders, coupons and gift cards there: use a development or test database, **never production**, and
never a server where `E2E_FIXTURES` could be left on.

When the dev server is opened as `127.0.0.1`, Next.js blocks its dev resources for that origin: use
`localhost` in `E2E_BASE_URL`.
