# قمرة · Qamra

«حكاية طفلك… تحت ضوء القمر»: personalized Arabic storybooks and activity books where the child is the hero and the child's own drawing becomes their companion.

Specs: [CLAUDE.md](CLAUDE.md) + addenda [01](docs/ADDENDUM-01.md), [03](docs/ADDENDUM-03.md), [04](docs/ADDENDUM-04.md) (store, Classic and Magic, the studio), [05](docs/ADDENDUM-05.md) (foundation workbook), [06](docs/ADDENDUM-06.md) (learning journey), [07](docs/ADDENDUM-07.md) (family book), [09](docs/ADDENDUM-09.md) (store UX). Decisions: [docs/decisions.md](docs/decisions.md). Plans and the master checklist: [docs/plans/](docs/plans/) ([remaining-work.md](docs/plans/remaining-work.md)). What each product does: [docs/feature-matrix.md](docs/feature-matrix.md). Changes: [docs/CHANGELOG.md](docs/CHANGELOG.md).

**Status (2026-09-29): every phase of the build prompt and Addenda 1–9 is built and deployed to the test server, except the activity-book volumes still being written. What remains needs Tareq or a third party (see the checklist).**
- **Story books:** «قمرة كلاسيك» (a template per story × style × look; only the hero is edited to the child, ≤ 2₪) and «قمرة سحري» (every page drawn for the child, ≤ $2.50), with real example books of invented children on the site, a flip-through, the free cover, the drawing companion, custom stories, «صوت أهلي» (recordings and a QR per page), the reader and share links.
- **Store (Addendum 9):** shop, quiz, the story page with a live price, add-ons after the preview, the cart (second book −15%, coupons, gift cards, gift orders), cash on delivery, email notifications, print batches with the printer's links.
- **Kindergartens:** sign-up with approval, classes, CSV import, parent invite links, «كتاب الصف» drawn in one batch with bulk approval, price lists, one invoice.
- **Activity books:** «مغامراتي مع عائلتي» (112 pages, both sizes, inserts with die lines, rendered per order), «رحلتي الأولى» stage 1 (118 pages, audio QR), «دوسية التأسيس» KG2 volume 1 (128 pages, answer key). The educational books stay «قريبًا» until the educator signs.
- **Admin:** approval queue, the template studio (theme versions, page editor, bulk actions), staff roles, the audit log, catalog and prices, reports, cost per line, print costs, organizations, leads, journey audio, settings with 2FA.
- **Operations:** the production overlay, encrypted backups with a restore drill, monitoring and runbooks (`docs/runbooks/`).

## Run the stack

Requirements: Docker with Compose v2.

```bash
cp .env.example .env        # defaults work locally; set real secrets anywhere else
docker compose up --build   # → http://localhost:3000 (ar) · API docs http://localhost:3000/api/docs
```

To open it to the network (e.g. a test server), set `QAMRA_BIND=0.0.0.0` and `QAMRA_WEB_PORT` in `.env`. Only the nginx `edge` is exposed; it sets the real client IP, which the login rate limits depend on. Without TLS, traffic (passwords included) is plain HTTP, so use test accounts only until HTTPS is on.

**HTTPS (Addendum 3 §6):** point a domain's A record at the server, then run `sudo infra/scripts/setup-https.sh qamra.example.com you@example.com`. It adds a host-nginx site with Let's Encrypt in front of the edge and binds the edge to localhost. `infra/scripts/firewall.sh` prepares ufw (22/80/443 only); it is a dry run unless given `--apply`.

**Production:** `docker compose -f compose.yaml -f compose.prod.yaml up -d --build`, following `docs/runbooks/production.md`.

**First admin sign-in:** the admin area asks for two-step verification setup (authenticator app + recovery codes). If an admin loses both, run `docker compose exec api qamra reset-2fa --email …` on the server.

| service | what | published port |
|---|---|---|
| `edge` | nginx, the only entry point: `/api/*` → api, everything else → web; sets the real client IP | `QAMRA_BIND`:`QAMRA_WEB_PORT` 3000 |
| `web` | Next.js (App Router, RTL, ar/en) | — |
| `api` | FastAPI: auth, the store, the create flow, the portal, the admin | `QAMRA_API_PORT` 8000 (debug) |
| `worker` / `cron` | RQ worker (books, Classic, class books, activity books, PDFs, emails, print batches) and the scheduler (privacy cleanup every 15 min, scheduled go-lives) | — |
| `migrate` | one-shot `alembic upgrade head`, then the theme and store seeds | — |
| `postgres` | Postgres 16 (`qamra` + `qamra_test`) | `QAMRA_PG_PORT` 5433 |
| `redis` | Redis 7 (queues, rate limits) | `QAMRA_REDIS_PORT` 6380 |
| `s3` | SeaweedFS as local S3 (R2 in production) | `QAMRA_S3_PORT` 8333 |

