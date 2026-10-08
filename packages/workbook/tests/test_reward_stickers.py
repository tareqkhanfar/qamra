"""The included reward sticker sheets of «رحلتي الأولى للتعلّم» (one per stage) and «قلبي يعرف الله» (one per
volume): every sticker the book's pages ask for is on the sheet, at a size that covers its spot, with the
child's name and gender; the Islamic sheet carries no sacred words; the sheet prints with its kiss-cut lines
on their own layer and passes preflight."""

import asyncio
import dataclasses
import datetime as dt
from pathlib import Path
from typing import Any

import pypdfium2 as pdfium  # type: ignore[import-untyped]
import pytest
from qamra_workbook import islamic
from qamra_workbook.render import islamic_volume as iv
from qamra_workbook.render.dielines import layers
from qamra_workbook.render.engine import PageProblems, build_pages
from qamra_workbook.render.islamic_content import IslamicContext
from qamra_workbook.render.islamic_figures import Kit
from qamra_workbook.render.islamic_units import volume_units
from qamra_workbook.render.journey_order import stage_specs
from qamra_workbook.render.pages.journey_shapes import period_answer
from qamra_workbook.render.pages.reward_stickers import (
    RING_MM,
    STAMP_MM,
    STATION_MM,
    IslamicNeeds,
    JourneyNeeds,
    count_cells,
    sacred_words,
)
from qamra_workbook.render.spec import BookSpec, Child
from qamra_workbook.render.stickers import NAME, SHEET, needs_of, render_sheet, sheet_book
from test_islamic_pages import ASSETS, DATE, fake_resolver

GIRL, BOY = Child("ليان", "f"), Child("آدم", "m")
# the opener's dashed circle: r 8 on the map, which the page draws at 0.8, and its stroke
OPENER_CIRCLE_MM = 2 * 8 * 0.8 + 0.7


def journey(stage: int, child: Child = GIRL) -> BookSpec:
    interior, _ = stage_specs(child, stage, day=dt.date(2026, 10, 1))
    return interior


def sheet_data(book: BookSpec) -> dict[str, Any]:
    return build_pages(sheet_book(book), ASSETS)[0].built.data


def cells(data: dict[str, Any], kind: str | None = None) -> list[dict[str, Any]]:
    every = [c for g in data["groups"] for b in g["blocks"] for c in b["cells"]]
    return [c for c in every if kind is None or c["kind"] == kind]


# ---- the journey ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(("stage", "asked"), [(1, 27), (2, 25), (3, 28)])
def test_a_stage_sheet_holds_every_sticker_its_pages_ask_for(stage: int, asked: int) -> None:
    book = journey(stage)
    needs = needs_of(book)
    assert isinstance(needs, JourneyNeeds) and needs.stage == stage
    types = [p.type for p in book.pages]
    assert len(needs.hero) == types.count("journey-map") == 1  # «أَلْصِقْ مُلْصَقَ بَطَلِكَ» on the map
    assert len(needs.stations) == types.count("journey-opener")  # a sticker for every opener's circle
    patterns = [p for p in book.pages if p.type == "create-your-pattern"]
    assert [r.page for r in needs.patterns] == [p.number for p in patterns]
    for row, page in zip(needs.patterns, patterns, strict=True):
        assert row.shapes == tuple(page.params["stickers"])
        spares = len(row.shapes)  # the simple repeat, and at least one more of each shape
        assert row.per_shape * len(row.shapes) >= page.params["slots"] + spares
    assert needs.asked == asked
    data = sheet_data(book)
    assert data["count"] == count_cells(data["groups"]) == needs.total == asked + needs.rewards


def test_the_train_gets_each_of_its_pictures_so_the_child_still_chooses() -> None:
    needs = needs_of(journey(1))
    assert isinstance(needs, JourneyNeeds)
    (wagon,) = needs.wagons  # p71 «قطار الفواكه» asks to stick; stage 2's train asks to draw
    page = next(p for p in journey(1).pages if p.number == wagon.page)
    _, blanks = period_answer([str(w) for w in page.params["sequence"]])
    assert wagon.page == 71 and set(blanks) <= set(wagon.choices) and len(wagon.choices) == 2
    assert not needs_of(journey(2)).wagons  # type: ignore[union-attr]


