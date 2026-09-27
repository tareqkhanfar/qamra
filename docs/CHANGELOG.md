# Changelog

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
