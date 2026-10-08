# Order flows per product: review and redesign

2026-10-07. Written after Tareq's report:

> «بس انا اصلا بعمل بدوسية او كتب انشطة شو علاقة الكتاب قاعد بتجيبلي اياه؟ … حتى موضوع لما اجي اختار للطفل شو اسمه وشو بيحب الخ … الأصل يكون في أشياء لها علاقة بالمنتج ويكون في أشياء أكثر وضحوها.»

He picked «قلبي يعرف الله», tapped «أكملوا بيانات الطفل» in the cart, and the site asked «أي كتاب تريدون لضحى؟ قمرة كلاسيك / قمرة سحري», then asked what she likes and for a story.

This document is the plan only. Nothing in the code has changed yet.

**Paths:**
- `web/` means `apps/web/src/`.
- `api/` means `apps/api/src/qamra_api/`.
- `worker/` means `apps/worker/src/qamra_worker/jobs/`.
- `wb/` means `packages/workbook/src/qamra_workbook/`.
- Line numbers are from commit `244d81f`.

---

## 0. Summary

### 0.1 Why Tareq saw the story steps

`web/lib/order.ts:117` has its own list of activity lines: `["workbook", "journey", "family"]`. That list leaves out `islamic`. The API's list includes it (`api/store/workbooks.py:15`), and so does the site's other list (`web/lib/shop.ts:9`).

Because of this, `completeHref()` (`web/lib/order.ts:123-135`) treats a «قلبي يعرف الله» cart line as a story:
- It builds `/create?item=<id>&format=softcover`, with no `product` and no `line`.
- The wizard then runs the whole story flow:
  - the story child step, with «ماذا تحب ضحى؟»;
  - consent and photo;
  - **«أي كتاب تريدون لضحى؟»** (Classic or Magic);
  - the art style, the character and «ارسم صاحبك»;
  - **«إلى أين تذهب ضحى؟»** (pick a story).
- It then starts a story preview, which is a real AI cost and counts toward the 3-a-day limit.
- At the end, the API refuses to put that book in the Islamic line (`item_mismatch`), so the parent can never finish the order.

### 0.2 The deeper problem

There is **one wizard with skips**, not a flow per product. The three other activity books avoid the line step only because of a hack: `completeHref` sets `line=magic` (`order.ts:127`). Even so, they still get story things:
- the story child step, with likes, a «شيء مميز» note and a **story title** as the name preview;
- the Magic art-style list, under «كل الصفحات ستُرسم بالأسلوب نفسه»;
- a Back button from the style step that opens the Classic/Magic chooser;
- «هذه ضحى في كل صفحات الكتاب»;
- «الخطوة 5 من 12», then a jump straight to the cart.

Meanwhile, things these products really print are **never asked**:
- the child's name in English letters (dawseyeh, journey stages 2–3);
- the family's city (the family book);
- a check that the level fits the child's age.

And nothing shows the parent what will be printed before it goes in the cart.

### 0.3 Problems found outside the wizard (they decide what the flow must ask)

1. **«دوسية التأسيس» is on sale but cannot be made for a child.**
   - Confirming an order queues jobs for `family`, `journey` and `islamic` only (`api/routers/admin_orders.py:385-397`). `LINE_JOBS` has no `workbook` entry either (`api/routers/admin_books.py:54-58`).
   - The only renderer is a CLI that always uses the sample child (`wb/render/workbook.py:115-120,147`).
   - It writes no cover and no black-and-white interior, yet B&W variants are sold at 49 ₪ and 129 ₪.
2. **The English name in the activity books is never asked.**
   - «دوسية التأسيس» has an English name-tracing page in every volume (`content/workbook/curriculum/kg2.yaml:154,318,482`). The build fails without it (`wb/render/pages/workbook_front.py:114-117`).
   - «رحلتي الأولى» stages 2 and 3 fall back to an automatic transliteration (`wb/journey_book.py:218-244`). It gets most names wrong. Measured today:

     | Arabic name | Transliteration |
     | --- | --- |
     | ضحى | **Daha** |
     | سلمى | Salama |
     | محمد | Mahamad |
     | عمر | Amar |
     | يوسف | Yousaf |
     | رؤى | Ra |

     The child would trace the wrong spelling of their own name.
3. **Arabic name tracing crashes on some letters.** `spell()` (`wb/render/pages/workbook_front.py:22-37`) raises `KeyError` for ؤ and ئ (رؤى, لؤي) and for Latin letters (Adam). Nothing checks the name at order time, so the order fails later in the worker.
4. **Values the workers read but nothing ever writes:**
   - `numerals` (`worker/family_book.py:84-86`), so digits are always ١٢٣;
   - `name_en` (`worker/journey_book.py:118`);
   - `org` (`worker/family_book.py:89-102`).
5. **Family book gaps:**
   - An empty city prints «سوق » with nothing after it (`content/family-book/plan.yaml:82`).
   - An empty family name prints «عائلة {child}» (`worker/family_book.py:74`).
   - The illustrated-family add-on cannot be attached from the site (`api/store/addons.py:23` offers only `format`/`checkout` add-ons).
6. **Activity books never get an add-ons screen.** `AddOnsStep` finds its cart line by `book_id` (`web/components/order/AddOnsStep.tsx:50`). So the sticker sheet, crayon kit, wipe-clean sleeve, gift box and printed parent guide are sold for these books but never offered.
7. **The workbook cart picks the wrong character in some cases.** `POST /api/shop/workbooks/cart` takes the newest approved character in **any** style (`api/routers/shop.py:242-252`), including a black-and-white `coloring` one. The art-style table lets activity lines use 3D, watercolor and cartoon, but `islamic` is in no style's `lines` (migration `20261002_c4e8a1f20b37_three_styles.py:20-24`).
8. **Privacy and data loss:**
   - «احذفوا كل بيانات طفلي» clears the child's name and age on orders, but leaves family names, the city and `character_id` (`api/routers/create.py:175,202`).
   - `PATCH /cart/items` silently drops `family` and `character_id` (`api/store/router.py:574-578`).
9. **Story books:**
   - Interests and the note are asked for every book. Only Magic uses them, as "a light touch on one or two pages" (`packages/ai/src/qamra_ai/prompts/story_adapt.v2.j2:16`). Classic and the free cover never read them.
   - The wizard never sends `language`, so every book is Arabic, even on `/en` (`web/lib/create.ts:52-60`; the default is at `api/routers/create.py:431`).
   - There is no way to correct a child's name or age: there is no `PATCH /children/{id}`.

---

## (a) Current flows per product

### a.1 Wizard mechanics

- **The state lives in the URL:** `/create?step&child&character&book&line&theme&style&product&companion&cstep&item&format` (`web/components/create/CreateWizard.tsx:29-34,93-106`; `format` is read by `FormatStep.tsx:54`).
- **`furthest()`** (`CreateWizard.tsx:39-50`) is the resume point. It returns **`"line"` whenever no line is known, whether or not `product` is set** (`:47`).
- **`allowed()`** (`:53-84`) gates a step named in the URL.
- **`continueWith()`** (`:275-286`): an activity product reuses **any** approved character, then calls `addProduct()` (`:292-304`), which goes to `POST /api/shop/workbooks/cart` and then `/cart`.
- **Three places send a parent to the line step when `line` is null:**
  - picking a known child (`:324-326`);
  - after consent (`:311-315`);
  - after the photo (`:352-353`).
- **The style step's Back always goes to the line step** (`:378`).
- **Progress is a fixed «الخطوة n من 12»** (`web/lib/create.ts:106`, `Frame.tsx:196-212`):
  - The steps are numbered 1 child, 2 consent, 3 photo, 4 line, 5 style, 6 character (the companion sub-steps reuse 6, `companion/SubFrame.tsx:10`), 7 story, 8 writing, 9 review, 10 format.
  - Add-ons have no number.
  - Checkout says 11 of 12 (`web/components/order/CheckoutScreen.tsx:93`).
  - Step 12 is never shown.
- **The child step** (`ChildStep.tsx`) is the same for every product:
  - Frame title «كتاب جديد» (`:68`).
  - «من بطل حكايتنا؟ / نستخدم هذه المعلومات لكتابة القصة فقط.» (`:77`).
  - Name, with a preview of a **story title**, which falls back to the first available theme (`:105-112`; `CreateWizard.tsx:322`).
  - Gender and age chips 2–9 (`:12`). The API accepts 2–10.
  - Likes up to 3 (`:147-164`), look (hijab/glasses, `:166-178`) and a note (`:180-192`).
  - A known child is one tap on a chip. There is no summary and no way to edit.

### a.2 Every entry point into `/create`

| # | Where (file:line) | URL | Product |
|---|---|---|---|
| 1 | Story page «جرّبوا المعاينة أولًا»: `web/lib/story.ts:90-95` via `components/story/StoryProduct.tsx:218` | `/create?theme&line&style&format` | story |
| 2 | Cart «أكملوا بيانات الطفل»: `web/lib/order.ts:123-135`, used at `components/order/CartBody.tsx:288-294`, `CartScreen.tsx:149`, `CheckoutScreen.tsx:126` | activity: `?item&product=<sku>&line=magic`; story: `?item[&line][&theme][&style][&format]`; **islamic: `?item&format` (bug)** | all |
| 3 | Cart «تعديل الإضافات»: `order.ts:138-143` | `?step=addons&child&book`; activity without a book → `/workbooks/<product>`; **islamic → `/shop`** | all |
| 4 | Cart cross-sell: `CartBody.tsx:60` | `?step=story&child&character&line&style` (no theme, no item) | story |
| 5 | Free-cover result: `components/freecover/FreeCoverResult.tsx:82` | `?child&line&theme` | story |
| 6 | Account book tile: `components/AccountView.tsx:288`; reader «أكملوا الطلب»: `components/reader/OwnerReader.tsx:80` | `?child&book` | story (resume) |
| 7 | Account «طفل جديد / اصنعوا أول كتاب / كتاب جديد» (`AccountView.tsx:186,328,356`); nav «ابدؤوا الحكاية» (`components/site/SiteNav.tsx:75,114`) | `/create` | story (line not chosen) |
| 8 | «حكاية جديدة معه»: `components/create/companion/MyCompanions.tsx:101` | `?child&companion` | story |