def test_each_sticker_covers_its_spot() -> None:
    assert OPENER_CIRCLE_MM < STATION_MM <= OPENER_CIRCLE_MM + 2.5
    for stage in (1, 2, 3):
        needs = needs_of(journey(stage))
        assert isinstance(needs, JourneyNeeds)
        for row in needs.patterns:  # a shape sits inside its dashed slot
            assert row.slot_mm - 1.5 <= row.sticker_mm < row.slot_mm
    art_box = {"passport": 32.0, "journey-card": 36.0}  # the passport's stamp art (islamic-book.css)
    for layout, ring in RING_MM.items():
        assert ring + 0.8 < STAMP_MM[layout] < art_box[layout]


def test_the_journey_sheet_follows_the_childs_gender_and_name() -> None:
    girl = build_pages(sheet_book(journey(1)), ASSETS)[0]
    boy = build_pages(sheet_book(journey(1, BOY)), ASSETS)[0]
    assert "انْزِعي" in girl.instruction and "وَأَلْصِقيهِ" in girl.instruction
    assert "انْزِعْ" in boy.instruction and "وَأَلْصِقْهُ" in boy.instruction
    assert "بَطَلَتِكِ" in girl.built.data["groups"][0]["label"]
    assert "بَطَلِكَ" in boy.built.data["groups"][0]["label"]
    assert {c["text"] for c in cells(girl.built.data, "badge")} == {"أَحْسَنْتِ!"}
    assert {c["text"] for c in cells(boy.built.data, "badge")} == {"أَحْسَنْتَ!"}
    assert [c["text"] for c in cells(boy.built.data, "name")] == ["آدم", "آدم"]
    assert girl.built.data["owner"] == "ليان" and "رحلتي الأولى" in girl.built.data["brand"]


# ---- «قلبي يعرف الله» -------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def plan() -> islamic.Plan:
    return islamic.load()


@pytest.fixture(scope="module")
def resolver() -> Any:
    return fake_resolver()


def volume(plan: islamic.Plan, resolver: Any, vid: str, child: Child = GIRL) -> BookSpec:
    content = iv.check_volume(plan, vid, resolver)
    context = IslamicContext(resolver, Kit(), "preview", DATE)
    return iv.volume_book(plan, content, context, child)


@pytest.mark.parametrize(
    ("vid", "passports", "boards"),
    [
        ("V1", 2, ["star", "star"]),
        ("V2", 2, ["star"]),
        ("V3", 2, ["star"]),
        ("V4", 2, ["leaf"]),
        ("V5", 2, ["star"]),
        ("R", 1, []),
    ],
)
def test_a_volume_sheet_has_a_stamp_for_every_passport_circle(
    plan: islamic.Plan, resolver: Any, vid: str, passports: int, boards: list[str]
) -> None:
    book = volume(plan, resolver, vid)
    needs = needs_of(book)
    assert isinstance(needs, IslamicNeeds)
    units = volume_units(vid)
    assert len(needs.passports) == passports
    passport_pages = [p for p in build_pages(book, ASSETS) if p.spec.type == "muslim-passport"]
    assert len(passport_pages) == passports
    for pp, page in zip(needs.passports, passport_pages, strict=True):
        assert pp.page == page.spec.number and pp.units == tuple(units)
        assert len(page.built.data["stamps"]) == len(pp.units)  # one sticker per ghost circle on the page
        assert pp.stars == len(page.built.data["stars"])
    assert [b.kind for b in needs.boards] == boards
    assert needs.reward_stars == needs.passports[0].stars
    data = sheet_data(book)
    stamps = [g for g in data["groups"] if g["icon"] == "stamp"]
    assert [len(g["blocks"][0]["cells"]) for g in stamps] == [len(units)] * passports
    numbers = [book.num(i) for i in range(1, len(units) + 1)]  # the passport's unit numbers
    assert [c["badge"] for c in stamps[0]["blocks"][0]["cells"]] == numbers
    assert data["count"] == needs.total == len(units) * passports + 7 * len(boards) + needs.rewards


