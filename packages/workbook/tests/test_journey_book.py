"""«رحلتي الأولى للتعلّم», stage 1 as a printed book: every page of the plan builds from its print layer and
passes its checks, the texts follow the child (name, gender), audio pages print a QR to their item's public
player, and a small render passes preflight."""

import asyncio
import datetime as dt
from pathlib import Path

import cv2  # type: ignore[import-not-found]
import pytest
from qamra_workbook.journey import load
from qamra_workbook.journey_book import (
    AUDIO,
    PLAN,
    audio_code,
    audio_items,
    built_stages,
    catalog_text,
    cover_specs,
    layer_problems,
    load_layer,
    page_specs,
    stage_book,
    stage_of,
)
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render.engine import book_html, build_pages, previews, print_pdf
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.samples import book_problems
from qamra_workbook.render.spec import Child, leftover_placeholders

from qamra_pdf import preflight

GIRL, BOY = Child("ليان", "f"), Child("آدم", "m")
ASSETS = Assets(LibraryStore())


@pytest.fixture(scope="module")
def stage1() -> list:  # type: ignore[type-arg]
    return page_specs(load(PLAN), load_layer(1))


def test_every_stage_one_page_builds_from_the_plan(stage1: list) -> None:  # type: ignore[type-arg]
    plan = load(PLAN)
    assert [p.number for p in stage1] == [p.n for p in stage_of(plan, 1)] and len(stage1) == 118
    assert layer_problems(plan, load_layer(1)) == []
    for child in (GIRL, BOY):
        book = stage_book(stage1 + cover_specs(load_layer(1)), child, day=dt.date(2026, 9, 29))
        assert book_problems(book) == []  # ≤ 7 words, a title and an instruction, no retired words
        pages = build_pages(book, ASSETS)  # raises PageProblems when any page fails its checks
        assert len(pages) == 120
    types = {p.type for p in stage1}
    assert {"journey-opener", "what-i-learned", "listen-rows", "write-progression", "shape-journey"} <= types
    assert "section-opener" not in types  # the family book's opener; the journey has its own


def test_the_texts_follow_the_child(stage1: list) -> None:  # type: ignore[type-arg]
    girl = build_pages(stage_book(stage1, GIRL), ASSETS)
    boy = build_pages(stage_book(stage1, BOY), ASSETS)
    by_n = {g.spec.number: (g, b) for g, b in zip(girl, boy, strict=True)}
    g4, b4 = by_n[4]
    assert "ضَعي" in g4.instruction and "ضَعْ" in b4.instruction and "ضَعي" not in b4.instruction
    g22, b22 = by_n[22]
    assert "ليان" in g22.title and "ساعِدي" in g22.title and "آدم" in b22.title and "ساعِدْ" in b22.title
    assert by_n[118][0].built.data["name"] == "ليان"  # the mini-certificate
    for p in girl:
        assert not leftover_placeholders(p.title + p.instruction)


def test_audio_pages_carry_their_items_code(stage1: list) -> None:  # type: ignore[type-arg]
    book = stage_book(stage1, GIRL, domain="qamra.test")
    audio = [p for p in stage1 if p.audio]
    plan_audio = [p.n for p in stage_of(load(PLAN), 1) if p.audio]
    assert [p.number for p in audio] == plan_audio
    codes = {p.params["audio_code"] for p in audio}
    assert len(codes) == len(audio)  # one item per page in stage 1
    assert book.audio_url(audio[0]) == f"https://qamra.test/a/{audio_code('journey:s1:p28')}"
    assert audio_code("journey:s1:p28") == "ogjmg6ob"  # stable: printed books keep working
    items = audio_items(load(PLAN), load_layer(1))
    assert {i.code for i in items} == codes and all("{" not in i.title for i in items)
    assert AUDIO.read_text(encoding="utf-8") == catalog_text(load(PLAN), built_stages())  # the API's catalog


def test_a_small_render_passes_preflight_and_the_qr_decodes(stage1: list, tmp_path: Path) -> None:  # type: ignore[type-arg]
    picked = tuple(p for p in stage1 if p.number in (3, 28, 50))
    book = stage_book(list(picked), GIRL, domain="qamra.test")
    pages = build_pages(book, ASSETS)
    pdf = asyncio.run(
        print_pdf(book_html(book, pages, ASSETS), tmp_path / "s.html", tmp_path / "s.pdf", book.geometry)
    )
    g = book.geometry
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed, report.to_dict()
    png = previews(pdf, tmp_path / "png", ["p3", "p28", "p50"], g, dpi=200)[1]
    image = cv2.imread(str(png))
    found, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    assert found == f"https://qamra.test/a/{audio_code('journey:s1:p28')}"