The activity-book product page has only «أضيفوا للسلة» (`components/workbook/AddWorkbook.tsx:28-37` → `POST /api/store/cart/items {sku, family?}`). Every activity book reaches the wizard through entry 2.

### a.3 Current flow per product

| Product | What the parent goes through today |
|---|---|
| **«قلبي يعرف الله»** (V1–V5, R, L1, L2, set; softcover/PDF) | Product page (volume, format) → cart → «أكملوا» (`?item&format`) → story child step (likes, note, story-title preview) → consent → photo → **line step «أي كتاب تريدون لضحى؟»** → Magic styles → character → **«ارسم صاحبك»** → **story choice** → story preview drawn (AI cost) → format → `toCart(item)` refused (`item_mismatch`). **The order can never be completed.** |
| **«دوسية التأسيس»** (KG1/KG2, volumes 1–3/set, color/B&W, spiral/PDF) | Product page → cart → «أكملوا» (`?item&product=<sku>&line=magic`) → story child step → (known child with any approved character: straight to `/cart`, nothing shown) or (new child: consent 2/12 → photo 3/12 → style 5/12 with Magic styles, Back → line step → character 6/12 «… في كل صفحات الكتاب» → `/cart`). The English name is never asked. **The order is never produced** (§0.3-1). |
| **«رحلتي الأولى للتعلّم»** (stages 1–3/set, spiral/PDF) | Same as dawseyeh. Stages 2–3 print an auto-transliterated English name. |
| **«مغامراتي مع عائلتي»** (wire-o/PDF) | Same, plus the optional «عائلتكم في الكتاب» form folded inside the product page (`components/workbook/WorkbookProduct.tsx:274`, `FamilyDetails.tsx`). It is sent with the one-tap add and is not shown again anywhere. No city, so the market adventure prints «سوق ». The illustrated-family add-on is a separate page (`/family-characters`) that nothing links to the cart line. |
| **قمرة كلاسيك** | Story page → (`?theme&line=classic&style&format`) → child step (likes and note asked, never used) → consent → photo → (preset style: drawn at once, `CreateWizard.tsx:252-272`) → character → story step (theme preselected, dedication +5 ₪) → writing → format → add-ons → cart. From `/create` with nothing chosen, the line step comes after the photo. |
| **قمرة سحري** | As Classic, plus «ارسم صاحبك» after the character and the page-review step. Likes and note are asked in the child step, before the parent knows what they are for. |
| **سحري بحكاية خاصة** | As Magic. In the story step, «حكاية خاصة» opens `CustomStoryForm`. Interests are sent to the custom prompt, which has no rule for them (`story_custom.v1.j2`). |
| **Free cover** | Its own one-screen form (`components/freecover/FreeCoverForm.tsx`): name, gender, age, hijab, then consent, photo and cover. A good model of "only what is printed". |
| **Class books (B2B)** | Not in `/create`. The school imports name, gender and age (`api/portal/importer.py:21-35`). The parent's invite link does consent → photo → character in the class style (`api/routers/invite.py:146-175`, `web/components/portal/InviteSteps.tsx`). Hijab and glasses are never collected. Noted only; out of scope here. |
| `coloring-book` | Inactive (`content/store/catalog.yaml:54`). Ignored. |

---

## (b) What each product really uses, and the gaps

### b.1 What each generator or renderer actually reads

