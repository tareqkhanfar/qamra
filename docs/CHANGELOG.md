# Changelog

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
