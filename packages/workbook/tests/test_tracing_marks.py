"""Small marks on the tracing pages (the owner's review of «دوسية التأسيس» KG1 p18, 2026-10-10: the hamza of أ
read like a damma): the hamza keeps its head and its tail at its true size, its dots never crowd or touch,
and no start dot or arrow ever sits on a mark or on a letter's dots, at every size the books print."""

import dataclasses
import math
import re
from itertools import combinations, pairwise
from pathlib import Path
from typing import Literal

import pytest
from qamra_workbook.curriculum import load
from qamra_workbook.geometry import Stroke, bounds
from qamra_workbook.letters import ARABIC
from qamra_workbook.letters.hamza import HAMZA, HAMZA_MARK
from qamra_workbook.letters.hand import BASE, TOP
from qamra_workbook.letters.model import Letter
from qamra_workbook.pictures import LibraryStore
from qamra_workbook.render import draw, marks
from qamra_workbook.render.foundation import volume_book
from qamra_workbook.render.foundation_text import letter_trace_say
from qamra_workbook.render.pages import workbook_kg1  # noqa: F401  (registers the builders)
from qamra_workbook.render.pages.letters import dotted_letter
from qamra_workbook.render.pages.workbook_arabic import big_track
from qamra_workbook.render.pages.workbook_common import arabic_shape, fit_capped, glyph, start_marks
from qamra_workbook.render.pages.workbook_front import letter_shape
from qamra_workbook.render.registry import REGISTRY, Assets, PageContext
from qamra_workbook.render.spec import Child, PageSpec

ALIF = BASE - TOP  # the alif's height, letter units
CAPS = (11.0, 13.0, 14.0, 17.0, 18.0, 22.0, 24.0, 28.0)  # every row cap height the books print (mm)
WITH_MARKS = [
    arabic_shape("أ"),
    arabic_shape("إ"),
    arabic_shape("آ"),
    arabic_shape("أ", "final"),
    ARABIC[("ك", "isolated")],
    ARABIC[("ك", "final")],
    letter_shape("ؤ", "isolated"),
    letter_shape("ئ", "medial"),
    letter_shape("ئ", "isolated"),
    letter_shape("ئ", "final"),
]
IDS = [f"{x.char}-{x.form}" for x in WITH_MARKS]
DOTTED = [ARABIC[(c, "isolated")] for c in "بتثجخذزشضظغفقني"]

CIRCLE = re.compile(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="([\d.]+)" fill="([^"]+)"')
ARROW = re.compile(r'<path d="[^"]+" fill="([^"]+)"[^>]*transform="translate\(([-\d.]+) ([-\d.]+)\) rotate')

Circle = tuple[float, float, float]


def circles(svg: str, fill: str | None = None) -> list[Circle]:
    return [(float(x), float(y), float(r)) for x, y, r, f in CIRCLE.findall(svg) if fill in (None, f)]


def mark_dots(svg: str) -> list[Circle]:
    return [c for group in re.findall(r'<g class="mark-dots">(.*?)</g>', svg) for c in circles(group)]


def dots_to_fill(svg: str) -> list[Circle]:
    found = re.findall(r'<circle cx="([-\d.]+)" cy="([-\d.]+)" r="([\d.]+)"[^>]*class="dot-to-fill"', svg)
    return [(float(x), float(y), float(r)) for x, y, r in found]


def arrows(svg: str, color: str) -> list[tuple[float, float]]:
    return [(float(x), float(y)) for fill, x, y in ARROW.findall(svg) if fill == color]


def apart(a: Circle, b: Circle) -> float:
    """The gap between two discs (negative when they overlap)."""
    return math.dist(a[:2], b[:2]) - a[2] - b[2]


def turning(points: list[tuple[float, float]]) -> float:
    """How far a polyline turns, in degrees (signed sum)."""
    total, last = 0.0, None
    for a, b in pairwise(points):
        if a == b:
            continue
        angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        if last is not None:
            total += (angle - last + 180) % 360 - 180
        last = angle
    return total


def test_the_hamza_has_a_round_head_and_a_tail_down_to_the_left() -> None:
    s = Stroke(HAMZA)
    head = [p for p, c in zip(s.polyline, s.lengths, strict=True) if c <= s.length * 0.6]
    assert abs(turning(head)) >= 220, "the head curls round, like the head of ع"
    (x0, y0), (x1, y1) = s.at(0.75)[0], s.end
    assert x1 < x0 - 15 and y1 > y0 + 8, "the tail runs down to the left"
    left, _, _, bottom = bounds([s])
    assert s.end == pytest.approx((left, bottom), abs=0.5), "the tail ends lowest and furthest left"


@pytest.mark.parametrize("shape", WITH_MARKS[:4] + WITH_MARKS[6:], ids=IDS[:4] + IDS[6:])
def test_a_hamza_or_madda_is_its_true_size_and_clear_of_its_letter(shape: Letter) -> None:
    *body, mark = shape.strokes
    assert shape.marks == (*(False for _ in body), True)
    _, y0, _, y1 = bounds([mark])
    if shape.char != "آ":
        assert 0.26 * ALIF <= y1 - y0 <= 0.34 * ALIF, "a little under a third of the alif, as in naskh"
    gap = min(math.dist(p, q) for b in body for p in b.polyline for q in mark.polyline)
    assert gap >= (12 if shape.char in "أإآ" else 7), "the mark never touches the letter it sits on"