| Field | Classic | Magic | Custom story | Dawseyeh | Journey | Family | Islamic |
|---|---|---|---|---|---|---|---|
| Name | template text, PDF | Claude text, PDF | Claude text, PDF | owner page, AR tracing, certificate (renderer only, no order job) | cover, owner page, AR tracing, certificate (`worker/journey_book.py:113`) | titles, missions, passport (`worker/family_book.py:202`) | cover, «هذا أنا», passport, certificate |
| Name in English letters | — | — | — | **required** in every volume | stages 2–3 (`name_en`, never written) | — | — |
| Gender | template variant + grammar | grammar, outfit, QA | grammar | `{m/f}` texts, certificate | `{m/f}` texts | `{m/f}`, «عائلته/عائلتها» | «أنا مسلم صغير / مسلمة صغيرة», «صاحب/صاحبة» |
| Age | edit prompt, font size; **text not adapted** | word limit, تشكيل ≤7, font size (`p/story.py:125,133`) | same as Magic | no (handwritten line on the owner page) | no (the stage's own range is printed) | no | no |
| Interests | **no** | light touch on 1–2 pages | sent, no rule | no | no | no | no |
| Note («شيء مميز») | **no** (merged into interests, `api/routers/create.py:155`) | as an interest | as an interest | no | no | no | no |
| Hijab / glasses | template variant / prompt | sheet + pages | same | only through the character sheet | sheet | sheet | sheet (Addendum 10 §8: the parent's choice) |
| Photo → character | portrait from the sheet | sheet on every page | same | cover, unit openers, certificate (if sheet) | **required** | **required** | **required** |
| Art style | watercolor only (needs a template) | 3d / watercolor / cartoon | same | any; activity lines allow 3d/watercolor/cartoon | same | same | not in any style's `lines` |
| Theme | ✓ | ✓ | `custom` | — | — | — | — |
| Variant | format | format | format | level, volume (CLI), numerals | stage (`worker/journey_book.py:42-48`) | — (size fixed 21×28) | volume (L1/L2/set expanded) |
| Dedication | printed; **paid add-on not enforced** | printed (not given to the writer) | same | — | — | — | — |
| Companion | ignored | ✓ | ✓ | — | — | — | — |
| Family name / city / members | — | — | brief's family (text) | — | — | ✓ (`worker/family_book.py:57-75`) | — |
| Digits | — | — | — | engine supports both | read, never set → ١٢٣ | read, never set | read, never set |
| Language | always `ar` | always `ar` | always `ar` | AR + fixed EN pages | AR + fixed EN pages (2–3) | AR | AR |

### b.2 Gap table

Kinds of gap:
- **remove**: asked but not used.
- **add**: used but not asked.
- **clarify**: asked unclearly.
- **wrong step**: shown in the wrong place.
- **wording**: confusing copy.

**All activity books (dawseyeh, journey, family, islamic)**

| # | Gap | Kind | Evidence | Fix (§c) |
|---|---|---|---|---|
| A1 | Story line chooser «قمرة كلاسيك / قمرة سحري», «ارسم صاحبك» and story choice (islamic) | wrong step | `order.ts:117`; `CreateWizard.tsx:47,314,326,353` | Activity flow never has `line`, `companion` or `story` (§c.3) |
| A2 | Style step Back goes to the line step | wrong step | `CreateWizard.tsx:378` | No style step for activity books |
| A3 | Art style asked, «كل الصفحات ستُرسم بالأسلوب نفسه» | remove + wording | `StyleStep.tsx:57-60`; `create.style.body`. Pages are drawn by the engine; only the cover/guide uses the character. | Draw in the product's default style (3D) without asking; reuse any approved 3D/watercolor/cartoon character |
| A4 | Likes («ماذا تحب ضحى؟») | remove | No activity renderer reads interests | Not shown |
| A5 | «شيء مميز عنها؟» | remove | Not read | Not shown |
| A6 | «من بطل حكايتنا؟ … لكتابة القصة فقط» | wording | `ChildStep.tsx:77` | «لمن هذا الكتاب؟» + why we ask (§c.4) |
| A7 | Name preview shows a story title («يوم تخرّج ضحى») | wording | `CreateWizard.tsx:322`, `ChildStep.tsx:105-112` | Preview the product's cover title («دوسية ضحى») |
| A8 | Age asked, but not used | clarify | Stored, never read | Keep it: one tap. Use it for a non-blocking level check on the review step, and say so |
| A9 | «هذه ضحى في كل صفحات الكتاب» | wording | `create.character.body` | «هكذا تظهر ضحى في الكتاب: على الغلاف وفي صفحات مختارة» |
| A10 | Known child: one tap → cart, with no confirmation of what will print | add | `CreateWizard.tsx:280-281` | Review step (name as printed, variant, character, details, price) |
| A11 | No way to fix the child's name or age | add | no `PATCH /children/{id}` | Edit from the who step (`PATCH`) |
| A12 | «الخطوة 5 من 12» then a jump to the cart | wording | `Frame.tsx`, `TOTAL_STEPS` | Real per-product count (2–6 steps) |
| A13 | Cart line shows only «دوسية التأسيس · مطبوع بتجليد حلزوني» | add | `CartBody.tsx:246` | Show level/volume/stage/interior, the child, the English name, the family |
| A14 | «ينقصه: بيانات الطفل وصورته»: a known child needs no photo | wording | `orderPath.cart.needsDetails` | «ينقصه: اسم الطفل وشخصيته» |
| A15 | Activity add-ons never offered | add | `AddOnsStep.tsx:50` (book only) | Optional add-ons on the review step |
| A16 | Newest approved character of any style, including coloring | clarify | `api/routers/shop.py:242-252` | Reuse rule by allowed styles; `character_id` chosen by the flow |
| A17 | Arabic name with ؤ, ئ or Latin letters crashes the render later | add (validation) | `wb/render/pages/workbook_front.py:22-37` | Check at the who step + API; fix the engine (§d chunk 9) |

**Per activity book**

| # | Product | Gap | Kind | Fix |
|---|---|---|---|---|
| W1 | Dawseyeh | English name required, never asked | add | «الاسم بالأحرف الإنجليزية» in the who step; saved on the child |
| W2 | Dawseyeh | No per-order render; no cover; no B&W interior | production gap | Chunk 10; open question Q1 |
| W3 | Dawseyeh | Level/volume chosen on the page but not shown again | add | Review step + cart line |
| J1 | Journey 2, 3, set | English name auto-transliterated (ضحى → Daha) | add | Same field as W1, only for stages 2–3/set |
| F1 | Family | Family form hidden in a collapsed `<details>` on the product page; not shown again | wrong step | «عائلة ضحى» step in the flow, prefilled from the line; product page keeps one line (chunk 11) |
| F2 | Family | City never shown as needed; empty → «سوق » | add + renderer fix | City field with its reason; renderer fallback «مدينتنا» |
| F3 | Family | Empty family name → «عائلة ضحى» silently | clarify | Hint shows exactly what prints when empty |
| F4 | Family | Illustrated-family add-on unreachable from the order | add | Offered in the family step when the setting is on (phase 2, flag off) |
| I1 | Islamic | Whole story flow (A1) | wrong step | Activity flow |
| I2 | Islamic | Gender drives the certificate «أنا مسلم صغير/مسلمة صغيرة»; the parent isn't told | clarify | Gender hint + sample line on the review step |
| I3 | Islamic | `islamic` missing from art-style `lines` | add (data) | Migration (chunk 8) |
| I4 | Islamic | Cart «تعديل» goes to `/shop` | wrong step | `editHref` uses the activity list (chunk 0) |

**Story books**

| # | Product | Gap | Kind | Fix |
|---|---|---|---|---|
| S1 | Classic | Likes and note asked, never used | remove | Not shown for Classic |
| S2 | Magic | Likes and note asked before the parent knows why | wrong step | Moved to Magic's story step, with the honest hint "a touch on one or two pages" |
| S3 | All | `language` never sent; English site makes Arabic books | add | Story step sends the book language (Magic: site language by default; Classic: Arabic) |
| S4 | All | Line step after the photo when the line is unknown | wrong step | Line right after the who step (decide what you buy before giving the photo) |
| S5 | All | Fixed 12-step counter; companion repeats 6 | wording | Per-flow count |
| S6 | Classic | Dedication says «+5 ₪» but prints even if the add-on is removed | clarify | Note for chunk 7: the add-on is locked while a dedication exists (or the text is dropped). Product decision is already "+5 ₪ in Classic"; enforce it |
| S7 | All | Age chips 2–9, API 2–10, free cover 3–8 | clarify | Chips 2–10 everywhere |
| S8 | Cross-sell | Link has no theme, so the story step opens unchosen | — | Fine as is (the parent picks a story); keep |

---

## (c) Proposed flows

### c.1 Principles

1. **The product decides the steps.** `flowFor()` (a pure function, chunk 1) returns the ordered steps for this product and this child's state. The wizard renders them. There is no single wizard with skips.
2. **Ask only what is printed, drawn or checked, and say why**, in one plain sentence under each question.
3. **Variant choices stay on the product page:**
   - format for stories;
   - level/volume/stage/interior/format for activity books.

   The flow shows them read-only (header chip, review step) with «تغيير», which goes back to the product page with the same picks.
4. **Consent and photo appear only when a new character must be drawn.** The consent is the existing versioned text (CLAUDE.md §3), shown before any upload.
5. **Reuse an approved character whenever the product accepts its style.** The server decides; the flow just follows the answer.
6. **Real progress.** «الخطوة n من N» counts this product's steps for this child, and N updates when a reusable character removes steps.
7. **End with what will be printed:**
   - activity books: a review step;
   - stories: the preview and format step, as today.

### c.2 Steps (ids in the URL)

The existing ids stay valid, so old links keep working: `child`, `line`, `consent`, `photo`, `style`, `character`, `companion`, `story`, `writing`, `review`, `format`, `addons`.

New ids:
- `family`: «مغامراتي مع عائلتي» only.
- `summary`: the activity-book review step.

The URL for activity books is `/create?product=<sku>[&item=<cart line>]`. `line` is never set for them: `completeHref` stops adding `line=magic`. Which family a product belongs to is decided from the catalog (`variant sku → product.line ∈ ACTIVITY_LINES`). There is one list: `ACTIVITY_LINES` in `web/lib/shop.ts:9`, imported everywhere.

### c.3 Flows

#### Stories («قمرة كلاسيك», «قمرة سحري», «سحري بحكاية خاصة»)

Steps in brackets appear only when needed.

| # | Step | When | Notes |
|---|---|---|---|
| 1 | `child`: «بطل الحكاية» | always | Name, gender, age, plus the look for a new child (§c.4). No likes or note. |
| 2 | `line`: «نوع الكتاب» | only when the line is unknown (`/create` from the account or nav) | Moved here from after the photo. |
| 3 | [`consent`] | no reusable character and no consent | unchanged text |
| 4 | [`photo`] | no reusable character and no photo | body per product (§c.5) |
| 5 | [`style`] | Magic, or Classic with more than one style; not when the style came from the story page | Uses `web/lib/styleSamples.ts` (story-showcase agent) for real example pages per style |
| 6 | [`character`] | a new drawing | unchanged |
| 7 | [`companion`] | when the catalog offers it for the line (Magic today) | sub-steps keep one number |
| 8 | `story`: «الحكاية» | always | The theme is preselected (a card with «تغيير»). Dedication. **Magic adds likes and the note here** (§c.6). Sends `language`. Custom story: `CustomStoryForm`. |
| 9 | `writing` | while the preview is drawn | |
| 10 | [`review`] | Magic | |
| 11 | `format` | always | |
| 12 | `addons`: «الإضافات (اختياري)» | always | then the cart |

Step counts:
- **Classic, new child, style from the story page:** child, consent, photo, character, story, writing, format, add-ons = **8**.
- **Classic, child with an approved watercolor character:** child, story, writing, format, add-ons = **5**.
- **Magic, new child:** child, consent, photo, style, character, companion, story, writing, review, format, add-ons = **11**.
- **Magic, character ready in the chosen style:** **7**.

#### Activity books (dawseyeh, journey, family, islamic)

| # | Step | When | Notes |
|---|---|---|---|
| 1 | `child`: «لمن الكتاب» | always | Name as printed, gender, age; English name when the variant needs it; look for a new child (§c.4) |
| 2 | [`consent`] | no reusable character and no consent | unchanged text |
| 3 | [`photo`] | no reusable character and no photo | body says where the character appears in *this* book |
| 4 | [`character`] | a new drawing | Drawn at once in the product's default style (the first active style whose `lines` include the product line, by `sort`: 3D today). No style step. |
| 5 | [`family`]: «عائلة {name}» | family book only | §c.7 |
| 6 | `summary`: «المراجعة» | always | §c.8; «أضيفوا للسلة» / «احفظوا في السلة» |

Step counts:
- **New child:** 5 (family book: 6).
- **Child with a usable character:** 2 (family book: 3).

**Character reuse rule.** The server is the source of truth: `GET /api/shop/workbooks/needs` (§d chunk 8).
- Use the newest approved character whose style is in the product line's styles: 3d, watercolor or cartoon. `coloring` is never used.
- If there is none, draw one in the default style.
- A girl's character is used as drawn: hijab or not follows the parent's choice when it was drawn (Addendum 10 §8).
- The review step offers «ارسموا شخصية جديدة» if the parent wants another look. That is a normal drawing, using one of the free redraws.

**Per-book specifics:**
- **Dawseyeh:** English name always (every volume has the English name page).
- **Journey:** English name only for stages 2, 3 and the set.
- **Family:** the `family` step. Digits stay ١٢٣ (Q4).
- **Islamic:** no extra field. Gender drives «أنا مسلم صغير / أنا مسلمة صغيرة», shown on the review step.
- **All four:** the age check uses the variant's range:
  - KG1 4–5, KG2 5–6;
  - stages 3–4, 4–5, 5–6;
  - islamic V1–V2 and L1 4–6, V3–V5 and L2 6–8, R 4–8.

### c.4 The child step per product (exact proposed copy)

These are the Arabic texts. The English ones go into `en.json` with the same keys. All of them go to the language review (chunk 13).

| Key | Stories | Activity books |
|---|---|---|
| Frame title | «كتاب {name}» (before a name: «كتاب جديد») | the product's cover title: «دوسية {name}», «رحلة {name} الأولى», «مغامرات {name}», «قلبي يعرف الله · {name}» (before a name: the product name) |
| Step label | «بطل الحكاية» | «لمن الكتاب» |
| Title | «من بطل الحكاية؟» | «لمن هذا الكتاب؟» |
| Why (body) | «نكتب اسمه في الحكاية بالتشكيل، ونخاطبه بالصيغة الصحيحة، ونقترح ما يناسب عمره.» | «نطبع اسم طفلكم على الغلاف وفي صفحات الكتاب، ونكتب له التعليمات بالصيغة الصحيحة.» |
| Known children | «لأحد أطفالكم؟» (unchanged) | same |
| Name label | «اسم البطل» | «الاسم كما سيُطبع في الكتاب» |
| Name hint | «الاسم الذي تنادونه به، كما سيُكتب في الحكاية.» | dawseyeh/journey: «بالحروف العربية، فطفلكم سيتتبّعه ويكتبه في صفحات «اسمي».»; family: «يظهر في عناوين المغامرات وجواز السفر والشهادة.»; islamic: «يظهر على الغلاف وفي صفحة «هذا أنا» والشهادة.» |
| Name preview | «سيظهر العنوان هكذا: «{title}»» only when a theme is chosen | «سيظهر على الغلاف هكذا: «{cover}»» |
| English name (dawseyeh; journey 2–3/set) | — | label «الاسم بالأحرف الإنجليزية»; hint «في الكتاب صفحة يتتبّع فيها طفلكم اسمه بالإنجليزية. اكتبوه كما تحبون أن يتعلّمه.»; placeholder «مثال: Duha»; error «اكتبوا الاسم بالأحرف الإنجليزية فقط، دون أرقام أو رموز.» |
| Arabic-letters error (tracing books) | — | «اكتبوا الاسم بالحروف العربية، فهكذا سيتتبّعه طفلكم.» |
| Gender legend | «بنت أم ولد؟» | «بنت أم ولد؟» |
| Gender hint | «لنكتب الحكاية بصيغة المؤنث أو المذكر.» | islamic: «لنكتب في الشهادة: «أنا مسلمة صغيرة» أو «أنا مسلم صغير».»; others: «لنخاطب طفلكم بالصيغة الصحيحة: «أحسنتِ» أو «أحسنتَ».» |
| Age legend | «العمر» (chips 2–10) | «العمر» (chips 2–10) |
| Age hint | «لنقترح حكايات تناسب العمر، ونختار حجم الخط المناسب.» | «لنتأكد أن المستوى الذي اخترتموه يناسب العمر.» |
| Look (new child, or no usable character) | legend «كيف نرسم {name}؟», hint «تفاصيل قد لا تظهر في الصورة.», chips unchanged («ترتدي الحجاب» for girls, «تلبس/يلبس نظارة») | same |
| Likes, note | **not here** (Magic: story step) | **never** |
| Required error | «اكتبوا اسم الطفل واختاروا: بنت أو ولد، والعمر.» (unchanged) | same, plus the English-name error when needed |

**A known child** is shown as a confirmation card, not as a bare chip:
- «{name} · بنت · {age} سنوات» (ICU: `{age, plural, =2 {سنتان} few {# سنوات} other {# سنة}}`)
- «شخصيتها جاهزة ✓» with a thumbnail, or «لم نرسم شخصيتها بعد» (gendered)
- the saved English name when the product needs it (editable inline)
- «تعديل البيانات» opens name, gender and age (`PATCH`), with the note «تعديل الاسم أو العمر لا يغيّر الشخصية المرسومة.»
- CTA «نعم، الكتاب لـ{name}»

### c.5 Drawing steps: why we ask (copy)

- **Consent:** the text and version are unchanged (`parent-2026-09`), and it is shown only when a photo is needed.
- **Photo body** (replaces «وجه {name} من الأمام، في ضوء النهار.» and keeps the quality checks):

  | Product | Copy |
  | --- | --- |
  | stories | «نرسم شخصية {name} من هذه الصورة لتكون بطل كل صفحة. يكفي وجه واضح من الأمام في ضوء النهار.» |
  | dawseyeh | «نرسم شخصية {name} من هذه الصورة لتظهر على غلاف الدوسية وفي صفحات «اسمي» والشهادة.» |
  | journey | «نرسم شخصية {name} من هذه الصورة لتظهر على الغلاف وخريطة الرحلة والشهادة.» |
  | family | «نرسم شخصية {name} من هذه الصورة لتظهر في المغامرات وجواز السفر والشهادة.» |
  | islamic | «نرسم شخصية {name} من هذه الصورة لتظهر على الغلاف وفي جواز السفر والشهادة.» |

  Plus, for every product: «بعد موافقتكم نحفظ الشخصية لكتب {name} القادمة، دون تكلفة إضافية، ونحذف الصورة الأصلية خلال 24 ساعة.»
- **Style (stories only):** the text is unchanged. Each style card shows real pages from `samplesForStyle(style, theme)`.
- **Character, activity body:** «{gender, select, f {هكذا تظهر {name} في الكتاب: على الغلاف وفي صفحات مختارة.} other {هكذا يظهر {name} في الكتاب: على الغلاف وفي صفحات مختارة.}}» Stories keep «… في كل صفحات الكتاب».

### c.6 The story step (Magic additions)

Likes and the note move here, under the theme cards, prefilled from the child:
- legend «{gender, select, f {ماذا تحب {name}؟} other {ماذا يحب {name}؟}}» «(اختاروا حتى 3)»
- hint «نضيف لمسة منها إلى صفحة أو صفحتين من الحكاية.» This matches the prompt rule.
- the note keeps its current label and placeholder.

They are saved with `PATCH /children/{id}` before `startBook`.

Language chips «لغة الحكاية: العربية · English» appear only on `/en`, for Magic. Classic stays Arabic: its تشكيل is Arabic only.

### c.7 The family step («مغامراتي مع عائلتي»)

- **Title:** «من في عائلة {name}؟»
- **Why:** «نكتب أسماءهم في المهمّات وفي صفحة «عائلتي» والشهادة. أضيفوا من تريدون فقط، فكل عائلة مختلفة وجميلة.»
- **Family name:** label «اسم العائلة»; hint «يُطبع على الغلاف وجواز السفر: «عائلة …». إن تركتموه فارغًا نكتب: عائلة {name}.»
- **City:** label «المدينة»; hint «تظهر في مغامرتي السوق والطبيعة.»
  - Optional.
  - The renderer falls back to «مدينتنا» (chunk 9).
- **Members:** the existing rows from `components/workbook/FamilyDetails.tsx`, imported unchanged:
  - relation, first name (optional), adult/child for «فرد آخر», head-scarf;
  - up to 6;
  - the existing privacy line.
- **Prefill:** from what the product page sent (`item.personalization.family`, exposed by chunk 8).
- **Skip:** «تخطّوا هذه الخطوة», with the hint «نكتب في المهمّات «أحد الكبار» بدل الأسماء.»
- **Illustrated family:** when `family_characters_enabled` is on (it is off today), a toggle «ارسموا أفراد العائلة أيضًا (+30 ₪)» attaches the add-on and runs the existing `FamilyCharacters` steps. This is phase 2.

### c.8 The review step (activity books)

- **Title:** «راجعوا كتاب {name}»
- **Body:** «هذا ما سنطبعه. تأكدوا من الاسم والتفاصيل قبل السلة.»
- **Rows**, each with «تغيير» where it applies:
  - «الكتاب»: product · level/volume/stage · colours · format (labels from `workbook.values.*` / `valuesOf.*`). «تغيير» goes back to `/workbooks/<product>?<picks>`.
  - «الاسم على الكتاب»: {name}. «بالإنجليزية»: {name_en} (dawseyeh; journey 2–3).
  - «هكذا نخاطب {name}»: «{gender, select, f {أحسنتِ يا {name}!} other {أحسنتَ يا {name}!}}». Islamic: «في الشهادة: {gender, select, f {أنا مسلمة صغيرة} other {أنا مسلم صغير}}».
  - «الشخصية»: a thumbnail, plus the link «ارسموا شخصية جديدة».
  - «العائلة» (family book): «عائلة {family} · {count} أفراد», or «أحد الكبار».
  - «السعر».
- **Age check** (non-blocking, amber):
  - «{gender, select, f {هذا الكتاب مُعدّ لعمر {min}–{max} سنوات، و{name} عمرها {age}.} other {هذا الكتاب مُعدّ لعمر {min}–{max} سنوات، و{name} عمره {age}.}} يمكنكم المتابعة، أو اختيار مستوى آخر.»
- **«إضافات اختيارية»** (collapsed): the line's add-ons (sticker sheet, crayon kit, wipe-clean sleeve, gift box, printed answer key or parent guide), shown with the generalized `AddOnsStep` by cart-line id.
- **CTA:** «أضيفوا للسلة», or «احفظوا في السلة» when filling a line added in one tap.

### c.9 Cart, checkout and order summary

**Activity line:**
- Title from the cover pattern: «دوسية ضحى».
- Details: «KG2 · الجزء الأول · ملوّن · مطبوع». Then «الاسم بالإنجليزية: Duha», or «العائلة: 4 أفراد».
- The «تعديل» link opens `step=summary` for that line.

**Story line:** as today, plus the line (Classic/Magic) and «إهداء ✓».

**A line still waiting for the child:**
- «ينقصه: اسم الطفل وشخصيته» (activity) or «ينقصه: بيانات الطفل والمعاينة» (story).
- The bottom bar says «قبل متابعة الطلب، أكملوا بيانات الطفل لكتاب «{name}».»

**Checkout header:** «الخطوة الأخيرة: العنوان والدفع», with no "n of 12". A cart can hold several books.

**Order page** (`components/store/OrderView.tsx`): the same detail line per item.

---

## (d) Implementation plan: independent chunks

### Ownership rules

**Files owned by other agents:** do **not** edit these. Reading or importing them is fine.
- Activity showcase:
  - `web/components/workbook/WorkbookProduct.tsx`
  - `web/components/workbook/showcase/**`
  - `web/lib/workbook.ts`, `web/lib/workbook-previews.json`
  - `apps/web/public/workbooks/**`
  - `ActivityBookCard.tsx`
  - messages `workbookShowcase`
- Story showcase:
  - `web/app/[locale]/stories/**`
  - `web/components/store/LineCompare.tsx`
  - `web/components/site/StoryCard.tsx`
  - `web/lib/styleSamples.ts`, `apps/web/public/samples/**`
  - messages `storyShowcase`
  - Treat `web/components/story/StoryProduct.tsx` and `web/lib/story.ts` as theirs too. The story entry link (`createHref`) needs no change.

**Messages:** `apps/web/messages/{ar,en}.json` are shared files.
- Each chunk owns only the key subtrees listed for it.
- Each chunk works in its own worktree and edits only inside its subtrees.
- The lead merges, then runs `npx prettier --write messages/*.json`.
- Every new Arabic string also gets its English twin.

**Order:**
- Chunk 0 goes first, today.
- Chunks 1–10 can run in parallel against the interfaces below.
- Chunk 11 runs after the showcase agent finishes.
- Chunk 12 runs after 1–9; chunk 13 runs last.

### Chunk 0: hotfix, Islamic lines complete as activity books (first, about 1 hour)

- **Files:**
  - `web/lib/order.ts`: `ACTIVITY` ← `ACTIVITY_LINES` from `web/lib/shop.ts`. `editHref` sends islamic to `/workbooks/islamic-series`.
  - `tests/e2e/test_one_tap_cart.py`: add `islamic-series`; assert the completion URL has `product=`.
- **Result:** the Islamic line takes the existing activity path. There is no line or story step any more. Until chunk 2, the style step remains (with `line=magic`).

### Chunk 1: the flow model (pure TypeScript)

- **Files:**
  - new `web/lib/flows.ts`
  - new `web/lib/flows.test.ts`
  - `apps/web/package.json` (`"test": "node --test src/lib/*.test.ts"`; Node 24 strips types, so no new dependency)
  - `.github/workflows/ci.yml` (web job: `npm test`)
  - `Makefile` (`web-check` runs `npm test`)
- **Interface.** No `@/` imports, so `node --test` can load it.

  ```ts
  export type Kind = "story" | "activity";
  export type StepId = "child" | "line" | "consent" | "photo" | "style" | "character" | "companion"
    | "story" | "writing" | "review" | "format" | "addons" | "family" | "summary";
  export type FlowState = {
    kind: Kind;
    productLine: string | null;     // classic|magic|workbook|journey|family|islamic, null = story type not chosen
    child: { consent: boolean; photos: number } | null;
    reusable: boolean;              // the server's "needs" answer (activity) / an approved char in the wanted style (story)
    character: { approved: boolean } | null;
    book: { status: string; line: "classic" | "magic" } | null;
    stylePreset: boolean;           // story: style fixed by the story page or a single option
    companionOffered: boolean;      // catalog offers the drawn companion for this line
    asksFamily: boolean;            // product needs the family step
  };
  export const ACTIVITY_LINES: readonly string[]; // re-exported single source (same values as lib/shop.ts)
  export function kindOf(productLine: string | null): Kind;
  export function stepsFor(s: FlowState): StepId[];            // ordered, only the applicable ones
  export function resumeAt(s: FlowState): StepId;              // replaces furthest()
  export function canShow(step: StepId, s: FlowState): boolean; // replaces allowed()
  export function progress(steps: StepId[], step: StepId): { n: number; total: number };
  ```
- **Tests:** table-driven, one row per product and state, with the counts from §c.3. Also: `line` is never in an activity flow, and `summary` is never in a story flow.

### Chunk 2: the wizard shell (routing and progress)

- **Files:**
  - `web/components/create/CreateWizard.tsx`
  - `web/components/create/Frame.tsx` (props `n`, `total`; drop `TOTAL_STEPS`)
  - `web/components/create/companion/SubFrame.tsx`
  - `web/lib/create.ts`
  - `web/app/[locale]/create/page.tsx`
- **Messages:** `create.steps.*`, `create.stepOf`, new `create.titles.*` (frame titles per product).
- **Work:**
  - Use `flows.ts`. Read `product` and find its line from the catalog. Ignore a `line` param on activity flows.
  - Call `needs` (chunk 8) for activity products.
  - Route `family` and `summary` to chunk 5's components.
  - `addProduct` moves into the summary step's CTA.
- **Client calls in `lib/create.ts`** (exact signatures, so chunks 3, 5 and 6 can code against them):

  ```ts
  updateChild(id, patch: Partial<{ name: string; gender: "m"|"f"; age: number; interests: string[];
    note: string; hijab: boolean; glasses: boolean; name_latin: string }>) => api<Child>  // PATCH /api/create/children/{id}
  needs(sku: string, childId?: string) => api<Needs>                                   // GET /api/shop/workbooks/needs
  addWorkbook(body: { sku: string; child_id: string; item_id?: string; character_id?: string;
    name_en?: string; family?: FamilyPayload }) => api<Cart>                           // POST /api/shop/workbooks/cart
  ```

  `Child` gains `interests: string[]` and `name_latin: string | null`. `StartBook` gains `language`.

### Chunk 3: the child step

- **Files:**
  - `web/components/create/ChildStep.tsx`
  - new `web/components/create/KnownChild.tsx`
  - new `web/components/create/EditChild.tsx`
- **Messages:** `create.child.*`, new `create.who.*`.
- **Work:**
  - Implement §c.4. The props from the wizard are `kind`, `productLine`, `coverTitle`, `asksNameEn`, `tracesName` and `ages`.
  - Arabic-letters check for tracing books.
  - Latin check for the English name (`^[A-Za-z][A-Za-z' -]{0,39}$`).

### Chunk 4: the drawing steps' copy and style samples

- **Files:**
  - `web/components/create/ConsentStep.tsx`, `PhotoStep.tsx`, `StyleStep.tsx`, `CharacterStep.tsx`, `LineStep.tsx`
- **Messages:** `create.consent.*`, `create.photo.*`, `create.style.*`, `create.character.*`, `create.line.*`.
- **Work:**
  - Implement §c.5, with the body per `productLine`.
  - The style step imports `samplesForStyle` from `web/lib/styleSamples.ts`, falling back to the current `LOOK` art until that file lands.
  - `StyleStep` filters by the product's line, not by `line=magic`.

### Chunk 5: the activity-book steps

- **Files:**
  - new `web/components/create/activity/FamilyStep.tsx`
  - new `web/components/create/activity/SummaryStep.tsx`
  - new `web/components/create/activity/AgeCheck.tsx`
- **Imports only:**
  - `web/components/workbook/FamilyDetails.tsx` and `WorkbookCover.tsx`, plus their `workbook.family.*` and `workbook.values.*` messages;
  - `ItemAddOns` from chunk 7;
  - `soldAges` from `web/lib/workbook.ts` (read-only).
- **Messages:** new `create.activity.*`.
- **Work:** implement §c.7 and §c.8.

### Chunk 6: the story step (Magic likes, language)

- **Files:**
  - `web/components/create/StoryStep.tsx`
  - `web/components/create/CustomStoryForm.tsx` (only if the layout needs it)
- **Messages:** `create.story.*`.
- **Work:** implement §c.6. Save likes and the note with `updateChild`, then send `language` with `startBook`.

### Chunk 7: cart, checkout and order summaries

- **Files:**
  - `web/components/order/CartBody.tsx`, `CartScreen.tsx`, `CheckoutScreen.tsx`
  - `web/components/order/AddOnsStep.tsx`: generalize to a cart-line id; export `ItemAddOns`
  - `web/components/store/OrderView.tsx`
  - `web/lib/order.ts` (after chunk 0): `completeHref` without `line=magic`; `editHref` → `step=summary`
  - new `web/lib/variantSummary.ts`
- **Messages:** `orderPath.cart.*`, `orderPath.checkout.*`, `orderPath.order.*`.
- **Work:**
  - Implement §c.9.
  - Lock the Classic dedication add-on while a dedication exists (S6).

### Chunk 8: API (children, the workbook line, needs, data fixes)

- **Files:**
  - `api/routers/create.py`:
    - `PATCH /children/{id}`, guardian only, with an audit entry;
    - `ChildOut` gains `interests` and `name_latin`;
    - the style × line check at `POST /characters` when `line`/`sku` is passed;
    - delete-my-data also clears `family`, `name_en` and `character_id` on order items (`:175,202`).
  - `api/routers/shop.py`: `add_workbook` gains `character_id?` and `name_en?`, uses the reuse rule, and saves `child.name_latin`. New `GET /workbooks/needs?sku&child_id`, which returns:

    ```json
    {"line": "journey", "product": "learning-journey", "ages": [4, 5],
     "asks": {"name_en": true, "family": false},
     "character": {"reuse_id": "…|null", "draw_style": "3d"},
     "child": {"name_traceable": true, "name_latin": "Duha|null"}}
    ```

  - `api/store/workbooks.py`: the needs rules, read from data:
    - `name_en`: dawseyeh always; journey for `stage ∈ {2, 3, set}`;
    - `family`: family line;
    - styles from the `ArtStyle.lines` table.
  - `api/store/router.py`:
    - `PATCH /cart/items` keeps `family` and `character_id`;
    - the cart-line output gains `child` (name), `name_en` and `family` for the owner.
  - `api/store/addons.py`: offer `checkout`/`format` add-ons for activity lines by cart line.
  - `packages/core/src/qamra_core/db/models.py`: `Child.name_latin` (String 40, nullable).
  - A new Alembic migration for that column. The same migration adds `islamic` to the `lines` of 3d, watercolor and cartoon.
  - Name validation for tracing books calls `qamra_workbook.render.pages.workbook_front.can_trace(name)` (chunk 9). Until chunk 9 lands, use a local Arabic-letter regex.
- **Tests:**
  - `apps/api/tests/test_create.py`, `test_workbooks.py`, `test_cart_one_tap.py`
  - new `apps/api/tests/test_order_flow_needs.py`

### Chunk 8: the API contract as built (2026-10-08)

Migration `18342eeba4e4` (after `0c695b89fde0`). Every error body is `{"error": {"code", "message": {"ar", "en"},
"details"?}}`: show `message[locale]` as it is.

**`PATCH /api/create/children/{id}`** (guardian only; anyone else gets 404, signed out 401). Send only what
changes:

```ts
{ name?: string /*1–40*/; gender?: "m"|"f"; age?: number /*2–10*/; interests?: string[] /*≤3, ≤30 chars*/;
  note?: string /*≤60*/; hijab?: boolean; glasses?: boolean; name_latin?: string|null /*"" or null clears*/ }
```

- `interests` and `note` are one list on the child (the note last, as on `POST /children`): sending either
  replaces it, so send both together.
- For a boy, `hijab` is always saved as false. Unknown fields → 422.
- Errors: `invalid_input` (422, `details.fields`); `name_en_invalid` (422, `fields: ["name_latin"]`): the
  name must be in English letters, `^[A-Za-z][A-Za-z' -]{0,39}$` after accents are dropped (é → e).
- The drawn character is never touched. The audit log gets `child.updated` with the changed field names only.
- The child's activity lines in an open cart (lines without a book) take the new name, gender, age and look,
  and the new English name when that book prints one.
- Returns `ChildOut`, which (here and on every `/children` endpoint) now has
  `interests: string[]` and `name_latin: string|null`.

**`GET /api/shop/workbooks/needs?sku=<sku>[&child_id=<id>]`.** Public without `child_id`. With it: the
caller's own child (signed out 401, someone else's 404). An unknown SKU, a story SKU or one not on sale gives
404 `unknown_product`.

```ts
type Needs = {
  line: "workbook"|"journey"|"family"|"islamic"; product: string; sku: string; options: Record<string,string>;
  ages: [number, number] | null;   // what the variant is made for (the review step's non-blocking check)
  traces_name: boolean;            // workbook, journey: the Arabic name is traced → ask for Arabic letters
  asks: { name_en: boolean; family: boolean };
  character: { reuse_id: string|null; draw_style: string|null /*"3d"*/; styles: string[] /*3d, watercolor, cartoon*/ };
  child: { id: string; name: string; name_traceable: boolean;
           name_problem: "not_arabic"|"not_traceable"|null; name_latin: string|null } | null;
};
```

- `asks.name_en`: «دوسية التأسيس» always; «رحلتي الأولى» stages 2, 3 and the set.
- `asks.family`: «مغامراتي مع عائلتي».
- `ages`: KG1 4–5, KG2 5–6; stages 3–4, 4–5, 5–6, set 3–6; family 3–7; islamic V1, V2, L1 4–6, V3–V5, L2 6–8,
  R and the set 4–8.
- `reuse_id` is the child's newest approved character in one of `styles` (never `coloring`). When it is null,
  draw one in `draw_style` without a style question:
  `POST /api/create/children/{id}/characters {style: draw_style, sku}`.
- `POST /characters` now takes optional `line` or `sku`. A style that line doesn't accept → 422 `invalid_style`.
- The name rules are `qamra_workbook.names` (chunk 9), so `name_traceable` is true for رؤى.

**`POST /api/shop/workbooks/cart`**:

```ts
{ sku: string; child_id: string; qty?: number; item_id?: string; character_id?: string; name_en?: string;
  family?: FamilyPayload }
```

- **Character:** the given one must be this child's (else 404 `not_found`), approved (else 409
  `character_not_approved`) and in an accepted style (else 409 `character_style`). Without it, the newest
  reusable one is used; if there is none → 409 `character_not_approved`.
