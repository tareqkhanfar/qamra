import asyncio
import datetime as dt
import re
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import PageProblems, book_html, build_pages, print_pdf
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import SPEC, book_from, load, spec_problems
from qamra_workbook.render.spec import BookSpec, Child, PageSpec

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
MM = 72 / 25.4
SAMPLE_TYPES = [
    "journey-map",
    "odd-one-out",
    "maze",
    "themed-pen-drill",
    "pattern-complete",
    "smart-coloring",
    "quantity-first",
    "listen-and-choose",
    "finger-trace",
    "en-letter",
    "spot-difference",
    "certificate",
]


def page(n: int, kind: str, section: str, **params: Any) -> PageSpec:
    lang = params.pop("lang", "ar")
    return PageSpec(
        id=f"test-p{n}",
        type=kind,
        number=n,
        section=section,
        title="{ساعد/ساعدي} {child}",
        instruction="{ضع/ضعي} دائرة حول المختلف",
        lang=lang,
        instruction_en="Trace the letters." if lang == "en" else "",
        stage=1,
        audio=kind in ("listen-and-choose", "en-letter"),
        params=params,
    )


def book(*pages: PageSpec) -> BookSpec:
    return BookSpec("journey", "رحلتي الأولى للتعلّم", Child("ليان", "f"), pages, dt.date(2026, 9, 28))


def mm(points: Any) -> float:
    return float(points) / MM


def test_pages_print_on_a4_with_bleed_and_exact_boxes(tmp_path: Path) -> None:
    b = book(page(6, "odd-one-out", "think", seed=6), page(19, "maze", "eye-hand", seed=19))
    pages = build_pages(b, ASSETS)
    pdf = asyncio.run(
        print_pdf(book_html(b, pages, ASSETS), tmp_path / "b.html", tmp_path / "b.pdf", b.geometry)
    )
    reader = PdfReader(pdf)
    assert len(reader.pages) == 2
    for p in reader.pages:
        assert mm(p.mediabox.width) == pytest.approx(216, abs=0.01)
        assert mm(p.mediabox.height) == pytest.approx(303, abs=0.01)
        assert mm(p.trimbox.left) == pytest.approx(3, abs=0.01)
        assert mm(p.trimbox.width) == pytest.approx(210, abs=0.01)
        assert mm(p.trimbox.height) == pytest.approx(297, abs=0.01)
        assert p.bleedbox == p.mediabox
    report = preflight(pdf, width_mm=216, height_mm=303, bleed_mm=3, safe_mm=12)
    assert report.passed, report.to_dict()
    assert all(c.ok for c in report.checks), report.to_dict()


def test_direction_binding_folio_and_personalization() -> None:
    b = book(
        page(3, "odd-one-out", "think"), page(90, "en-letter", "english", lang="en", letter="A", word="apple")
    )
    pages = build_pages(b, ASSETS)
    assert [p.side for p in pages] == ["left", "right"]  # right-bound Arabic book: odd pages on the left
    assert pages[0].title == "ساعدي ليان" and pages[0].instruction == "ضعي دائرة حول المختلف"
    assert pages[0].folio == "٣" and pages[1].folio == "٩٠"  # one digit style for the whole book
    html = book_html(b, pages, ASSETS)
    assert re.search(r'<section class="page type-odd-one-out side-left[^>]*dir="rtl"', html)
    assert re.search(r'<section class="page type-en-letter side-right[^>]*dir="ltr"', html)


def test_rendered_pictures_match_the_answer_keys() -> None:
    b = book(
        page(52, "smart-coloring", "smart-coloring", seed=52),
        page(71, "quantity-first", "math", seed=71, example=2),
    )
    coloring, quantity = build_pages(b, ASSETS)
    scene = str(coloring.built.data["scene"])
    assert scene.count('data-shape="circle"') == coloring.built.data["count"]
    rows = quantity.built.data["rows"]
    for row in rows:
        assert str(row["group"]).count("data-count-item") == row["count"]
        assert [str(card).count("data-dot") for card in row["cards"]].count(row["count"]) == 1
    assert rows[0]["count"] == 2 and sorted(r["count"] for r in rows[1:]) == [1, 2, 3]
    assert "٣" not in "".join(str(r["group"]) + "".join(map(str, r["cards"])) for r in rows)  # no numerals


def test_a_failing_check_stops_the_render() -> None:
    wrong = page(88, "listen-and-choose", "listening", choices=["cow", "cat", "duck"], answer="lion")
    with pytest.raises(PageProblems, match="must match exactly one picture"):
        build_pages(book(wrong), ASSETS)


def test_the_sample_spec_is_valid_and_every_page_passes_its_checks() -> None:
    b = book_from(load(ROOT / SPEC))
    assert [p.type for p in b.pages] == SAMPLE_TYPES
    assert spec_problems(list(b.pages), b.child) == []
    pages = build_pages(b, ASSETS)
    assert sum(1 for p in pages if p.built.answer) == 7
    assert all(p.qr is not None for p in pages if p.spec.audio)
