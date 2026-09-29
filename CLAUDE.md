Read docs/ADDENDUM-09.md — it overrides earlier prompts where they conflict.
Read docs/ADDENDUM-07.md — it overrides earlier prompts where they conflict.
Read docs/ADDENDUM-06.md — it overrides earlier prompts where they conflict.
Read docs/ADDENDUM-05.md — it overrides earlier prompts where they conflict.
Read docs/ADDENDUM-04.md — it overrides earlier prompts where they conflict.
Read docs/ADDENDUM-03.md — it overrides earlier prompts where they conflict.
Read docs/ADDENDUM-01.md — it overrides the main prompt where they conflict.

# Build prompt — Qamra (قمرة) — Arabic personalized storybooks

> Originally written as "KidPix 2.0 / حكايتي"; renamed to **قمرة / Qamra** per Addendum 1.

---

## 1. Who you are and how we work

You are the lead engineer building **Qamra** (brand: **قمرة**; names come from config — `BRAND_NAME_AR`, `BRAND_NAME_EN`, `BRAND_DOMAIN`) from scratch. I am Tareq, the product owner and reviewer. I work on this in evenings and weekends, so:

- Work in **phases** (section 9). Finish one phase completely before starting the next.
- At the start of each phase: write a short plan in `docs/plans/phase-N.md`, then implement.
- At the end of each phase: run all tests, update `README.md` and `docs/CHANGELOG.md`, commit with a clear message, and give me a short summary: what works, how to run it, what I need to do (keys, accounts, decisions).
- **Ask me before**: adding a paid service, changing the stack, deleting data or files, or anything touching production.
- Never commit secrets. All keys go in `.env` (with `.env.example` committed). Never print keys in logs.
- Prefer boring, well-documented libraries. Small functions, typed code, clear names.
- If something is ambiguous, pick the simplest reasonable option, note it in `docs/decisions.md`, and continue.

## 2. The product in one paragraph

Parents (and kindergartens/schools on their behalf) upload a photo of a child. The system creates a consistent illustrated **character** of that child, then generates a **16–24 page personalized storybook** in **Arabic (fully vowelized for young kids) or English**, where the child is the hero on every page. The result is a web reader, a shareable link, and a **print-ready PDF** sent to a local print partner. The primary customer is **kindergartens** (graduation books, "my first school year" books — one book per child, ordered as a class batch). Secondary customer is parents buying gifts (birthday, Ramadan/Eid, new sibling, first day at school). Markets: Palestine first, then Jordan.

## 3. Hard constraints

1. **Child photo privacy is the #1 requirement.**
   - Explicit guardian consent checkbox (versioned consent text stored with timestamp) before any upload.
   - Original photos stored encrypted in private object storage, accessed only via signed URLs valid ≤ 15 minutes.
   - Original photos auto-deleted within 24h after the character sheet is approved (scheduled job + test).
   - "Delete all my child's data" button that deletes photos, character, books, and logs references immediately.
   - Only use paid AI APIs whose terms exclude training on our data. Never send photos to any analytics or third party other than the image model provider.
2. **Commercial licensing**: only use models/APIs that allow commercial use. Do NOT use InsightFace/inswapper or any research-only model. No copyrighted characters (no Superman, Disney, etc.). Themes and art styles must be original.
3. **Content safety**: every generated text and image passes a safety check. Every printed book goes through a human approval step in the admin panel before it is sent to print.
4. **Arabic done right**: full RTL UI, correct Arabic fonts in the PDF, correct masculine/feminine grammar based on the child's gender, and diacritics (تشكيل) for ages 3–7.
5. **Provider-agnostic AI**: image, text and TTS providers sit behind interfaces so I can switch models via config without code changes. Models get deprecated every few months.
6. **Mobile-first**: most parents will use a phone.

## 4. Tech stack

- **Frontend**: Next.js (App Router, TypeScript), Tailwind CSS, RTL-first, i18n (ar default, en). Implement the UI from the design handoff in `/design` (HTML/Tailwind exported from Claude Design). Match it closely: tokens, spacing, components.
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 16, Redis + a job queue (Celery or RQ — pick one and document why).
- **Storage**: S3-compatible (Cloudflare R2 in production, MinIO locally), private buckets, server-side encryption.
- **PDF**: HTML/CSS page templates rendered to PDF with Playwright (Chromium). Print spec: 300 DPI images, CMYK-safe colors, 3 mm bleed, separate cover PDF, embedded Arabic fonts.
- **AI**:
  - Text (story adaptation, vowelization, safety review): Anthropic Claude API.
  - Images (character sheet + pages from a reference image, character consistency): implement adapters for **Google Gemini image model**, **FLUX Kontext (via fal.ai or BFL)** and **OpenAI GPT Image**. Default chosen by config. Check each provider's current docs for model names and parameters before implementing — do not guess API shapes.
  - TTS (phase 5): adapter interface only at first.
- **Auth**: email + password and phone OTP later; Google login. JWT in httpOnly cookies.
- **Payments**: `PaymentProvider` interface. Implement **Cash on Delivery** first, plus a stub for a card gateway (to be chosen later).
- **Notifications**: email (SMTP/provider adapter) and a WhatsApp adapter interface (I already have Twilio experience).
- **Infra**: Docker + docker-compose for local; production on a VPS with Docker (Swarm-compatible stack file), Nginx reverse proxy, Cloudflare in front. GitHub Actions for lint + tests.
- **Observability**: structured JSON logs, Sentry-compatible error hook, and a per-book cost log (tokens/images/$) stored in DB.

## 5. Repo layout

