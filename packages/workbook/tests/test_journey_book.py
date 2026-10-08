"""«رحلتي الأولى للتعلّم», stage 1 as a printed book: every page of the plan builds from its print layer and
passes its checks, the texts follow the child (name, gender), audio pages print a QR to their item's public
player, and a small render passes preflight."""

import asyncio
import dataclasses
import datetime as dt
from pathlib import Path

import cv2  # type: ignore[import-not-found]
import pytest
from qamra_workbook.journey import load
from qamra_workbook.journey_book import (
    AUDIO,
    JOURNEY_TYPES,
    PLAN,
    audio_code,
    audio_items,
    built_stages,
    catalog_text,
    colour_problems,
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


@pytest.mark.parametrize(("stage", "count"), [(1, 118), (2, 120), (3, 120)])
def test_every_page_of_each_stage_builds_from_the_plan(stage: int, count: int) -> None:
    plan, layer = load(PLAN), load_layer(stage)
    pages = page_specs(plan, layer)
    assert [p.number for p in pages] == [p.n for p in stage_of(plan, stage)] and len(pages) == count
    assert layer_problems(plan, layer) == []
    for child in (GIRL, BOY):
        book = stage_book(pages + cover_specs(layer), child, day=dt.date(2026, 9, 29))
        assert book_problems(book) == []  # ≤ 7 words, a title and an instruction, no retired words
        built = build_pages(book, ASSETS)  # raises PageProblems when any page fails its checks
        assert len(built) == count + 2
    types = {p.type for p in pages}
    assert "section-opener" not in types  # the family book's opener; the journey has its own
    assert {"journey-opener", "what-i-learned"} <= types
    if stage == 1:
        assert {"listen-rows", "write-progression", "shape-journey"} <= types
    else:
        assert {"journey-finger-trace", "journey-letter-trace", "find-letter", "journey-en-letter"} <= types
        assert sum(p.type == "journey-finger-trace" for p in pages) == 14  # one new letter per page
    if stage != 1:  # the plan's letter-trace pages are drawn by the journey's own builder (small letters fit)
        assert "journey-letter-trace" in types and "letter-trace" not in types
        assert JOURNEY_TYPES == {"letter-trace": "journey-letter-trace"}
    if stage == 3:
        assert {"journey-harakat", "journey-syllables", "journey-word-write", "journey-assessment"} <= types
        assert {"journey-observation-checklist", "journey-picture-sum", "certificate"} <= types


def test_the_english_name_page_gets_a_latin_name() -> None:
    from qamra_workbook.journey_book import latin_name

    assert latin_name("ليان") == "Layan" and latin_name("سلمى") == "Salama" and latin_name("آدم") == "Adam"
    pages = page_specs(load(PLAN), load_layer(2))
    named = [
        p for p in stage_book(pages, BOY).pages if p.type == "name-trace" and p.params.get("script") == "en"
    ]
    assert named and named[0].params["name_en"] == "Adam"
    given = stage_book(pages, BOY, name_en="Adam Karim").pages  # the parent's spelling wins
    assert (
        next(p for p in given if p.type == "name-trace" and p.params.get("script") == "en").params["name_en"]
        == "Adam Karim"
    )
    odd = stage_book(pages, BOY, name_en="Adam K.").pages  # not a spelling the API accepts: the guess
    assert next(p for p in odd if p.params.get("script") == "en").params["name_en"] == "Adam"


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
    shared = {i.key: i.code for s in (2, 3) for i in audio_items(load(PLAN), load_layer(s))}
    assert shared["letter:ar:ب"] == audio_code("letter:ar:ب") and shared["letter:en:A"] == audio_code(
        "letter:en:A"
    )
    assert (
        len({i.code for s in (1, 2, 3) for i in audio_items(load(PLAN), load_layer(s))}) == len(shared) + 10
    )
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


STAGES_2_3 = pytest.mark.parametrize("stage", [2, 3])


@STAGES_2_3
def test_stage_2_and_3_texts_follow_the_child(stage: int) -> None:
    pages = page_specs(load(PLAN), load_layer(stage))
    girl = build_pages(stage_book(pages, GIRL, name_en="Layan"), ASSETS)
    boy = build_pages(stage_book(pages, BOY, name_en="Adam"), ASSETS)
    by_n = {g.spec.number: (g, b) for g, b in zip(girl, boy, strict=True)}
    for g, b in by_n.values():
        for built in (g, b):
            assert not leftover_placeholders(built.title + built.instruction)
    g1, b1 = by_n[1]  # «هذا الكِتابُ لِـ {child}»: the owner page carries the name
    assert "ضَعي" in g1.instruction and "ضَعْ" in b1.instruction and "ضَعي" not in b1.instruction
    assert g1.built.data["name"] == "ليان" and b1.built.data["name"] == "آدم"
    assert "ليان" in by_n[2][0].title and "آدم" in by_n[2][1].title  # the journey map
    last = by_n[120]  # the stage's certificate (stage 2) or finale (stage 3), with the child's own name
    assert "يا" in last[0].instruction or "أَحْسَنْتِ" in last[0].title
    english = [n for n, (g, _) in by_n.items() if g.spec.lang == "en" and "{name_en}" in g.spec.title]
    assert english, "an English page greets the child by name"
    for n in english:
        assert (
            "Layan" in by_n[n][0].title and "Adam" in by_n[n][1].title
        )  # the Latin name, not the Arabic one
    if stage == 3:
        assert "أَحْسَنْتِ يا بَطَلَةُ" in by_n[120][0].title and "أَحْسَنْتَ يا بَطَلُ" in by_n[120][1].title


@STAGES_2_3
def test_stage_2_and_3_answer_keys_cover_every_puzzle_page(stage: int) -> None:
    pages = page_specs(load(PLAN), load_layer(stage))
    built = build_pages(stage_book(pages, GIRL), ASSETS)
    puzzles = {
        "journey-story",
        "memory-recall",
        "journey-picture-sum",
        "journey-hidden-picture",
        "spot-difference",
        "picture-riddle",
        "journey-key-coloring",
        "journey-before-after",
        "journey-count-frame",
        "journey-number-intro",
        "journey-match-letters",
        "journey-first-sound",
        "journey-claps",
        "journey-rhyme",
        "journey-tangled",
        "maze",
    }
    found = [p for p in built if p.spec.type in puzzles]
    assert found
    assert all(p.built.answer for p in found), [p.spec.number for p in found if not p.built.answer]


def test_the_find_letter_colours_follow_the_pages_order() -> None:
    page = page_specs(load(PLAN), load_layer(2))[33]  # p34: «لَوِّنِ الأَلِفَ بِالأَحْمَرِ وَالباءَ بِالأَزْرَقِ»
    assert page.type == "find-letter" and colour_problems(page) == []
    swapped = dataclasses.replace(page, instruction="{لَوِّنِ/لَوِّني} الأَلِفَ بِالأَزْرَقِ وَالباءَ بِالأَحْمَرِ")
    assert colour_problems(swapped) and "أَحْمَر" not in swapped.instruction.split("بِالأَزْرَقِ")[0]


def test_audio_codes_are_stable_and_one_per_item_across_the_three_stages() -> None:
    plan = load(PLAN)
    items = {s: audio_items(plan, load_layer(s)) for s in (1, 2, 3)}
    assert [len(items[s]) for s in (1, 2, 3)] == [10, 38, 41]
    assert audio_code("letter:ar:ب") == "uqysnb2n" and audio_code("letter:en:A") == "wptk3srn"
    assert audio_code("song:ar:alphabet") == "3m4pqu7q" and audio_code("journey:s2:p14") == "d635p4w4"
    letters = [i for s in (2, 3) for i in items[s] if i.key.startswith("letter:")]
    assert len(letters) == 28 + 26 and len({i.key for i in letters}) == 54  # every letter once, in its stage
    assert {i.stage for i in letters if i.key.startswith("letter:ar:")} == {2, 3}
    assert all(i.code == audio_code(i.key) and i.tts for i in letters)  # a letter's code comes from its key
    assert {i.lang for i in letters if i.key.startswith("letter:en:")} == {"en"}
    everything = [i for s in (1, 2, 3) for i in items[s]]
    assert len({i.code for i in everything}) == len(everything) == 89  # no two items share a code
    assert all("{" not in i.title for i in everything)  # the player: the same for every child
    assert all(i.show for i in everything if i.stage > 1)  # stages 2 and 3 show what is heard
    for s in (2, 3):
        assert layer_problems(plan, load_layer(s)) == []
    assert AUDIO.read_text(encoding="utf-8") == catalog_text(plan, built_stages())


@STAGES_2_3
def test_a_small_render_of_stage_2_or_3_passes_preflight_and_the_qr_decodes(
    stage: int, tmp_path: Path
) -> None:
    all_pages = page_specs(load(PLAN), load_layer(stage))
    numbers = {2: (3, 30, 103), 3: (27, 65, 73)}[stage]  # an opener, a letter with sound, a writing page
    book = stage_book([p for p in all_pages if p.number in numbers], GIRL, domain="qamra.test")
    pages = build_pages(book, ASSETS)
    pdf = asyncio.run(
        print_pdf(book_html(book, pages, ASSETS), tmp_path / "s.html", tmp_path / "s.pdf", book.geometry)
    )
    g = book.geometry
    report = preflight(pdf, width_mm=g.page_w, height_mm=g.page_h, bleed_mm=g.bleed, safe_mm=g.safe)
    assert report.passed, report.to_dict()
    assert all(c.ok for c in report.checks), (
        report.to_dict()
    )  # the safe-area warning too: nothing near the edge
    pngs = previews(pdf, tmp_path / "png", [f"p{n}" for n in numbers], g, dpi=220)
    letter_page = pngs[
        numbers.index(30 if stage == 2 else 27)
    ]  # the finger-trace page: its QR plays the letter
    found, _, _ = cv2.QRCodeDetector().detectAndDecode(cv2.imread(str(letter_page)))
    key = "letter:ar:أ" if stage == 2 else "letter:ar:ض"
    assert found == f"https://qamra.test/a/{audio_code(key)}"
