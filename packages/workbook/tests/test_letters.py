import math
from itertools import combinations

import pytest
from qamra_workbook.letters import ALPHABET, ARABIC, EXPECTED, placed, word
from qamra_workbook.letters.hand import BASE, LOW, TOP
from qamra_workbook.letters.model import Letter
from qamra_workbook.strokes import BA, LETTERS, letter

ALL = sorted(ARABIC.values(), key=lambda x: (ALPHABET.index(x.char), x.form))
ids = [f"{x.char}-{x.form}" for x in ALL]
NON_CONNECTING = set("ادذرزو")
FOUR_FORMS = set(ALPHABET) - NON_CONNECTING - {"ة", "ى", "ء", "لا"}
TOLERANCE = 0.5


def angle_between(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def test_every_letter_has_every_form_it_should() -> None:
    assert len(FOUR_FORMS) == 22 and len(NON_CONNECTING) == 6
    want = {(c, f) for c in FOUR_FORMS for f in ("isolated", "initial", "medial", "final")}
    want |= {(c, f) for c in NON_CONNECTING | {"ة", "ى", "لا"} for f in ("isolated", "final")}
    want |= {("ء", "isolated")}
    assert set(ARABIC) == want
    assert len(ARABIC) == 107
    assert {(c, f) for c in ALPHABET for f in EXPECTED[c]} == want


@pytest.mark.parametrize("shape", ALL, ids=ids)
def test_strokes_are_single_paths_that_start_and_stay_in_the_box(shape: Letter) -> None:
    assert shape.strokes and shape.guides.base == BASE and shape.guides.low == LOW
    for s in shape.strokes:
        assert len(s.polyline) >= 2 and s.length > 10
        x, y = s.start
        assert 0 <= x <= shape.width and TOP - 2 <= y <= LOW, f"start {s.start} outside the box"
        for x, y in s.polyline:
            assert -TOLERANCE <= x <= shape.width + TOLERANCE and TOP - 2 <= y <= LOW, (x, y)
    for x, y in shape.dots:
        assert shape.dot_r <= x <= shape.width - shape.dot_r and TOP <= y <= LOW, (x, y)


@pytest.mark.parametrize("shape", ALL, ids=ids)
def test_the_body_comes_first_then_marks_then_dots(shape: Letter) -> None:
    body, *marks = shape.strokes
    if shape.join_right is None and shape.join_left is None:
        assert all(m.length < body.length for m in marks), "the body is the first and longest stroke"
    # dots are written after every stroke and never sit on the letter
    for dot in shape.dots:
        for s in shape.strokes:
            assert min(math.dist(dot, p) for p in s.polyline) > shape.dot_r + 5, f"dot {dot} touches a stroke"
    for a, b in combinations(shape.dots, 2):
        assert math.dist(a, b) >= 3 * shape.dot_r, "dots touch each other"


@pytest.mark.parametrize("shape", ALL, ids=ids)
def test_joins_sit_on_the_base_line_on_the_right_side(shape: Letter) -> None:
    right, left = shape.form in ("medial", "final"), shape.form in ("initial", "medial")
    assert (shape.join_right is not None) == right and (shape.join_left is not None) == left
    body = shape.strokes[0]
    if shape.join_right is not None:
        assert shape.join_right == pytest.approx((shape.width, BASE), abs=TOLERANCE)
        assert body.start == pytest.approx(shape.join_right, abs=TOLERANCE), "the pen arrives at the join"
        assert angle_between(body.at(0)[1], 180) < 15, "arrives level, heading left"
    if shape.join_left is not None:
        assert shape.join_left == pytest.approx((0, BASE), abs=TOLERANCE)
        assert body.end == pytest.approx(shape.join_left, abs=TOLERANCE), "the body ends at the join"
        assert angle_between(body.at(1)[1], 180) < 15, "leaves level, heading left"


@pytest.mark.parametrize(("first", "second"), [("ب", "ت"), ("ل", "ا"), ("ع", "ة"), ("ك", "ي"), ("س", "م")])
def test_joined_forms_meet(first: str, second: str) -> None:
    a, b = letter(first, "initial"), letter(second, "final")
    (xa, xb), total = placed([a, b])
    assert total == pytest.approx(a.width + b.width)
    assert a.join_left is not None and b.join_right is not None
    end = (xa + a.strokes[0].end[0], a.strokes[0].end[1])
    start = (xb + b.strokes[0].start[0], b.strokes[0].start[1])
    assert end == pytest.approx(start, abs=TOLERANCE)
    assert end == pytest.approx((xa + a.join_left[0], BASE), abs=TOLERANCE)


def test_every_initial_and_medial_meets_every_medial_and_final() -> None:
    lefts = [x for x in ALL if x.join_left is not None]
    rights = [x for x in ALL if x.join_right is not None]
    for a in lefts:
        for b in rights:
            (xa, xb), _ = placed([a, b])
            end = (xa + a.strokes[0].end[0], a.strokes[0].end[1])
            start = (xb + b.strokes[0].start[0], b.strokes[0].start[1])
            assert math.dist(end, start) < 1, f"{a.char}-{a.form} + {b.char}-{b.form}"


@pytest.mark.parametrize(
    ("text", "forms"),
    [
        ("بيت", ["initial", "medial", "final"]),
        ("لعبة", ["initial", "medial", "medial", "final"]),
        ("ورد", ["isolated", "isolated", "isolated"]),
        ("ماء", ["initial", "final", "isolated"]),
        ("بلا", ["initial", "final"]),
    ],
)
def test_words_are_spelled_with_the_right_forms(text: str, forms: list[str]) -> None:
    shapes = word(text)
    assert [s.form for s in shapes] == forms
    if text == "بلا":
        assert shapes[1].char == "لا"


# Letters that share a body in a form differ only in their dots.
FAMILIES = [
    ("بتث", ("isolated", "initial", "medial", "final")),
    ("بتثني", ("initial", "medial")),
    ("جحخ", ("isolated", "initial", "medial", "final")),
    ("دذ", ("isolated", "final")),
    ("رز", ("isolated", "final")),
    ("سش", ("isolated", "initial", "medial", "final")),
    ("صض", ("isolated", "initial", "medial", "final")),
    ("طظ", ("isolated", "initial", "medial", "final")),
    ("عغ", ("isolated", "initial", "medial", "final")),
    ("فق", ("initial", "medial")),
    ("هة", ("isolated", "final")),
    ("يى", ("isolated", "final")),
]


@pytest.mark.parametrize(("chars", "forms"), FAMILIES, ids=[f[0] for f in FAMILIES])
def test_a_dot_family_shares_its_main_stroke(chars: str, forms: tuple[str, ...]) -> None:
    for form in forms:
        shapes = [ARABIC[(c, form)] for c in chars]
        first = shapes[0]
        for other in shapes[1:]:
            assert [s.d for s in other.strokes] == [s.d for s in first.strokes], f"{other.char} {form}"
            assert other.width == first.width
        assert len({s.dots for s in shapes}) == len(shapes), f"{form}: the dots must tell them apart"


def test_the_samples_keep_their_shapes() -> None:
    assert letter("ب", "isolated") is BA
    assert BA.strokes[0].d == "M176 36 C177 56 180 78 169 88 C159 96 147 97 130 97 L62 97 C42 97 27 93 22 70"
    assert BA.dots == ((100, 124),) and BA.dot_r == 8 and BA.width == 200
    assert letter("A", "capital").strokes[2].d == "M34 60 L66 60"
    assert len(letter("a", "small").strokes) == 2
    assert LETTERS[("ت", "final")].rtl and not LETTERS[("A", "capital")].rtl
    with pytest.raises(KeyError, match="no stroke data"):
        letter("ب", "capital")
