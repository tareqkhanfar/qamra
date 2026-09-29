"""Web previews for the activity-book pages (Addendum 9, WorkbookProduct): a few real pages per product, drawn
by the workbook engine for its sample child (an invented «ليان», AI-drawn character), exported once as small
JPEGs into apps/web/public/workbooks/<product>/, listed in apps/web/src/lib/workbook-previews.json (the page
imports it). No real child's data.

    uv run python -m qamra_workbook.render.samples      # the engine's sample pages → out/samples/<book>/png/
    uv run python scripts/export_workbook_previews.py

«دوسية التأسيس» has no engine renders yet: add it here once `qamra_workbook.render.workbook` renders pages.
"""

import io
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/web/public/workbooks"
MANIFEST = ROOT / "apps/web/src/lib/workbook-previews.json"
WIDTH = 720  # A4 pages at ~2× a 360 px card

# product slug → (source folder, [(file stem, title ar, title en)])
PAGES: dict[str, tuple[Path, list[tuple[str, str, str]]]] = {
    "learning-journey": (
        ROOT / "out/samples/journey/png",
        [
            ("03-maze", "متاهة: ساعدي ليان للوصول إلى الحديقة", "A maze to the garden"),
            ("06-smart-coloring", "تلوين ذكي", "Smart coloring"),
            ("09-finger-trace", "أتتبّع بإصبعي", "Trace with a finger"),
            ("10-en-letter", "حرف إنجليزي", "An English letter"),
            ("11-spot-difference", "جِد الفرق", "Spot the difference"),
            ("12-certificate", "شهادة الرحلة باسمه", "A certificate in their name"),
        ],
    ),
    "family-adventures": (
        ROOT / "out/samples/family/png",
        [
            ("01-passport", "جواز سفر المغامر", "The adventurer's passport"),
            ("04-scavenger-hunt", "مغامرة البحث في البيت", "A treasure hunt at home"),
            ("06-shopping-list", "قائمة مشتريات السوق", "The market shopping list"),
            ("07-recipe-steps", "الشيف الصغير: خطوات الوصفة", "Little chef: the recipe steps"),
            ("08-feelings-thermometer", "ميزان المشاعر", "The feelings thermometer"),
            ("12-play-money", "نقود قمرة للّعب", "Qamra play money"),
        ],
    ),
}
CHARACTER = ROOT / "out/samples/journey/assets"  # the sample character's standing pose, for the cover mock-up


def _jpeg(src: Path, width: int, quality: int = 80) -> bytes:
    with Image.open(src) as img:
        rgb = img.convert("RGB")
    rgb.thumbnail((width, width * 2), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def main() -> None:
    listing: dict[str, list[dict[str, str]]] = {}
    for slug, (folder, pages) in PAGES.items():
        target = OUT / slug
        target.mkdir(parents=True, exist_ok=True)
        manifest = []
        for n, (stem, title_ar, title_en) in enumerate(pages, start=1):
            name = f"{n:02d}.jpg"
            (target / name).write_bytes(_jpeg(folder / f"{stem}.png", WIDTH))
            manifest.append({"src": f"/workbooks/{slug}/{name}", "title_ar": title_ar, "title_en": title_en})
        listing[slug] = manifest
        print(f"{slug}: {len(manifest)} pages")
    MANIFEST.write_text(json.dumps(listing, ensure_ascii=False, indent=2) + "\n")
    pose = next(CHARACTER.glob("character-*-pose1.png"), None)
    if pose is not None:
        with Image.open(pose) as img:
            rgba = img.convert("RGBA")
        rgba.thumbnail((320, 640), Image.Resampling.LANCZOS)
        rgba.save(OUT / "character.webp", format="WEBP", quality=85, method=6)
        print("character.webp")


if __name__ == "__main__":
    main()
