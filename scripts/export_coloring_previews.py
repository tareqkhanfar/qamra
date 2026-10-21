"""Web previews of «دفاتر التلوين والرسم» (the site's /coloring pages): for each of the four books, its real
cover and a selection of inside pages, drawn by the local engine for the sample child «ليان» and her
AI-drawn sample character (no real child's data, no AI cost).

    uv run python scripts/export_coloring_previews.py               # render (if missing) and export all four
    uv run python scripts/export_coloring_previews.py --only coloring-letters --render

Sources: out/coloring/<title>/f/{cover,interior}.pdf (`python -m qamra_workbook.render.coloring --title …`).
Writes apps/web/public/coloring/<slug>/cover.webp and NN.webp (720 px wide) with a 360 px copy (…-sm.webp),
and apps/web/src/lib/coloring-previews.json:
{slug: {"cover": {src, sm, w, h}, "pages": [{src, sm, w, h, caption_ar, caption_en}]}}. URLs carry a digest
of the image (`?v=…`) so a new export is never hidden by a cached copy.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/web/public/coloring"
MANIFEST = ROOT / "apps/web/src/lib/coloring-previews.json"
WIDTH, SMALL = 720, 360
QUALITY = 82
BLEED_MM = 3.0
DPI = 150

sys.path.insert(0, str(ROOT / "packages/workbook/src"))

import re  # noqa: E402

from qamra_workbook.coloring.book import content, interior_pages  # noqa: E402
from qamra_workbook.coloring.letters import load as load_letters  # noqa: E402
from qamra_workbook.coloring.titles import TITLES, title_of  # noqa: E402
from qamra_workbook.render.spec import Child  # noqa: E402

SAMPLE = Child("ليان", "f")
# the site's captions are plain Arabic with the shadda and the tanween of «ـًا» kept («لوّني»، «يومًا»)
_SHORT_VOWELS = re.compile("[ٌٍَُِْ]")


def plain(text: str) -> str:
    return _SHORT_VOWELS.sub("", text)


# the inside pages each product page shows (page numbers in the book)
PICKS: dict[str, list[int]] = {
    "letters": [1, 2, 3, 4, 7, 12, 19, 25, 30, 31],
    "palestine": [1, 2, 3, 5, 8, 11, 14, 17, 21, 27],
    "ramadan": [1, 2, 3, 5, 7, 10, 13, 16, 19, 23],
    "sketchbook": [1, 2, 3, 5, 8, 12, 17, 23, 30, 46],
}


# The site describes a drawing page neutrally (never «ارسمي…» to a girl): by the sketchbook page's id or kind,
# the free drawing page of a scene book, the fixed pages. Scenes and letters keep their own titles.
SITE_CAPTIONS: dict[str, tuple[str, str]] = {
    "my-sketchbook": ("صفحة اسم الطفل وعمره والتاريخ", "The page for the child's name, age and the date"),
    "draw-yourself": ("صفحة يرسم فيها الطفل نفسه", "A page where the child draws themselves"),
    "my-family": ("صفحة لرسم العائلة", "A page to draw the family"),
    "finish-butterfly": ("صفحة لإكمال رسم الفراشة", "A page to finish drawing the butterfly"),
    "winter-rain": ("الشتاء: صفحة لرسم يوم ممطر", "Winter: a page to draw a rainy day"),
    "my-garden": ("صفحة لتلوين الحديقة ورسمها", "A page to color and draw a garden"),
    "night-sky": ("صفحة لرسم السماء في الليل", "A page to draw the sky at night"),
    "my-favourite-drawing": ("صفحة «رسمتي المفضّلة»", "The “My favorite drawing” page"),
    "blank": ("صفحة رسم حرّ بإطار مزيّن", "A framed page for free drawing"),
    "free-palestine": ("صفحة يرسم فيها الطفل فلسطين", "A page where the child draws Palestine"),
    "free-ramadan": ("صفحة يرسم فيها الطفل فانوسه", "A page where the child draws a lantern"),
    "cb-title": ("صفحة العنوان باسم الطفل", "The title page with the child's name"),
    "cb-me": ("صفحة الاسم، ويرسم فيها الطفل نفسه", "The name page, where the child draws themselves"),
    "cb-certificate": ("صفحة «أحسنت!» في آخر الدفتر", "The “Well done!” page at the end"),
    "about-qamra": ("عن قمرة ورمز الكتاب", "About Qamra and the book code"),
}


def captions(key: str) -> dict[int, tuple[str, str]]:
    """Each page's caption on the site in Arabic and English: a scene's or a letter's own title, else a
    neutral description (`SITE_CAPTIONS`); a `{child}` left in a caption takes the sample child's name."""
    pages = interior_pages(key)
    out: dict[int, tuple[str, str]] = {}
    scenes: dict[str, str] = {}
    if key in ("palestine", "ramadan"):
        scenes = {str(p["caption_ar"]): str(p.get("caption_en", "")) for p in content(key)["pages"]}
    sketch = content("sketchbook")["pages"] if key == "sketchbook" else []
    letters = {x.name_ar: x.name_en for x in load_letters().letters}
    for p in pages:
        if p.type == "cb-letter":
            ar, en = p.title, f"The letter {letters.get(p.title, '')}"
        elif p.type == "cb-scene":
            ar, en = p.title, scenes.get(p.title, "")
        elif p.type in SITE_CAPTIONS:
            ar, en = SITE_CAPTIONS[p.type]
        elif key in ("palestine", "ramadan"):
            ar, en = SITE_CAPTIONS[f"free-{key}"]
        else:  # a sketchbook page (the title page comes first): by its id, a blank page by its kind
            page = sketch[p.number - 2]
            found = SITE_CAPTIONS.get(str(page["id"])) or SITE_CAPTIONS.get(str(page.get("kind")))
            ar, en = found or (str(page.get("prompt_ar") or ""), str(page.get("prompt_en", "")))
        out[p.number] = (plain(SAMPLE.personalize(ar)), en.replace("{child}", SAMPLE.name))
    return out