def test_marks_are_the_small_later_strokes_only() -> None:
    kaf = ARABIC[("ك", "isolated")]
    assert kaf.marks == (False, True)
    a, b = bounds([kaf.strokes[1]]), bounds([Stroke(HAMZA).scaled(HAMZA_MARK)])
    assert (a[2] - a[0], a[3] - a[1]) == pytest.approx((b[2] - b[0], b[3] - b[1])), (
        "the kaf's mark is a hamza"
    )
    assert not any(ARABIC[("ط", "isolated")].marks), "the stick of ط is long"
    assert not any(ARABIC[("ك", "medial")].marks), "the head of the medial kaf is long"
    assert ARABIC[("ء", "isolated")].small == (True,) and ARABIC[("ء", "isolated")].marks == (False,)
    assert not any(any(x.marks) for (c, _), x in ARABIC.items() if c not in "كء")


@pytest.mark.parametrize("cap", CAPS)
@pytest.mark.parametrize("shape", [*WITH_MARKS, ARABIC[("ء", "isolated")]], ids=[*IDS, "ء"])
def test_mark_dots_are_many_enough_and_never_touch(shape: Letter, cap: float) -> None:
    scale = cap / ALIF
    svg = dotted_letter(shape, scale=scale, x=10, y=10, first=True, number=str)
    dots = mark_dots(svg)
    small = [s.scaled(scale) for s, m in zip(shape.strokes, shape.small, strict=True) if m]
    assert len(dots) >= min(6, min(math.floor(s.length / (marks.MIN_PITCH * 0.7)) for s in small))
    for a, b in combinations(dots, 2):
        assert apart(a, b) >= 0.25 * a[2], f"two dots of the mark touch at cap {cap}"
    assert 'class="mark-ghost"' in svg, "the mark's shape shows under its dots"


def no_cover(svg: str, badge_fill: str, arrow_color: str, label: str) -> None:
    dots = mark_dots(svg)
    for badge in circles(svg, badge_fill):
        for dot in dots:
            assert apart(badge, dot) >= 0, f"{label}: a start dot sits on the mark"
    for ax, ay in arrows(svg, arrow_color):
        for dot in dots:
            assert math.dist((ax, ay), dot[:2]) >= dot[2] + 0.3, f"{label}: an arrow sits on the mark"


@pytest.mark.parametrize("shape", WITH_MARKS, ids=IDS)
def test_start_dots_and_arrows_never_cover_a_mark_on_a_row(shape: Letter) -> None:
    for cap in CAPS:
        for first in (True, False):
            svg = dotted_letter(shape, scale=cap / ALIF, x=10, y=10, first=first, number=str)
            no_cover(svg, draw.START, draw.ARROW, f"cap {cap}")


@pytest.mark.parametrize("shape", WITH_MARKS, ids=IDS)
def test_start_dots_and_arrows_never_cover_a_mark_on_the_big_letter(shape: Letter) -> None:
    for most, band in ((0.5, 24.0), (0.85, 24.0), (0.8, 12.0)):
        svg = big_track(shape, 20, 2, 146, 92, str, "#123456", most=most, band_units=band)
        no_cover(svg, draw.START, "#123456", f"xl {most}")
        dots = mark_dots(svg)
        assert len(dots) >= (6 if shape.char == "آ" else 8), "the big mark shows its whole shape in dots"


@pytest.mark.parametrize("shape", WITH_MARKS, ids=IDS)
def test_a_model_letter_keeps_its_mark_visible(shape: Letter) -> None:
    scale, dx, dy = fit_capped(shape, 0, 0, 34, 30, 1, 1.0)
    body = glyph(shape, scale, dx, dy, width=15)
    widths = [float(w) for w in re.findall(r'stroke-width="([\d.]+)"', body)]
    assert widths[-1] == pytest.approx(widths[0] / 2, rel=0.05), "the mark is drawn thinner, an open shape"
    svg = start_marks(shape, scale, dx, dy, 2.2, str)
    mark = shape.strokes[-1].scaled(scale, dx, dy)
    for x, y, r in circles(svg, draw.START):
        assert min(math.dist((x, y), p) for p in mark.polyline) >= r, "the start dot sits beside the mark"


