# Changelog

## Activity-book covers redesigned: a scene per part, the child among its letters, a back that shows the book (2026-10-09)
- **Why:** Tareq: the covers of the four activity series looked plain («موضوع الغلاف لكل دوسية صراحة مش عاجبني»): flat navy or cream backgrounds, a small title, the character alone, a thin back. He asked for covers that look professional and show what is inside, with the child on both sides.
- **Scenes:** one illustrated scene per part (16: «دوسية التأسيس» KG1/KG2 × 3 volumes, «رحلتي الأولى» stages 1–3, «مغامراتي مع عائلتي», «قلبي يعرف الله» V1–V5 and R), in one 3D house style that matches the children's characters, with no text and no people. Drawn on fal with Nano Banana Pro, reviewed at full size (4 redrawn for a seam, writing-like marks or an inset panel): 22 calls, **$3.30** of the $5.50 cap. Installed in `content/covers/scenes/`. Plan, prompts and commands: `docs/plans/cover-scenes.md`, `scripts/cover_scenes.py`. A part without its scene falls back to the older plate (`content/assets/G*`, `F5`–`F10`).
- **Front:** the scene runs into the bleed; the series title as sticker letters (one color per word, a white keyline, a dark outline, a toy-block extrusion) on the series' panel (a spiral-notebook page, a trail sign, a house, a pointed arch); the level, volume or stage pills; the child's name on a ribbon («دوسية ليان», «رحلة ليان», the family's name, the child's name); the age chip; the child large in the scene's lit spot (the family book: the child in the middle of the family); toy blocks of the part's own letters, numbers or shapes (أ ب ت · ١ ٢ ٣ …); three info badges (the page count with its agreement, what it teaches, «باسم ليان وشخصيتها»).
- **Back:** a band of the same scene with the child waving, the title and pills, a short blurb for parents, «في هذا الجزء» (from the part's real content; the Islamic units with their icons), three real pages of the volume (rendered from the interior that was just printed; Islamic: only pages that never carry sacred text), «يأتي مع الكتاب» (only what the book holds), the ages, page count and binding, qamra.app and «صُنعت خصيصًا لـ…». The Islamic back keeps the series list and the care note, and no reviewer line.
- **Spine:** the Islamic volumes are perfect-bound, so their cover is now one wrap [front | spine | back] with the spine sized from the page count (`covers.spine_mm`: V1 7.8 mm, R 4.9 mm with the moon only); the other series are spiral or wire-o and keep front and back as two pages.
- **Print:** every scene and page picture at 300 DPI at its printed size, every letter vector (outlines are filled copies), text in the safe area or ≥ 7 mm from the hinge; all 16 covers pass the preflight. Long names shrink on the ribbon, and an overfull back drops its optional pieces in a fixed order instead of failing an order (tested with «محمد عبد الرحمن», a six-member family and a kindergarten logo).
- **Same contract:** `render_order`, `render_volume`, `--cover` and the job outputs are unchanged; `covers.with_thumbs` is called between the interior and the cover. The web previews were re-exported (`scripts/export_workbook_previews.py`, which now shows the front panel of a wrap).
- **Language:** a separate review of every cover string for a girl and a boy. Errors fixed: «تدرّب ليان يدها», the family's passport, certificate and badges line in the girl's gender, «مُغامَراتُ ليان مَعَ عائِلَتِها» (cover and title page; it mixed «مغامرات ليان» with «عائلتي»), «أقرأ وأكتب وأحلّ». The suggested improvements are applied (wording, one style per row, vowelized Islamic facts, «خِصِّيصًا», «في هذه المحطة», parent-facing blurbs for the Islamic volumes), except three older strings left for the owner: «(التمهيدي)» in the KG2 pill, «وَأَرْقامي» in the KG2 V1 subtitle, and «الشّيفُ الصَّغيرَةُ» in the family book's sections.
- **Code:** `qamra_workbook.render.covers` (scenes, lettering, panels, blocks, thumbnails, spine, the shared front/back data), `templates/_cover.html.j2` and `_cover.css.j2`, the four series' cover builders, `content/covers/covers.yaml` (every word the covers add). Tests: `packages/workbook/tests/test_covers.py`.


## Activity-book covers redesigned: a scene per part, the child among its letters, a back that shows the book (2026-10-09)
- **Why:** Tareq: the covers of the four activity series looked plain («موضوع الغلاف لكل دوسية صراحة مش عاجبني»): flat navy or cream backgrounds, a small title, the character alone, a thin back. He asked for covers that look professional and show what is inside, with the child on both sides.
- **Scenes:** one illustrated scene per part (16: «دوسية التأسيس» KG1/KG2 × 3 volumes, «رحلتي الأولى» stages 1–3, «مغامراتي مع عائلتي», «قلبي يعرف الله» V1–V5 and R), in one 3D house style that matches the children's characters, with no text and no people. Drawn on fal with Nano Banana Pro, reviewed at full size (4 redrawn for a seam, writing-like marks or an inset panel): 22 calls, **$3.30** of the $5.50 cap. Installed in `content/covers/scenes/`. Plan, prompts and commands: `docs/plans/cover-scenes.md`, `scripts/cover_scenes.py`. A part without its scene falls back to the older plate (`content/assets/G*`, `F5`–`F10`).
- **Front:** the scene runs into the bleed; the series title as sticker letters (one color per word, a white keyline, a dark outline, a toy-block extrusion) on the series' panel (a spiral-notebook page, a trail sign, a house, a pointed arch); the level, volume or stage pills; the child's name on a ribbon («دوسية ليان», «رحلة ليان», the family's name, the child's name); the age chip; the child large in the scene's lit spot (the family book: the child in the middle of the family); toy blocks of the part's own letters, numbers or shapes (أ ب ت · ١ ٢ ٣ …); three info badges (the page count with its agreement, what it teaches, «باسم ليان وشخصيتها»).
- **Back:** a band of the same scene with the child waving, the title and pills, a short blurb for parents, «في هذا الجزء» (from the part's real content; the Islamic units with their icons), three real pages of the volume (rendered from the interior that was just printed; Islamic: only pages that never carry sacred text), «يأتي مع الكتاب» (only what the book holds), the ages, page count and binding, qamra.app and «صُنعت خصيصًا لـ…». The Islamic back keeps the series list and the care note, and no reviewer line.
- **Spine:** the Islamic volumes are perfect-bound, so their cover is now one wrap [front | spine | back] with the spine sized from the page count (`covers.spine_mm`: V1 7.8 mm, R 4.9 mm with the moon only); the other series are spiral or wire-o and keep front and back as two pages.
- **Print:** every scene and page picture at 300 DPI at its printed size, every letter vector (outlines are filled copies), text in the safe area or ≥ 7 mm from the hinge; all 16 covers pass the preflight. Long names shrink on the ribbon, and an overfull back drops its optional pieces in a fixed order instead of failing an order (tested with «محمد عبد الرحمن», a six-member family and a kindergarten logo).
- **Same contract:** `render_order`, `render_volume`, `--cover` and the job outputs are unchanged; `covers.with_thumbs` is called between the interior and the cover. The web previews were re-exported (`scripts/export_workbook_previews.py`, which now shows the front panel of a wrap).
- **Language:** a separate review of every cover string for a girl and a boy. Errors fixed: «تدرّب ليان يدها», the family's passport, certificate and badges line in the girl's gender, «مُغامَراتُ ليان مَعَ عائِلَتِها» (cover and title page; it mixed «مغامرات ليان» with «عائلتي»), «أقرأ وأكتب وأحلّ». The suggested improvements are applied (wording, one style per row, vowelized Islamic facts, «خِصِّيصًا», «في هذه المحطة», parent-facing blurbs for the Islamic volumes), except three older strings left for the owner: «(التمهيدي)» in the KG2 pill, «وَأَرْقامي» in the KG2 V1 subtitle, and «الشّيفُ الصَّغيرَةُ» in the family book's sections.
- **Code:** `qamra_workbook.render.covers` (scenes, lettering, panels, blocks, thumbnails, spine, the shared front/back data), `templates/_cover.html.j2` and `_cover.css.j2`, the four series' cover builders, `content/covers/covers.yaml` (every word the covers add). Tests: `packages/workbook/tests/test_covers.py`.

## Story covers redesigned: front, back and spine (2026-10-09)
- **Why:** Tareq found the covers not professional enough and asked for the same polish on the stories as on the activity books. Audit of the old wraps: the title was one tone (the name lost in it) under a fixed dark band, the ribbon sat on the child's hair on taller heroes, there was no product line on the front, the back was a muddy blurred tint holding only a small portrait and one paragraph (two thirds empty), the spine was a thin strip in an unrelated color, and the class-book cover was plain text on a gradient.
- **Front:** poster lettering in code: the child's name in its own gradient and larger («يوم تخرّج **ليان**», or the name on its own leading line for longer titles), extruded 3D letters, a soft wash of the art's own tone behind the title that adapts to light/dark and busy art, a title block sized to where the scene begins, the ribbon tucked under it, and a series pill «قمرة | سحري / كلاسيك / حكاية خاصّة / كتاب الصفّ». Display lettering uses light tashkeel (shadda kept, «الله», «بالروضة»). New texts language-reviewed; fixes applied.
- **Back:** the art continued under a tint of its own palette (dark or light), the title, the story's blurb, three pages from the book as photo prints, fact chips (the theme's ages, the page count, «الحكاية مشكّلة بالكامل» only when every page is), «نُسْخَةٌ خاصَّةٌ بِـ…», the child waving (cut out of the approved character sheet, never under 300 DPI) with the companion in front of a moon disc, the logo and domain, and a reserved barcode area. The QR card stays family-voice only.
- **Spine:** the art's deep tone, the title with the name in gold, the brand and moon at the tail (type only from 6 mm).
- **Class books** use the same design with the class words, the gendered ribbon, the school, year and logo, and the theme's lettering and ages.
- **Code:** `qamra_pdf.cover` (art reading, `CoverDesign`), `lettering` (poster lines, two-tone, extrusion, display text), `assets` (hero cut-out, thumbnails), `strings.page_count`; `BookSpec.series/age_range`, `CoverSpec.hero`, `BookPlan.age_range`, `AssemblyInputs.series`, `ChildCopy.gender`, `ClassBookSpec.title_style/age_range` (all optional). Tests: poster lines, display text, page-count agreement, art reading, back-cover facts and figure with preflight, portrait fallback, thumbnails, spine, English wrap, class covers, the worker's series and class theme. Decisions in `docs/decisions.md`; before/after sheets in `out/cover-redesign/`.

## The order-flow overhaul: one flow per product, from the product page to the download (2026-10-07 → 2026-10-08)
Summary of the work planned in `docs/plans/order-flows.md` (Tareq, 2026-10-07: an Islamic-series line fell into the story flow and asked for a story, likes and Classic or Magic). The entries below and the plan's «as built» sections have the details.
- **One flow per product** (`web/lib/flows.ts`, unit-tested with `npm test`): an activity book is who → [consent → photo → character, drawn in 3D with no style question] → [family] → review; a story is who → [type] → [consent → photo → style → character → companion] → story → writing → [review] → format → add-ons. «الخطوة n من N» counts this product's steps for this child. Activity books never see the story type, style, companion or story steps; one list of activity lines (`ACTIVITY_LINES`) everywhere.
- **Ask only what is printed, and say why:** the child step per product (the name as printed, the English name only where the book traces it, the age checked against the variant without blocking), a known child as a card that can be corrected (`PATCH /children/{id}`), Magic's likes moved to the story step, the family step for «مغامراتي مع عائلتي» (moved off the product page), and a review of what will be printed before the cart.
- **Cart, checkout and order page** say what each line prints (`web/lib/variantSummary.ts`: «دوسية ضحى» · «KG2 · الجزء الأول · ملوّن · مطبوع» · the English name · the family), what a waiting line still needs, and offer each line its own add-ons. The checkout header is «الخطوة الأخيرة: العنوان والدفع».
- **API** (migration `18342eeba4e4`): `GET /api/shop/workbooks/needs`, the cart takes the character and the English name with friendly refusals, `children.name_latin`, delete-my-data also clears the family, English name and character on order lines.
- **Showcase pages:** every activity-book part shows its real cover, ten real pages and what it teaches (`showcase/copy.json`); the story pages show real pages in every art style and Classic vs Magic side by side; «يأتي مع الكتاب» and the add-ons show pictures of the real printed things (`web/lib/addonsMedia.ts`).
- **Add-ons audit:** every add-on traced from the cart to what is made. Switched off (inactive, not deleted): the three physical extras with no stock and every add-on nothing can produce yet (12 in all, `editable-files` was already off), and the black-and-white «دوسية التأسيس». The answer key reaches the printer only when bought, with its label and honest texts.
- **Sticker sheets:** every «رحلتي الأولى» stage and every «قلبي يعرف الله» volume now ships with its own A4 sheet, made for the child (entry below).
- **«دوسية التأسيس» per order:** a new job (`jobs/workbook_book.py`) renders each ordered volume for the child (name, gender, character, English spelling, digits ١٢٣) with a new cover and the answer key, each preflighted; confirm and admin retry enqueue it.
- **Name rules** (`qamra_workbook.names`): one light module the API calls at order time; the «اسمي» page traces ؤ and ئ, compound and long names by whole parts, never crashes on a name (a Latin name prints as a model, the book is flagged); the English name is the parent's spelling, a transliteration only as a flagged last resort; the family city is optional («مَدينَتِنا»).
- **Digital downloads:** parents download the PDFs they bought from the order page and their account, with an email when ready (entry below).
- **Tests:** `tests/e2e/test_order_flows.py`, a browser test per product to a confirmed order and the download, with no AI (`docs/e2e.md`: the worker runs on the `pdf` queue only).
- **Language (chunk 13):** a final strict review of every customer-facing string of these two days as one whole (the create, order, download, showcase, story-showcase, workbook, theme and shop messages; the product-page details; the add-on and sample pictures' texts; the download email, errors and file labels), plus a second check of the result. 49 strings changed: terminology 21 («سنوات» not «سنين»; «تنزيل» for downloads; «جواز المسلم الصغير» for the Islamic passport; «رفيق من رسمته» for the drawn companion; «كتب الأنشطة», not «دوسيات», for the category), consistency 15 (the «دوسية التأسيس» owner page is a hand to trace around, not a handprint; English twins), punctuation 8 (English apostrophes), grammar 2 (Arabic plurals of weeks and volumes), gender 2, spelling 1. The house terms are in `docs/decisions.md`; the colloquial lines from the Addendum 9 design are left for Tareq.

## «رحلتي الأولى» and «قلبي يعرف الله» come with their own sticker sheet (2026-10-08)
- **Why:** the journey map and openers and the Islamic passports ask the child to stick stickers, and stage 1's back cover promises «ملصقات», but no sticker sheet was printed or shipped (the add-ons audit).
- **The sheets:** one A4 sheet of matte sticker paper with kiss-cut lines per journey stage and per Islamic volume (V1–V5, R), read from the very pages being printed: the hero for the map, a sticker for every opener circle, the train's pictures and the pattern shapes (journey: 25–28 stickers); a unit stamp for every circle of both passport pages and stars or leaves for the home boards (Islamic: 6–30); then rewards (stars, Qamra's moon, «أحسنتَ/أحسنتِ», the child's name). Each covers its spot (15 mm over a 13 mm circle; 30.8 / 34.4 mm stamps over 29.1 / 32.8 mm rings). The Islamic sheet has no person, no sacred words (checked) and no series title on its backing.
- **Engine:** `qamra_workbook.render.stickers` (and the `reward-stickers` page type): `inserts/stickers.pdf` with its cut lines on the «CutContour» layer, `inserts/stickers-die.pdf`, and a preflight; `journey_order.render_order` and `islamic_volume.render_volume` render it. Staff CLI: `uv run python -m qamra_workbook.render.stickers --journey 1` / `--islamic v1`.
- **Orders:** the journey and Islamic jobs store it as `generation["files"]["stickers"]` (the die beside it): the print batch sends it with every printed copy as «ورقة الملصقات», the admin book detail lists and downloads it, and a digital copy's downloads include it to print at home.
- **Site:** «ورقة ملصقات» with a real picture of the rendered sheet under «يأتي مع الكتاب» for the journey and the Islamic series; the journey map's and the passport's lines say what is stuck on them. Language-reviewed (Arabic and English); all fixes applied.

## Digital delivery: parents download the PDFs they bought (2026-10-08)
- **Why:** the store sold «نسخة رقمية» and «ملف PDF» lines (19–75 ₪), and a parent had no way to get the file.
- **API (`routers/downloads.py`):** the parent's downloadable lines, each file's state and the file itself (attachment with an Arabic UTF-8 name such as «قلبي-يعرف-الله-المجلد-1-ضحى.pdf» and an ASCII fallback). Only the owning parent (403 otherwise), rate-limited, and every download goes in the audit log with ids only. A story is ready after staff's «تأكيد», an activity book after a clean render, a set as each volume is ready. The order tracking now sends each line's id.
- **Home copy:** the worker cuts the print files to their trim (no bleed) with the cover around the book, in under a second (`qamra_pdf.home`, `jobs/downloads.py`). It is kept under the child's storage prefix, so «حذف كل بيانات طفلي» removes it.
- **Web:** «ملفات للتنزيل» on the account page and «تنزيل PDF» on each digital line of the order page (`components/order/DownloadButton.tsx`), with preparing, ready and failed states in Arabic and English.
- **Email:** «ملف … جاهز للتنزيل» once per digital line when it is ready (a 5-minute cron), linking to the account page.
- **Language:** an independent Arabic/English review of every new string (UI, email, errors, file names); all its fixes applied, among them «تنزيل» rather than «تحميل» (which the site uses for "loading").

## Design audit: the site photos show our real books, the social posts lead with the photo (2026-10-08)
- **Why:** Tareq (2026-10-07): check every design again, make sure none looks AI-made, and that each one stops the scroll.
- **Biggest tell found:** in 5 of the 10 site photos the book in hand was a blurred colour smear (hero, family table, the teacher's book, the gift box) or blank paper with an empty phone screen (journey QR). `scripts/retouch_site_photos.py` (no paid API) lays our real art onto those surfaces, lit by the photo's own light and masked around fingers, crayons and tissue: «يوم تخرّج ليان» (front and a back cover with the Qamra mark), real pages of «مغامراتي مع عائلتي» and «رحلتي الأولى للتعلّم» (the audio-QR page, and a player on the father's phone), the class-on-stage spread. Every photo then gets one fine film grain against the over-smooth "AI sheen". Same names, sizes and ratios; each under 1 MB.
- **Social kit:** a `layout: hero` for posts and ads that have a real photo: the picture full-bleed on the top half (logo and pill on a soft scrim), the headline, sub and note below, the button at the bottom. Used by posts 04, 05, 06, 11, 13, 15, 17, the kindergarten and gift Meta ads (1:1 and 4:5) and the three stories; the gift posts show the real book in the gift box instead of a drawn book pasted over the photo. The Facebook cover's hardcover now carries the real «يوم تخرّج ليان» front (optional re-upload). Slots in `images.yaml` prefer the retouched public photos. Published posts 01–03, the profile photo and both films are unchanged. No words changed.
- **Language:** an independent review of the text drawn into the photos (the phone, the back cover, the cover ribbon); its two optional fixes applied.

## Story books: real pages in every art style, Classic vs Magic side by side, what's included and the extras (2026-10-08)
- **Why:** Tareq (2026-10-07): a parent must see how the book looks in each art style before choosing, with examples that convince, and choosing anything should show pictures and suggestions at once.
- **Samples (`apps/web/public/samples/<style>/`, 3.2 MB):** real pages laid out with the theme's own text and the current page designs, WebP at 900 px (lightbox) and 480 px (carousels). 3D: 7 («يوم تخرّجي»); watercolor: 18 (graduation, first day for a boy and a girl, new sibling); and «قَمّور» in each of the three styles. `apps/web/src/lib/styleSamples.ts` exposes them, typed: `samplesForStyle(style, theme?, {look, limit, strict})` (the story's own pages first, then other stories in that style), `styleThumb`, `bookSampleCount`, `sampleAlt`.
- **How they are made:** `scripts/style_samples.py`: `fetch` the published examples, `reuse` them as book pages with the theme text (no AI, no cost), `draw` missing pages on fal under a hard budget with every call in the ledger (`--provider sketch` is a free dry run), `export` the chosen pages.
- **Stories page:** each card shows its art styles; «شاهدوا الرسم قبل أن تختاروا» switches styles and swaps a swipeable gallery (tap to enlarge, right-to-left, keyboard and swipe); «أيّ كتاب يناسبكم؟» puts Classic and Magic side by side with a style switch (the same page in each style, or a note when a line doesn't sell it), what each price includes, the facts both share (free preview, cash on delivery, delivery zones and working days) and the optional extras with their prices. Prices, styles, inclusions, add-ons and zones all come from the catalog; inactive add-ons never reach it.
- **Story page:** the story's values; style cards with real pages instead of the drawn placeholder; under step 2 the chosen style's pages (this story's first, borrowed ones labelled with their story); the extras of the chosen line and format; «قد يعجبكم أيضًا». The old note that named the gift box is gone.
- **Gap:** no cartoon book pages yet. The fal account ran out of balance on 2026-10-07 (the first call was refused, $0 spent); the cartoon tab shows «قَمّور» and says the free preview shows the child's story in that style. Cost to fill: about $0.32 per story (character sheet, cover and 2 pages at $0.08), so $0.64 for first day and new sibling; 3D for those two stories the same again.
- **Language:** an independent Arabic/English review of every new string and alt text; all fixes applied (second pass all clear).

## «دوسية التأسيس»: odd one out says its rule (2026-10-07)
- **Why:** the owner's review (kg1-v1 p120, kg1-v2 p116, kg1-v3 p52, kg2-v1 p16, kg2-v2 p10): rows of four different pictures (apple, banana, strawberry + car or duck) gave no rule, and the duck was yellow like the banana. The generator (`puzzles/odd.py`) took `category` rows from a three-fruit pool with no name and no check of a second answer.
- **Now:** a row is either seen (three identical pictures + one) or a named group printed on a chip over the row (فَواكِهُ، حَيَواناتٌ، مَلابِسُ، وَسائِلُ نَقْلٍ، أَشْياءُ تَطيرُ، طَعامٌ); review and assessment panels ask the group's question under the pictures («أَيُّها لَيْسَ فاكِهَةً؟»). Members are hand-picked, the odd picture comes from a list of things clearly outside the group, a row's members have different main colours, and groups that share a picture never meet on one page. KG1 V1 shows only seen differences; KG1 uses four basic groups; groups come in by level. Answer keys name the group.
- **Instructions:** pages with group rows turn through three new lines that fit both kinds of row; KG2 V3 p30's skill line follows the page. Language review (linguist + early-childhood educator) applied.
- **Checks:** `tests/test_odd_one_out_rules.py` records every odd-one-out row the six volumes draw and asserts it is seen or names its group, with exactly one picture outside it. 14 pages changed; volumes re-rendered locally, preflight passed. Islamic series: no odd-one-out exercises (reported only).

## Activity books: every instruction rewritten in «رحلتي الأولى للتعلّم» and «مغامراتي مع عائلتي» (2026-10-06)
- **What:** the line at the start of each exercise is clear and ordered (one action or two short steps), keeps the page's idea, goal and answer action, and no two neighbouring pages open the same way. «رحلتي الأولى»: 352 Arabic lines and 43 English lines across the three stages (the 26 English letter pages rotate four wordings instead of one; map openers, Arabic letter pages and reviews each vary). «مغامراتي مع عائلتي»: 94 lines, including the insert sheets; the twelve «ذكرى اليوم» pages each ask their own question.
- **Language:** full tashkeel in each book's own convention, both gender forms written out, ≤ 7 words (journey) / ≤ 10 (family). An independent linguist + early-childhood reviewer passed every line after three rounds (40+ fixes applied).
- **Before/after tables:** `docs/review/journey-instructions.md`, `docs/review/family-instructions.md`. The plan's brief (`content/journey/plan.yaml`, `docs/journey/plan.md`) and the family samples follow the printed lines.
- **Audio:** no QR clip reads these instructions, so none needs re-recording (`audio.yaml` unchanged). Books re-rendered (preflight passed) and web previews re-exported.

## «دوسية التأسيس»: every exercise instruction rewritten (2026-10-06)
- **All 732 pages of KG1 and KG2 (six volumes)**: the moon's one-line instruction now gives one clear step or two ordered ones («…، ثُمَّ …») in easy, fully vowelized Arabic, for a boy and a girl, at most 7 words; English pages keep a matching English line. Titles, skill lines and in-page labels are unchanged.
- **Varied, not repeated:** a recurring exercise turns through 2–5 wordings page by page (`foundation_text.pick` with the page's `turn`); pages that come once a volume change by volume; a new test keeps neighbouring pages from opening with the same word and caps any wording at 3 uses a volume.
- **Matched to the page:** big/small circles (as the answer key), KG1 V1 English letters are traced only, single-picture letters say «الصّورَةَ», equal rows are two, paths and mazes name their walker.
- **Language review:** two reviewer passes (linguist + early-childhood educator); all fixes applied. Before/after table: `docs/review/foundation-instructions.md`. Volumes re-rendered locally (preflight passed) and the web previews re-exported.

## Staff review and confirm every story's text (2026-10-06)
- **Where:** Admin → `/ar/admin/queue`. Story books whose final files are ready show «بانتظار مراجعة النص»; the book's screen has a new «نصوص الكتاب» section: the child's name, gender and age with a grammar reminder, then the title (also the cover), the dedication, the family's message, every story page beside its picture, the «للأهل» page and the back-cover blurb, each in an RTL box in the books' Naskh font (tashkeel kept).
- **Each text saves on its own, at once,** with «استرجاع النص المولَّد» and its history (who, when, before → after, `book_text_edits`, migration `e5dd2afbd62c`). Words with a link, a phone number or an unsafe word ask for a note before they are kept. «إعادة إخراج الملفات» rebuilds the PDFs once (no AI cost); «تأكيد النص واعتماد الكتاب» waits for it, records who and when, and releases the book.
- **Nothing reaches the family before «تأكيد»:** the reader and share links open only for confirmed books (a book back in review closes its link), the "book ready" email goes out at «تأكيد», and parents can no longer change page text once the final files are being made. Print was already gated.
- **Optional alert:** setting «بريد تنبيهات مراجعة النص» gets one email per story waiting for review.
- **Class copies** show their shared class text read-only; per-page AI text regeneration is not offered (the pipeline writes the whole story at once).

## Sound for the brand films: music, sparkles, page turns and an Arabic voice (2026-10-05)
- **One soundtrack design** (`content/marketing/film-audio/soundtrack.yaml`, `scripts/film_audio.py`): a gentle bedtime lullaby (Google Lyria 2: music box, celesta, felt piano, soft strings; no drums, no vocals), a sparkle chime when the moon or the photo-to-character magic appears and a soft page-turn whoosh on each scene change (ElevenLabs sound effects), and one calm female voice (ElevenLabs Multilingual v2, «Charlotte», the voice of the activity books' QR clips) reading the words each film shows. All through fal, all licensed for commercial use. A language review checked every line before it was read; ElevenLabs Scribe heard all 19 back as written.
- **Mix:** voice on top, the music 6 dB under it between lines and 12 dB under it while she speaks, the bed evened out, fades at both ends, every film at −14 LUFS with true peaks under −1.5 dBTP, AAC 48 kHz stereo (Opus in the WebM).
- **Every video now has sound,** plus a music-only twin (`*-music.mp4`) for ads that run muted: `social_kit.py --videos` mixes each reel and ad from its cue sheet and warns when a line would not fit. The end cards of the cut-downs and ads got 0.4–1.1 s longer so the last line is never cut (cuts 7–8 s, ads 11–13 s).
- **Home hero:** `scripts/build_film.py` (moved here from the gitignored `out/video/`) builds the brand film and then writes `hero-reading.mp4/.webm` with the soundtrack. The site still plays it muted and looping; the site's own music stays the lullaby.
- **Cost:** about $0.35 on fal, once (bed $0.10, effects $0.01, voice $0.11, transcription checks $0.14); the sounds are kept in the repo, so every rebuild is free.

## Design images drawn, the graduation proof in 3D and watercolor, a framing check (2026-10-03)
- **Images (fal, $8.76 for 81 calls):** the 10 site photos (`apps/web/public/photos`), the fixed character sheets (`content/cast`: «قمّور», the teacher, the classmates, the family; 3D and watercolor), cover backgrounds for graduation, first day and the new sibling (`content/themes/*/plates`), the moon portrait frame and the cloud wash (`packages/pdf/layouts/decor`), and the activity-book and «قلبي يعرف الله» art (`content/assets`). Every image was looked at; prompts were tightened where the first drawings missed (Levantine classmates, no white paper borders, one continuous scene under the title).
- **Proof (Addendum 11 §6):** «يوم تخرّج ليان» for an invented child, in cinematic 3D and premium watercolor, with real images and the theme's own text (`sample_book.py --text-provider fake`, no Claude key here): about $1.65 of images per book, ~$1.9 with the story and QA calls. `out/redesign/graduation-before-after.pdf` puts the old proof next to both, with the five title treatments at phone size and the mockups.
- **Framing check:** 3 of the first 3D proof's 18 pictures were two images stacked behind a white line or carried a pasted band; `framing.py` finds them from the pixels and the page is redrawn (the next 3D run: one redraw, none left). Watercolor fades to the paper stay allowed.
- **Store:** the coloring book is out of the store (migration `e5b9c3d71a20`); fresh installs seed the three styles in order.

## Addendum 11 redesign, three styles that draw, one-tap cart, social kit (2026-10-02)
- **Styles:** «سينمائي ثلاثي الأبعاد» (first), «مائي فاخر» and «كرتون ملوّن» for the story books and the activity books. Choosing 3D or cartoon used to fail every character drawing (generation only knew watercolor, crayon and paper-cut); styles now come from `prompts/style/*.md` with their own negatives, the house style (v4) no longer says "watercolor, no 3D", and page QA (v4/v5) judges the book's own style. Migration `c4e8a1f20b37` renames and orders the styles and retires semi-realistic from the stories.
- **Covers:** title lettering drawn in code in five treatments (`cover_title_style`), the «بطولة» ribbon, the moon mark; a back cover without the «قريباً» QR; the spine from the page count.
- **Pages:** an 8-layout library (`packages/pdf/layouts/`) that never repeats a layout twice in a row, text boxes that fit their text, bigger story text (26/24 pt for 3–5, 21/20 pt for 6–8), redesigned dedication, «للأهل», «ارسم» and «ذكرياتنا» pages. Fonts: Lalezar, Marhey, Aref Ruqaa (OFL).
- **Consistency:** a style bible per book (outfit per scene group, one hijab, companion, side characters), fixed reference sheets for «قمّور» (always a crescent), the teacher, the classmates and the family, cover plates, a text-completeness check and QA for outfit, hijab, companion and cropping.
- **Cart:** «أضيفوا للسلة» adds any story or activity book in one tap (guests too); the line asks for the child's details («أكملوا بيانات الطفل») and checkout waits for them; a signed-out browser can no longer read a parent's cart; guest lines join the parent's cart at sign-in.
- **Activity books:** family members are drawn in the child's style; admin retries a family/journey book with its own job and can approve it (the preflight names never matched); preflight frees each page (a 112-page book peaked at 1.9 GB, now 220 MB — the likely reason Tareq's family book stayed «قيد التوليد»); work left `generating` for 2 hours with no job behind it becomes `failed` so it can be retried.
- **Social kit:** `scripts/social_kit.py` renders the Instagram/Facebook profile, cover, highlights, 7 ads, a carousel and stories to `out/social/`.
- **Design images:** `docs/image-prompts.md` (77 prompts), `scripts/design_images.py` draws them on fal within a hard budget, `scripts/install_design_images.py` installs them (site photos, cast sheets, cover plates).

## «قلبي يعرف الله» step 1: the proposal package (Addendum 10), and every activity book complete (2026-10-01)
- **Proposal:** `docs/islamic/proposal.md` and `out/islamic/proposal.pdf` (`scripts/islamic_proposal.py --pdf`): concept and 5 names, 5 volumes + a Ramadan book (639 pages, 43 units, 93 concepts), the full table of contents, the retention matrix computed from the plan, characters, unit identities, 12 designed sample pages, the source list, print and prices. Waiting for Tareq's approval (step 1 stops here).
- **No religious text typed by us:** `content/islamic/sources.yaml` + `sources.d/` hold references only (192); hadith candidates come from an open dataset (`scripts/islamic_sources.py fetch`), the Quran from the Tanzil file once Tareq places it; a print build fails on any placeholder or source the scholar has not approved. The scholar's readable list: `scripts/islamic_sources.py scholar-pdf`.
- **Engine:** 18 Islamic page types, the checks (sources, sacred text off disposable pages, no depiction, typed wording), Amiri Quran (OFL) for verses; 41 tests.
- **Activity books:** «دوسية التأسيس» KG1 volumes 1–3 and KG2 volume 3, «رحلتي الأولى» stages 2–3, all rendered, preflighted and on sale (migration `b7d2e91c4a05`).

## The launch site, and a clear sign-up for new parents (2026-10-01)
- **One structure:** the menu is الحكايات · كتب الأنشطة · للروضات · الأسعار · كيف نعمل. New pages: an activity-books hub (`/workbooks`), `/pricing` (read from the catalog, in shekels or, with `?country=jo`, dinars) and `/how-it-works`. The home has one promise, four offers with real covers and "from" prices, a real book to flip through and a short FAQ. «العوالم» is gone everywhere.
- **Only what renders is sold, and nothing says «قريبًا»:** a volume or stage that does not render yet is an inactive variant (`variant_matrix.rendered`, `active: false`, migration `a3c1f0b7e2d4`), so no page, price list, structured data or cart mentions it. Checkout offers cash on delivery only, and the API messages no longer promise "soon".
- **Sign-in:** a guest sent to sign in from «أضف للسلة» sees «أهلًا بكم» and a full-width «إنشاء حساب جديد», and switching between sign-in and sign-up keeps where they were going, so a new parent comes back to their book instead of `/account`.
- **Search and tests:** Organization, WebSite, Product and FAQPage structured data and a fuller sitemap; `tests/e2e/test_public_site.py` checks every public page as an anonymous visitor on a 390 px phone.

## «رحلتي الأولى للتعلّم» stage 1 in full, with the audio QR system (W9) (2026-09-30)
- **The whole stage:** `python -m qamra_workbook.render.journey --stage 1 --book` renders 118 pages, the cover and a 20-page answer key; every file passes preflight. About 40 new page types (thinking, eye, listening, hand, shapes, math, review), 18 new pictures, the print layer `content/journey/stage-1.yaml` with every text marked for the educator.
- **Audio QR:** pages with audio print a QR to `/a/{code}` (a stable code per letter or word); the public player plays the recording through a 10-minute signed link, shows the words when nothing is recorded, and never carries child data. Staff upload recordings in Admin → صوتيات الرحلة; the TTS fallback stays off.
- **Orders:** confirming an order renders each stage's book from the plan with the child's approved character (no AI cost), as a book in review; print batches pick it up. The store previews show real pages. The product stays «قريبًا» until the educator signs. Migration `97b657f5bf00`.

## «دوسية التأسيس» KG2 volume 2 (W8) (2026-09-30)
- 124 A4 pages and an 18-sheet answer key, both passing preflight: letter positions and place words, numbers to ten (10 as two digits), twin letters, spirals and narrow paths, categories, story order, colour by letter, and the volume's reviews and assessments. 23 page types and 40 pictures; number sequences run left to right as numerals are read (for the educator to confirm). `--volume 2` renders it through the same CLI.

## «دوسية التأسيس» KG2 volume 1 in full (W8) (2026-09-29)

- **Renderer from the curriculum plan:** `python -m qamra_workbook.render.workbook --level kg2 --volume 1 [--size a4] [--pages 1-40] [--numerals latin]` renders every page of a volume, in order, for the journey samples' child and character: `out/workbook/kg2-v1.pdf` (128 pages), `kg2-v1-answer-key.pdf` (17 sheets), page PNGs, a sheet of open spreads and preflight (both PDFs pass: bleed, boxes, embedded fonts, 300 DPI, safe area).
  - `render/foundation.py` turns plan pages into engine pages: a child-facing title and a ≤ 7-word instruction per page type (`foundation_text.py`), English pages LTR and bilingual, the week on every page's chip, and the params builders need from the plan (unit titles, objectives, the table of contents).
  - The workbook has its own subject tabs (pen, Arabic, math, English, thinking, review) in `render/sections.py`.
- **28 new page types** (`render/pages/workbook_*.py`): owner page with the handprint, name tracing (Arabic and English), table of contents, unit openers, letter intro (hollow letter to color), letter trace (big track, then smaller rows), letter write (guided, then alone), find the letter (grid by color and "count the dots", then pick the first letter), letter–picture–word matching, first-sound connect and sort, number intro / trace / write, count and circle, number ↔ quantity, compare (big/small, long/short, many/few, more/less), pen lines (straight to loops to letter strokes), road tracing, dot-to-dot, shapes, coloring (colors and inside the borders), memory, cut and paste (one-sided, with its blank back), symmetry drawing, unit reviews for every subject, assessments with a score box, and the pen-skills check (grip, pressure, direction, and two tracing tasks; decision 9). Every puzzle has an answer key and checks.
- **Letters and numerals:** English A–Z and a–z (`latin.py`) and Hindi and Latin digits (`digits.py`) as single-stroke paths; أ is the alif with its hamza. `tracing_row` keeps room below the base line down to the tail line for Arabic letters and runs right to left (English rows unchanged).
- **26 new pictures** for the volume's words (`pictures/workbook_words.py`), including ذَيْل (decision 7).
- **Store previews:** `scripts/export_workbook_previews.py` exports six real pages for `foundation-workbook`.

## «مغامراتي مع عائلتي» in the store: quotes for organizations, illustrated family (W4) (2026-09-29)

- **«طلب عرض سعر» for organizations:** `POST /api/leads/family-quote` (multipart) takes the organization, the contact, 10–5000 copies, the desired date and an optional logo for the back cover.
  - It is a request, never an order (`request_only`).
  - The logo must be PNG or JPG, ≤ 5 MB and ≥ 300 px on its long side; it is re-encoded and kept private at `leads/<id>/logo.png`.
  - Staff (`/api/admin/leads`) list the requests, see the logo and set the status.
  - `POST /api/admin/leads/{id}/quote` prices the request from the printer's tiers and the margin rules. From 10 copies it answers `bulk_price_pending` while the tiers are estimates (Tareq, 2026-09-28).
- **The logo on the back cover:** the renderer's back cover has an organization slot (the name and the logo, never printed below 300 DPI); `render_order(org=…)` fills it for an organization's copies.
- **The illustrated-family add-on (off by default: `family_characters_enabled`):**
  - Up to four of the child's family, each with the parent's consent for that person, one photo (one clear face, re-encoded, private), a drawing with the approved providers (3 redraws) and approval.
  - The photo is deleted by the cleanup job after approval, like the child's; «forget this person» deletes everything at once.
  - Approved members are drawn from their sheets in place of the placeholder figures (`render_order(member_sheets=…)`).
  - One sheet costs about $0.07–0.08 (Gemini 3.1 Flash Image at 1K, or Nano Banana 2 on fal).
- **Migration** `5c7e2f19a4b6`: the `family_members` table and `leads.details`.

## The template studio (Addendum 4 step 4) (2026-09-29)
- **Admin → الاستوديو:**
  - Classic templates per story × style × look, with status, pages, flags, cost, vowelized texts and a scheduled go-live;
  - bulk actions: copy to another style as a draft, publish or unpublish several, schedule.
- **The page editor:**
  - drag or resize the hero box;
  - lock, redraw, draw missing pages (paid actions ask first);
  - m/f/en texts with a live preview of the book's text panel.
- **Theme versions:**
  - draft → in review → approved → live, with history, rollback and a diff against live;
  - an English draft made on request, with its cost shown first;
  - the deploy seed no longer overwrites a theme published from the studio.
- **Staff:** roles in the UI (only owners grant owner; nobody edits their own roles), and an audit-log viewer with filters.
- Migration `918b650a07fc`.

## W3: «ارسم صاحبك» and «حكاية خاصة» in the parent flow (2026-09-29)

- **«ارسم صاحبك»**, optional sub-steps of step 6, between the character and the story (designs CompIntro, CompUpload, CompCrop, CompName, CompGen, CompChoose):
  - photograph the drawing (camera or gallery), then crop, turn and clean it (original / cleaned views);
  - name it, say what it is, pick its nature, and see 2 options drawn in the book's art style, each beside the drawing;
  - choose one, or redraw (3 free); a big «تخطّي» keeps the theme's own companion;
  - the book is drawn with it: the story names it, every page shows it, and the book ends with «وهكذا وُلد صاحبي».
- **Privacy:** consent first, no EXIF/GPS, private storage under the child. The original photo is deleted 24 h after the choice, the options not chosen at once, and everything with "delete my child's data".
- **«أصحابي»** in the account: the chosen companions, «حكاية جديدة معه», and delete.
- **Pricing:** included in Magic; +20₪ on a Classic cart line, added automatically.
- **«حكاية خاصة» (Magic, 169₪):** a short guided brief on the story step (the occasion, the place, 2–3 loved things, a wish, optional family members in the family's own words). Claude writes the story and every page's picture from it (prompt `story_custom.v1`). The brief gets an instant screen and the safety review before anything is written; errors are friendly and per field.
- Migration `d022f9307892` (companion status, options, crop choices).

## Phase 5: «صوت أهلي», SEO and a performance pass (2026-09-29)

- **«صوت أهلي» (family voice)** for books bought with the «أصوات العائلة» extra:
  - **Record screen** (account → «سجّلوا الحكاية»): the page text in large type, one page at a time, with record, listen and record again. Up to three voices per page (ماما، بابا، ستّي… or any name the family types).
  - **Grandparent link:** no account, works 7 days, can be cancelled, and can cover the whole book or chosen pages. It is sent from the parent's own WhatsApp, and the parent sees who opened it and how many pages they recorded.
  - **A QR on every story page** of the print PDF (18 mm, in the outer bottom corner inside the safe area) and on the back cover. It opens the listen page: the picture, the words, and the family's voices to switch between.
  - Parents can pause and resume listening, and delete any recording. Deleting the child's data deletes the recordings.
  - **Narration fallback** behind a TTS adapter; it stays off (no paid provider yet).
- **WhatsApp adapter interface:** manual links (the default), a log sender, and Twilio built but disabled. Nothing is sent automatically.
- **SEO for the story pages:** per-language titles and descriptions, canonical and ar/en alternates, the example's cover as the share picture, and Product/Book structured data with the price. Also `/sitemap.xml` and `/robots.txt`.
- **Performance:** a week of browser caching for images and audio in `/public`, and Lighthouse before/after numbers in `docs/plans/phase-5.md`.

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

## «مغامراتي مع عائلتي», the whole book (Addendum 7, W7) (2026-09-29)

- **The whole book from the plan:** `uv run python -m qamra_workbook.render.family --book --size both` renders all 112 pages, the cover and the insert sheets, personalized for the sample child and family.
  - The front pages: the title page (the child in the middle of the family), the adventures map, the passport with a slot for each of the 12 adventure stamps and the 7 badges, «عائلتي» (a portrait for each of 1–6 members) and «هذا أنا» (repeated at the end as «هذا أنا الآن»).
  - Adventures 3–12 and the back pages (the 7-day challenge and the certificate).
  - New page types: title page, contents map, «عائلتي», sequence cards (the day, a story, a chain of moves), routine builder, chore chart, nature bingo, picture talk, feelings faces, situation–feeling match, finish the story, the interview, family game night (memory and scoreboard), and the cover.
  - New variants of the existing types: a checklist hunt, counting pictures, things, the family table, money and change («الباقي» at ⭐⭐), fruit colors, weather, toy boxes and six jobs to sort, choosing within a budget or the kindest solution, recipes that count pieces or layer a cup, a blank shop, one-entry and day-by-day journals, and nine drawing frames.
  - 30 new pictures in the house style (nature, weather, the routine, toys, the jobs' tools, the recipes, the games).
- **The inserts as print files:** the sticker sheet (a sticker for every passport slot, 21 chore stars, 7 day stars, 10 routine icons) and five card-stock sheets (play money «للعب فقط» with blank price tags, recipe step cards, memory cards, question cards, role cards, finger puppets).
  - Every cut and kiss-cut line is on the optional-content layer «CutContour»; each file also comes as `…-die.pdf` with the die lines alone. The cards' color runs 1.5 mm past the cut.
- **Order-time render:** `qamra_worker.jobs.family_book.render_family_item(item_id)` renders one order's book from the child's approved character (no new AI cost), stores the interior, cover and inserts like the story books with every file's preflight, and leaves the book `in_review` for the print approval.
- **Plan:** render params for every page, the cover and the insert sheets are in `content/family-book/plan.yaml`; draft texts are marked `# draft: educator review`. The interview and «حكايات زمان» now go to a grown-up (`{adult}`), not any family member.
- **Checks:** 112 pages at both sizes, the cover and all inserts pass preflight (fonts embedded, bleed, no text in the safe margin). Tests cover every page and sheet building from the plan, 1 to 6 members, a boy and a girl, a child raised by a grandmother only, a father only, the numerals and the die layer.

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
