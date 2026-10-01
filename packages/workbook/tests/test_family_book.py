"""«مغامراتي مع عائلتي» from its plan: the render CLI's pages, the two print sizes, and the activity page
types of the first adventures (drawing, counting, sorting, the journal, role cards, price tags)."""

import asyncio
import dataclasses
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfReader
from qamra_workbook.family import load
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.family import PLAN, SAMPLES, plan_pages, spread_pairs
from qamra_workbook.render.pages.adventures import payable
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import FamilySamples, family_book
from qamra_workbook.render.samples import load as load_samples
from qamra_workbook.render.spec import PageSpec, product_geometry

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
MM = 72 / 25.4
needs_plan = pytest.mark.skipif(not (ROOT / PLAN).exists(), reason="the family plan is not written yet")


def sample_family() -> FamilySamples:
    samples = load_samples(ROOT / SAMPLES)
    assert isinstance(samples, FamilySamples)
    return samples


def book_of(pages: list[PageSpec], size: str | None = None, **changes: Any) -> Any:
    return dataclasses.replace(family_book(sample_family(), tuple(pages), size), **changes)


def test_the_family_book_prints_at_either_size_by_one_setting() -> None:
    assert (product_geometry("family").page_w, product_geometry("family").page_h) == (216, 286)
    assert (product_geometry("family", "21x28").page_h, product_geometry("family", "a4").page_h) == (286, 303)
    with pytest.raises(ValueError, match="prints at"):
        product_geometry("family", "a5")


def test_spreads_open_on_the_even_right_hand_page() -> None:
    assert spread_pairs([6, 7, 8, 9]) == [(7, 6), (9, 8)]
    assert spread_pairs([3, 6, 7, 8, 15]) == [(3, None), (7, 6), (None, 8), (15, None)]


@needs_plan
def test_plan_pages_come_in_book_order_with_the_missing_params() -> None:
    plan = load(ROOT / PLAN)
    extra = {
        "home-colors": {"counting": {"mode": "tally", "colors": ["red"]}, "scavenger-hunt": {"colors": ["x"]}}
    }
    specs, filled = plan_pages(plan, range(6, 24), extra)
    assert [s.number for s in specs] == list(range(6, 24))
    counting = next(s for s in specs if s.type == "counting" and s.number == 11)
    assert counting.params["mode"] == "tally" and 11 in filled
    hunt = next(s for s in specs if s.number == 10)
    assert hunt.params["colors"] == ["red", "yellow", "blue"]  # the plan's own params win
    assert {s.type for s in specs} >= {"drawing", "counting", "sort-choose", "observation-journal"}


@needs_plan
@pytest.mark.parametrize("size", ["21x28", "a4"])
def test_the_first_adventures_render_at_both_sizes(tmp_path: Path, size: str) -> None:
    """Pages 6–23 from the plan, as the CLI renders them: nothing overflows (the engine refuses to print
    otherwise), the pages have the size's boxes and preflight passes. Every page's params are in the plan."""
    specs, filled = plan_pages(load(ROOT / PLAN), range(6, 24), {})
    assert filled == []  # nothing borrowed from a staging file
    book = book_of(specs, size)
    pages = build_pages(book, ASSETS)
    pdf = asyncio.run(
        print_pdf(book_html(book, pages, ASSETS), tmp_path / "b.html", tmp_path / "b.pdf", book.geometry)
    )
    reader = PdfReader(pdf)
    g = book.geometry
    assert len(reader.pages) == 18
    assert float(reader.pages[0].mediabox.height) / MM == pytest.approx(g.page_h, abs=0.01)
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed and all(c.ok for c in report.checks), report.to_dict()


def test_every_price_can_be_paid_with_the_pieces_shown() -> None:
    assert payable(4, [1, 1, 2, 2, 5]) == [2, 2]
    assert payable(8, [1, 1, 2, 2, 5]) == [5, 2, 1]
    assert payable(19, [1, 2, 2, 5, 10, 20]) == [10, 5, 2, 2]
    assert payable(4, [5, 10]) is None


def page(n: int, kind: str, section: str = "home", **params: Any) -> PageSpec:
    return PageSpec(f"family-p{n}", kind, n, section, "مغامرة", "{ابحث/ابحثي} معنا", params=params)


def test_sorting_keys_the_answers_only_when_there_is_one() -> None:
    shapes, baskets = build_pages(
        book_of([page(12, "sort-choose", groups=["circle", "square", "triangle"]),
                 page(20, "sort-choose", "market", groups=["healthy", "needed", "not-needed"])]),
        ASSETS,
    )  # fmt: skip
    assert shapes.built.answer and "صحن ← دائرة" in shapes.built.answer[0]
    assert baskets.built.answer is None  # «لا توجد إجابة واحدة صحيحة دائمًا»
    assert len(shapes.built.data["things"]) == 5 and len(baskets.built.data["groups"]) == 3


def test_counting_compares_baskets_that_never_tie_and_tallies_colors() -> None:
    compare, tally = build_pages(
        book_of([page(19, "counting", "market"), page(11, "counting", mode="tally", colors=["red", "blue"])]),
        ASSETS,
    )
    rows = compare.built.data["rows"]
    assert [r["level"] for r in rows] == [1, 1, 2]
    assert all(len({b["count"] for b in r["baskets"]}) == 2 for r in rows)
    assert all(b["count"] <= 5 for r in rows[:2] for b in r["baskets"])
    assert [strip_tashkeel(c["name"]) for c in tally.built.data["columns"]] == ["أحمر", "أزرق", "أخضر"]


def test_the_color_hunt_and_the_star_count_come_from_the_plan_params() -> None:
    hunt, memory = build_pages(
        book_of(
            [page(10, "scavenger-hunt", colors=["red", "yellow", "blue"]), page(15, "memory-page", stars=3)]
        ),
        ASSETS,
    )
    assert hunt.built.data["mode"] == "colors" and len(hunt.built.data["columns"]) == 4
    assert memory.built.data["stars"] == 3 and "كم نجمة" in strip_tashkeel(memory.built.data["stars_q"])


def test_role_cards_need_something_to_say() -> None:
    from qamra_workbook.render.engine import PageProblems

    with pytest.raises(PageProblems, match="need `roles` or `cards`"):
        build_pages(book_of([page(21, "conversation-cards", "market")]), ASSETS)
    roles = [{"name": "البائع", "picture": "stall", "lines": ["أهلًا!", "تفضّلوا"], "challenge": ["بكم؟"]}]
    built = build_pages(book_of([page(21, "conversation-cards", "market", roles=roles)]), ASSETS)[0]
    assert built.built.data["roles"][0]["challenge"] == ["بكم؟"]


@pytest.mark.parametrize(("numerals", "price"), [("hindi", "٣"), ("latin", "3")])
def test_prices_and_money_follow_the_books_numerals(numerals: str, price: str) -> None:
    book = book_of([page(22, "price-tags", "market")], numerals=numerals)
    tags = build_pages(book, ASSETS)[0]
    html = book_html(book, [tags], ASSETS)
    html = html[html.index("<body") :]  # the printed page, not the stylesheet
    prices = [it["price"] for row in tags.built.data["rows"] for it in row["items"]]
    assert all(any(ch.isdigit() for ch in p) or strip_tashkeel(p) in ("قمرتان", "قمرة واحدة") for p in prices)
    assert (price in html) and (("٣" in html) == (numerals == "hindi"))
