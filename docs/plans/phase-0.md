# Phase 0 — Prototype script

Goal: prove the generation pipeline end to end, from one command, with no web app.

```
uv run scripts/prototype.py --photo kid.jpg --name "سلمى" --gender f --age 5 \
  --theme first-day --style watercolor --lang ar \
  --provider gemini|flux|openai|fake \
  [--drawing drawing.jpg --companion-name "بوبو" --companion-type creature]
```

Output in `out/<run-id>/`: photo-check report, character sheet, (companion: cleaned drawing, 2 options, chosen sheet), story JSON, 12 page images, `interior.pdf`, `cover.pdf`, `cost.json` + `report.md`.

## Pieces (all reused in later phases)

| Piece | Where | Notes |
|---|---|---|
| Settings + brand config | `packages/ai/src/qamra_ai/config.py` | pydantic-settings, `.env`; `BRAND_NAME_AR/EN`, `BRAND_DOMAIN`; per-task model names |
| Prompt templates (versioned) | `packages/ai/src/qamra_ai/prompts/*.v1.j2` | Jinja2, loaded by name + version. No inline prompt strings. |
| Text provider | `qamra_ai/text/` | `TextProvider` protocol; `AnthropicTextProvider` (structured output via `messages.parse`), `FakeTextProvider` |
| Image providers | `qamra_ai/image/` | `ImageProvider` protocol → `GeminiImageProvider` (`gemini-3.1-flash-image`), `FluxImageProvider` (fal `fal-ai/flux-2-pro/edit`), `OpenAIImageProvider` (`gpt-image-2.5-sunburst`), `FakeImageProvider` |
| Cost ledger | `qamra_ai/cost.py` | Every call records provider, model, units, USD. Prices in `pricing.yaml`. |
| Photo check | `qamra_ai/pipeline/photo_check.py` | OpenCV (bundled Haar cascade, BSD): one face, face size, blur, brightness, resolution. Friendly ar/en messages. |
| Drawing clean-up | `qamra_ai/pipeline/drawing.py` | OpenCV: paper contour → perspective warp → shadow removal (background division) → contrast. |
| Character / companion / story / pages | `qamra_ai/pipeline/*.py` | Async, semaphore-bounded concurrency, tenacity retries. |
| Safety | `qamra_ai/pipeline/safety.py` | Claude reviews story text, drawing and each image (vision) → pass/fail + reason. |
| Consistency judge | `qamra_ai/pipeline/judge.py` | Claude vision compares each page against the character sheet → "recognizable" yes/no. Gives the ≥ 80% metric. |
| Theme | `content/themes/first-day/theme.yaml` | 12 pages, gendered Arabic templates, `companion_slot`, `companion_action` per page. |
| PDF | `packages/pdf` | Jinja2 HTML/CSS, 216×216 mm (210 + 2×3 mm bleed), embedded OFL fonts, Playwright → `interior.pdf` + `cover.pdf`. Keepsake page «وهكذا وُلد صاحبي». |

## Tests (fake providers, no network)

- photo check accepts/rejects synthetic images
- drawing pre-processing on 5 synthetic fixtures (perspective + shadow) → output is square-ish, background near-white
- page prompt includes both character and companion references
- story schema validation + gender variant rendering
- cost ledger totals
- PDF renders: page count, page size incl. bleed, fonts embedded, keepsake page present

## Acceptance (needs real keys — Tareq)

- runs end to end with `--provider gemini|flux|openai`
- judge says recognizable on ≥ 80% of pages
- Arabic PDF renders with diacritics
- companion fidelity reported on ≥ 5 drawings (`scripts/companion_eval.py`)

## Cost model (estimate, before real runs)

Per 12-page book with a drawing companion, defaults (Gemini 2K images, `claude-opus-5` everywhere):

| step | calls | est. USD |
|---|---|---|
| character sheet | 1 image | 0.10 |
| companion (review + 2 options + fidelity) | 2 images + 2 Claude | 0.25 |
| cover + 12 pages | 13 images | 1.34 |
| auto-redraws (~15% of pages) | ~2 images | 0.20 |
| story + safety | 2 Claude | 0.20–0.30 |
| page reviews (vision) | ~15 Claude | 0.30–0.45 |
| **total** | | **≈ $2.4–2.6** |

Scaled to 20 pages this is about $3.3–3.6, which is **over the $3 target**. The levers, in order of quality risk:
1. `TEXT_MODEL_FAST=claude-sonnet-5` for reviews and safety: about −$0.3.
2. Generate at `GEMINI_IMAGE_SIZE=1K` and upscale: about −$0.7 at 20 pages (quality to be judged on real prints).
3. Review only on the first attempt and on redraws flagged by the parent.

The real numbers come from `report.md` after the first keyed runs.
