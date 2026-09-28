# قمرة · Qamra

«حكاية طفلك… تحت ضوء القمر»: personalized Arabic storybooks where the child is the hero and the child's own drawing becomes their companion.

Specs: [CLAUDE.md](CLAUDE.md) + [docs/ADDENDUM-01.md](docs/ADDENDUM-01.md). Decisions: [docs/decisions.md](docs/decisions.md). Plans: [docs/plans/](docs/plans/). Changes: [docs/CHANGELOG.md](docs/CHANGELOG.md).

**Status: Phase 1 (foundations) done.** You can sign up, sign in and sign out in Arabic or English, on top of the full data model, the API, the worker and the prototype pipeline from Phase 0.

## Run the stack

Requirements: Docker with Compose v2.

```bash
cp .env.example .env        # defaults work locally; set real secrets anywhere else
docker compose up --build   # → http://localhost:3000 (ar) · API docs http://localhost:8000/api/docs
```

| service | what | port (127.0.0.1) |
|---|---|---|
| `web` | Next.js (App Router, RTL, ar/en). `/api/*` is proxied to the api | `QAMRA_WEB_PORT` 3000 |
| `api` | FastAPI: auth, health (later: books, orders…) | `QAMRA_API_PORT` 8000 |
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

## Prototype (Phase 0)

```bash
uv run scripts/prototype.py --photo kid.jpg --name "سلمى" --gender f --age 5 \
  --theme first-day --style watercolor --lang ar --provider gemini \
  --drawing drawing.jpg --companion-name "بوبو"
make fake-run      # same, offline with fake providers ($0) → out/<run>/
uv run scripts/companion_eval.py --drawings path/to/drawings/ --provider gemini
```

The prototype writes to `out/<run>/`: the character sheet, the companion, `story.json`, the pages, `interior.pdf` + `cover.pdf` (216 mm with bleed, fonts embedded), and `report.md` + `cost.json`.

## Layout

```
apps/api        qamra_api: FastAPI app (auth, health), admin CLI (`qamra`)
apps/worker     qamra_worker: RQ jobs (maintenance/privacy cleanup), cron config
apps/web        Next.js frontend (src/app/[locale], messages/ar.json + en.json)
packages/core   qamra_core: settings, SQLAlchemy models, Alembic migrations, S3 storage, test fixtures
packages/ai     qamra_ai: provider adapters, versioned prompts, generation pipeline, pricing
packages/pdf    qamra_pdf: print templates + Playwright renderer + OFL fonts
content/        themes/<slug>/theme.yaml, styles/styles.yaml
infra/          Dockerfiles, postgres init
design/         Claude Design handoff (read-only)
```

## Privacy (so far)

- Photos and drawings live under `children/{child_id}/` in a private bucket. Browsers only get signed URLs that expire within 15 minutes; the code enforces the cap.
- The `maintenance` cron deletes original photos and drawings whose `delete_after` has passed, and drafts abandoned for 30 days. Every deletion is written to the audit log without PII.
- Deleting a child removes all of that child's rows in one cascade. Order items and costs keep their rows, with the link set to NULL.
- Never commit real children's photos or drawings. `out/` and `.env` are gitignored.
