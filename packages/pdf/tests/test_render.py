from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader
from qamra_pdf import BookSpec, Brand, KeepsakeSpec, PageSpec, render_book, render_html

VOWELIZED = "فِي صَبَاحٍ مُشْرِقٍ، اسْتَيْقَظَتْ سَلْمَى بَاكِرًا وَقَلْبُهَا يَرْقُصُ فَرَحًا."
BRAND = Brand("قمرة", "Qamra", "qamra.app", "حكاية طفلك… تحت ضوء القمر", "Your child's story, by moonlight.")


def _img(path: Path, color: str) -> Path:
    Image.new("RGB", (300, 300), color).save(path)
    return path


def _spec(tmp: Path, *, keepsake: bool, n: int = 3, watermark: bool = False) -> BookSpec:
    pages = [
        PageSpec(index=i, image=_img(tmp / f"p{i}.png", "#22306A"), text=VOWELIZED) for i in range(1, n + 1)
    ]
    ks = None
    if keepsake:
        ks = KeepsakeSpec(
            _img(tmp / "d.png", "white"),
            _img(tmp / "c.png", "#A99BD6"),
            "سَلْمَى",
            "بوبو",
            "28 / 09 / 2026",
        )
    return BookSpec(
        lang="ar",
        title="سَلْمَى فِي أَوَّلِ يَوْمٍ بِالرَّوْضَةِ",
        dedication="إِلَى سَلْمَى",
        child_name="سَلْمَى",
        cover_image=_img(tmp / "cover.png", "#F2B33D"),
        pages=pages,
        brand=BRAND,
        keepsake=ks,
        watermark=watermark,
        extra={"gender": "f"},
    )


def _fonts(reader: PdfReader) -> dict[str, str]:
    found: dict[str, str] = {}
    for page in reader.pages:
        fonts = page.get("/Resources", {}).get("/Font", {})
        for f in fonts.values():
            f = f.get_object()
            found[str(f.get("/BaseFont"))] = str(f.get("/Subtype"))
    return found


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    import asyncio

    tmp = tmp_path_factory.mktemp("book")
    spec = _spec(tmp, keepsake=True)
    return spec, asyncio.run(render_book(spec, tmp / "out"))


def test_interior_page_count_and_size(rendered) -> None:  # type: ignore[no-untyped-def]
    spec, book = rendered
    reader = PdfReader(book.interior_pdf)
    assert len(reader.pages) == 1 + len(spec.pages) + 1  # title + story + keepsake
    for page in reader.pages:
        w_mm = float(page.mediabox.width) / 72 * 25.4
        h_mm = float(page.mediabox.height) / 72 * 25.4
        assert w_mm == pytest.approx(216, abs=0.3) and h_mm == pytest.approx(216, abs=0.3)


def test_cover_is_separate_two_pages(rendered) -> None:  # type: ignore[no-untyped-def]
    _, book = rendered
    assert len(PdfReader(book.cover_pdf).pages) == 2


def test_fonts_embedded_and_not_type3(rendered) -> None:  # type: ignore[no-untyped-def]
    _, book = rendered
    fonts = _fonts(PdfReader(book.interior_pdf))
    assert any("NotoNaskhArabic" in name for name in fonts)
    assert any("BalooBhaijaan2" in name for name in fonts)
    assert "/Type3" not in fonts.values(), fonts


def test_keepsake_page_rendered(rendered) -> None:  # type: ignore[no-untyped-def]
    _, book = rendered
    html = book.interior_html.read_text(encoding="utf-8")
    assert 'data-kind="keepsake"' in html and "وَهٰكَذا وُلِدَ صاحِبي" in html
    assert "رَسَمَتْهُ سَلْمَى" in html  # feminine keepsake note


def test_no_keepsake_without_drawing(tmp_path: Path) -> None:
    html = render_html("interior.html.j2", _spec(tmp_path, keepsake=False))
    assert 'data-kind="keepsake"' not in html
    assert html.count('data-kind="story"') == 3


def test_rtl_and_brand_from_spec(tmp_path: Path) -> None:
    html = render_html("cover.html.j2", _spec(tmp_path, keepsake=False))
    assert 'dir="rtl"' in html and "قمرة" in html and "qamra.app" in html
    for old in ("حكايتي", "Hikayati", "KidPix"):
        assert old not in html


def test_preview_watermark(tmp_path: Path) -> None:
    html = render_html("interior.html.j2", _spec(tmp_path, keepsake=False, watermark=True))
    assert html.count('class="watermark"') == 3 and "مُعايَنَة · قمرة" in html
