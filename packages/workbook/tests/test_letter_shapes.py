"""The shapes of the code-drawn letters against printed naskh (the owner's review of 2026-10-17): the dots of
ي under its belly, و with a round head on the line and a long tail, ق with a small head and a bowl deeper
than ن, ف and ب with a tail that curls up, ج ح خ open under the hat. Every renderer (tracing rows, big
outlines, the circles to colour, name rows, journey pages) draws these same shapes."""

import re

import pytest
from qamra_workbook.letters import ARABIC
from qamra_workbook.letters.hand import BASE, LOW, MID
from qamra_workbook.letters.model import Letter
from qamra_workbook.render.pages.workbook_front import arabic_name_row, spell_name

X_HEIGHT = BASE - MID


def lowest(shape: Letter) -> float:
    return max(y for s in shape.strokes for _, y in s.polyline)


def at_x(shape: Letter, x: float, stroke: int = 0) -> list[float]:
    """The heights where the stroke passes over `x`."""
    return [py for px, py in shape.strokes[stroke].polyline if abs(px - x) < 2]


@pytest.mark.parametrize("form", ["isolated", "final"])
def test_the_dots_of_ya_sit_under_its_belly_inside_the_writing_band(form: str) -> None:
    ya = ARABIC[("ي", form)]
    assert len(ya.dots) == 2
    for x, y in ya.dots:
        under = at_x(ya, x)
        assert under, f"dot {x} is not under the belly"
        assert y - ya.dot_r > max(under) + 4, "the dot sits under the belly, not inside it"
        assert y > BASE and y + ya.dot_r <= LOW, "below the base line, above the descender line"
    assert lowest(ya) < BASE + X_HEIGHT * 0.6, "the belly stays shallow enough for its dots"
    # ى is the same body without the dots
    assert [s.d for s in ARABIC[("ى", form)].strokes] == [s.d for s in ya.strokes]


@pytest.mark.parametrize(
    ("char", "below"), [("ب", True), ("ت", False), ("ث", False), ("ن", False), ("ي", True)]
)
@pytest.mark.parametrize("form", ["initial", "medial"])
def test_the_tooth_letters_carry_their_dots_on_the_right_side(char: str, below: bool, form: str) -> None:
    shape = ARABIC[(char, form)]
    for _, y in shape.dots:
        assert (y > BASE + shape.dot_r) if below else (y < MID - shape.dot_r)


@pytest.mark.parametrize("char", ["ب", "ت", "ث"])
@pytest.mark.parametrize("form", ["isolated", "final"])
def test_the_bowl_of_ba_ends_in_a_tail_that_rises(char: str, form: str) -> None:
    body = ARABIC[(char, form)].strokes[0]
    x, y = body.end
    assert y < BASE - X_HEIGHT * 0.7, "the tail rises clearly (never «بـ»)"
    assert x <= min(px for px, _ in body.polyline) + 6, "at the left end"
    if char == "ب":
        assert all(dy > BASE for _, dy in ARABIC[(char, form)].dots)


@pytest.mark.parametrize("form", ["isolated", "final"])
def test_fa_curls_up_at_its_left_end(form: str) -> None:
    fa = ARABIC[("ف", form)]
    x, y = fa.strokes[0].end
    assert y < BASE - X_HEIGHT * 0.7 and x <= min(px for px, _ in fa.strokes[0].polyline) + 6
    assert lowest(fa) <= BASE + 8, "ف sits on the line, its bowl just under it"


@pytest.mark.parametrize("form", ["isolated", "final"])
def test_waw_has_a_round_head_on_the_line_and_a_long_tail(form: str) -> None:
    waw = ARABIC[("و", form)]
    points = waw.strokes[0].polyline
    head = [(x, y) for x, y in points if y <= BASE + 1]
    if form == "final":
        head = [(x, y) for x, y in head if x < waw.width - 30]  # not the line from the previous letter
    hx0, hx1 = min(x for x, _ in head), max(x for x, _ in head)
    top = min(y for _, y in head)
    assert BASE - top >= X_HEIGHT * 0.75, "the head is about as tall as the tooth line"
    assert 0.8 <= (hx1 - hx0) / (BASE - top) <= 1.2, "and round, not narrow"
    end_x, end_y = waw.strokes[0].end
    assert end_y > BASE + X_HEIGHT * 0.7, "the tail goes well under the line"
    assert end_x < hx0 - 20, "and sweeps to the left, past the head"


def test_qaf_has_a_small_head_and_a_bowl_deeper_than_noon() -> None:
    for form in ("isolated", "final"):
        qaf, noon = ARABIC[("ق", form)], ARABIC[("ن", form)]
        points = qaf.strokes[0].polyline
        k = next(i for i, (_, y) in enumerate(points) if y < BASE - 3)  # past the line from the letter before
        end = next(i for i in range(k, len(points)) if points[i][1] > BASE + 3)
        head, bowl = points[k:end], [(x, y) for x, y in points[end:] if y > BASE + 1]
        head_w = max(x for x, _ in head) - min(x for x, _ in head)
        bowl_w = max(x for x, _ in bowl) - min(x for x, _ in bowl)
        assert head_w < 0.45 * bowl_w, "a small head on a wide bowl"
        assert BASE - min(y for _, y in head) < X_HEIGHT * 0.7, "the head is small"
        assert lowest(qaf) > lowest(noon) + 10, "the bowl of ق goes deeper than the bowl of ن"
        assert lowest(qaf) <= LOW
        head_top = min(y for _, y in head)
        assert all(y < head_top - qaf.dot_r for _, y in qaf.dots), "two dots above the head"


@pytest.mark.parametrize("char", ["ج", "ح", "خ"])
def test_hah_stays_open_under_its_hat(char: str) -> None:
    initial = ARABIC[(char, "initial")]
    body = initial.strokes[0].polyline
    corner = max(x for x, y in body if y < 60)
    on_line = [x for x, y in body if y > BASE - 2]
    assert max(on_line) < corner - 30, "the slant meets the line well left of the corner (never «د»)"
    for form in ("medial", "final"):
        shape = ARABIC[(char, form)]
        line, head = shape.strokes
        assert line.start == (shape.width, BASE), "the line from the previous letter comes first"
        hat = head.polyline
        corner = max(x for x, y in hat if y < 60)
        foot = min((p for p in hat if abs(p[1] - BASE) < 3), key=lambda p: p[0])
        assert foot[0] < corner - 30


def test_the_name_rows_draw_the_dots_of_ya_under_the_line() -> None:
    letters = spell_name("علي")
    for mode in ("solid", "dotted"):
        svg = str(arabic_name_row(letters, 176, 20, first=True, mode=mode, number=str))
        base = float(re.findall(r'<path d="M2 ([\d.]+) L174', svg)[2])  # the third line is the base line
        ya = svg[svg.rindex('data-glyph="ي"') :] if mode == "solid" else svg
        circles = [float(cy) for cy in re.findall(r'<circle cx="[\d.]+" cy="([\d.]+)"', ya)]
        under = [cy for cy in circles if cy > base + 1]
        assert len(under) >= 2, f"{mode}: the two dots of ي are under the base line"
