# قمرة · Qamra

«حكاية طفلك… تحت ضوء القمر»: personalized Arabic storybooks where the child is the hero and the child's own drawing becomes their companion.

Specs: [CLAUDE.md](CLAUDE.md) + [docs/ADDENDUM-01.md](docs/ADDENDUM-01.md). Decisions: [docs/decisions.md](docs/decisions.md). Plans: [docs/plans/](docs/plans/).

**Status: Phase 0 (prototype script).** There is no web app yet.

## Setup

Requirements: Python 3.12, [uv](https://docs.astral.sh/uv/).

```bash
make install            # uv sync + Playwright Chromium
cp .env.example .env    # add keys: ANTHROPIC_API_KEY + one of GEMINI_API_KEY / FAL_KEY / OPENAI_API_KEY
make check              # ruff + mypy + tests (offline, fake providers)
make fake-run           # full book end to end with fake providers, $0 → out/<run>/
```

## Prototype

```bash
uv run scripts/prototype.py --photo kid.jpg --name "سلمى" --gender f --age 5 \
  --theme first-day --style watercolor --lang ar --provider gemini \
  --drawing drawing.jpg --companion-name "بوبو" --companion-type creature
```

- `--provider gemini|flux|openai|fake` (default `IMAGE_PROVIDER`).
- `--style watercolor|crayon|papercut`, `--lang ar|en`.
- `--photo` can be repeated up to 3 times.
- `--interests "الرسم,الديناصورات"`, `--companion-pick 1|2`, `--preview` (watermark).

Output in `out/<timestamp>-<provider>-<theme>/`:

| file | what |
|---|---|
| `character-sheet.png` | hero reference sheet (front + 2 poses) |
| `companion/` | cleaned drawing, 2 options, drawing review |
| `pages/` | raw cover + page images |
| `story.json` | adapted story (vowelized for ages ≤ 7) |
| `interior.pdf`, `cover.pdf` | print files: 216 mm pages with 3 mm bleed, fonts embedded |
| `report.md`, `cost.json` | recognizability per page, companion fidelity, cost per step |
| `reviews.json` | every page attempt with its review |

Companion fidelity over a folder of drawings:

```bash
uv run scripts/companion_eval.py --drawings path/to/drawings/ --provider gemini
```

## Layout

```
packages/ai     qamra_ai: config, provider adapters (image/, text/), prompts/*.v1.j2, pipeline/, pricing.yaml
packages/pdf    qamra_pdf: HTML/CSS print templates, fonts (OFL), Playwright renderer
content/        themes/<slug>/theme.yaml, styles/styles.yaml
scripts/        prototype.py, companion_eval.py
design/         Claude Design handoff (read-only)
docs/           plans, decisions, changelog
```

Switch models without touching code: `IMAGE_PROVIDER`, `GEMINI_IMAGE_MODEL`, `FLUX_IMAGE_MODEL`, `OPENAI_IMAGE_MODEL`, `TEXT_MODEL`, `TEXT_MODEL_FAST` in `.env`. Prices live in `packages/ai/src/qamra_ai/pricing.yaml`.

## Privacy notes (Phase 0)

The prototype writes to local `out/`, which git ignores. Never commit real children's photos or drawings. Photos go only to the chosen image provider and to Claude (for the page review). For fal, images are sent inline as data URIs, never uploaded to their CDN. Encrypted storage, signed URLs and auto-deletion start in Phase 1 and 2.