- **Name:** for the tracing books, a name that isn't in Arabic letters → 422 `name_not_arabic`. One with a
  letter the tracing hand doesn't have → 422 `name_not_traceable`. Both have `details.fields: ["name"]`; fix it with
  `PATCH /children/{id}`.
- **English name:** when the book prints it, send `name_en`, or the child's saved `name_latin` is used. If
  there is neither → 422 `name_en_required`. An invalid one → 422 `name_en_invalid`. Both have
  `details.fields: ["name_en"]`. A `name_en` that is sent is saved on the child (`name_latin`) for the next
  book.
- **The line keeps** `personalization.character_id`, plus `name_en` when printed, plus `family` for the family
  line. With `item_id`, the family sent on the product page stays unless a new `family` is sent.
- **Checkout** copies the line's personalization onto the order line.

**Cart line (`CartItemOut`), new fields** (the cart's owner only):
- `missing: ("name_en"|"name")[]`: a line filled before these rules that still lacks the English name, or
  whose name can't be traced;
- `child_name_en: string|null` (`name_en` is already taken by the product's English name);
- `family: {name, city, members: [{relation, role, name, adult, scarf}]} | null`;
- `character_id: string|null`.

`needs_details` is also true when `missing` is not empty. Checkout's `details_missing` items then carry
`missing` too.

**Cart edits.** `PATCH /api/store/cart/items/{id}` with `personalization` keeps `character_id`, `name_en` and
`family`.

**Order tracking.** Each item in the `GET /api/store/orders/{code}?phone=` response now also has the cart's detail fields, as
frozen on the order line: `line`, `product`, `sku`, `options`, `theme`, `style`, `book_title`, `child_name_en`,
`family` and `addons: [{slug, name_ar, name_en, qty}]`.

**Add-ons by cart line:** `GET`/`PUT /api/store/cart/items/{id}/addons` works for every line, activity books
included. Only active add-ons are offered. After the deactivations below, the only add-ons offered for activity books are:
- `printed-answer-key` for journey spiral;
- `printed-parent-guide` for islamic softcover.

A line that still holds an add-on that has since been switched off drops it in the cart, on edit and at
checkout; the line itself is never refused.

**Privacy.** «احذفوا كل بيانات طفلي» also removes `family`, `name_en`, `character_id` and `custom_brief` from
the child's order lines. The prices, quantities and SKUs stay.

**Owner's decisions in the catalog** (`content/store/catalog.yaml` and the migration). Switched-off items are made
inactive, not deleted:
- the 8 black-and-white «دوسية التأسيس» SKUs (`wb-kg1|kg2-v1|v2|v3|set-bw-spiral`);
- the 11 add-ons in «Deactivate (exact slugs)» below (`editable-files` was already off);
- the answer key goes to the printer only when bought (F1), with its label (F2) and the new
  «إجابات الأنشطة مطبوعةً» texts (F3).

### Chunk 9: the engine and workers use what the flow now collects

- **Files:**
  - `wb/render/pages/workbook_front.py`:
    - new `can_trace(name) -> bool`;
    - handle ؤ and ئ (add the forms, or draw those letters with the dotted font);
    - never raise on a name.
  - `wb/journey_book.py`: transliteration only as a last resort, flagged on the book.
  - `worker/journey_book.py` and `worker/family_book.py`: `name_en` from the item, else `Child.name_latin`; city fallback.
  - `content/family-book/plan.yaml`: the «مدينتنا» fallback in the market and nature texts.
  - Tests in `packages/workbook/tests/`.

### Chunk 10: «دوسية التأسيس» per-order render (independent, larger)

- **Files:**
  - new `worker/workbook_book.py` (render per volume and set, from the item, like `journey_book`)
  - `wb/render/workbook.py`: accept a real child, sheet, `name_en`, numerals and cover; B&W if Q1 says so
  - `api/routers/admin_orders.py`: enqueue on confirm
  - `api/routers/admin_books.py`: `LINE_JOBS["workbook"]`
  - tests
- See Q1 for what to do with the B&W variants until then.

### Chunks 1, 2, 3 and 5: the interface as built (2026-10-08)

**The flow model** (`web/lib/flows.ts`, no `@/` imports; `npm test` runs `web/lib/*.test.ts` with `node --test`):
- As specified: `Kind`, `StepId`, `FlowState`, `ACTIVITY_LINES` (the test checks it equals `lib/shop.ts`), `kindOf`, `stepsFor`, `resumeAt`, `canShow`, `progress`.
- `FlowState.plan`: the optional steps the flow pinned, kept in the URL as **`plan`** (`line`, `consent`, `photo`, `style`, `character`, or `reuse`). The wizard writes it when it leaves the child step (or, for a story, the type step), so giving the consent or approving the character never drops a step from «n من N». `planFor(state, lineAsked)`, `parsePlan`, `formatPlan`.
- The mirror of the server's needs rules, used for the first paint and as the fallback: `asksNameEn(line, options)`, `agesFor(line, options)`, `outsideAges`, `tracesName(line)`, `isArabicName` (Arabic letters; spaces or hyphens between words; tashkeel ignored) and `isLatinName` (`^[A-Za-z][A-Za-z' -]{0,39}$`).

**The wizard** (`CreateWizard.tsx`):
- Activity books: `/create?product=<sku>[&item=<line>][&child=<id>][&step=summary]`. A `line` in the URL is ignored. The steps are child → [consent → photo → character] → [family] → summary. A new character is drawn in `needs.character.draw_style` (3D) as soon as a photo is saved; there is no style step.
- Stories: child → [line] → [consent] → [photo] → [style] → [character] → [companion] → story → writing → [review] → format → add-ons. The type step now comes right after the child.
- Back on every drawing step goes to the previous step of this flow.
- **Frame titles and counts come from the flow:** `FlowFrameContext` in `Frame.tsx` gives `{ title, n, total, close }`, and `Frame` and the companion `SubFrame` read it, so the steps' own `n` props are ignored. Other headers can call `useFlowFrame()` (chunk 7: `AddOnsStep`'s `FlowHeader` could show «n من N»). `TOTAL_STEPS` stays exported, deprecated, only for `CheckoutScreen` until §c.9 drops "n of 12".
- ✕ goes to `/cart` when the flow fills a cart line, else to `/account`.

**API calls** (`web/lib/create.ts`, as specified): `updateChild`, `needs`, `addWorkbook`, plus `missingEndpoint(r)` (a bare 404 or 405 with no error body).
- **Marked fallbacks, used only while chunk 8 is not deployed:**
  - `needs`: the same rules locally (styles from the catalog; `islamic` gets 3d, watercolor and cartoon; `coloring` is never reused).
  - `PATCH /children/{id}`: the English name is kept for the visit and sent as `name_en` with the cart line.
- **`addWorkbook` sends:** `character_id` (the reused or newly approved one), `name_en` when the book asks it, and `item_id`.
  - It sends `family` for the family book. An empty family is sent only when the line's own `family` could be read from `GET /api/store/cart`, so a family given on the product page is never erased by an older API.
  - The family step keeps its form in `sessionStorage` (`qamra-family:<item or sku>`), so a reload does not lose it. It is cleared after the line is saved.
- **`ChildStep` props:** `kind`, `productLine`, `known`, `initial`, `preview(name, gender)`, `asksNameEn`, `traces`, `ready(child)`, `nameEnOf(child)`, `onSelect`, `onEdited`, `onDone(child, { nameEn }) → error | null`.
  - A known child is a confirmation card (`KnownChild`): the English name (editable), the look when a new character will be drawn, and «تعديل البيانات» (`EditChild`, a `PATCH`).
- **Review step** (`activity/SummaryStep.tsx`):
  - The add-ons of the line come from chunk 7's `ItemAddOns`, shown only when the flow fills an existing line (`item`). A new line gets its add-ons in the cart.
  - The age check (`AgeCheck`) links back to the product page with the same picks.
- **Messages:** `create.steps` (`child`, `who`, `family`, `summary`), `create.titles.*`, `create.child.*` (the story copy; `likes`, `likesList`, `note` and `notePlaceholder` are kept for the story step), `create.who.*` and `create.activity.*`.
  - The English strings put the Arabic text the book prints inside `<ar>…</ar>`, rendered as `<bdi dir="rtl">` so it stays in order.

### Chunk 11: product page (after the activity-showcase agent finishes)

- **Files:**
  - `web/components/workbook/WorkbookProduct.tsx`: replace the inline `FamilyDetails` with one line, «تضيفون أسماء العائلة بعد اختيار الطفل». For signed-in parents, optionally add a secondary «ابدؤوا لطفلكم الآن» → `/create?product=<sku>`.
  - `web/components/workbook/AddWorkbook.tsx`: stop sending `family`.
- **Messages:** `workbook.familyLater`.

### Chunk 12: end-to-end tests

- **Files:**
  - new `tests/e2e/test_order_flows.py`
  - `tests/e2e/e2e_flow.py`
  - `api/routers/e2e.py`: new fixtures — a child with an approved placeholder character; "approve a placeholder character for this child" after the photo, so no AI runs.

### Chunk 13: language review and docs

- A language-review agent checks every new and changed string in `ar.json` and `en.json` (memory rule).
- Then update `docs/decisions.md`, `docs/CHANGELOG.md`, `docs/feature-matrix.md` and `docs/e2e.md`.

### File ownership at a glance

| Chunk | Owns |
|---|---|
| 0 | `web/lib/order.ts` (first), `tests/e2e/test_one_tap_cart.py` |
| 1 | `web/lib/flows.ts`, `web/lib/flows.test.ts`, `apps/web/package.json`, `.github/workflows/ci.yml`, `Makefile` |
| 2 | `CreateWizard.tsx`, `Frame.tsx`, `companion/SubFrame.tsx`, `web/lib/create.ts`, `app/[locale]/create/page.tsx`; msgs `create.steps/stepOf/titles` |
| 3 | `ChildStep.tsx`, `KnownChild.tsx`, `EditChild.tsx`; msgs `create.child/who` |
| 4 | `ConsentStep.tsx`, `PhotoStep.tsx`, `StyleStep.tsx`, `CharacterStep.tsx`, `LineStep.tsx`; msgs `create.consent/photo/style/character/line` |
| 5 | `create/activity/*`; msgs `create.activity` |
| 6 | `StoryStep.tsx`, `CustomStoryForm.tsx`; msgs `create.story` |
| 7 | `order/CartBody.tsx`, `CartScreen.tsx`, `CheckoutScreen.tsx`, `AddOnsStep.tsx`, `store/OrderView.tsx`, `web/lib/order.ts` (after 0), `web/lib/variantSummary.ts`; msgs `orderPath.*` |
| 8 | `api/routers/create.py`, `api/routers/shop.py`, `api/store/{workbooks,router,addons}.py`, `qamra_core/db/models.py`, new migration, API tests |
| 9 | `wb/render/pages/workbook_front.py`, `wb/journey_book.py`, `worker/{journey,family}_book.py`, `content/family-book/plan.yaml`, workbook tests |
| 10 | new `worker/workbook_book.py`, `wb/render/workbook.py`, `api/routers/admin_orders.py`, `api/routers/admin_books.py` |
| 11 | `WorkbookProduct.tsx`, `AddWorkbook.tsx`; msgs `workbook.familyLater` (after the showcase agent) |
| 12 | `tests/e2e/test_order_flows.py`, `tests/e2e/e2e_flow.py`, `api/routers/e2e.py` |

---

## (e) Test plan

### Unit tests (web, `node --test`, chunk 1)

`flows.test.ts` checks, for every product and child state (no child, new child, consent but no photo, photo but no character, usable character):
- the step list;
- `resumeAt`;
- «n من N».

Hard rules it asserts:
- no `line`, `style`, `companion` or `story` step in any activity flow;
- no `summary` or `family` step in story flows;
- `family` only for the family line;
- `ACTIVITY_LINES` includes `islamic`.

### API tests (pytest)

- `PATCH /children/{id}`:
  - the owner only (another parent gets 404);
  - the field limits (age 2–10, `name_latin` Latin only);
  - an audit row is written;
  - the character is not touched.
- `GET /workbooks/needs`:
  - `name_en` for dawseyeh and journey 2/3/set, not for journey 1, family or islamic;
  - `family` only for the family line;
  - `reuse_id` skips a `coloring` character and picks the newest 3d/watercolor/cartoon one;
  - `draw_style` is `3d`;
  - `name_traceable` is false for «رؤى» before chunk 9 and true after.
- `POST /workbooks/cart`:
  - a `character_id` of another child → 404;
  - a coloring or unapproved character → 409;
  - `name_en` is required for dawseyeh (422 with a friendly code);
  - `name_en` is saved on the line and on the child;
  - `item_id` keeps the family given on the page;
  - the islamic SKU fills an islamic line.
- `PATCH /cart/items` keeps `family` and `character_id`.
- Delete-my-data clears the family, `name_en` and `character_id` on order items.
- The migration: `islamic` is in the 3d, watercolor and cartoon `lines`.
- Activity add-ons are offered by cart line (sticker sheet for islamic, wipe-clean sleeve for spiral only).
- Checkout still refuses a waiting line (`details_missing`).
- Chunk 10: confirming an order with a workbook item enqueues the job, and the job renders a fake child with `name_en`.
- Chunk 9: `spell()` and `can_trace()` on رؤى, لؤي, هيئة, «نور الهدى» and Adam. The journey English page uses `name_en` from the item.

### End-to-end (Playwright, 390 px, Arabic; `tests/e2e/test_order_flows.py`; no AI calls)

| Test | Family | Checks |
|---|---|---|
| `test_islamic_line_completes_as_an_activity_book` | islamic | one tap V1 → «أكملوا» → known child → review → cart line filled; the page never shows «أي كتاب تريدون», «قمرة كلاسيك», «ماذا تحب», «أسلوب الرسم», «إلى أين»; «الخطوة 2 من 2»; the review shows «أنا مسلمة صغيرة» |
| `test_workbook_asks_the_english_name_and_shows_the_level` | dawseyeh | KG2 volume 1 → the child step has «الاسم بالأحرف الإنجليزية» (Latin validation) → the review shows «KG2 · الجزء الأول» → the cart line shows the same |
| `test_journey_stage_1_does_not_ask_the_english_name` | journey | stage 1: no English field; stage 2: field shown |
| `test_family_book_family_step` | family | details given on the page are prefilled; add a member and a city → the review shows «عائلة … · 3 أفراد» |
| `test_new_child_activity_flow_draws_once` | activity | new child → consent → photo → (fixture approves a placeholder) → review; 5 steps; no style step |
| `test_classic_story_asks_no_interests` | story | the story page «جرّبوا المعاينة» → the child step has no likes or note; no line step; «من 8» |
| `test_magic_story_asks_interests_on_the_story_step` | story | Magic: likes on the story step, saved to the child |
| `test_age_check_warns_but_does_not_block` | activity | a 3-year-old with KG2 → amber note → can still add |

---

## (f) Open questions for Tareq

Each one has a default that we use unless Tareq says otherwise.

1. **«دوسية التأسيس» is sold but nothing makes a child's copy (§0.3-1).**
   - Default: build the order job now (chunk 10) and keep it on sale.
   - Hide the black-and-white variants (49 ₪ and the 129 ₪ set) until a B&W interior exists.
   - Any order that arrives before then is rendered by hand by staff.
2. **Art style for activity books.**
   - Default: no style question. Reuse any approved 3D, watercolor or cartoon character.
   - A new drawing is 3D, as Tareq said: "3D for the stories and the activity books".
3. **Family details move from the product page into the flow** (the «عائلة ضحى» step, chunk 11 after the showcase work).
   - Default: yes. The product page keeps one line saying they come after choosing the child.
4. **Digits in activity books.**
   - Default: Arabic-Indic (١٢٣), not asked, as the Palestinian KG uses.
   - The engine can print 123 if you want the choice later.

**Decided by Tareq (2026-10-07): all four defaults above are confirmed.** (1) build the «دوسية التأسيس» order job
and hide the black-and-white variants until a B&W interior exists; (2) no art-style question for activity books —
reuse any approved character, a new one is drawn in 3D; (3) the family details become the «عائلة …» step in the
order flow; (4) ١٢٣ digits, not asked.

---

## Add-ons: what is deactivated (2026-10-07)

Tareq: «أي إضافات لازم تذكرها من ضمن المنتج مع صور إلهم». His decisions:
- the physical add-ons we have no stock of (`gift-box`, `wipe-sleeve`, `crayon-kit`) are hidden now;
- any add-on that nothing in the system can produce is hidden until it can be produced.

So every add-on in `content/store/catalog.yaml` `addons:` was traced from the cart to what is actually made: the
order job, the PDF engine, the print batch (manifest, printer email, `/api/printer/…` files) and the admin.
Paths as in the header; line numbers from commit `0d85b87`.

### What the print batch carries for an add-on

- The manifest (`api/print_batches.py:128-160`) has, per book: `format` (the hardcover upgrade turns softcover
  into hardcover, `qamra_core/printing.py:69-73`), `copies` (×(1+extra copies), `printing.py:76-78`), the interior
  and cover PDFs, and `inserts` = **every** file in `book.generation["files"]` (`print_batches.py:151`).
- Every other add-on reaches the printer **only as its slug** in the CSV column `extras` (`printing.py:81-86`).
  A slug is not a print file: nothing renders a poster, a coloring interior or a sticker sheet for it.

### Audit

| Slug | Lines | Verdict | Evidence | Decision |
|---|---|---|---|---|
| `hardcover-upgrade` | classic (softcover) | **DELIVERABLE** | `printing.py:69-73` → manifest `format: hardcover` (`print_batches.py:144`); the one cover wrap already has the board allowance (`packages/ai/…/pipeline/layout.py:45,59-64`) | keep |
| `gift-box` | all printed | physical, no stock | slug in `extras` only | **hide** (owner) |
| `dedication-page` | classic (+5 ₪), magic (included) | **DELIVERABLE** | attached on the story step (`api/routers/create.py:678-679`); printed on page 1 with the parent's words (`packages/ai/…/pipeline/assemble.py:241-250`, `qamra_pdf/spec.py:47`) | keep |
| `drawing-companion` | magic (included) | **DELIVERABLE** | attached on the companion step (`create.py:680-688`); the companion is on the pages and on «وهكذا وُلد صاحبي» (`layout.py:7,213-214`, `assemble.py:257-266`) | keep |
| `extra-character` | classic, magic | **NOT DELIVERABLE** | no step can attach it (`step: character`; the add-ons screen offers only `format`/`checkout`, `api/store/addons.py:23,69`); no story or image input for a second character; only listed as "not printed" (`printing.py:25`) | **hide** |
| `family-voice` | classic, magic | **DELIVERABLE** | recording and listening flow (`api/routers/voice.py`, `voice_public.py`, `web/app/[locale]/books/[id]/voice`, `web/app/[locale]/v/[token]`); the final render prints a QR per story page (`worker/…/voice.py:9-21`, `worker/books.py:700`, `assemble.py:235,288`) | keep |
| `extra-copy` | classic, magic | **DELIVERABLE** | `printing.py:76-78` → manifest `copies` (`print_batches.py:146`) | keep |
| `coloring-version` | classic, magic | **NOT DELIVERABLE** | nothing renders a line-art interior of a story (no "coloring" in `worker/`, `pipeline/`, `qamra_pdf/`); the coloring book itself is off for the same reason (`catalog.yaml:54`) | **hide** |
| `cover-poster` | classic, magic | **NOT DELIVERABLE** | no poster file: the printer gets the slug and the book's 21×21 wrap cover (spine and back included), not an A3 print file | **hide** |
| `express` | printed lines | **PARTIAL** | a daily cap is enforced at checkout (`api/store/router.py:686-699,751-754`) and the slug shows in the admin order list and packing slip; but nothing puts the book first (generation, approval queue, print batch), and there is no printer agreement for 48 h | **hide**: not a small gap |
| `digital-copy` | classic, magic (printed) | **DELIVERABLE** | added free and automatically to a printed book (`api/store/catalog.py:181-189`); the owner's web reader and share link work for every finished book (`api/routers/reader.py:188-309`). It is the web reader, **not** a PDF download | keep |
| `wipe-sleeve` | workbook, journey (spiral) | physical, no stock | slug only | **hide** (owner) |
| `sticker-sheet` | workbook, journey, family, islamic | **NOT DELIVERABLE** | no reward sticker sheet is rendered for workbook, journey or islamic; the family book's own sticker sheet is already in every copy (see below), so the add-on would be a second copy of nothing new | **hide** |
| `crayon-kit` | workbook, journey, family | physical, no stock | slug only | **hide** (owner) |
| `audio-qr` | workbook | **NOT DELIVERABLE** | no page of «دوسية التأسيس» has audio (the QR engine, `wb/render/engine.py:114`, is used by the journey only), and the dawseyeh has no per-order render yet (§0.3-1) | **hide** |
| `parent-guide` | workbook (free PDF) | **NOT DELIVERABLE** | no teacher/parent guide file exists for buyers (`docs/workbook/educator-kg*.md` are the internal plan for the educator's sign-off) and there is no download for it | **hide** |
| `printed-answer-key` | journey (spiral) | **PARTIAL, small gap** | the order job renders `answer-key.pdf` for every stage (`worker/journey_book.py:125-129`) and it reaches the printer as an insert (`print_batches.py:151`, `routers/printer.py:88`). Gaps: it is sent for **every** journey order, bought or not, and the printer email labels it with the raw name `answer-key` (`printing.py:48-52`) | **keep**, with fixes F1–F2 |
| `family-characters` | family | **PARTIAL** | the worker draws approved members into the book when the item has the add-on (`worker/family_book.py:105-131`); but the drawing flow is behind `family_characters_enabled` (off, `api/routers/family_members.py:63`) and nothing can attach the add-on to a cart line (`addons.py:23`) | **hide** until the family step (§c.7, phase 2) |
| `editable-files` | family | **NOT DELIVERABLE** | nothing produces source files (`printing.py:28`); already `active: false` | **hide** (already) |
| `printed-parent-guide` | islamic (softcover) | **PARTIAL, small gap** | the order job renders each volume's `answer-key.pdf` (`worker/islamic_book.py:200-209`; all six volumes have one) and it reaches the printer as an insert. Gaps: as for the journey (F1–F2), and the description promises «صفحات الأهل» but the file has only the solved activity pages (`wb/render/engine.py:135-141`); the parents' pages are inside the book itself | **keep**, with fixes F1–F3 |

### Deactivate (exact slugs)

```
gift-box  wipe-sleeve  crayon-kit                      # physical, no stock (owner)
extra-character  coloring-version  cover-poster        # nothing produces them
sticker-sheet  audio-qr  parent-guide  editable-files  # nothing produces them (editable-files is already off)
express  family-characters                             # partial: the gap is not small
```

### Stay on

```
hardcover-upgrade  dedication-page  drawing-companion  family-voice  extra-copy  digital-copy
printed-answer-key  printed-parent-guide               # only with F1–F3 below
```

**Small fixes for the two answer-key add-ons** (API/worker owner, same migration round). If they can't land with
the deactivation, hide these two as well.
- **F1:** `build_manifest` puts `answer-key` in `inserts` only when the item has `printed-answer-key` or
  `printed-parent-guide` (`api/print_batches.py:151`).
- **F2:** add a label: `INSERT_LABELS["answer-key"] = "مفتاح الإجابات (كتيّب منفصل)"` (`qamra_core/printing.py:48`).
- **F3:** `printed-parent-guide` text, to match what is printed:
  - `name_ar` «إجابات الأنشطة مطبوعة», `name_en` "Printed activity answers";
  - `description_ar` «إجابات أنشطة الكتاب في كتيّب منفصل للأهل»;
  - `description_en` "The answers to the book's activities, in a separate booklet for parents".

### What each product already includes (verified in the renderers)

| Product | Included | Where it comes from |
|---|---|---|
| قمرة كلاسيك | title page with a dedication to the child (the parent's own words are the +5 ₪ add-on) | `assemble.py:241-250`; `pipeline/classic.py:591` |
| قمرة سحري (and the custom story) | the drawing companion and the dedication page | `catalog.yaml` `included_addons`, `create.py:678-688` |
| رحلتي الأولى للتعلّم | «هذا الكتاب لـ…» owner page, the journey map, a certificate at the end, audio QR codes on the pages that have sound | `out/journey/stage-*/png-book/p001,p002,p118`; `wb/render/pages/journey_frame.py:33`; `wb/render/engine.py:114`; `api/routers/journey_audio.py` |
| مغامراتي مع عائلتي | **printed apart:** a sticker sheet (passport badges, rewards, routine icons) and two card-stock sheets: play money and recipe cards; memory, question and role cards and finger puppets. **In the book:** the family passport, «عائلتي» page and a certificate | `wb/render/family_order.py:115-143`; `printing.py:48-52`; `worker/family_book.py:214-226`; `out/family-book/inserts/png`, `png-book-21x28/p003,p004,p112` |
| قلبي يعرف الله | in every volume: «هذا أنا», the young Muslim's passport (a stamp circle per unit), a «للأهل» page after each unit, and the certificate at the end | `wb/render/islamic_volume.py:114-140`; `content/islamic/plan.yaml:82-87`; `out/islamic/v1/png` |
| دوسية التأسيس | owner page, name-tracing pages (Arabic and English), the certificate | `wb/render/pages/workbook_front.py:97,110`; `wb/render/foundation.py:24`. Not yet made per order (§0.3-1, chunk 10) |

**Side findings (not add-ons, for the owners of those books):**
- The Islamic passport draws "ghost" stamp circles «to stick the real one over» (`wb/render/pages/islamic_keepsake.py:41`, `content/islamic/samples.yaml:147`).
- The journey map has a dashed circle for the child's sticker (`journey_frame.py:50`).
- No sticker sheet is made for either book. The child can draw or colour the circle, but the page asks for a sticker.

### Pictures for the product pages and the add-ons step: `web/lib/addonsMedia.ts`

Rendered locally from our own engines and outputs, with no AI calls, then composed as product mockups (WebP, 640 px):
- `apps/web/public/addons/<slug>.webp`: one per add-on that stays;
- `apps/web/public/included/<product>/<item>.webp`: the included items.

**How to use it** (chunk 5's review step, chunk 7's `AddOnsStep`/`ItemAddOns`, the product pages):

```ts
import { addonMedia, includedItems, type AddonMedia, type IncludedItem } from "@/lib/addonsMedia";

const media = addonMedia[addon.slug];          // AddonMedia | undefined: {src, alt_ar, alt_en}
// show the picture only when media exists; a hidden add-on has no entry and is never offered anyway
<Image src={media.src} alt={locale === "ar" ? media.alt_ar : media.alt_en} width={640} height={480} />

const items = includedItems[product.slug] ?? []; // IncludedItem[]: {src, title_ar, title_en, desc_ar, desc_en}
// «يأتي مع الكتاب» / "Comes with the book": a small grid of these on the product page and the review step
```

- Keys:
  - `addonMedia` is keyed by add-on slug;
  - `includedItems` by product slug (`classic-book`, `magic-book`, `magic-custom-story`, `learning-journey`,
    `family-adventures`, `islamic-series`, `foundation-workbook`).
- The texts are short and language-reviewed. They describe the printed thing, never a delivery time or stock.
- The module has no other imports, so a `node --test` file can load it.
- The story pages (`stories/page.tsx`, `stories/[slug]/page.tsx`) already pass `media={addonMedia}` to
  `LineCompare` and `StoryProduct`.

**What the pictures are made from** (all local, no paid calls):

| Pictures | Source |
|---|---|
| `addons/hardcover-upgrade`, `extra-copy`, `dedication-page`, `family-voice`, `digital-copy` | «ليلى في أوّل يوم بالروضة»: the published example's pictures (with their «نموذج» mark) laid out by the story pipeline as a final book (dedication text, family-voice QR), then the `qamra_pdf.mockups` CSS book scenes. The QR in the picture opens `/how-it-works`. The phone in `family-voice` is the real listening page (`out/samples/phase-5/voice-listen.png`). |
| `addons/drawing-companion` | A test drawing (`packages/ai/tests/fixtures`) beside the book. It shows the drawing, **not** a drawn companion: no companion drawn from a child's drawing exists yet, and making one needs a paid image call. |
| `addons/printed-answer-key`, `printed-parent-guide` | The cover and `answer-key.pdf` of journey stage 1 and of Islamic V1 (a print build, so there is no draft mark) |
| `included/classic-book/*` | Page 1 (default dedication) and the «للأهل» page of the same book. Magic and the custom story reuse the add-on pictures and this «للأهل» picture. |
| `included/learning-journey/*`, `family-adventures/*`, `islamic-series/*`, `foundation-workbook/*` | The engines' renders for the sample child «ليان»: the journey stages, the family book and its insert PDFs, Islamic V1 (print build), and KG1 volumes 1 and 3 |