Useful commands:

```bash
make admin email=you@example.com name="Tareq"    # create an admin (prompts for the password)
make seed-themes                                  # load content/themes/*/theme.yaml into the DB
docker compose run --rm migrate qamra seed-store   # insert the starting catalog and quiz rules (insert-only; runs on deploy)
uv run python scripts/classic_proof.py --creds DIR status   # Classic templates on a server (from-samples, texts, publish, proof)
uv run python -m qamra_workbook.render.family --book --size both        # «مغامراتي مع عائلتي», 112 pages + inserts
uv run python -m qamra_workbook.render.journey --stage 1 --book         # «رحلتي الأولى» stage 1
uv run python -m qamra_workbook.render.workbook --level kg2 --volume 1  # «دوسية التأسيس» KG2 volume 1
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

Tests use fake AI providers, fakeredis and moto (S3). Only Postgres is real: each run rebuilds `*_test` through the migrations, and each test is rolled back. The browser E2E flows of the order path are in `tests/e2e/` (`docs/e2e.md`).

## Sample books, examples and Classic templates

On the server: **Admin → Sample books** (consent checkbox, 1–3 photos, optional drawing). Tick "placeholder art" for a $0 run. The book appears in **Admin → Approval queue**, where an approved book of an **invented** child can be published as a public example («انشره نموذجًا على الموقع») and, through `scripts/classic_proof.py from-samples`, turned into a Classic template (hero boxes, vowelized texts, then `publish`). Real children's books are never published.

Locally:

```bash
make sample-book                 # offline, design-style placeholder art ($0) → out/<run>/
uv run scripts/sample_book.py --photo kid.jpg --name "سلمى" --gender f --age 5 --hijab \
  --theme first-day --provider fal --message "إلى سلمى…"   # real providers (keys in .env)
```

Each run writes `interior.pdf`, `cover.pdf` (RTL wrap with spine), `proof.pdf`, `report.md` (preflight, QA per page, regeneration rate, cost), `story.json` and `cost.json`.

## Layout

```
apps/api        qamra_api: FastAPI (auth + 2FA, the store and order path, the create flow, examples, the portal, voice, admin), CLI (`qamra`)
apps/worker     qamra_worker: RQ jobs (Magic and Classic books, class books, companions, family/journey books, emails, print batches, cleanup), cron
apps/web        Next.js frontend (src/app/[locale], messages/ar.json + en.json)
packages/core   qamra_core: settings, SQLAlchemy models, Alembic migrations, S3 storage, pricing, printing, test fixtures
packages/ai     qamra_ai: providers (fal/Gemini/OpenAI/Claude + sketch), the pipelines (Magic, Classic, class books, custom stories), prompts, pricing, TTS adapter
packages/pdf    qamra_pdf: print templates, Playwright renderer, preflight, QR codes, OFL fonts
packages/workbook qamra_workbook: the activity-book engine (plans, page types, pictures, letter paths, die lines, the family/journey/foundation books)
content/        themes/, store/catalog.yaml, class-books/, family-book/, journey/, workbook/curriculum/, emails/
infra/          Dockerfiles, nginx, postgres init, backup/restore/monitor scripts
design/         Claude Design handoff (read-only); design/addendum-09/ holds the store screens
tests/e2e       Playwright flows of the order path
```

## Privacy

- Photos, drawings, recordings and family members' photos live under `children/{child_id}/` in a private bucket. Browsers only get signed URLs that expire within 15 minutes; the code enforces the cap.
- Original photos and drawings are deleted 24 h after the character or companion is approved; the free cover's photo 24 h after upload; drafts abandoned for 30 days. The `maintenance` cron runs every 15 minutes and writes every deletion to the audit log without PII.
- Deleting a child removes all of that child's rows and files in one cascade, including their likeness on a class book's shared pages. Order items and costs keep their rows, with the link set to NULL.
- Only sample books of invented children can be public examples or Classic templates; backups never contain children's photos.
- Never commit real children's photos or drawings. `out/` and `.env` are gitignored.
