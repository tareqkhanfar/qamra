# Licenses: models, fonts and software

Every model and font Qamra uses, and its license. Addendum 4 §8: **only commercially licensed models**. Before adding any model (and before self-hosting any weights), record its license here and get Tareq's approval. A self-hosted workflow runs only if its name is in `APPROVED_WORKFLOWS` (`packages/ai/src/qamra_ai/image/comfy.py`), which is added after approval.

## Models used through paid APIs

The provider's terms cover commercial use of outputs. Each is used only with terms that exclude training on our data (CLAUDE.md §3).

| Model | Where | Use | Notes |
|---|---|---|---|
| Nano Banana 2 (`fal-ai/nano-banana-2`, `/edit`) | fal | Magic pages, covers, character sheets | Default image model. fal privacy headers: no stored I/O, 15-minute file expiry |
| FLUX.2 [pro] edit (`fal-ai/flux-2-pro/edit`) | fal | Fallback image model | |
| SeedVR upscaler (`fal-ai/seedvr/upscale/image`) | fal | Print upscaling | API only. Weights license to verify before any self-hosting |
| Gemini image (`gemini-3.1-flash-image`) | Google | Selectable alternative | Paid tier: no training on our data |
| GPT Image (`gpt-image-2.5-sunburst`) | OpenAI | Selectable alternative | |
| Claude Sonnet 5 / Haiku 4.5 | Anthropic | Story, vowelization, safety review, page QA | API data is not used for training |

## Classic edits (Addendum 4 step 3): awaiting approval

| Model | License | Status |
|---|---|---|
| FLUX.2 [klein] **4B** (`fal-ai/flux-2/klein/4b/edit`) | Apache 2.0 (weights): commercial use and self-hosting allowed | Recommended; **awaiting Tareq's approval** |
| FLUX.2 [klein] 9B | FLUX Non-Commercial License (weights) | fal allows commercial use through its API, but the weights can **never** be self-hosted |

## Never allowed without a bought commercial license

- InsightFace models and anything built on them: inswapper, antelopev2, buffalo_l, and face-swap tools that load them.
- "dev" or non-commercial weights, e.g. FLUX.1 [dev].

## Local models (run inside our own code)

| Model | License | Use |
|---|---|---|
| YuNet face detector (OpenCV zoo, `face_detection_yunet_2023mar.onnx`) | MIT | Photo check before upload. Detection only: no recognition or embeddings |

## Fonts (embedded in PDFs and the site)

| Font | License |
|---|---|
| Baloo Bhaijaan 2 | SIL Open Font License 1.1 |
| Noto Naskh Arabic | SIL Open Font License 1.1 |
| IBM Plex Sans Arabic | SIL Open Font License 1.1 |
| Amiri Quran 1.003 | SIL Open Font License 1.1 (the Quran text of «قلبي يعرف الله», Addendum 10) |

## «قلبي يعرف الله»: the Quran font and the religious texts (Addendum 10 §3)

| Item | License / status | Note |
|---|---|---|
| **Amiri Quran** (`packages/pdf/src/qamra_pdf/fonts/AmiriQuran-Regular.ttf`, licence text `OFL-AmiriQuran.txt`) | SIL OFL 1.1, © 2010-2022 The Amiri Quran Project Authors (github.com/aliftype/amiri). Embedding in print PDFs and commercial sale of documents that use it is allowed; the font itself must not be sold on its own | Static TrueType (no variable font, so Chromium embeds it as TrueType, not Type 3). Fetched from `github.com/google/fonts` (`ofl/amiriquran`, Amiri release 1.003). Covers the harakat, the dagger alef, the Quranic annotation signs (U+06D6–U+06ED), the ayah-end sign U+06DD and ﷺ (U+FDFA). Used only for verses on the series' pages |
| KFGQPC Uthmanic Hafs (King Fahd Complex) | **not used**: its licence has not been read and recorded | Alternative if the scholar prefers the Madinah mushaf script: read its licence terms first and record them here before adding it |
| Tanzil Uthmani text (`content/islamic/quran/quran-uthmani.txt`) | Tanzil terms: verbatim copies may be distributed, changing the text is not allowed, the copyright header must be kept | **File not in the repo yet** (tanzil.net does not answer from the build server). Tareq places it there; then copy its header lines here. Until then pages print a marked placeholder and a print build fails |
| Hadith candidates (`fawazahmed0/hadith-api` through jsdelivr) | The API code is Unlicense; the status of each collection's text is the scholar's call | Used only to sanity-check references and to preview pages (`content/islamic/candidates.json`, status `text_candidate`). Never printed before the scholar approves each source |

## Self-hosted software

| Software | License | Note |
|---|---|---|
| ComfyUI | GPL-3.0 | Runs as a separate server that we don't distribute; our code talks to it over HTTP |
