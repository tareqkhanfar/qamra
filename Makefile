.PHONY: install lint typecheck test web-check check up down logs e2e migration seed-themes admin fake-run

# .env is optional; when present its variables (e.g. TEST_DATABASE_URL) are exported to every recipe
ifneq (,$(wildcard .env))
include .env
export
endif

install:
	uv sync
	uv run playwright install chromium
	cd apps/web && npm ci

lint:
	uv run ruff check packages apps scripts conftest.py
	uv run ruff format --check packages apps scripts conftest.py

typecheck:
	uv run mypy

test:
	uv run pytest -q

web-check:
	cd apps/web && npx prettier --check "src/**/*.{ts,tsx,css}" "messages/*.json" && npx eslint . && npx tsc --noEmit

check: lint typecheck test web-check

# ---- docker compose
up:
	docker compose up --build -d
	@echo "→ http://localhost:$${QAMRA_WEB_PORT:-3000}"

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

e2e:  # browser acceptance check against a running stack
	uv run scripts/e2e_auth.py --base-url http://localhost:$${QAMRA_WEB_PORT:-3000} --screenshots out/e2e

# ---- database
migration:  # make migration m="add something"
	uv run python scripts/make_migration.py $(m)

seed-themes:
	docker compose exec api qamra seed-themes

admin:  # make admin email=you@example.com name="Tareq"
	docker compose exec api qamra create-user --email $(email) --name "$(name)" --role admin

# Offline end-to-end book with fake providers ($0)
fake-run:
	uv run scripts/prototype.py --photo packages/ai/tests/fixtures/face-astronaut-public-domain.png \
		--name "سلمى" --gender f --age 5 --theme first-day --style watercolor --lang ar \
		--provider fake --drawing packages/ai/tests/fixtures/drawings/drawing-2.jpg --companion-name "بوبو"
