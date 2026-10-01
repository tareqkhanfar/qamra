"""«مغامراتي مع عائلتي», the whole book (W7): every plan page and insert sheet builds from the plan, the
passport has a slot for every sticker, personalization holds for 1 to 6 members with long names, a boy and a
girl, and a child raised by a grandmother only (A7 §11), numbers follow the book's numerals, and the insert
sheets carry their die lines on their own layer."""

import asyncio
import dataclasses
import re
from pathlib import Path

import pypdfium2 as pdfium
import pytest
from qamra_workbook.family import INSERT_TYPES, Insert, Page, book_pages, check_inserts, load
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.render.dielines import layers
from qamra_workbook.render.engine import book_html, build_pages, print_pdf
from qamra_workbook.render.family import PLAN, cover_specs, insert_sheets, plan_pages
from qamra_workbook.render.family_order import family_spec, render_insert
from qamra_workbook.render.registry import Assets
from qamra_workbook.render.spec import Child, Family, Member

from qamra_pdf import preflight

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
KHATIB = Family(
    "الخطيب",
    (Member("ماما", scarf=True), Member("بابا"), Member("أخي", "كرم"), Member("ستّي", scarf=True)),
    "رام الله",
)
LONG_SIX = Family(
    "أبو الهيجاء الكيلاني",
    (
        Member("ماما", "نور الهدى", scarf=True),
        Member("بابا", "عبد الرحمن"),
        Member("أخي", "محمد الأمين"),
        Member("أختي", "سلسبيل"),
        Member("ستّي", "أم خليل", scarf=True),
        Member("سيدي", "أبو خليل"),
    ),
    "بيت ساحور",
)
GRANDMOTHER_ONLY = Family("الكيلاني", (Member("ستّي", scarf=True),), "الخليل")
FATHER_ONLY = Family("النجار", (Member("بابا", "سامي"),), "نابلس")
GRANDMA_AND_COUSIN = Family("الأحمد", (Member("ستّي"), Member("من العائلة", "جود", "child")), "جنين")
GIRL, BOY = Child("ليان", "f"), Child("عبد الرحمن نور الدين", "m")
PARENTS = re.compile(r"(?<![\w])(ماما|بابا)(?![\w])")


def plan_book(child: Child = GIRL, family: Family = KHATIB, size: str = "21x28", **changes: object):
    plan = load(ROOT / PLAN)
    specs, _ = plan_pages(plan, list(range(1, len(book_pages(plan)) + 1)), {})
    return dataclasses.replace(family_spec(tuple(specs), child, family, size), **changes)


def body(book: object, pages: list[object]) -> str:
    html = book_html(book, pages, ASSETS)  # type: ignore[arg-type]
    return html[html.index("<body") :]


def test_every_page_of_the_book_builds_from_the_plan() -> None:
    book = plan_book()
    pages = build_pages(book, ASSETS)  # raises when a page's checks fail
    assert len(pages) == 112 and [p.spec.number for p in pages] == list(range(1, 113))
    types = {p.spec.type for p in pages}
    assert types >= {
        "title-page", "toc", "my-family", "routine-builder", "picture-talk", "feelings-faces",
        "situation-feeling-match", "story-finish", "chore-chart", "nature-bingo", "interview-template",
        "family-game-cards", "sequence-cards", "recipe-steps", "passport", "certificate-family",
    }  # fmt: skip
    recipes = [p for p in pages if p.spec.type == "recipe-steps"]
    assert {p.built.data["variant"] for p in recipes} == {"steps", "count", "layers"}
    assert all(p.built.data["safety"] for p in recipes)


def test_the_passport_has_a_slot_for_every_sticker() -> None:
    plan = load(ROOT / PLAN)
    passport = next(p for p in build_pages(plan_book(), ASSETS) if p.spec.type == "passport")
    stickers = dict(insert_sheets(plan))["stickers"]
    sheet = build_pages(family_spec(tuple(stickers), GIRL, KHATIB), ASSETS)[0].built.data
    assert len(passport.built.data["slots"]) == len(sheet["stamps"]) == 12
    assert len(passport.built.data["badges"]) == len(sheet["badges"]) == 7
    assert [s["label"] for s in passport.built.data["slots"]] == [s["label"] for s in sheet["stamps"]]
    assert len(sheet["chores"]) == 21 and len(sheet["days"]) == 7 and len(sheet["routine"]) == 10


