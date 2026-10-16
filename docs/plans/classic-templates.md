# «قمرة كلاسيك» templates: what exists, what it costs, how to build the rest

2026-10-09. A Classic book needs a **live template** for its story × art style × look. The look is one of
`girl`, `girl_hijab`, `boy` (`VARIANTS`, `packages/ai/src/qamra_ai/pipeline/classic.py:50`, `parse_variant`
:70). The studio calls them «بنت», «بنت بحجاب» and «ولد». A story sells Classic only to the looks that have a
live template. No template has been built and no paid API has been called for this plan. The budget is the
owner's decision (§5).

## 1. What exists

### 1.1 Templates per story × style × look

| Story | Story status | Watercolor «مائي فاخر» (girl · girl_hijab · boy) | 3D | Cartoon |
|---|---|---|---|---|
| `first-day` | live (17 beats + cover = 18 images) | live · live · live | missing × 3 | missing × 3 |
| `graduation` | live (18 images) | live · live · live | missing × 3 | missing × 3 |
| `new-sibling` | live (18 images) | live · **missing** · **missing** | missing × 3 | missing × 3 |
| `olive-season` | written 2026-10-09 (v2), on sale as Magic; 17 beats + cover = 18 images | missing × 3 | missing × 3 | missing × 3 |
| `moon-trip` | written 2026-10-09 (v2), on sale as Magic; 18 images | missing × 3 | missing × 3 | missing × 3 |
| `dream-boat` | written 2026-10-09 (v2), on sale as Magic; 18 images | missing × 3 | missing × 3 | missing × 3 |
| `neighborhood-friends` | written 2026-10-09 (v2), on sale as Magic; 15 beats + cover = 16 images | missing × 3 | missing × 3 | missing × 3 |
| `star-keeper` | written 2026-10-09 (v2), on sale as Magic; 18 images | missing × 3 | missing × 3 | missing × 3 |
| `custom` | the custom story; no catalog | no Classic | — | — |

- **Live = 7 templates, all watercolor.** The brief's "3 styles" for first day and graduation means the
  three looks in one style.
- **Drafts or templates in review:** none are recorded in the docs or the logs.
- **Sources:**
  - `docs/plans/remaining-work.md:10`: «7 templates from the example books».
  - `docs/feature-matrix.md:19`: «all watercolor».
  - `out/style-samples/ref/examples.json`, fetched from `/api/examples` on 2026-10-07. The 7 published
    example books are exactly these 7 story × style × look combinations. The templates were made from them
    with "sample → template".
- **Verify on the server** (read-only):

  ```sql
  SELECT th.slug, t.art_style, t.variant, t.status, t.job, t.source, t.cost_usd,
         t.generation->>'source_cost_usd' AS book_usd, t.theme_version, t.flags, t.live_at
  FROM classic_templates t JOIN themes th ON th.id = t.theme_id ORDER BY 1, 2, 3;
  SELECT slug, lines, active, sort FROM art_styles ORDER BY sort;
  ```

  Without SQL, use Admin → «محرر الثيمات» (`/ar/admin/studio`, «استوديو القوالب»), or `GET /api/themes`,
  whose `classic` field lists only the live templates.

### 1.2 Which styles Classic can sell

The site offers a style in Classic only if two things are true. The style's `ArtStyle.lines` must include
`classic`, and the story must have a live template in that style (`apps/web/src/lib/story.ts:55-75`,
`components/create/StyleStep.tsx:84-88`).

| Style | `classic` in its lines | Fixed sheets (`content/cast`) | Cover plates (`content/themes/*/plates`) |
|---|---|---|---|
| watercolor | **yes**: the only Classic style (`prompts/style/watercolor.md:5`, migration `c4e8a1f20b37`) | «قمّور», teacher, classmates, mom, dad, grandma, grandpa, baby | first-day 1, graduation 3, new-sibling 1 |
| 3d | no: Magic and the activity lines (`prompts/style/3d.md:5`) | all of them | the same as watercolor |
| cartoon | no (`prompts/style/cartoon.md:5`) | «قمّور» only | none |
| semi-realistic «شبه حقيقي» | no, by decision of 2026-10-09: Magic and the activity lines only (`CHANGELOG.md:5`, `decisions.md:704`, migration `a58eeffa5362`, guide `lines` :5) | none | none |
| coloring | a separate product (line `coloring`, off) | — | — |

- No admin screen edits `ArtStyle.lines`. The seed only inserts styles that don't exist yet
  (`seed_store.py:89-91`).
- So opening 3D or cartoon to Classic needs a migration plus the style guide's `lines:`.

## 2. Cost

### 2.1 Two ways to make a template (`docs/decisions.md:209`)

| Path | What it pays for | ≈ per template |
|---|---|---|
| **Generated**: `POST /api/admin/classic/templates`. The premium page pipeline draws around a neutral placeholder hero. | placeholder sheet, every page with QA, redraws, upscale, hero boxes | **$2.16** (formula below) |
| **Sample book → template**: an approved Magic sample book of an invented child, then `POST …/templates/from-book`. All 7 live templates were made this way. | invented face $0.08 + character sheet $0.08 + the book ($1.49–2.01 measured on 9 example books, `feature-matrix.md:30`) + hero boxes ≈ $0.05 | ≈ $1.9–2.3, and the book doubles as a public example |