def _webp(img: Image.Image, width: int) -> tuple[bytes, int, int]:
    out = img.copy()
    if out.width > width:
        out = out.resize((width, round(out.height * width / out.width)), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="WEBP", quality=QUALITY, method=6)
    return buf.getvalue(), out.width, out.height


def _page(pdf: Path, index: int) -> Image.Image:
    doc = pdfium.PdfDocument(pdf)
    try:
        img: Image.Image = doc[index].render(scale=DPI / 72).to_pil().convert("RGB")
    finally:
        doc.close()
    cut = round(BLEED_MM / 25.4 * DPI)
    trimmed: Image.Image = img.crop((cut, cut, img.width - cut, img.height - cut))
    return trimmed


def _save(slug: str, name: str, img: Image.Image, extra: dict[str, Any]) -> dict[str, Any]:
    target = OUT / slug
    target.mkdir(parents=True, exist_ok=True)
    big, w, h = _webp(img, WIDTH)
    small, _, _ = _webp(img, SMALL)
    (target / f"{name}.webp").write_bytes(big)
    (target / f"{name}-sm.webp").write_bytes(small)
    digest = hashlib.sha1(big + small).hexdigest()[:8]
    base = f"/coloring/{slug}/{name}"
    return {"src": f"{base}.webp?v={digest}", "sm": f"{base}-sm.webp?v={digest}", "w": w, "h": h, **extra}


def export(key: str, render: bool) -> dict[str, Any]:
    t = title_of(key)
    src = ROOT / "out/coloring" / key / "f"
    if render or not (src / "interior.pdf").is_file():
        cmd = [
            "uv",
            "run",
            "python",
            "-m",
            "qamra_workbook.render.coloring",
            "--title",
            key,
            "--out",
            str(src),
        ]
        subprocess.run(cmd, cwd=ROOT, check=True)
    caps = captions(key)
    entry: dict[str, Any] = {"cover": _save(t.slug, "cover", _page(src / "cover.pdf", 0), {}), "pages": []}
    for i, n in enumerate(PICKS[key], start=1):
        ar, en = caps[n]
        entry["pages"].append(
            _save(
                t.slug, f"{i:02d}", _page(src / "interior.pdf", n - 1), {"caption_ar": ar, "caption_en": en}
            )
        )
    return entry


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", default="", help="store slugs, comma-separated")
    ap.add_argument("--render", action="store_true", help="render the sources first")
    args = ap.parse_args()
    only = {s for s in args.only.split(",") if s}
    manifest: dict[str, Any] = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    for t in TITLES.values():
        if only and t.slug not in only:
            continue
        manifest[t.slug] = export(t.key, args.render)
        print(t.slug, len(manifest[t.slug]["pages"]), "pages")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