@pytest.mark.parametrize("shape", DOTTED, ids=[x.char for x in DOTTED])
def test_letter_dots_are_round_dots_with_their_numbers_beside_them(shape: Letter) -> None:
    for cap in (14.0, 24.0):
        svg = dotted_letter(shape, scale=cap / ALIF, x=10, y=10, first=True, number=str)
        dots = dots_to_fill(svg)
        assert len(dots) == len(shape.dots) and "stroke-dasharray" not in svg, "solid round dots"
        numbers = circles(svg, draw.START)[len(shape.strokes) :]
        assert len(numbers) == len(shape.dots)
        for badge in numbers:
            assert all(apart(badge, d) >= 0 for d in dots), f"a dot's number sits on a dot ({shape.char})"
    svg = big_track(shape, 20, 2, 146, 92, str, "#123456", most=0.85)
    rings = dots_to_fill(svg)
    assert len(rings) == len(shape.dots) and "stroke-dasharray" not in svg
    pale = [c for c in circles(svg, "#F9DA8F")]
    for badge in circles(svg, draw.START)[len(shape.strokes) :]:
        assert all(apart(badge, d) >= 0 for d in pale), f"a dot's number sits on a dot ({shape.char})"


# ---- the review pages, words and the wording of sizes (foundation QA of KG1 V3, 2026-10-10) -------------

ROOT = Path(__file__).resolve().parents[3]
ASSETS = Assets(LibraryStore())
KG1 = load(ROOT / "content/workbook/curriculum/kg1.yaml")


def built(kind: str, section: str = "arabic", **params: object) -> tuple[str, list[str]]:
    lang: Literal["ar", "en"] = "en" if section == "english" else "ar"
    page = PageSpec(
        "t-1", kind, 1, section, "عنوان", "تعليمات", lang, "Do it." if lang == "en" else "", params=params
    )
    book = dataclasses.replace(
        volume_book(KG1, 3, Child("ليان", "f"), name_en="Layan", pages=range(0)), pages=(page,)
    )
    out = REGISTRY[kind].build(PageContext(page, book, ASSETS))
    return str(out.data.get("svg", "")), out.problems


def row_caps(svg: str) -> list[float]:
    """The cap height (top line to base line) of every writing row on a page."""
    caps = []
    for row in re.findall(r'class="trace-row".*?</svg>', svg):
        top = re.search(r'd="M2 ([\d.]+) L[^"]+" stroke="#9BB7E0" stroke-width="0.5"', row)
        base = re.search(r'd="M2 ([\d.]+) L[^"]+" stroke="#E27D63"', row)
        assert top and base
        caps.append(float(base.group(1)) - float(top.group(1)))
    return caps


REVIEWS = [
    ("english", ["W", "X", "Y", "Z"]),
    ("english", ["M", "N", "O", "P", "Q", "R"]),
    ("arabic", ["م", "ن"]),
    ("arabic", ["م", "ن", "ه", "و", "ي"]),
    ("arabic", ["ف", "ق", "ك", "ل"]),
]


@pytest.mark.parametrize(("section", "letters"), REVIEWS)
def test_a_review_traces_every_letter_big_enough_to_show_its_shape(section: str, letters: list[str]) -> None:
    svg, problems = built("kg1-unit-review", section, letters=letters, volume=3)
    caps = row_caps(svg)
    assert problems == [] and len(caps) == len(letters), "a row for every letter (Z too)"
    assert min(caps) >= 13, f"letters {min(caps):.1f} mm high are a few scattered dots"


def test_the_assessment_writes_its_letters_big_and_leaves_room_to_write_alone() -> None:
    svg, problems = built("kg1-assessment", "arabic", letters=list("لفيكوقنهم"), write=["ل", "ن"], volume=3)
    assert problems == [] and min(row_caps(svg)) >= 13


def test_a_traced_word_numbers_each_pen_lift_and_draws_no_start_dot_where_the_pen_goes_on() -> None:
    svg, _ = built("kg1-word-write", words=["أسد", "قمر"], mode="dotted")
    labels = re.findall(r'class="dot-label">([^<]+)<', svg)
    assert labels.count("١") == 2 and labels.count("٢") == 1 and labels.count("٣") == 1, labels
    starts = circles(svg, draw.START)
    # «أسد»: the alif, its hamza and the س (the د goes on from it); «قمر»: the ق, and the pen goes on
    assert len(starts) == 3 + 1, "no start dot in the middle of a joined word"


def test_dots_where_the_pen_comes_back_along_a_tooth_are_drawn_once() -> None:
    seen = ARABIC[("س", "initial")]
    svg = dotted_letter(seen, scale=0.2, x=0, y=0, first=False, number=str)
    dots = circles(svg, draw.DOT)
    for a, b in combinations(dots, 2):
        assert math.dist(a[:2], b[:2]) >= 3.5 * 0.79, "two dots of the way up and down a tooth"


def test_the_size_words_are_feminine_like_the_letter_names() -> None:
    svg, _ = built("kg1-letter-trace", letter="أ", sizes=["xl", "l"])
    assert ">كَبيرَةٌ<" in svg and "كَبيرٌ" not in svg
    plan = (ROOT / "content/workbook/curriculum/kg2.yaml").read_text(encoding="utf-8")
    assert "الكبير ثم الأصغر" not in plan and "حرف الألف من أعلى إلى أسفل: الكبير" not in plan
    say = letter_trace_say({"letter": "ب", "turn": 2, "volume": 1})
    assert say == "أَوَّلًا {تَتَبَّعِ/تَتَبَّعي} الباءَ الكَبيرَةَ، ثُمَّ الصَّغيرَةَ"