### 2.2 Inputs (current defaults; the admin settings decide)

| Symbol | What | Value | Source |
|---|---|---|---|
| N | images per template: cover + story beats | 18 for the live stories; 14–19 for a new story (16–20 printed story pages, 2–3 spreads) | `plan_book`; `pipeline/theme.py:30-31` |
| H | hero pages (need a hero box) | N − 1 (one child-free plate per live story) | theme yaml `no_child` |
| I | one page or cover: Nano Banana 2, 1K | $0.080 | `pricing.yaml:20-21`; `config.py:45`, `final_mode` 1k_upscale :66 |
| I′ | the cover, if `cover_image_model` = Nano Banana Pro | $0.150 (+$0.07) | `pricing.yaml:24-25`; `config.py:48` (empty by default) |
| U | print upscale (SeedVR, $0.001 per output MP) | $0.0073 per image ($0.132 per 18) | `pricing.yaml:37`; measured in `addendum-03.md:134` and `out/redesign/proof/20261003-112823-fal-graduation/cost.json` |
| Q | Haiku page QA, every attempt | $0.0031 cached ($0.062 / 20 calls), $0.0049 uncached | `addendum-03.md:135` |
| r | automatic redraws (up to 2 per page) | 15% expected; measured 11% and 33% (`addendum-03.md:137`); first 3D proof 3 of 18 (`CHANGELOG.md:158`) | `config.py:71` |
| P | the placeholder hero sheet (text to image, 1K) | $0.080, once per template | `pipeline/classic.py:153-168` |
| B | one hero-box call (Haiku vision, 2 images) | ≈ $0.003 (estimate: ~2.5k tokens in, ~150 out) | `jobs/classic.py:234-268`; `pricing.yaml:5` |
| m | manual redraws while reviewing («إعادة الرسم») | 2 per template, each I + U + Q = $0.090 | `admin_classic.py:373-392` |
| V | vowelized words (Sonnet), once per story and gender, shared by every style and look | $0.02–0.05 per gender, ≤ $0.10 per story | `decisions.md:188` |
| — | cast and «قمّور» sheets, cover plates | $0 when the file exists; a missing companion sheet is drawn once ($0.08) and cached | `pipeline/pages.py:421-481` |
| — | the child-free plate | cached per story × style × model × story version × house-style version: the 2nd and 3rd look skip it. The house style moved to v5 on 2026-10-09, so older cached plates no longer match. | `pipeline/pages.py:523-541` |

### 2.3 Formula and result

```
template = P + N·(I + U + Q) + r·N·(I + Q) + H·B + m·(I + U + Q)          (+ V once per story and gender)
         = 0.080 + 18·0.0904 + 0.15·18·0.0831 + 17·0.003 + 2·0.0904
         = 0.080 + 1.627 + 0.224 + 0.051 + 0.181 = $2.16
```

| Case | Assumptions | Per template | Set of 3 looks (story × style) |
|---|---|---|---|
| Clean | r 11%, no manual redraws | $1.92 | $5.6 |
| **Expected** | r 15%, 2 manual redraws, Nano Banana 2 cover | **$2.16** (2nd and 3rd look $2.07: plate cached) | **$6.3** |
| Bad | r 33%, uncached QA, Nano Banana Pro cover, 4 manual redraws | $2.73 | $8.0 |

- About $2.04 of the expected $2.16 is fal and $0.12 is Anthropic.
- Per image, everything included, it is ≈ $0.106, plus $0.26 fixed per template. A new story with N = 14
  costs ≈ $1.74 per template; one with N = 19 costs ≈ $2.27.

### 2.4 Totals

Totals for watercolor only (sellable today), and with 3D and cartoon added (needs the change in §1.2).

| Scope | Templates (wc / all 3) | Watercolor only | + 3D + cartoon |
|---|---|---|---|
| **(a)** olive-season, every look | 3 / 9 | **$6.4** ($5.7–8.1) | **$19.4** ($17–25), incl. ≈ $0.4 for its cast sheets in cartoon |
| **(b)** the five new stories (includes a) | 15 / 45 | **$32** ($28–41) | **$97** ($86–126), incl. ≈ $2 of cast sheets (cartoon, and any new character per style) |
| **(c)** the gaps of the three live stories | 2 / 20 | **$4.3** ($3.8–5.4): new-sibling girl_hijab + boy, plus the boy's vowelization | **$43** ($38–54), incl. ≈ $0.8 for 6 cartoon cast sheets (classmates needed 6 tries before) |
| (b) + (c) | 17 / 65 | **≈ $36** | **≈ $140** |

Extras, outside the totals:

| Item | ≈ Cost | Source |
|---|---|---|
| The Classic per-order proof: 5 invented children on a live template | $3 | `remaining-work.md:11` |
| One Classic test book on a new template before it goes live | $0.4–0.6 with the invented face | `admin_classic.py:540-627` |
| A cover plate for a new story (optional) | $0.12 per style | ledger `D*` rows at 2K |
| Redraw the 7 live templates in the Addendum 11 look (optional; §5) | ≈ $15 | 7 × $2.1 |
| A semi-realistic set, if it were ever opened to Classic | +$6.3 per story | same formula |

## 3. Recommended order

