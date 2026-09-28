# قمرة · Qamra

«حكاية طفلك… تحت ضوء القمر»: personalized Arabic storybooks where the child is the hero and the child's own drawing becomes their companion.

Specs: [CLAUDE.md](CLAUDE.md) + [docs/ADDENDUM-01.md](docs/ADDENDUM-01.md) + [docs/ADDENDUM-03.md](docs/ADDENDUM-03.md). Decisions: [docs/decisions.md](docs/decisions.md). Plans: [docs/plans/](docs/plans/). Changes: [docs/CHANGELOG.md](docs/CHANGELOG.md).

**Status: Phase 1 + Addendum 3 (premium books at ≤ $2.50).**
- The public site, sign-up and sign-in work in Arabic and English.
- The full book pipeline runs on the server:
  - story (Sonnet 5), then page art (fal Nano Banana 2 with a FLUX.2 fallback);
  - Haiku QA with automatic redraws, a per-book budget cap and print upscaling;
  - premium RTL print PDFs with preflight.
- Admins with two-step verification review books in the approval queue, redraw pages, edit text, approve for print, and follow cost on a dashboard.
- The parent create flow (Phase 2) is next.

## Run the stack

Requirements: Docker with Compose v2.

```bash
cp .env.example .env        # defaults work locally; set real secrets anywhere else
docker compose up --build   # → http://localhost:3000 (ar) · API docs http://localhost:3000/api/docs
```

To open it to the network (e.g. a test server), set `QAMRA_BIND=0.0.0.0` and `QAMRA_WEB_PORT` in `.env`. Only the nginx `edge` is exposed; it sets the real client IP, which the login rate limits depend on. Without TLS, traffic (passwords included) is plain HTTP, so use test accounts only until HTTPS is on.

**HTTPS (Addendum 3 §6):** point a domain's A record at the server, then run `sudo infra/scripts/setup-https.sh qamra.example.com you@example.com`. It adds a host-nginx site with Let's Encrypt in front of the edge and binds the edge to localhost. `infra/scripts/firewall.sh` prepares ufw (22/80/443 only); it is a dry run unless given `--apply`.

**First admin sign-in:** the admin area asks for two-step verification setup (authenticator app + recovery codes). If an admin loses both, run `docker compose exec api qamra reset-2fa --email …` on the server.

| service | what | published port |
|---|---|---|
| `edge` | nginx, the only entry point: `/api/*` → api, everything else → web; sets the real client IP | `QAMRA_BIND`:`QAMRA_WEB_PORT` 3000 |
| `web` | Next.js (App Router, RTL, ar/en) | — |
| `api` | FastAPI: auth, health (later: books, orders…) | `QAMRA_API_PORT` 8000 (debug) |
| `worker` / `cron` | RQ worker (generation, pdf, maintenance) and scheduler (privacy cleanup every 15 min) | — |
| `migrate` | one-shot `alembic upgrade head` | — |
| `postgres` | Postgres 16 (`qamra` + `qamra_test`) | `QAMRA_PG_PORT` 5433 |
| `redis` | Redis 7 (queues, rate limits) | `QAMRA_REDIS_PORT` 6380 |
| `s3` | SeaweedFS as local S3 (R2 in production) | `QAMRA_S3_PORT` 8333 |

Useful commands:

```bash
make admin email=you@example.com name="Tareq"   # create an admin (prompts for the password)
make seed-themes                                 # load content/themes/*/theme.yaml into the DB
make logs
```

## Develop and test

Requirements: Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 24.

```bash
make install       # uv sync + Chromium + npm ci
make test          # pytest (needs TEST_DATABASE_URL: compose provides qamra_test on :5433)
make check         # ruff + mypy + pytest + prettier/eslint/tsc for the web
make migration m="add something"   # autogenerate + tidy a migration
```

Tests use fake AI providers, fakeredis and moto (S3). Only Postgres is real: each run rebuilds `*_test` through the migrations, and each test is rolled back.

## Sample books (Addendum 3)

On the server: **Admin → Sample books** (consent checkbox, 1–3 photos, optional drawing). Tick "placeholder art" for a $0 run. The book appears in **Admin → Approval queue**. Costs and QA results of the first real books are in `docs/plans/addendum-03.md` §5.

Locally:

```bash
make sample-book                 # offline, design-style placeholder art ($0) → out/<run>/
uv run scripts/sample_book.py --photo kid.jpg --name "سلمى" --gender f --age 5 --hijab \
  --theme first-day --provider fal --message "إلى سلمى…"   # real providers (keys in .env)
uv run scripts/ab_resolution.py --photo kid.jpg --pages 3   # 1K+upscale vs 2K A/B (real providers)
```

Each run writes `interior.pdf`, `cover.pdf` (RTL wrap with spine), `proof.pdf` (low-res web proof), `report.md` (preflight, QA per page, regeneration rate, cost and the projection on the paid stack), `story.json` and `cost.json`. `scripts/prototype.py` (Phase 0 command) runs the same pipeline.

## Layout

```
apps/api        qamra_api: FastAPI app (auth + 2FA, catalog, admin settings/queue/samples/metrics), CLI (`qamra`)
apps/worker     qamra_worker: RQ jobs (book generation, redraws, re-render, privacy cleanup), cron config
apps/web        Next.js frontend (src/app/[locale], messages/ar.json + en.json)
packages/core   qamra_core: settings, SQLAlchemy models, Alembic migrations, S3 storage, test fixtures
packages/ai     qamra_ai: providers (fal/Gemini/OpenAI/Claude + sketch), house style, prompts, pipeline, pricing
packages/pdf    qamra_pdf: print templates, Playwright renderer, panel checks, preflight, OFL fonts
content/        themes/<slug>/theme.yaml, styles/styles.yaml
infra/          Dockerfiles, postgres init
design/         Claude Design handoff (read-only)
```

## Privacy (so far)

- Photos and drawings live under `children/{child_id}/` in a private bucket. Browsers only get signed URLs that expire within 15 minutes; the code enforces the cap.
- The `maintenance` cron deletes original photos and drawings whose `delete_after` has passed, and drafts abandoned for 30 days. Every deletion is written to the audit log without PII.
- Deleting a child removes all of that child's rows in one cascade. Order items and costs keep their rows, with the link set to NULL.
- Never commit real children's photos or drawings. `out/` and `.env` are gitignored.