def test_every_insert_sheet_builds_and_prints_on_its_own_paper() -> None:
    plan = load(ROOT / PLAN)
    sheets = insert_sheets(plan)
    assert [name for name, _ in sheets] == ["stickers", "card-money-recipes", "card-games-roles"]
    types = [s.type for _, specs in sheets for s in specs]
    assert set(types) == set(INSERT_TYPES) and all(s.number == 0 for _, specs in sheets for s in specs)
    for _, specs in sheets:
        build_pages(family_spec(tuple(specs), GIRL, KHATIB), ASSETS)
    bad_sheets = [
        Page(type="toc", title="x", instruction="x"),  # a book page on card stock
        Page(type="badge-sticker-sheet", title="x", instruction="x"),  # stickers on card stock
    ]
    wrong = plan.model_copy(
        update={"inserts": [Insert(kind="card-stock", title="x", items=[], sheets=bad_sheets)]}
    )
    assert len(check_inserts(wrong)) == 2


@pytest.mark.parametrize(
    ("child", "family"),
    [
        (GIRL, GRANDMOTHER_ONLY),
        (BOY, LONG_SIX),
        (BOY, FATHER_ONLY),
        (GIRL, KHATIB),
        (BOY, GRANDMA_AND_COUSIN),
    ],
    ids=[
        "girl, grandmother only",
        "boy, six members, long names",
        "boy, father only",
        "girl, four",
        "cousin",
    ],
)
def test_personalization_never_assumes_a_mother_and_a_father(child: Child, family: Family) -> None:
    book = plan_book(child, family)
    pages = build_pages(book, ASSETS)
    html = body(book, pages)
    words = {m.label for m in family.members} | {m.role for m in family.members}  # the family's own words
    assert set(PARENTS.findall(html)) <= words  # «ماما» / «بابا» only when the family has them
    assert "{" not in html.replace("{{", "")  # no placeholder left anywhere on the pages
    assert f"عائِلَةُ {family.name}" in html and all(m.label in html for m in family.members)
    assert child.name in html
    scoreboard = next(p for p in pages if p.spec.number == 99)
    assert len(scoreboard.built.data["players"]) == len(family.members) + 1


def test_gender_forms_follow_the_child() -> None:
    girl = {p.spec.number: p for p in build_pages(plan_book(GIRL), ASSETS)}
    boy = {p.spec.number: p for p in build_pages(plan_book(BOY), ASSETS)}
    assert strip_tashkeel(girl[8].instruction).startswith("ابحثي") and strip_tashkeel(
        boy[8].instruction
    ).startswith("ابحث ")
    assert strip_tashkeel(girl[3].title).endswith("المغامرة الصغيرة") and strip_tashkeel(
        boy[3].title
    ).endswith("المغامر الصغير")
    assert "مستكشفة" in strip_tashkeel(girl[34].title) and "مستكشف الطبيعة" in strip_tashkeel(boy[34].title)


@pytest.mark.parametrize("numerals", ["hindi", "latin"])
def test_every_number_follows_the_books_numerals(numerals: str) -> None:
    book = plan_book(numerals=numerals)
    html = body(book, build_pages(book, ASSETS))
    hindi = bool(re.search("[٠-٩]", html))
    assert hindi == (numerals == "hindi")
    assert bool(re.search(r">\s*112\s*<", html)) == (numerals == "latin")


def test_new_page_types_print_at_both_sizes(tmp_path: Path) -> None:
    for size in ("21x28", "a4"):
        full = plan_book(size=size)
        picked = tuple(p for p in full.pages if p.number in (1, 2, 4, 37, 49, 57, 63, 81, 96, 99))
        book = dataclasses.replace(full, pages=picked)
        html = book_html(book, build_pages(book, ASSETS), ASSETS)
        pdf = asyncio.run(print_pdf(html, tmp_path / f"{size}.html", tmp_path / f"{size}.pdf", book.geometry))
        g = book.geometry
        report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
        assert report.passed and all(c.ok for c in report.checks), report.to_dict()


def test_the_cover_has_a_front_and_a_back() -> None:
    plan = load(ROOT / PLAN)
    pages = build_pages(family_spec(tuple(cover_specs(plan)), BOY, LONG_SIX), ASSETS)
    assert [p.spec.type for p in pages] == ["cover-front", "cover-back"]
    assert "عبد الرحمن" in pages[1].built.data["made_for"] and "يجمع" in pages[1].built.data["collect"]


def test_insert_sheets_carry_their_die_lines_on_their_own_layer(tmp_path: Path) -> None:
    stickers = dict(insert_sheets(load(ROOT / PLAN)))["stickers"]
    book = family_spec(tuple(stickers), GIRL, KHATIB)
    pdf, die = asyncio.run(render_insert(book, ASSETS, tmp_path, "stickers"))
    assert layers(pdf) == ["CutContour"]

    def pink(path: Path) -> int:
        image = pdfium.PdfDocument(path)[0].render(scale=0.5).to_pil().convert("RGB")
        return sum(1 for r, g, b in image.get_flattened_data() if r > 200 and g < 60 and b > 100)

    assert pink(tmp_path / "work" / "stickers-art.pdf") == 0  # the art never prints a cut line
    assert pink(die) > 500 and pink(pdf) > 500  # the die has them, and the layered file shows them