| # | Work | Templates | ≈ Cost | Why |
|---|---|---|---|---|
| 0 | The per-order proof on `graduation` × watercolor | 0 | $3 | The klein hero edit has never run with real providers (`feature-matrix.md:30`). A template earns nothing if the edit fails on likeness or seams. |
| 1 | `olive-season` × watercolor × **girl** | 1 | $2.2 | See the notes below this table. |
| 2 | `olive-season` × watercolor × girl_hijab, then boy | 2 | $4.1 | Classic shows only for looks with a template. girl_hijab reuses the girl's vowelized words; boy needs its own (+$0.05). |
| 3 | `new-sibling` × watercolor × girl_hijab, boy | 2 | $4.3 | A live story that refuses Classic to every boy and every girl in hijab today. Its sheets exist, and the second look reuses the first one's plate. |
| 4 | `moon-trip` → `dream-boat` → `star-keeper` → `neighborhood-friends`, watercolor × 3 looks each | 12 | $26 | Ordered by catalog rank (40, 60, 70, 80), the only demand signal before sales. Build each one only after its v2 story is approved, language-reviewed and live. |
| 5 | (owner) Open 3D to Classic: migration, then one 3D template (`graduation` × 3d × girl) with a test book | 1, then 12 | $2.6, then ≈ $26 | 3D is the house default, preselected and «الأكثر اختيارًا» (`decisions.md:706`). A klein edit on 3D art is unproven. Then first-day and graduation (rank 10 and 20, the kindergarten books), olive-season and new-sibling. If chosen, this goes before step 4. |
| 6 | (owner) Cartoon: draw its 7 cast sheets first, then the same sets | 7 sheets, then sets | ≈ $1, then $6.3 per story | It has no side-character sheets, so its classmates and family would drift. |

Notes on steps 1 and 2:
- **Why olive-season first:** the olive harvest is October–November, now.
- **Why watercolor:** it is the only style Classic can sell today, all 7 live templates use it, and its
  fixed sheets exist (grandpa included). It needs no catalog change and no new sheets.
- **Why the girl first:** her template takes the hardest review (the scenes, the boxes and the words). Its
  vowelized words then serve girl_hijab too.
- **Why not 3D first:** it is the house default, but Classic doesn't sell it (§1.2). A 3D template would stay
  invisible until a migration, so 3D is step 5, the owner's call.

## 4. Building one template (example: `olive-season` × watercolor × girl)

### 4.1 Prerequisites

1. **The story is live.**
   - `content/themes/olive-season/theme.yaml` v2 has its pages, `catalog.status: available`, and passes
     `theme_problems`: 16–20 story pages, 2–3 spreads, text on every page, `for_parents`, blurb.
   - It is committed and deployed. The compose `migrate` job runs
     `qamra-migrate && qamra seed-themes && qamra seed-store` (`compose.yaml:109`).
   - Check: `GET https://qamra.app/api/themes/olive-season?lang=ar` gives `"status": "available"` and
     `pages` > 0.
   - A coming-soon story makes the POST answer 404 (`admin_classic.py:186-190`).
2. **The story's words are final and language-reviewed.**
   - Changed words afterwards only need «تحديث النصوص وتشكيلها».
   - Changed scenes or page order need a new template, about $2 per look.
