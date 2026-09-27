.PHONY: install lint typecheck test check fake-run

install:
	uv sync
	uv run playwright install chromium

lint:
	uv run ruff check packages scripts
	uv run ruff format --check packages scripts

typecheck:
	uv run mypy

test:
	uv run pytest -q

check: lint typecheck test

# Offline end-to-end run with fake providers ($0)
fake-run:
	uv run scripts/prototype.py --photo packages/ai/tests/fixtures/face-astronaut-public-domain.png \
		--name "سلمى" --gender f --age 5 --theme first-day --style watercolor --lang ar \
		--provider fake --drawing packages/ai/tests/fixtures/drawings/drawing-2.jpg --companion-name "بوبو"
