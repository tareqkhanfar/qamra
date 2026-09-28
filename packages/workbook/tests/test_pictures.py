import re
from pathlib import Path

from PIL import Image
from qamra_workbook.pictures import PICTURES, ImageDirStore, LibraryStore, by_category, find_ar, get
from qamra_workbook.pictures.model import OUTLINE

FILL = re.compile(r'fill="(#[0-9A-Fa-f]{6})"')


def test_library_size_and_tags() -> None:
    assert 25 <= len(PICTURES) <= 400  # placeholders now; the approved library is 300–400 pictures (A5 §4)
    for pic in PICTURES.values():
        assert pic.word_ar and pic.word_en and pic.category
        assert pic.first_letter_en == pic.word_en[0].upper()
    assert get("duck").first_letter_ar == "ب"
    assert get("apple").first_letter_ar == "ت"
    assert {p.id for p in by_category("fruit")} >= {"apple", "banana", "strawberry"}
    assert find_ar("بطة") is get("duck")


def test_no_text_inside_pictures() -> None:
    for pic in PICTURES.values():
        for style in ("color", "line"):
            assert "<text" not in pic.svg(style)


def test_line_art_comes_from_the_same_drawing() -> None:
    for pic in PICTURES.values():
        color, line = pic.svg("color"), pic.svg("line")
        assert color != line
        assert line.count("<g ") <= color.count("<g ")  # same parts, minus color-only highlights
        fills = set(FILL.findall(line))
        assert fills <= {"#FFFFFF", OUTLINE}, (pic.id, fills)


def test_recolor_changes_only_the_named_key() -> None:
    ball = get("ball")
    blue = ball.inner("color", {"main": "#123456"})
    assert "#123456" in blue and ball.palette["main"] not in blue


def test_approved_images_replace_placeholders(tmp_path: Path) -> None:
    Image.new("RGB", (40, 40), "white").save(tmp_path / "apple.color.png")
    store = ImageDirStore(tmp_path)
    assert "<img" in store.markup("apple") and "apple.color.png" in store.markup("apple")
    assert store.markup("apple", "line") == LibraryStore().markup("apple", "line")  # falls back