```
/apps/web            Next.js frontend
/apps/api            FastAPI app
/apps/worker         queue workers (story, images, pdf, cleanup)
/packages/ai         provider adapters + prompt templates (python package)
/packages/pdf        page templates (HTML/CSS) + renderer
/content/themes      theme definitions (yaml/json + assets)
/design              design handoff from Claude Design (read-only reference)
/infra               docker-compose, stack files, nginx
/docs                plans, decisions, runbooks
/scripts             one-off scripts (prototype, seed, backfills)
```

## 6. Core data model (adjust as needed, document changes)

- `User` (parent / school_admin / admin), `Organization` (kindergarten/school), `Classroom`, `Child` (name, gender, birth year, interests, org/classroom optional).
- `Consent` (child, guardian user, consent_text_version, accepted_at, ip).
- `ChildPhoto` (child, storage_key, status, delete_after).
- `Character` (child, art_style, sheet_image_key, approved_at, provider, model, seed/params).
- `Theme` (slug, title_ar, title_en, age_range, pages[], cover, is_b2b, active). Each page: scene description (for image prompt), story beat, text template ar/en with gender variants, layout id.
- `Book` (child, character, theme, language, status: draft→generating→preview→approved→ordered→printed, page texts, page image keys, pdf keys, share_token).
- `BookPage` (book, index, text, image_key, regen_count, safety_status).
- `Order` (user or org, items, product: digital/softcover/hardcover, price, currency ILS/JOD, payment method, status, shipping address, print_batch).
- `PrintBatch` (org or date, pdf bundle, printer status).
- `GenerationCost` (book, provider, model, units, usd).
- `AuditLog`.

## 7. Generation pipeline

1. **Photo check**: face detected, single child, decent resolution/lighting (use the image model or a lightweight check; reject with a friendly Arabic message).
2. **Character sheet**: from 1–3 photos + chosen art style, generate a front view + 2 poses. Parent approves or regenerates (max 3 free).
3. **Story**: load theme template → Claude adapts text to child name, gender, age, interests, language; keeps the theme's plot and page count; vowelizes Arabic for ages ≤ 7; returns strict JSON (validated with Pydantic). Safety check the output.
4. **Pages**: for each page, image prompt = art style guide + character reference image(s) + scene description. Run pages in parallel with a concurrency limit and retries with backoff. Store each image; run safety check; mark failed pages for regeneration.
5. **Preview**: first 3–4 pages at low resolution + watermark before payment. One free preview per account.
6. **Final**: after payment/approval, upscale if needed to print resolution, render interior PDF + cover PDF, generate web reader data, create share link.
7. **Admin approval** for printed products, then create/append to a `PrintBatch` and notify the printer (email with PDF links for now).
8. **Cleanup job**: delete original photos after approval + 24h; delete abandoned drafts after 30 days.
9. Log cost per step in `GenerationCost`. Target: total AI cost per 20-page book < $3.

Keep all prompts in versioned template files under `/packages/ai/prompts`, never inline strings scattered in code.

## 8. Features by area

**Parents (B2C)**: landing page, theme catalog, create flow (child info → consent → photo → art style → character approval → theme → text review/edit per page → preview → checkout), my children, my books, web reader (page flip, RTL), share link, order tracking, delete data.

**Kindergarten portal (B2B)**: organization signup (admin approves), classrooms, import children from Excel/CSV, **per-parent invite link** (parent gives consent and uploads the photo themselves), choose one theme for the whole class, class photo + teacher message + school logo page, batch generation with progress, bulk approval, wholesale pricing, one invoice, delivery to the school.

**Admin**: themes CRUD (pages, scene descriptions, text templates), orders and print batches, book approval queue with page-level regenerate, organizations and pricing, cost dashboard (cost per book, preview→purchase conversion), user data deletion requests.

## 9. Phases and acceptance criteria

**Phase 0 — Prototype script (no web app)**
`scripts/prototype.py --photo kid.jpg --name "سلمى" --gender f --age 5 --theme first-day --style watercolor --lang ar`
→ character sheet + 12 pages + PDF in `out/`, plus a cost report.
Accept when: runs end to end with each of the 3 image providers (flag), the child is recognizable on ≥ 80% of pages, the Arabic PDF renders correctly with diacritics.

**Phase 1 — Foundations**: monorepo, docker-compose (Postgres, Redis, MinIO, api, worker, web), auth, models + migrations, AI adapters from phase 0 moved into `/packages/ai`, CI.
Accept when: `docker compose up` gives a working login and `make test` passes.

**Phase 2 — Parent flow MVP**: full create flow, 3 original Arabic themes (first day at school, kindergarten graduation, new sibling), preview, COD checkout, web reader, PDF, email notifications, privacy features from section 3.
Accept when: a parent on a phone can go from photo to ordered hardcover in < 10 minutes, and the photo is deleted automatically.

**Phase 3 — Admin**: approval queue, print batches, themes CRUD, cost dashboard.

**Phase 4 — Kindergarten portal**: everything in section 8 B2B.
Accept when: a class of 30 can be generated in one batch and exported as one print bundle.

**Phase 5 — Polish**: English, audio narration adapter, coupons/gift cards, WhatsApp notifications, Jordan pricing (JOD), SEO pages per theme, performance pass.

**Phase 6 — Production**: production compose/stack, Nginx, backups, monitoring, runbook in `docs/runbooks/`.

## 10. Quality bar

- Tests: unit tests for pipeline steps (with fake providers), API tests, one Playwright e2e for the parent flow.
- Lint/format: ruff + mypy (python), eslint + prettier + tsc (web).
- Accessibility: proper labels, contrast, keyboard navigation.
- Every error message shown to parents is friendly Arabic (and English).

## 11. Start now

1. Read `/design` if it exists (otherwise build with clean placeholder styling and note it).
2. Create `docs/plans/phase-0.md`.
3. Build Phase 0, then stop and report to me with the output samples and cost per book.
