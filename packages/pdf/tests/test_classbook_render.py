"""«كتاب الصف» print files: every copy is the shared interior with its own portrait as page 2, and its own
cover; the combined print file stores the shared pictures once; preflight passes; file names are readable."""

import asyncio
import re
import unicodedata
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader

from qamra_pdf import Brand
from qamra_pdf.classbook import (
    ChildCopy,
    ClassBookSpec,
    ClassFiles,
    Classmate,
    SchoolPage,
    StoryPage,
    file_stem,
    render_class_book,
)

BRAND = Brand("قمرة", "Qamra", "qamra.app", "", "")
PAGE_PX = 2551  # 216 mm at 300 DPI
MM = 72 / 25.4


def _img(path: Path, color: str, size: tuple[int, int]) -> Path:
    Image.new("RGB", size, color).save(path, quality=90)
    return path


@pytest.fixture(scope="module")
def rendered(tmp_path_factory: pytest.TempPathFactory) -> tuple[ClassBookSpec, list[ChildCopy], ClassFiles]:
    tmp = tmp_path_factory.mktemp("class")
    pages = [
        StoryPage(_img(tmp / f"p{i}.jpg", color, (PAGE_PX, PAGE_PX)), f"صَفْحَةٌ {i}: يوسف وجنى وليان.")
        for i, color in enumerate(["#22306A", "#7FA38A", "#E9826B"], start=1)
    ]
    names = ["يوسف", "جنى", "ليان"]
    face = _img(tmp / "face.jpg", "#FCEFD2", (460, 460))
    spec = ClassBookSpec(
        lang="ar",
        brand=BRAND,
        title="كِتابُ صف الفراشات",
        cover_subtitle="وَأَصْدِقاءُ صف الفراشات",
        blurb="سَنَةٌ كامِلَةٌ مِنَ اللَّعِب.",
        portrait_title="هٰذا أَنا",
        group_title="أَصْدِقائي في صف الفراشات",
        memories_title="ذِكْرَياتي",
        school=SchoolPage(
            title="كِتابُ صف الفراشات",
            school="روضة القمر",
            year="2026-2027",
            teacher_title="كَلِمَةٌ مِنَ القَلْب",
            teacher_message="أحبائي الفراشات، كنتم نور صفّنا طوال السنة.",
            teacher_name="أ. رنا",
            logo=_img(tmp / "logo.png", "#F2B33D", (720, 720)),
            class_photo=_img(tmp / "class.jpg", "#A99BD6", (1780, 1040)),
        ),
        pages=pages,
        classmates=[Classmate(n, face) for n in names],
    )
    copies = [
        ChildCopy(
            stem=file_stem("روضة القمر", "صف الفراشات", n),
            name=n,
            cover_image=_img(tmp / f"cover{i}.jpg", "#F2B33D", (PAGE_PX, PAGE_PX)),
            portrait=_img(tmp / f"portrait{i}.jpg", "#FCEFD2", (1300, 1950)),
            portrait_line=f"{n} نَجْمٌ يُضيءُ صَفَّنا.",
            gender=("m", "f", None)[i],
            portrait_title="هٰذِهِ أَنا" if i == 1 else "",  # جنى's own heading; the others take the book's
        )
        for i, n in enumerate(names)
    ]
    return spec, copies, asyncio.run(render_class_book(spec, copies, tmp / "out"))


def _text(reader: PdfReader, page: int) -> str:
    """Chromium writes shaped Arabic (presentation forms): NFKC maps them back to plain letters."""
    return unicodedata.normalize("NFKC", reader.pages[page].extract_text())


def test_file_names_follow_school_class_child() -> None:
    assert file_stem("روضة القمر", "صف الفراشات", "جنى") == "روضة-القمر-صف-الفراشات-جنى"
    assert file_stem("Moon KG", "Class 2/B", "Yusuf!") == "Moon-KG-Class-2-B-Yusuf"


def test_every_copy_has_the_shared_pages_with_its_own_portrait_second(
    rendered: tuple[ClassBookSpec, list[ChildCopy], ClassFiles],
) -> None:
    spec, copies, files = rendered
    assert spec.interior_pages == 8  # school + portrait + 3 story + group = 6 → padded to 8
    for copy in copies:
        reader = PdfReader(files.interiors[copy.stem])
        assert len(reader.pages) == 8
        assert copy.name in _text(reader, 1)  # the portrait page
        assert "روضة القمر" in _text(reader, 0)  # the school page
        side = float(reader.pages[0].mediabox.width) / MM
        assert abs(side - spec.page_mm) < 0.3
        cover = PdfReader(files.covers[copy.stem])
        assert (
            len(cover.pages) == 1
            and abs(float(cover.pages[0].mediabox.width) / MM - spec.wrap_width_mm) < 0.3
        )
        assert files.passed(copy.stem), {k: v.to_dict() for k, v in files.preflight[copy.stem].items()}


def test_a_girl_says_hadhihi_ana_over_her_portrait(
    rendered: tuple[ClassBookSpec, list[ChildCopy], ClassFiles],
) -> None:
    """The heading over each child's portrait is in the child's gender («هٰذِهِ أَنا» for جنى)."""
    _, copies, files = rendered

    def heading(i: int) -> str:
        return re.sub("[\u064b-\u0652\u0670]", "", _text(PdfReader(files.interiors[copies[i].stem]), 1))

    assert "هذه أنا" in heading(1) and "هذا أنا" not in heading(1)
    assert "هذا أنا" in heading(0)


def test_the_combined_print_file_holds_every_copy_and_shares_the_pictures(
    rendered: tuple[ClassBookSpec, list[ChildCopy], ClassFiles],
) -> None:
    _, copies, files = rendered
    combined = PdfReader(files.combined)
    assert len(combined.pages) == len(copies) * (1 + 8)  # a cover, then its interior, child after child
    separate = sum(p.stat().st_size for p in [*files.interiors.values(), *files.covers.values()])
    assert files.combined.stat().st_size < separate  # the shared pictures are stored once


def test_every_cover_is_the_story_cover_design_with_the_class_words(
    rendered: tuple[ClassBookSpec, list[ChildCopy], ClassFiles],
) -> None:
    _, copies, files = rendered
    out = files.combined.parent
    covers = [(out / f"cover-{i}.html").read_text(encoding="utf-8") for i in range(len(copies))]
    for copy, html in zip(copies, covers, strict=True):
        assert 'class="title-art"' in html and '<tspan class="nm"' in html  # poster lettering, name in gold
        assert ">كتاب الصفّ<" in html  # the series pill
        assert "روضة القمر، ٢٠٢٦-٢٠٢٧" in html  # the school on the back, digits as in the book
        assert f'نُسْخَةٌ خاصَّةٌ بِـ<span class="nm">{copy.name}</span>' in html
        assert 'class="school-logo"' in html and 'data-reserved="barcode"' in html
    assert "بُطُولَةُ الْبَطَلِ الرَّائِعِ" in covers[0] and "بُطُولَةُ الْبَطَلَةِ الرَّائِعَةِ" in covers[1]
    assert (
        '<span class="r-label">روضة القمر</span>' in covers[2]
    )  # gender unknown: the ribbon names the school
