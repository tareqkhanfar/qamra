"""Web previews for the activity-book pages (Addendum 9, WorkbookProduct): a few real pages per product, drawn
by the workbook engine for its sample child (an invented «ليان», AI-drawn character), exported once as small
JPEGs into apps/web/public/workbooks/<product>/, listed in apps/web/src/lib/workbook-previews.json (the page
imports it). No real child's data.

    uv run python -m qamra_workbook.render.samples      # the engine's sample pages → out/samples/<book>/png/
    uv run python -m qamra_workbook.render.journey --stage 1 --book   # «رحلتي الأولى» stage 1 → out/journey/
    uv run python -m qamra_workbook.render.samples --product family
    uv run python -m qamra_workbook.render.workbook --level kg2 --volume 1   # «دوسية التأسيس» → out/workbook/
    uv run python -m qamra_workbook.render.workbook --level kg1 --volume 1   # and --volume 3 for KG1
    uv run python scripts/export_workbook_previews.py
    uv run python -m qamra_workbook.render.workbook --level kg2 --volume 3   # reading and adding
    uv run python scripts/export_workbook_previews.py --only foundation-workbook-kg1   # one product
    uv run python scripts/export_workbook_previews.py --only foundation-workbook-v3    # KG2 volume 3
"""

import io
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/web/public/workbooks"
MANIFEST = ROOT / "apps/web/src/lib/workbook-previews.json"
WIDTH = 720  # A4 pages at ~2× a 360 px card

