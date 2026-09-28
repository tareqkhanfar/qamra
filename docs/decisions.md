# Decisions log

Newest first. Each entry: date — decision — why.

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