3. **Every `cast` id of the story has a sheet in the style:** `content/cast/<id>-watercolor.*` or
   `content/themes/olive-season/cast/<id>-watercolor.*`.
   - Without one, the character is drawn from words and drifts (Addendum 11 §0.1 #9).
   - A cover plate `plates/watercolor-1.jpg` is optional.
   - Both are repo files: commit and deploy them before drawing.
4. **The worker is ready.**
   - The `worker` container serves `generation pdf maintenance default` (`infra/docker/python.Dockerfile:38`).
   - The server `.env` holds `FAL_KEY` and `ANTHROPIC_API_KEY`.
   - Without the text key, QA is skipped (`qa_unavailable`), the hero boxes and the vowelization fail, and the
     template cannot be approved.
5. **Settings are checked** in Admin → «الإعدادات»:
   - `image_provider` fal and `fal_image_model` `fal-ai/nano-banana-2`;
   - `final_mode` 1k_upscale and `page_max_regenerations` 2;
   - `cover_image_model`: empty means $0.08 covers, Nano Banana Pro means $0.15;
   - `book_budget_usd`: the per-run cap when the request sets none.
6. **fal is topped up** by the approved amount plus about 20%. The fal balance is the only hard ceiling
   (§5).
7. **An active admin with the `templates` permission** (owner or editor) is signed in with 2FA on
   https://qamra.app.
   - `ops-bot` stays deactivated.
   - `scripts/classic_proof.py` signs in as `ops-bot` and defaults to the old `http://62.84.179.155:3300`.
     Its `generate` command is watercolor-only.
   - Use the browser or curl below, unless Tareq re-enables an ops account. Then run
     `classic_proof.py --base https://qamra.app status|texts|wait`.
   - Don't use its `publish` before the review: it walks draft → in_review → approved → live in one go.

### 4.2 Steps

| Step | Admin UI | API (same origin, header `X-Qamra-Client` on every POST/PATCH) |
|---|---|---|
| 1. Create and draw | No button: the studio has no "new template". Use the API (below). | `POST /api/admin/classic/templates` with `{"theme":"olive-season","style":"watercolor","variant":"girl","lang":"ar","budget_usd":2.5}` → 202, `draft`, job `queued` |
| 2. Watch | «محرر الثيمات» → «استوديو القوالب», tab «القوالب» → the story's group → «مائي فاخر · بنت»: «قيد الرسم», «n من 18 صفحة مرسومة», «تكلفة لمرة واحدة» | `GET /api/admin/classic/templates/{id}` (`job`, `pages_drawn`, `cost_usd`, `flags`) |
| 3. Finish a stopped run | «توليد الصفحات الناقصة» (flags `budget_exceeded`, `pages_missing`, `job_failed`) | `POST …/templates/{id}/generate` |
| 4. Review every page | Open the row (`/ar/admin/studio/templates/{id}`). For «الغلاف» and each «صفحة n», check: one hijab and outfit per scene group; «قمّور» always a crescent; the same side characters; no text in the art; nobody cut at the edge; the hero box (drag, «حفظ الصندوق», «إضافة صندوق البطل», «البطل في هذه الصفحة»); the words in «المعاينة». | `PATCH …/pages/{beat}` with `hero_box`, `has_hero`, `text_box` (0–1 boxes) |
| 5. Fix or keep | A bad page: «إعادة الرسم» (asks first, ≈ $0.09). A good page: «قفل الصفحة» (locked pages are never redrawn). | `POST …/pages/{beat}/regenerate`; `PATCH …/pages/{beat}` `{"locked":true}` |
| 6. Words | The job vowelizes by itself and shows «✓ مشكّل». Otherwise use «تشكيل النصوص», or «تحديث النصوص وتشكيلها» when the story's words changed. Then run a language review of the vowelized words. | `POST …/texts` `{"refresh":false}` (or `true`) |
| 7. Try it (optional, ≈ $0.5) | — | `POST /api/admin/classic/samples` (multipart: theme, name, gender, age, `consent=true`, an invented face from `POST /api/admin/classic/synthetic-faces`, style, `mode=final`). A sample book may use a template still in review. |
| 8. Approve | «إرسال للمراجعة» if it is still a draft, then «اعتماد (يقفل الصفحات)». It is refused (`template_incomplete`) until every page is drawn, every hero page has a box and the words are vowelized. | `POST …/status` `{"to":"approved"}` |
| 9. Publish | «نشر» in the editor, or in the list: tick it → «نشر», or «جدولة النشر» (a cron job runs every 5 minutes) | `POST …/status` `{"to":"live"}`; `POST /api/admin/studio/templates/publish` `{"ids":[…],"to":"live"}` |
| 10. The other looks | Repeat step 1 with `girl_hijab`, then `boy`. For another style (once it sells Classic): tick the three templates → «أسلوب الرسم» → «نسخ الإعدادات كمسودة» → open each draft → «توليد الصفحات الناقصة». | `POST /api/admin/studio/templates/copy` `{"ids":[…],"style":"3d"}` |

Step 1 in the browser console, signed in on https://qamra.app/ar/admin:

```js
await (await fetch("/api/admin/classic/templates", {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-Qamra-Client": "web" },
  body: JSON.stringify({ theme: "olive-season", style: "watercolor", variant: "girl", lang: "ar", budget_usd: 2.5 }),
})).json()
```

Step 1 with curl. The password is read without echo; the code is the authenticator's:

```sh
B=https://qamra.app; J=$(mktemp); H='X-Qamra-Client: ops'; C='Content-Type: application/json'
read -rs PW
curl -s -c "$J" -b "$J" -H "$H" -H "$C" -d "{\"email\":\"<admin email>\",\"password\":\"$PW\"}" "$B/api/auth/login"
curl -s -c "$J" -b "$J" -H "$H" -H "$C" -d '{"code":"<6 digits>"}' "$B/api/auth/mfa/verify"
curl -s -b "$J" -H "$H" -H "$C" \
  -d '{"theme":"olive-season","style":"watercolor","variant":"girl","lang":"ar","budget_usd":2.5}' \
  "$B/api/admin/classic/templates"
```

Body fields (`TemplateIn`, `admin_classic.py:217-223`):

| Field | Values |
|---|---|
| `theme` | the story's slug |
| `style` | default `watercolor` |
| `variant` | `girl` \| `girl_hijab` \| `boy` |
| `lang` | `ar` (default) or `en` |
| `budget_usd` | > 0 and ≤ 20, **per run** |
| `offline` | placeholder art at $0 |

- Don't run `offline` on a slot that will be drawn for real. The row keeps the flag and there is no delete
  endpoint.
- Answers: 409 `busy` while a job runs; 409 `template_exists` once the slot is approved or live.

The run draws in this order:
1. the placeholder sheet;
2. the cover;
3. each scene group's first page;
4. the rest, 4 at a time;
5. then the hero boxes and the vowelized words.

It ends `in_review` when every page is drawn (`jobs/classic.py:344-430`).

The `budget_usd` of 2.5 is meant as an alarm. An automatic run is expected to cost $1.98, and the cap
leaves room for a redraw rate up to ~45%. A stop means "look before spending more".

### 4.3 Verifying it went live

- `GET https://qamra.app/api/themes?lang=ar` now shows `olive-season` with
  `"classic": {"watercolor": ["girl"]}`. It lists live templates only (`apps/api/src/qamra_api/classic.py`,
  `classic_availability`).
- The story page `/ar/stories/olive-season` shows «قمرة كلاسيك» متوفّرة لهذه الحكاية بأسلوب: مائي فاخر.
  و«قمرة سحري» متوفّرة بكل الأساليب.
- The stories list card shows «قمرة كلاسيك» بأسلوب: مائي فاخر.
- The style card shows «متوفر لـ: بنت» until all three looks are live.
- In the create flow, a boy still gets «رسوم «قمرة كلاسيك» الجاهزة غير متاحة لطفل بهذا الشكل…» until his
  template is live.
- On the server, the template's spend per step:

  ```sql
  SELECT split_part(step, ':', 2) AS kind, count(*), sum(usd)
  FROM generation_costs WHERE step LIKE 'tpl:%' AND units->>'template' = '<id>' GROUP BY 1 ORDER BY 1;
  ```

## 5. Risks and the owner's decisions

**Decisions for Tareq**

| # | Decision | Options |
|---|---|---|
| 1 | Budget and fal top-up | **A** olive-season in watercolor: $6.4, cap $8. **B** all five new stories + new-sibling gaps in watercolor: $36, cap $45. **C** everything in 3 styles: $140, cap $170, plus the catalog change. In every case, the $3 proof first. |
| 2 | The per-order proof before any template | Recommended yes, $3. |
| 3 | Open 3D (and cartoon) to Classic | A migration that adds `classic` to the style's lines. Cartoon also needs ≈ $1 of cast sheets. |
| 4 | Cover model for templates | Nano Banana 2 ($0.08) or Pro ($0.15: +$0.07 per template, more with cover redraws). |
| 5 | The 7 live templates | They were drawn on 2026-09-28/30, before Addendum 11's consistency work (cast sheets and cover plates on 2026-10-03). Review them for hijab, outfit and «قمّور» drift and fix single pages (≈ $0.09 each), or redo all 7 (≈ $15). |
| 6 | Scripted runs | Keep them in the browser, or re-enable an ops account and update `classic_proof.py` (base URL, `--style`). |

**Risks**

| Risk | Effect | Mitigation |
|---|---|---|
| The cap is **per run**, not per template. Every generate, resume and page redraw starts a fresh `Budget` (`jobs/classic.py:352`, `db/classic.py:72`). RQ retries a crashed job twice (`jobs.py:19`). | A template's total has no automatic ceiling. | Watch «تكلفة لمرة واحدة». Stop and look at any template over $3. Top fal up only by the approved amount. |
| The Classic hero edit is unproven with real providers, in any style. | Templates could be wasted. | Step 0 of §3. |
| The story changes after drawing. | New words: a free refresh (back to review). New scenes or page order: about $2 per look. | Draw only from the final, reviewed v2. |
| A new story's side characters have no sheet. | Characters drift between pages. | Draw the sheets (≈ $0.08 each per style) before drawing the template. |
| 3D framing failures (3 of 18 in the first 3D proof). | A higher redraw rate. | The "bad" column of §2.3. |
| An offline dry run on the real slot. | The slot stays offline-only (no delete). | Never dry-run a slot you mean to draw. |
| Classic templates draw only the default companion. | The «ارسم صاحبك» add-on stays Magic-only (`remaining-work.md:13`). | No cost impact. |

**Not verified from here (no server access in this task)**

- The exact server state: the evidence (docs plus the published examples) agrees on the 7 watercolor
  templates. Run the SQL in §1.1 to confirm their status (`live` or `approved`), flags and theme version.
- `art_styles.lines` in the server's database: the migration sets them, but confirm with the same SQL.
- The server's `cover_image_model` value: Admin → «الإعدادات» → «نموذج fal للغلاف».
- The fal balance, and whether the server's `FAL_KEY` is the same account as the local one. The local ledger
  shows the 2026-10-09 top-up almost spent, so expect a top-up before any of this.
- The real Anthropic cost of the hero-box calls ($0.003 is an estimate), and the page count of each new
  story. Re-run the formula with its N once each v2 story is final.

## 6. 2026-10-16: runbook for «موسم الزيتون» × watercolor (all three looks) and its example books

Prepared on 2026-10-16. **No paid call was made.** Everything below waits for the owner's fal top-up.

### 6.1 Server state, checked read-only on 2026-10-16

| Item | Finding |
|---|---|
| Deployed code | `31a2799` (`/opt/qamra/REVISION`), the same as `addendum-4` HEAD. |
| olive-season theme | Live version **3** (`theme_versions`: v1 retired, v2 an empty studio draft, v3 live from the file). `catalog.status: available`, 17 story pages + cover = **18 images**, one child-free page (beat 11, the olive press). The live definition matches `content/themes/olive-season/theme.yaml`: the vowelize source hashes are the same on both sides (girl `8a5a2c2272d5562e`, boy `93b42a71a828b44a`). |
| Story words | Final v3 (written and language-reviewed on 2026-10-10; «طفلك» catalog fix in `TEXT_FIXES`). The page texts in the yaml are already fully vowelized by hand. |
| Vowelized words cache | **None for olive-season.** The cache lives in a Classic template (`generation.texts`), and no olive-season template exists yet. The first template job vowelizes once per gender: Sonnet, ≈ $0.05 per gender, ≈ $0.10 for both. girl_hijab borrows the girl's copy (same hash). |
| Classic templates | 7, all watercolor and live: first-day × 3 looks, graduation × 3 looks, new-sibling × girl. **None for olive-season.** graduation girl/boy carry a stale `no_hero_box` flag, but every hero page has a box. |
| Side characters | `cast`: mom, dad, grandma, grandpa. All four have `content/cast/<id>-watercolor.jpg` in the worker image, and so does «قمّور». |
| Cover plate | None (`content/themes/olive-season/plates/` does not exist). It is optional: the cover is drawn as usual. |
| Styles | watercolor is the only style with `classic` in `art_styles.lines`. |
| Settings (admin, resolved in the worker) | `image_provider` fal, `fal_image_model` nano-banana-2, `cover_image_model` empty ($0.08 covers), `final_mode` 1k_upscale, `page_max_regenerations` 2, `book_budget_usd` **$3.00**, portrait and sheet on nano-banana-pro/edit ($0.30 per character since 2026-10-10), `classic_fal_model` klein 4B, Classic cap 2₪ = $0.54. `fal_key` and `anthropic_api_key` are set. |
| Worker | One worker on `generation, pdf, maintenance, default`. Queues empty, idle. |
| Admin users | `admin@qamra.app` active with 2FA; `ops-bot` inactive (it stays off). |
| Public examples | 7: first-day × 3, graduation × 3, new-sibling × girl. None for olive-season, so the site shows its 3D cover art (`apps/web/src/lib/themeArt.ts`). |
| olive-season books | None on the server. |

### 6.2 How to run admin actions without a login

- The admin API needs a 2FA session, and `ops-bot` stays off.
- The cleanest path is to run the **same routers in-process inside the api container**, with FastAPI's `TestClient`. Only `require_admin` is overridden, by a lookup of `admin@qamra.app`.
- Everything else is unchanged: the validation, the permission check, the audit rows (attributed to `admin@qamra.app`) and the RQ jobs. Nothing is copied to the server, because the script goes through stdin.
- Note: this skips the admin's password and 2FA. It needs root on the server, which can already reach the database. The owner may prefer the browser (§4.2), and the steps are the same.
- **Tested at no cost on 2026-10-16:** `get /api/admin/classic/templates` → 200. A POST to `/api/admin/classic/templates`, `/api/admin/samples` and `/api/admin/classic/samples` with an unknown story → 404 before any write. `save` of a template page image → 200. The `Q` wrapper below passes JSON with Arabic intact (tested).
- The script is in §6.7. Save it as `qamra_admin.py` outside the repo (e.g. the scratchpad).

```sh
export QAMRA_SSHPASS=… SSH_ASKPASS=<scratchpad>/askpass.sh SSH_ASKPASS_REQUIRE=force DISPLAY=:1
# printf %q keeps the JSON's quotes and the Arabic names intact through the remote shell
Q() { ssh root@62.84.179.155 "cd /opt/qamra && docker compose exec -T api python - $(printf '%q ' "$@")" < qamra_admin.py 2>&1 | grep -v '^{"'; }
Q get /api/admin/classic/templates                      # free
```

### 6.3 Before any paid step (free)

1. **Top-ups.**
   - The owner confirms the fal top-up (dashboard balance ≥ the approved cap + the $3 kept for live orders).
   - The Anthropic credit must cover ≈ $1.
2. **Worker idle.** Check with `docker compose exec -T worker sh -c 'rq info --url $REDIS_URL'`. No other paid job should run in parallel, so the per-step costs stay readable.
3. **Spend before the run.** Note it with this SQL, to compare afterwards:
   `SELECT round(sum(usd)::numeric,4) FROM generation_costs WHERE created_at > now() - interval '1 hour';`
4. **Stop rule.**
   - Run one paid step at a time, and read its cost before the next.
   - Stop and report if a step costs more than 1.25 × its estimate, or if the run total passes the cap.

### 6.4 (a) The per-order proof: one Classic book on graduation × watercolor

This is the go/no-go for the klein hero edit with real providers, which has never run. It goes **before** the
olive-season spend, because the olive templates will be the same kind (made from a sample book).

| Step | Command | ≈ Cost |
|---|---|---|
| a1. An invented girl and her Classic book (final) | `Q sample classic '{"theme":"graduation","name":"ريم","gender":"f","age":5,"style":"watercolor","mode":"final"}' '{"gender":"f","age":5,"skin":"fair","hair":"light brown wavy","top":"pink","seed":15}'` | face $0.08 + identity portrait (klein + QA) ≈ $0.02 + 17 hero edits with QA ≈ $0.26 + auto-redraws ≈ $0.05 = **≈ $0.41** (the 2₪ guard stops the book at $0.54) |
| a2. Wait | `Q wait-book <book_id>` | — |
| a3. Look | `Q save /api/admin/books/<id>/files/interior.pdf /tmp/proof-interior.pdf`, then `docker compose cp api:/tmp/proof-interior.pdf .` (also `cover.pdf`). Or the admin UI: «الكتب». Check likeness to the face, the seams around the box, one hero per page, and the vowelized words. | — |
| a4. Optional | The same for a hijab girl (`"hijab":true`, seed 11) and a boy (seed 13, `"glasses":true`). These are two more risks: hijab framing and glasses. | +$0.82 |

- One book is enough to show the edit works. Three books cover the three looks: **$1.25**, instead of $3 for five.
- If a1 fails on likeness or seams, stop. Don't spend on olive-season templates until the edit is fixed.

**Result of (a), run 2026-10-16: FAILED; olive-season was not started.**

- **The run:** book `17fb9eb8-7dda-4d71-b9ab-6af1886d4734`, invented girl «ريم», graduation × watercolor × girl. It cost **$0.617**: face $0.08, klein edits ≈ $0.47, Haiku QA ≈ $0.06. It hit the 2₪ guard (`budget_exceeded`).
- **QA:** 13 of 17 hero pages came back `needs_review`, mostly for `seams`. The likeness is mostly 7–8, but page 3 scored 2: the wrong child was edited.
- **What the pages show:**
  - The klein crop comes back as a visible rectangle: a violet/indigo wash, with lanterns and leaves painted into the background.
  - The hero's outfit is recoloured (the green gown turns blue).
- **Likely cause:**
  - The edit prompt carries the watercolor guide, which asks for "deep indigo and violet shadows … foreground framing elements (leaves, arches, lanterns)" (`prompts/style/watercolor.md:14-16`).
  - The 7 templates were drawn before that guide, so the edit "restyles" its crop instead of matching the page.
- **Fix before any olive spend:** the edit must keep the page's palette and add nothing, so it should not get the style's mood paragraph.
- **Live Classic orders hit the same problem today.**

### 6.5 (b) + (c) olive-season × watercolor × girl, girl_hijab, boy, each from a Magic sample book

**Recommendation: make each template from an approved Magic sample book of an invented child.** All 7 live
templates were made this way. Each sample book is a full «قمرة سحري» book, so it is also the public example
of its look. The money buys both the template and a Magic-quality example.

- A **generated** template (§4.2) costs about the same ($2.07–2.16) and gives no example.
- **About (c):** a $0.5 example would be a *Classic* sample book: the template's art with a pasted face, not
  Magic quality. A Magic book costs ≈ $2.2.

Per look, in this order: girl first (the hardest review; her words serve girl_hijab), then girl_hijab, then boy.

| Step | Command | ≈ Cost |
|---|---|---|
| b1. Invented face + Magic sample book (final) | girl: `Q sample magic '{"theme":"olive-season","name":"زينة","gender":"f","age":5,"style":"watercolor","mode":"final"}' '{"gender":"f","age":5,"skin":"light olive","hair":"dark brown","top":"light blue","seed":31}'`. girl_hijab: `"name":"رهف"`, `"hijab":true` in both JSONs, `"top":"yellow"`, seed 32. boy: `"name":"عمر","gender":"m"`, face `{"gender":"m","age":5,"hair":"black","top":"green","seed":33}`. | face $0.08 + character $0.30 (Pro portrait + Pro 2K sheet) + story ≈ $0.08 + 18 images × ($0.08 + upscale $0.007 + QA $0.003) = $1.63 + 15% auto-redraws ≈ $0.22 = **≈ $2.3** (the book's own cap is $3.00) |
| b2. Wait (≈ 15 min) | `Q wait-book <book_id>` | — |
| b3. Review the book | In the admin UI («الكتب» → the book): every page for the same face, hijab, outfit, «قمّور», grandpa (keffiyeh, cane, glasses) and no text in the art. Bad pages: «إعادة الرسم». Run a language-review agent on the page texts (`Q get /api/admin/books/<id>`). | manual redraws ≈ $0.09 each; budget 2 per look |
| b4. Approve the book | `Q post /api/admin/books/<id>/approve` | — |
| b5. Publish it as the look's example | `Q post /api/admin/books/<id>/example '{"synthetic_child":true}'` | — |
| b6. Book → template | `Q post /api/admin/classic/templates/from-book '{"book_id":"<id>","synthetic_child":true}'`, then `Q wait-template <template_id>` | hero boxes 17 × $0.003 ≈ $0.05 + vowelize ≈ $0.05 (girl and boy only) = **≈ $0.10** |
| b7. Review the template | The studio (`/ar/admin/studio/templates/<id>`): the hero boxes (fix with `PATCH …/pages/{beat}`, free) and «✓ مشكّل». Run a language-review agent on the vowelized words (`Q get /api/admin/classic/templates/<id>` → `texts`). | — |
| b8. Approve, then publish | `Q post /api/admin/classic/templates/<id>/status '{"to":"in_review"}'` if it is still a draft. Then `'{"to":"approved"}'` (locks the pages; refused until every page, box and vowelized word is there), then `'{"to":"live"}'`. | — |

**Totals**

| Scope | Expected | Range | Cap (stop and report) |
|---|---|---|---|
| (a) one proof book | $0.41 | $0.35–0.54 | $0.54 (the 2₪ guard) |
| (a) optional 2 more looks | +$0.82 | — | +$1.10 |
| (b + c) one look (template + example) | $2.40 | $2.1–2.8 | $3.20 per look |
| (b + c) three looks | **$7.2**, plus ≈ $0.5 manual redraws | $6.3–8.4 | **$8.5** |
| **All: (a) single + (b + c)** | **≈ $7.6–8.1** | — | **$9.0** |

- About $0.8 of it is Anthropic (stories, QA, boxes, vowelization); the rest is fal.
- **fal top-up asked:** ≥ $9 for this work, on top of the $3 kept for live orders. Add $1.10 if the optional proofs are wanted.
- **Cheaper variant:** girl from a sample book, girl_hijab and boy generated (§4.2: `POST /api/admin/classic/templates` with `budget_usd` 2.5). It costs ≈ $6.6 and gives only one olive example.

### 6.6 What the site shows afterwards (all free, no deploy)

- **Examples:** `GET https://qamra.app/api/examples?lang=ar&theme=olive-season` lists the published books.
  - The story page, cards and landing take them within ≈ 60 s (Next data cache).
  - The real watercolor cover replaces the 3D art of `themeArt.ts`. That file can stay: it is the fallback.
  - The story page shows the example of the visitor's look.
- **Classic:** once each template is live, `GET /api/themes?lang=ar` shows olive-season with
  `"classic": {"watercolor": ["girl", "girl_hijab", "boy"]}`. The checks in §4.3 apply.
- **Spend:** read it per step with the SQL in §4.3 and
  `SELECT step, count(*), sum(usd) FROM generation_costs WHERE book_id = '<id>' GROUP BY 1;`.
  Add each row to the spend ledger.

### 6.7 `qamra_admin.py` (the in-process admin helper of §6.2; not part of the repo)

```python
"""Admin API calls in-process in the api container, as admin@qamra.app, with no login (no password, no 2FA).

The same routers, checks, audit rows and RQ jobs as the admin site; only `require_admin` is replaced by a
lookup of the admin user. Run it through stdin, so nothing is copied to the server:

  ssh root@62.84.179.155 'cd /opt/qamra && docker compose exec -T api python - get /api/admin/classic/templates' < qamra_admin.py

  get PATH                      GET, print the JSON
  save PATH FILE                GET bytes (a page image, a PDF) into FILE inside the container; then
                                `docker compose cp api:FILE .` on the host
  post PATH [JSON]              POST with a JSON body (paid when the route enqueues a paid job)
  sample magic|classic FORM FACE
                                FACE = a FaceIn JSON ({"gender":"f","age":5,"seed":21,...}): draws the invented face
                                ($0.08), then POSTs /api/admin/samples (magic) or /api/admin/classic/samples (classic)
                                with FORM (JSON: theme, name, gender, age, hijab, style, mode). Prints the book id.
  wait-book ID                  polls the book every 20 s until it leaves `generating`; prints progress and cost
  wait-template ID              the same for a Classic template's job
"""

import json
import sys
import time
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from qamra_api.app import create_app
from qamra_api.deps import SessionDep, require_admin
from qamra_core.db.models import User

ADMIN = "admin@qamra.app"
H = {"X-Qamra-Client": "ops-inproc"}


async def as_admin(session: SessionDep) -> User:
    return (await session.execute(select(User).where(User.email == ADMIN, User.is_active))).scalar_one()


def show(r: Any) -> Any:
    try:
        body = r.json()
    except ValueError:
        body = r.text[:500]
    print(r.status_code, json.dumps(body, ensure_ascii=False, default=str)[:4000])
    if r.status_code >= 400:
        sys.exit(1)
    return body


def form_of(d: dict[str, Any]) -> dict[str, str]:
    return {k: (str(v).lower() if isinstance(v, bool) else str(v)) for k, v in {**d, "consent": True}.items()}


def main(argv: list[str]) -> None:
    app = create_app()
    app.dependency_overrides[require_admin] = as_admin
    with TestClient(app, base_url="http://localhost") as c:
        cmd, *rest = argv
        if cmd == "get":
            show(c.get(rest[0], headers=H))
        elif cmd == "save":
            r = c.get(rest[0], headers=H)
            if r.status_code != 200:
                show(r)
            with open(rest[1], "wb") as f:
                f.write(r.content)
            print(r.status_code, rest[1], len(r.content), "bytes")
        elif cmd == "post":
            show(c.post(rest[0], json=json.loads(rest[1]) if len(rest) > 1 else None, headers=H))
        elif cmd == "sample":
            line, form, spec = rest[0], json.loads(rest[1]), json.loads(rest[2])
            assert line in ("magic", "classic")
            face_id = show(c.post("/api/admin/classic/synthetic-faces", json=spec, headers=H))["id"]
            for _ in range(60):
                r = c.get(f"/api/admin/classic/synthetic-faces/{face_id}", headers=H)
                if r.status_code == 200:
                    break
                time.sleep(5)
            else:
                sys.exit(f"face {face_id} not drawn in 5 minutes (is the worker up?)")
            path = "/api/admin/samples" if line == "magic" else "/api/admin/classic/samples"
            files = [("photos", ("face.png", r.content, "image/png"))]
            show(c.post(path, data=form_of(form), files=files, headers=H))
        elif cmd in ("wait-book", "wait-template"):
            url = f"/api/admin/books/{rest[0]}" if cmd == "wait-book" else f"/api/admin/classic/templates/{rest[0]}"
            while True:
                r = c.get(url, headers=H)
                d = r.json() if r.status_code == 200 else {}
                if cmd == "wait-book":
                    prog = (d.get("generation") or {}).get("progress")
                    print(time.strftime("%H:%M:%S"), d.get("status"), prog, d.get("cost_usd"), d.get("flags"), flush=True)
                    if d.get("status") not in (None, "generating"):
                        break
                else:
                    keys = ("status", "job", "pages_drawn", "cost_usd", "flags")
                    print(time.strftime("%H:%M:%S"), {k: d.get(k) for k in keys}, flush=True)
                    if d.get("job") not in (None, "queued", "running"):
                        break
                time.sleep(20)
        else:
            sys.exit(__doc__)


main(sys.argv[1:])
```