def journey_pages(stage: int, folder: str, pages: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    """One stage's pages of «رحلتي الأولى»: the stem is read from the stage's folder (relative to stage 1's),
    and the stage goes in front of both captions."""
    return [(f"{folder}/{stem}", f"المحطة {stage}: {ar}", f"Stage {stage}: {en}") for stem, ar, en in pages]


# product slug → (source folder, [(file stem, title ar, title en)])
PAGES: dict[str, tuple[Path, list[tuple[str, str, str]]]] = {
    # «رحلتي الأولى للتعلّم»: eight real pages of each stage, as rendered by
    # `uv run python -m qamra_workbook.render.journey --stage N --book`, with the stage in every caption (see
    # `journey_pages`). One product, so one preview strip of 24 pages.
    "learning-journey": (
        ROOT / "out/journey/stage-1",
        [
            *journey_pages(
                1,
                ".",
                [
                    (
                        "png-cover/journey-cover-front",
                        "الغلاف باسم طفلك وشخصيته",
                        "the cover with your child's name",
                    ),
                    ("png-book/p002-journey-map", "خريطة الرحلة", "the journey map"),
                    ("png-book/p022-maze", "متاهة، ساعدي ليان للوصول إلى الحديقة", "a maze to the garden"),
                    (
                        "png-book/p028-listen-rows",
                        "أسمع وأميّز مع رمز QR",
                        "listen and choose, with a QR code",
                    ),
                    ("png-book/p050-shape-journey", "رحلة الدائرة", "meet the circle"),
                    ("png-book/p077-smart-coloring", "تلوين ذكي", "smart coloring"),
                    ("png-book/p104-quantity-first", "كم تفاحة؟", "how many apples?"),
                    ("png-book/p118-certificate", "شهادة المحطة الأولى", "the certificate"),
                ],
            ),
            *journey_pages(
                2,
                "../stage-2",
                [
                    ("png-cover/journey-cover-front", "الغلاف باسم طفلك", "the cover with your child's name"),
                    ("png-book/p014-journey-first-sound", "الصوت الأول للكلمة", "the first sound of a word"),
                    (
                        "png-book/p032-journey-finger-trace",
                        "حرف الباء بإصبعي وصوته",
                        "the letter ب, with its sound",
                    ),
                    ("png-book/p033-journey-letter-trace", "الباء بالقلم", "the letter ب with a pen"),
                    ("png-book/p080-journey-en-letter", "A a، Apple", "A a, Apple"),
                    ("png-book/p103-journey-number-trace", "أتتبّع الأرقام 1–5", "tracing the numbers 1–5"),
                    ("png-book/p116-journey-hidden-picture", "ابحث في السوق", "search the market"),
                    ("png-book/p120-certificate", "شهادة المحطة الثانية", "the certificate"),
                ],
            ),
            *journey_pages(
                3,
                "../stage-3",
                [
                    ("png-cover/journey-cover-front", "الغلاف باسم طفلك", "the cover with your child's name"),
                    ("png-book/p065-journey-harakat", "الفتحة", "the fatha"),
                    ("png-book/p070-journey-syllables", "أركّب كلمة", "build a word"),
                    ("png-book/p071-journey-word-read", "أقرأ كلمات قصيرة", "read short words"),
                    (
                        "png-book/p081-journey-word-write",
                        "أكتب الكلمة على السطر",
                        "write the word on the line",
                    ),
                    ("png-book/p105-journey-sentence-read", "I see a cat.", "I see a cat."),
                    ("png-book/p109-journey-picture-sum", "أجمع بالصور", "add with pictures"),
                    ("png-book/p120-certificate", "شهادة إتمام الرحلة", "the journey certificate"),
                ],
            ),
        ],
    ),
    "foundation-workbook": (
        ROOT / "out/workbook/png-kg2-v1",
        [
            ("p001-owner-page", "هذا الكتاب لطفلك: اسمه وصورته وبصمة كفّه", "This book belongs to your child"),
            ("p002-name-trace", "يتتبّع اسمه ويكتبه", "Tracing their own name"),
            ("p018-letter-intro", "أتعرّف على الحرف وألوّنه", "Meet a letter and color it"),
            ("p027-letter-trace", "أتتبّع الحرف من نقطة البداية", "Trace the letter from the start dot"),
            ("p033-number-intro", "العدد: رقمه وكميّته واسمه", "A number: numeral, amount and name"),
            ("p124-assessment", "تقييم مهارات القلم للأهل والمعلّمة", "The pen-skills check for grown-ups"),
            (
                "../png-kg2-v3/p074-harakat",
                "الجزء الثالث: الحركات، أقرأ الحرف مع الفتحة",
                "Volume 3: the vowel marks",
            ),
            (
                "../png-kg2-v3/p101-word-read",
                "الجزء الثالث: أقرأ كلمات وأصلها بصورها",
                "Volume 3: reading words",
            ),
            (
                "../png-kg2-v3/p130-workbook-certificate",
                "شهادة إنجاز باسمه وصورته",
                "A certificate in their name",
            ),
        ],
    ),
    # KG2 volume 3 (reading and adding), rendered by `... render.workbook --level kg2 --volume 3`
    "foundation-workbook-v3": (
        ROOT / "out/workbook/png-kg2-v3",
        [
            (
                "p009-teen-quantity-match",
                "عشرة وآحاد: أصل العدد بكميّته",
                "Tens and ones: match a number to its amount",
            ),
            (
                "p074-harakat",
                "الحركات: أقرأ الحرف مع الفتحة",
                "The vowel marks: read a letter with its fatha",
            ),
            ("p101-word-read", "أقرأ كلمات وأصلها بصورها", "Read words and match their pictures"),
            ("p046-picture-add", "أجمع بالصور وأكتب جملة الجمع", "Add with pictures and write the sum"),
            (
                "p118-sentence-read",
                "أنا أقرأ: أصل الجملة بصورتي",
                "I can read: match each sentence to my picture",
            ),
            (
                "p130-workbook-certificate",
                "شهادة إنجاز باسمه وصورته",
                "A certificate in their name and picture",
            ),
        ],
    ),
    # KG1 (ages 4–5), rendered by `uv run python -m qamra_workbook.render.workbook --level kg1 --volume 1|3`
    "foundation-workbook-kg1": (
        ROOT / "out/workbook/png-kg1-v1",
        [
            ("p001-owner-page", "هذا الكتاب لطفلك: اسمه وصورته وبصمة كفّه", "This book belongs to your child"),
            ("p005-kg1-pen-lines", "خطوط كبيرة بالقلم من النقطة الخضراء", "Big pen lines from the green dot"),
            (
                "p018-kg1-letter-trace",
                "أتتبّع الألف الكبيرة بإصبعي ثم بقلمي",
                "Trace a big letter, then a smaller one",
            ),
            ("p033-kg1-number-intro", "العدد واحد: رقمه وكميّته", "Meet the number one"),
            (
                "p065-kg1-cut-shadows",
                "أقصّ الصورة وألصقها فوق ظلّها",
                "Cut each picture and paste it on its shadow",
            ),
            ("../png-kg1-v3/p090-kg1-harakat", "أسمع الفتحة وأحوّط ما أسمع", "Listening to the fatha"),
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


def main(only: str | None = None) -> None:
    """Export every product, or just `only` (the others stay as the manifest lists them)."""
    listing: dict[str, list[dict[str, str]]] = {}
    if only is not None:
        if only not in PAGES:
            raise SystemExit(f"unknown product {only!r}; one of: {', '.join(PAGES)}")
        if MANIFEST.exists():
            listing = json.loads(MANIFEST.read_text())
    for slug, (folder, pages) in PAGES.items():
        if only is not None and slug != only:
            continue
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
    if pose is not None and only is None:
        with Image.open(pose) as img:
            rgba = img.convert("RGBA")
        rgba.thumbnail((320, 640), Image.Resampling.LANCZOS)
        rgba.save(OUT / "character.webp", format="WEBP", quality=85, method=6)
        print("character.webp")


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None)