def test_the_islamic_sheet_carries_no_sacred_words(plan: islamic.Plan, resolver: Any) -> None:
    assert sacred_words("يَوْمِي مَعَ اللهِ") and sacred_words("نَبِيُّنَا مُحَمَّدٌ ﷺ") and sacred_words("أَعْرِفُ رَبِّي")
    assert not sacred_words("أَخْتَامُ وَحَدَاتِي: بِطَاقَةُ رِحْلَةِ الْإِيمَانِ (ص ١١٨)")
    assert not sacred_words("قمرة · كتاب رمضان والعيد") and not sacred_words("تَرْتِيبُ الْقُرْبِ")
    for vid in ("V1", "V3", "V4", "R"):
        data = sheet_data(volume(plan, resolver, vid))
        copy = [g["label"] for g in data["groups"]] + [data["brand"], data["key"]]
        copy += [str(b.get("caption", "")) for g in data["groups"] for b in g["blocks"]]
        assert not [w for line in copy for w in sacred_words(line)], vid
    # the child's own name is theirs: «عبد الله» prints on the name sticker
    data = sheet_data(volume(plan, resolver, "V1", Child("عبد الله", "m")))
    assert [c["text"] for c in cells(data, "name")] == ["عبد الله"]


def test_a_sheet_with_sacred_copy_is_never_built(plan: islamic.Plan, resolver: Any) -> None:
    book = sheet_book(volume(plan, resolver, "R"))
    params = {**book.pages[0].params, "brand": "قمرة · قلبي يعرف الله"}
    page = dataclasses.replace(book.pages[0], params=params)
    bad = dataclasses.replace(book, pages=(page,))
    with pytest.raises(PageProblems, match="no sacred words"):
        build_pages(bad, ASSETS)


def test_the_islamic_sheet_follows_the_childs_gender(plan: islamic.Plan, resolver: Any) -> None:
    girl = build_pages(sheet_book(volume(plan, resolver, "R")), ASSETS)[0]
    boy = build_pages(sheet_book(volume(plan, resolver, "R", Child("يوسف", "m"))), ASSETS)[0]
    assert "انْزِعِي" in girl.instruction and "انْزِعْ " in boy.instruction
    assert "الْمُسْلِمَةِ" in girl.built.data["groups"][0]["label"]
    assert "الْمُسْلِمِ " in boy.built.data["groups"][0]["label"]
    assert {c["text"] for c in cells(girl.built.data, "badge")} == {"أَحْسَنْتِ!"}
    assert {c["text"] for c in cells(boy.built.data, "badge")} == {"أَحْسَنْتَ!"}


# ---- the print file ------------------------------------------------------------------------------------


def test_the_sheet_prints_on_a4_with_its_die_lines_on_their_own_layer(tmp_path: Path) -> None:
    files = asyncio.run(render_sheet(journey(3, BOY), ASSETS, tmp_path))
    assert files.pdf == tmp_path / f"{NAME}.pdf" and files.die == tmp_path / f"{NAME}-die.pdf"
    assert layers(files.pdf) == ["CutContour"]
    assert files.passed, [c for c in files.report["checks"] if not c["ok"]]
    assert all(files.report["die_ink"]) and files.stickers == 41
    page = pdfium.PdfDocument(files.pdf)[0]
    assert round(page.get_width() / 72 * 25.4) == round(SHEET.page_w)  # A4 with its bleed

    def pink(path: Path) -> int:
        image = pdfium.PdfDocument(path)[0].render(scale=0.5).to_pil().convert("RGB")
        return sum(1 for r, g, b in image.get_flattened_data() if r > 200 and g < 60 and b > 100)

    assert pink(tmp_path / "work" / f"{NAME}-art.pdf") == 0  # the art never prints a cut line
    assert pink(files.die) > 300
