# Decisions log

Newest first. Each entry: date — decision — why.

## 2026-09-28

- **Brand is قمرة / Qamra** (Addendum 1). The name, domain and support contacts come from config (`BRAND_NAME_AR`, `BRAND_NAME_EN`, `BRAND_DOMAIN`), not code. `CLAUDE.md` was renamed too. `design/README.md` still says "حكايتي" in two places (the preview watermark text and the B2B owner tag). `/design` is read-only, so I left it; the code renders the watermark from config.
- **Design handoff is partial.** The `/design` canvas holds the design system (tokens, dark mode, logo options, components, illustration parts). It does not hold the 77 screen artboards or the print-layout artboards that `design/README.md` lists. The Phase 0 PDF follows the README print spec and `tokens.json`. The screens will need the per-screen HTML exports before Phase 2.
- **Logo placeholder: option A «هلال على صفحة»**, matching the design README.
- **Python tooling: uv workspace** (`packages/ai`, `packages/pdf`). It is fast and gives a single lockfile. It is also already installed.
- **Default image model: Gemini `gemini-3.1-flash-image` at 2K** ($0.101 per image; the paid tier does not train on our data). The alternatives are behind the same interface: fal `fal-ai/flux-2-pro/edit` (FLUX.2 has replaced FLUX.1 Kontext as fal's multi-reference editor, with up to 9 refs) and OpenAI `gpt-image-2.5-sunburst` (the "editing precision" variant). Model IDs live in `.env`.
- **fal: no CDN uploads.** Reference images go to fal as base64 data URIs, and results come back with `sync_mode` as data URIs. A child's photo therefore never gets a public fal.media URL.
- **Text model default: `claude-opus-5`** for story adaptation and vowelization, where Arabic quality matters most. Safety and judge calls use a separate setting (`TEXT_MODEL_FAST`), which also defaults to `claude-opus-5`. Moving those to a cheaper model is a cost decision for Tareq.
- **Print size: 216×216 mm pages** (210 mm trim + 3 mm bleed on each side). Images are generated square and upscaled to 2551 px (300 DPI at 216 mm) with Lanczos in Phase 0. A real upscaler is a Phase 2 decision.
- **CMYK:** Chromium writes RGB PDFs. Phase 0 keeps the palette CMYK-safe by avoiding saturated RGB-only colors in the layouts; the images are left untouched. Converting to the printer's ICC profile (Ghostscript) is deferred until we know the print partner's profile.
- **Book body font:** Baloo Bhaijaan 2 (the design's display font) for titles. Story text uses Noto Naskh Arabic because its تشكيل placement is clearer for early readers than a rounded display face. This is a deviation from the design body font (IBM Plex Sans Arabic); see the PDF samples to decide.
- **Photo check uses YuNet** (`FaceDetectorYN`, MIT license, OpenCV zoo, 230 KB model in `qamra_ai/models_data`). OpenCV 5 no longer ships Haar cascades, and YuNet handles non-frontal kid photos far better. It is a detector only; no face recognition or embeddings. No InsightFace or other research-only models are used.
- **Fonts are embedded as static instances.** Chromium embeds *variable* fonts as Type 3, which print RIPs often reject. `BalooBhaijaan2-{Medium,ExtraBold}` and `NotoNaskhArabic-{Regular,Bold}` were instanced with fontTools from the OFL variable fonts. A test asserts that no Type 3 fonts are present.
- **PDF page box is 612 × 612 pt (215.9 mm)**, not exactly 216 mm, because Chromium quantizes to CSS px (816 px, the design's artboard size). That is 0.1 mm under the bleed box. Confirm with the print partner; if they need exact sizes, post-process the MediaBox with pypdf.
- **Prompt templates render with `trim_blocks=False`**, and `render()` collapses runs of blank lines. With `trim_blocks` on, an inline `{% endif %}` swallowed the following newline and glued prompt lines together (caught in the story prompt).
- **Drawing shadow removal fits a quadratic lighting surface to paper pixels only** (low saturation, bright). The first version used local dilate + median-blur background estimation, which erased large crayon fills to white.
- **Cover and page composition:** page prompts ask for a calm top quarter (a third on the cover) for the text box. Faces stay out of the outer 6%, which is roughly the bleed plus a margin.
- **Interior page count is not yet padded to a multiple of 4** (it is currently title + 12 + keepsake = 14). Padding rules depend on the print partner's binding.
- **Recognizability metric (Phase 0):** a Claude vision judge compares each page with the approved character sheet. This is a proxy until a commercially licensed face-similarity model is chosen for the admin QA screen.
