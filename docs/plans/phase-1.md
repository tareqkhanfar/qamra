# Phase 1 — Foundations

Accept when: `docker compose up` gives a working login (register → login → account → logout) and `make test` passes.

## Pieces

| Piece | Where | Notes |
|---|---|---|
| Shared core | `packages/core` (`qamra_core`) | settings, SQLAlchemy 2 models (psycopg 3, async + sync), Alembic migrations, S3 storage adapter. Used by the api and the worker. |
| API | `apps/api` (`qamra_api`) | FastAPI under `/api`. Auth: email + password (argon2 via pwdlib), JWT access cookie (15 min) + rotating opaque refresh cookie (30 days, hashed in the DB, reuse detection). Google OIDC login is enabled when `GOOGLE_CLIENT_ID` is set. Roles parent / school_admin / admin. Friendly ar/en errors. JSON logs (structlog), request ids, optional Sentry. Login rate limit (Redis). CSRF: SameSite=Lax + required `X-Qamra-Client` header on unsafe methods. |
| Worker | `apps/worker` (`qamra_worker`) | RQ 2 worker and `rq cron`. First jobs: privacy cleanup (expired photos and drawings, abandoned drafts) and `ping`. |
| Web | `apps/web` | Next.js App Router, TypeScript, Tailwind with tokens from `design/tokens.json`, RTL-first, ar (default) / en. Pages: home, register, login, account. `/api/*` is rewritten to the api, so cookies are first-party. |
| Infra | `compose.yaml` + `infra/` | postgres 16, redis 7, local S3 (SeaweedFS, since MinIO no longer publishes images; bucket created at startup, data encrypted at rest), migrate (one-shot), api, worker, cron, web. All ports bound to 127.0.0.1 and overridable. Dockerfiles for python (api / worker targets) and web. |
| CI | `.github/workflows/ci.yml` | python: ruff, mypy, pytest against a postgres service (redis and S3 are faked in tests). web: prettier, eslint, tsc, build. images: `docker compose build`. |

## Data model (first migration)

- **Accounts:** users, organizations, classrooms, refresh_tokens.
- **Children and their media:** children, consents, child_photos, characters, companions.
- **Books:** themes, books, book_pages.
- **Orders and printing:** orders, order_items, print_batches.
- **Tracking:** generation_costs, audit_logs.
- **Family voice** (designed now, used in Phase 5): recordings, share_tokens.

Deviations from the spec are listed in `docs/decisions.md`.

## Test database

- **Local tests:** `TEST_DATABASE_URL` points at a `qamra_test` database on the Qamra test server, reached through an SSH tunnel.
- **CI:** uses service containers.
- **Test run:** each session rebuilds the schema by running the Alembic migrations, so the migrations themselves are tested. Each test then runs inside a transaction that is rolled back.
