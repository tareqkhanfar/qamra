"""The drawings: simple, flat, friendly vocabulary pictures in a 100 × 100 box (no text inside pictures).

Placeholders for the AI picture library (Addendum 5 §4). Palette keys (`main`, `leaf`, …) let puzzles
recolor a picture (spot-the-difference edits) without touching the drawing.
"""

from __future__ import annotations

import math

from qamra_workbook.pictures.model import (
    Part,
    Picture,
    body,
    c,
    cheeks,
    e,
    eyes,
    glint,
    ink,
    line,
    p,
    rect,
    scallop_d,
    shine,
)

RED = "#E5604E"
CORAL = "#EE8A6E"
ORANGE = "#F39A3D"
YELLOW = "#F7C84A"
GOLD = "#F2B33D"
LEAF = "#7DB46C"
LEAF_DARK = "#5E9651"
SKY = "#8EC1EC"
TEAL = "#4FA89A"
SKY_LIGHT = "#E3F0FB"
BLUE = "#5E86D6"
LAVENDER = "#A99BD6"
PURPLE = "#9376CF"
PINK = "#F4A6B8"
PINK_DEEP = "#E97A98"
BROWN = "#A8734D"
TAN = "#E3B982"
CREAM = "#FFF4DC"
WHITE = "#FFFFFF"
GRAY = "#CFD2DC"
SLATE = "#6E6A7A"


def _fmt(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".")


def _polar(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def scallop(cx: float, cy: float, rx: float, ry: float, bumps: int, bulge: float = 0.62) -> str:
    """A cloud-like closed outline: `bumps` arcs around an ellipse (lion mane, sheep fleece)."""
    return p(scallop_d(cx, cy, rx, ry, bumps, bulge))


def star_path(cx: float, cy: float, outer: float, inner: float, points: int = 5) -> str:
    pts = [_polar(cx, cy, outer if i % 2 == 0 else inner, -90 + 180 * i / points) for i in range(2 * points)]
    return p("M" + " L".join(f"{_fmt(x)} {_fmt(y)}" for x, y in pts) + " Z")


def _rays(cx: float, cy: float, r0: float, r1: float, n: int = 8, half: float = 9) -> str:
    out = []
    for i in range(n):
        a = 360 * i / n
        (x1, y1), (x2, y2), (x3, y3) = (
            _polar(cx, cy, r0, a - half),
            _polar(cx, cy, r1, a),
            _polar(cx, cy, r0, a + half),
        )
        out.append(p(f"M{_fmt(x1)} {_fmt(y1)} L{_fmt(x2)} {_fmt(y2)} L{_fmt(x3)} {_fmt(y3)} Z"))
    return "".join(out)


def _face(y: float, dx: float = 9, r: float = 3.4, cheek_dx: float = 15) -> tuple[Part, ...]:
    """Eyes, a small smile and cheeks centred on x = 50."""
    return (
        *eyes((50 - dx, y), (50 + dx, y), r),
        line(p(f"M{50 - 5} {y + 8} Q50 {y + 13} {50 + 5} {y + 8}")),
        cheeks((50 - cheek_dx, y + 7), (50 + cheek_dx, y + 7), 4),
    )


def _pic(
    id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str
) -> tuple[str, Picture]:
    return id, Picture(id, ar, en, category, parts, palette)


_P = [
    _pic(
        "apple",
        "تُفّاحَة",
        "apple",
        "fruit",
        (
            body("stem", p("M47.5 30 L49 13 Q51 11 53 13 L52.5 30 Z")),
            body(
                "main",
                p(
                    "M50 29 C44 24 34 22 26 26 C15 32 13 48 17 60 C22 76 34 88 44 86 C47 85 49 84 50 84 "
                    "C51 84 53 85 56 86 C66 88 78 76 83 60 C87 48 85 32 74 26 C66 22 56 24 50 29 Z"
                ),
            ),
            body("leaf", p("M53 21 C57 10 71 8 80 12 C74 22 62 26 53 21 Z")),
            line(p("M56 19 C63 16 69 14 75 13")),
            shine(e(30, 46, 5, 9, 20)),
        ),
        main=RED,
        leaf=LEAF,
        stem=BROWN,
    ),
    _pic(
        "ball",
        "كُرَة",
        "ball",
        "toy",
        (
            body("main", c(50, 52, 35)),
            body("left", p("M50 17 A35 35 0 0 0 50 87 C33 72 33 32 50 17 Z")),
            body("right", p("M50 17 A35 35 0 0 1 50 87 C67 72 67 32 50 17 Z")),
            body("cap", e(50, 18.5, 6, 3.4)),
            shine(e(31, 38, 5, 9, 35)),
        ),
        main=YELLOW,
        left=RED,
        right=BLUE,
        cap=WHITE,
    ),
    _pic(
        "sun",
        "شَمْس",
        "sun",
        "sky",
        (
            body("ray", _rays(50, 50, 30, 46)),
            body("main", c(50, 50, 27)),
            *_face(46, dx=9, cheek_dx=15),
        ),
        main=YELLOW,
        ray=ORANGE,
    ),
    _pic(
        "cloud",
        "غَيْمَة",
        "cloud",
        "sky",
        (
            body(
                "main",
                p(
                    "M24 72 C12 72 8 58 17 51 C14 38 28 30 38 36 C42 24 60 20 68 31 C78 27 90 36 86 48 "
                    "C95 52 94 72 80 72 Z"
                ),
            ),
            shine(e(38, 46, 9, 4, -12)),
        ),
        main=SKY_LIGHT,
    ),
    _pic(
        "raindrop",
        "قَطْرَة",
        "raindrop",
        "sky",
        (
            body(
                "main",
                p("M50 10 C44 24 26 42 26 60 C26 75 37 86 50 86 C63 86 74 75 74 60 C74 42 56 24 50 10 Z"),
            ),
            shine(e(39, 58, 4, 9, 15)),
        ),
        main=SKY,
    ),
    _pic(
        "flower",
        "زَهْرَة",
        "flower",
        "plant",
        (
            body("stem", p("M48.3 50 L48.3 93 L51.7 93 L51.7 50 Z")),
            body(
                "leaf",
                p("M50 82 C40 68 26 70 21 74 C29 84 42 86 50 82 Z"),
                p("M50 74 C60 62 74 62 79 66 C71 76 58 78 50 74 Z"),
            ),
            body("main", *(c(*_polar(50, 36, 16, a), 11) for a in range(-90, 270, 60))),
            body("center", c(50, 36, 9.5)),
            *eyes((46.5, 35), (53.5, 35), 1.7),
        ),
        main=PINK_DEEP,
        center=YELLOW,
        leaf=LEAF,
        stem=LEAF_DARK,
    ),
    _pic(
        "butterfly",
        "فَراشَة",
        "butterfly",
        "insect",
        (
            body(
                "main",
                p("M50 48 C40 22 17 14 11 27 C5 40 20 54 50 52 Z"),
                p("M50 48 C60 22 83 14 89 27 C95 40 80 54 50 52 Z"),
            ),
            body(
                "second",
                p("M50 52 C33 54 19 64 23 77 C27 87 44 81 50 58 Z"),
                p("M50 52 C67 54 81 64 77 77 C73 87 56 81 50 58 Z"),
            ),
            body("spot", c(27, 33, 5.5), c(73, 33, 5.5), c(33, 71, 3.6), c(67, 71, 3.6)),
            line(p("M48 36 C45 26 40 21 35 19"), p("M52 36 C55 26 60 21 65 19")),
            ink(c(35, 19, 2.4), c(65, 19, 2.4)),
            body("body", e(50, 55, 4.6, 20)),
        ),
        main=LAVENDER,
        second=PINK,
        spot=YELLOW,
        body=SLATE,
    ),
    _pic(
        "rabbit",
        "أَرْنَب",
        "rabbit",
        "animal",
        (
            body("main", e(37, 27, 8.5, 21, -8), e(63, 27, 8.5, 21, 8)),
            body("inner", e(37, 29, 4, 13, -8), e(63, 29, 4, 13, 8)),
            body("main", e(50, 63, 29, 25)),
            *eyes((40, 58), (60, 58), 3.4),
            body("inner", p("M46.5 66 Q50 63.5 53.5 66 Q50 70.5 46.5 66 Z")),
            line(p("M50 70 L50 73 M50 73 Q46 77 43 74 M50 73 Q54 77 57 74")),
            line(p("M31 67 L21 65 M31 71 L21 72 M69 67 L79 65 M69 71 L79 72")),
            cheeks((34, 69), (66, 69), 4),
        ),
        main="#E6DCD2",
        inner=PINK,
    ),
    _pic(
        "carrot",
        "جَزَرَة",
        "carrot",
        "vegetable",
        (
            body(
                "leaf",
                p("M50 30 C43 18 35 11 28 13 C32 21 41 28 50 30 Z"),
                p("M50 30 C49 16 53 7 58 6 C61 14 57 25 50 30 Z"),
                p("M50 30 C58 20 68 15 75 19 C69 27 59 31 50 30 Z"),
            ),
            body(
                "main",
                p("M35 32 C43 26 58 26 65 33 C69 39 61 60 53 84 C52 88 48 88 47 85 C39 62 30 39 35 32 Z"),
            ),
            line(p("M41 43 L48 44"), p("M55 53 L61 52"), p("M45 63 L51 64")),
            shine(e(42, 50, 2.5, 7, -15)),
        ),
        main=ORANGE,
        leaf=LEAF,
    ),
    _pic(
        "car",
        "سَيّارَة",
        "car",
        "vehicle",
        (
            body(
                "main",
                p(
                    "M9 66 L9 55 C9 50 12 48 17 47 L28 45 L38 30 C40 27 43 26 46 26 L66 26 "
                    "C70 26 73 28 75 31 L84 45 C89 46 92 49 92 54 L92 66 C92 69 90 70 87 70 L13 70 "
                    "C11 70 9 68 9 66 Z"
                ),
            ),
            body(
                "glass",
                p("M44 32 L37 45 L52 45 L52 32 Z"),
                p("M57 32 L57 45 L78 45 L71 33.5 C70 32.5 69 32 67 32 Z"),
            ),
            line(p("M54.5 48 L54.5 64"), p("M58.5 53 L63 53")),
            body("light", e(88, 55, 2.6, 3.6)),
            body("tire", c(28, 70, 11), c(74, 70, 11)),
            body("hub", c(28, 70, 4.5), c(74, 70, 4.5)),
            shine(p("M15 52 L30 50 L30 53 L15 55 Z")),
        ),
        main=CORAL,
        glass=SKY_LIGHT,
        light=YELLOW,
        tire=SLATE,
        hub=GRAY,
    ),
    _pic(
        "house",
        "بَيْت",
        "house",
        "home",
        (
            body("chimney", rect(64, 20, 10, 20, 1.5)),
            body("wall", rect(20, 50, 60, 40, 3)),
            body("roof", p("M11 51 L50 17 L89 51 C91 53 89 56 86 56 L14 56 C11 56 9 53 11 51 Z")),
            body("door", p("M42 90 L42 73 C42 66 58 66 58 73 L58 90 Z")),
            ink(c(54, 80, 1.6)),
            body("glass", rect(26, 62, 11, 11, 2), rect(63, 62, 11, 11, 2)),
            line(p("M31.5 62 L31.5 73 M26 67.5 L37 67.5 M68.5 62 L68.5 73 M63 67.5 L74 67.5")),
        ),
        wall=CREAM,
        roof=RED,
        chimney=BROWN,
        door=BROWN,
        glass=SKY_LIGHT,
    ),
    _pic(
        "tree",
        "شَجَرَة",
        "tree",
        "plant",
        (
            body("trunk", p("M44 90 L46 58 L54 58 L56 90 Z")),
            body(
                "main",
                p(
                    "M30 66 C16 66 11 48 21 41 C17 27 31 16 43 22 C49 10 70 11 72 25 C85 25 91 42 83 50 "
                    "C89 60 81 71 69 67 C63 73 49 73 45 67 C40 70 34 69 30 66 Z"
                ),
            ),
            body("fruit", c(35, 45, 4), c(62, 33, 4), c(66, 55, 4), c(47, 58, 3.6)),
            shine(e(36, 30, 6, 3.5, -25)),
        ),
        main=LEAF,
        trunk=BROWN,
        fruit=RED,
    ),
    _pic(
        "star",
        "نَجْمَة",
        "star",
        "sky",
        (body("main", star_path(50, 54, 42, 19)), *_face(52, dx=7, r=2.8, cheek_dx=11)),
        main=YELLOW,
    ),
    _pic(
        "heart",
        "قَلْب",
        "heart",
        "shape",
        (
            body(
                "main",
                p(
                    "M50 85 C36 75 12 61 12 38 C12 24 24 16 35 16 C43 16 48 21 50 26 C52 21 57 16 65 16 "
                    "C76 16 88 24 88 38 C88 61 64 75 50 85 Z"
                ),
            ),
            shine(e(28, 34, 5, 8, 30)),
        ),
        main=PINK_DEEP,
    ),
    _pic(
        "fish",
        "سَمَكَة",
        "fish",
        "animal",
        (
            body("fin", p("M40 37 C43 25 56 24 61 34 Z")),
            body("fin", p("M71 50 L89 34 C91 32.5 94 34 93 37 L88 50 L93 63 C94 66 91 67.5 89 66 Z")),
            body("main", p("M11 50 C21 30 54 26 74 42 C78 45 78 55 74 58 C54 74 21 70 11 50 Z")),
            line(p("M45 43 Q50 50 45 57"), p("M56 44 Q61 50 56 56")),
            ink(c(27, 46, 3.8)),
            glint(c(28.3, 44.5, 1.4)),
            line(p("M14 54 Q18 56 21 53")),
            shine(e(36, 60, 7, 2.5, -8)),
        ),
        main=ORANGE,
        fin=YELLOW,
    ),
    _pic(
        "cat",
        "قِطَّة",
        "cat",
        "animal",
        (
            body(
                "main",
                p("M21 46 L23 13 C24 10 27 9.5 29 11.5 L47 30 Z"),
                p("M79 46 L77 13 C76 10 73 9.5 71 11.5 L53 30 Z"),
            ),
            body("inner", p("M26.5 37 L27.5 19 L39 30.5 Z"), p("M73.5 37 L72.5 19 L61 30.5 Z")),
            body("main", e(50, 59, 34, 28)),
            line(p("M44 33 L45 39"), p("M50 32 L50 38.5"), p("M56 33 L55 39")),
            *eyes((38, 56), (62, 56), 4),
            body("inner", p("M46 64.5 L54 64.5 L50 69 Z")),
            line(p("M50 69 Q46 74 42 71 M50 69 Q54 74 58 71")),
            line(p("M27 64 L13 61 M27 69 L13 70 M73 64 L87 61 M73 69 L87 70")),
            cheeks((31, 67), (69, 67), 4.2),
        ),
        main="#F4A259",
        inner=PINK,
    ),
    _pic(
        "duck",
        "بَطَّة",
        "duck",
        "animal",
        (
            body(
                "main",
                p(
                    "M30 57 C31 47 39 42 48 45 C56 48 63 50 72 44 C80 39 89 44 87 55 C85 72 68 83 50 83 "
                    "C36 83 25 75 25 64 C25 61 27 58 30 57 Z"
                ),
            ),
            body("main", c(36, 36, 16.5)),
            body("beak", p("M22 38 C14 37.5 7 40.5 9.5 44.5 C12 48 20 47 24.5 44 Z")),
            body("wing", p("M50 60 C56 55 69 55 73 61 C71 69 61 73 53 69 C49 66 48 62 50 60 Z")),
            ink(c(33, 33, 3.4)),
            glint(c(34.3, 31.6, 1.3)),
            cheeks((39.5, 42), (39.5, 42), 3.4),
        ),
        main=YELLOW,
        beak=ORANGE,
        wing="#F9DC7C",
    ),
    _pic(
        "bird",
        "عُصْفور",
        "bird",
        "animal",
        (
            body("second", p("M75 50 L92 41 C94 40 95.5 42 94.5 44 L86 60 Z")),
            line(p("M46 79 L44 89 M56 80 L56 90")),
            body("main", e(52, 56, 28, 24)),
            body("belly", e(45, 65, 15, 10)),
            body("second", p("M52 54 C60 47 74 49 77 58 C71 66 58 66 52 62 C49 60 49 56 52 54 Z")),
            body("beak", p("M26 47 L13 52 L26 56 Z")),
            ink(c(36, 46, 3.5)),
            glint(c(37.3, 44.6, 1.3)),
            cheeks((40, 54), (40, 54), 3.4),
        ),
        main=SKY,
        second=BLUE,
        belly=SKY_LIGHT,
        beak=ORANGE,
    ),
    _pic(
        "umbrella",
        "مِظَلَّة",
        "umbrella",
        "home",
        (
            line(p("M50 45 L50 80 C50 89 39 89 39 81")),
            body(
                "main",
                p(
                    "M9 49 C11 26 29 11 50 11 C71 11 89 26 91 49 C86 45 79 45 74 49 C69 45 61 45 56 49 "
                    "C53 46 47 46 44 49 C39 45 31 45 26 49 C21 45 14 45 9 49 Z"
                ),
            ),
            body("second", p("M50 11 C41 22 39 37 44 49 C47 46 53 46 56 49 C61 37 59 22 50 11 Z")),
            body("second", c(50, 10, 2.8)),
            shine(p("M22 36 C24 28 30 22 36 19 C32 25 29 31 28 37 Z")),
        ),
        main=PURPLE,
        second=YELLOW,
    ),
    _pic(
        "lion",
        "أَسَد",
        "lion",
        "animal",
        (
            body("mane", scallop(50, 52, 40, 38, 13)),
            body("main", c(30, 31, 7.5), c(70, 31, 7.5)),
            body("inner", c(30, 31, 3.6), c(70, 31, 3.6)),
            body("main", c(50, 54, 26)),
            *eyes((41, 49), (59, 49), 3.4),
            body("muzzle", e(50, 64, 11.5, 8.5)),
            ink(p("M45 58.5 L55 58.5 L50 63.5 Z")),
            line(p("M50 63.5 L50 67 M50 67 Q46 71 43 68 M50 67 Q54 71 57 68")),
            cheeks((34, 60), (66, 60), 4),
        ),
        main=YELLOW,
        mane=ORANGE,
        inner=CORAL,
        muzzle=CREAM,
    ),
    _pic(
        "garden",
        "حَديقَة",
        "garden",
        "place",
        (
            body(
                "bush",
                p("M3 91 C-1 77 9 64 20 70 C22 57 37 59 37 70 L37 91 Z"),
                p("M97 91 C101 77 91 64 80 70 C78 57 63 59 63 70 L63 91 Z"),
            ),
            body("gate", rect(38, 45, 5, 46, 1.5), rect(47.5, 42, 5, 49, 1.5), rect(57, 45, 5, 46, 1.5)),
            body("gate", rect(36, 55, 28, 4.5, 1.5), rect(36, 77, 28, 4.5, 1.5)),
            body(
                "leaf", p("M25 91 L25 38 C25 8 75 8 75 38 L75 91 L65 91 L65 38 C65 21 35 21 35 38 L35 91 Z")
            ),
            body("flower", c(30, 50, 3.4), c(33, 26, 3.4), c(50, 15.5, 3.4), c(67, 26, 3.4), c(70, 50, 3.4)),
            body("flower2", c(29, 70, 3.4), c(40, 18, 3.4), c(60, 18, 3.4), c(71, 70, 3.4)),
            body("flower", c(12, 75, 4), c(23, 66, 3.4), c(88, 75, 4), c(77, 66, 3.4)),
            line(p("M1 91 L99 91")),
        ),
        leaf=LEAF_DARK,
        bush=LEAF,
        gate=WHITE,
        flower=PINK_DEEP,
        flower2=YELLOW,
    ),
    _pic(
        "boat",
        "قارِب",
        "boat",
        "vehicle",
        (
            body("wood", rect(48, 13, 4, 52, 1.5)),
            body("flag", p("M52 13 L52 5 L64 9 Z")),
            body("sail", p("M55 17 L55 58 L83 58 C81 44 71 26 55 17 Z")),
            body("sail2", p("M45 25 L45 58 L23 58 C27 44 35 32 45 25 Z")),
            body("main", p("M13 63 L87 63 C85 74 77 80 67 80 L33 80 C23 80 15 74 13 63 Z")),
            body(
                "water",
                p(
                    "M4 83 C12 77 20 77 28 83 C36 77 44 77 52 83 C60 77 68 77 76 83 C84 77 92 77 96 83 "
                    "L96 93 L4 93 Z"
                ),
            ),
        ),
        main=RED,
        wood=BROWN,
        sail=WHITE,
        sail2=YELLOW,
        flag=CORAL,
        water=SKY,
    ),
    _pic(
        "cup",
        "كوب",
        "cup",
        "home",
        (
            line(p("M40 24 C36 18 44 14 40 8"), p("M56 24 C52 18 60 14 56 8")),
            body("main", p("M70 40 C87 40 89 67 70 69 L70 62 C80 60 80 47 70 47 Z")),
            body("main", p("M21 32 L79 32 L74.5 80 C74 85 70 88 65 88 L35 88 C30 88 26 85 25.5 80 Z")),
            body("drink", e(50, 32, 29, 5)),
            body(
                "deco",
                p(
                    "M50 71 C44 67 40 63 40 58.5 C40 54.5 44 52.5 47 54.5 C48 55.5 49 56.5 50 57.5 "
                    "C51 56.5 52 55.5 53 54.5 C56 52.5 60 54.5 60 58.5 C60 63 56 67 50 71 Z"
                ),
            ),
        ),
        main=TEAL,
        drink=BROWN,
        deco=CREAM,
    ),
    _pic(
        "sheep",
        "خَروف",
        "sheep",
        "animal",
        (
            body("dark", rect(33, 64, 6.5, 22, 3), rect(45, 67, 6.5, 19, 3), rect(62, 67, 6.5, 19, 3)),
            body("dark", rect(73, 64, 6.5, 22, 3)),
            body("main", scallop(57, 54, 30, 19, 12, bulge=0.6)),
            body("dark", e(26, 46, 12, 14, -15)),
            body("dark", e(35, 36, 7, 3.6, -35)),
            body("main", scallop(29, 33, 8, 5, 6, bulge=0.65)),
            body("eye", c(22, 45, 3.4), c(30.5, 43.5, 3.4)),
            ink(c(22.4, 45.4, 1.8), c(30.9, 43.9, 1.8)),
            line(p("M21 54 Q25 57 29 53")),
        ),
        main="#FBF6EA",
        dark=SLATE,
        eye=WHITE,
    ),
    _pic(
        "cow",
        "بَقَرَة",
        "cow",
        "animal",
        (
            body(
                "horn",
                p("M31 27 C23 23 19 15 23 10 C27 16 33 18 37 21 Z"),
                p("M69 27 C77 23 81 15 77 10 C73 16 67 18 63 21 Z"),
            ),
            body("main", e(17, 40, 11, 6, -20), e(83, 40, 11, 6, 20)),
            body("inner", e(17, 40, 5.5, 3, -20), e(83, 40, 5.5, 3, 20)),
            body("main", p("M24 44 C24 26 34 19 50 19 C66 19 76 26 76 44 L76 62 L24 62 Z")),
            body("spot", p("M29 29 C35 25 43 29 41 37 C39 43 30 43 28 37 Z")),
            body("spot", p("M61 23 C68 23 72 29 69 34 C65 37 60 32 61 23 Z")),
            *eyes((40, 45), (60, 45), 3.4),
            body("snout", e(50, 67, 23, 15)),
            ink(e(43, 67, 2.8, 3.6), e(57, 67, 2.8, 3.6)),
        ),
        main=WHITE,
        spot=SLATE,
        horn=CREAM,
        inner=PINK,
        snout=PINK,
    ),
    _pic(
        "dog",
        "كَلْب",
        "dog",
        "animal",
        (
            body(
                "ear",
                p("M27 30 C14 27 7 44 11 60 C13 67 22 67 26 58 Z"),
                p("M73 30 C86 27 93 44 89 60 C87 67 78 67 74 58 Z"),
            ),
            body("main", e(50, 51, 27, 27)),
            body("ear", p("M57 38 C65 33 74 41 71 50 C67 55 58 51 57 38 Z")),
            *eyes((40, 49), (61, 49), 3.4),
            body("muzzle", e(50, 65, 13.5, 10)),
            ink(e(50, 60, 5.2, 3.8)),
            body("tongue", p("M46.5 69 C46.5 77 53.5 77 53.5 69 Z")),
            line(p("M50 63.5 L50 67.5 M50 67.5 Q46 71 42.5 68 M50 67.5 Q54 71 57.5 68")),
        ),
        main=TAN,
        ear=BROWN,
        muzzle=CREAM,
        tongue=PINK_DEEP,
    ),
    _pic(
        "bee",
        "نَحْلَة",
        "bee",
        "insect",
        (
            body("wing", e(47, 30, 10, 15, -18), e(64, 31, 9, 13, 22)),
            body("stripe", p("M77 55 L87 58 L77 61.5 Z")),
            body("main", e(50, 58, 28, 20)),
            body(
                "stripe",
                p("M46 38.2 L54 38.2 L54 77.8 L46 77.8 Z"),
                p("M61 39.3 L67.5 42.4 L67.5 73.6 L61 76.7 Z"),
            ),
            line(p("M29 44 C25 34 21 32 16 32"), p("M35 41 C35 31 32 27 28 25")),
            ink(c(16, 32, 2.4), c(28, 25, 2.4)),
            ink(c(32, 54, 3.2)),
            glint(c(33.2, 52.7, 1.2)),
            line(p("M28 63 Q32 66 36 63")),
        ),
        main=YELLOW,
        stripe=SLATE,
        wing=SKY_LIGHT,
    ),
    _pic(
        "banana",
        "مَوْزَة",
        "banana",
        "fruit",
        (
            body(
                "main",
                p("M20 30 C20 60 40 82 72 80 C82 79 88 74 86 70 C66 74 44 62 34 30 C32 24 22 24 20 30 Z"),
            ),
            body("tip", p("M20.5 29 C19 23 22 19 27 19 C31 20 32 25 31 28 Z")),
            body("tip", p("M86 70 C90 72 90.5 78 86.5 79.5 L81 80 Z")),
            line(p("M27 36 C31 56 45 70 66 75")),
            shine(e(28, 45, 2.5, 8, -20)),
        ),
        main="#F9D55B",
        tip=BROWN,
    ),
    _pic(
        "strawberry",
        "فَراوْلَة",
        "strawberry",
        "fruit",
        (
            body(
                "main",
                p("M50 88 C34 80 18 60 20 42 C22 30 34 28 50 32 C66 28 78 30 80 42 C82 60 66 80 50 88 Z"),
            ),
            ink(
                *(
                    e(x, y, 1.3, 2)
                    for x, y in (
                        (34, 45),
                        (46, 44),
                        (58, 45),
                        (68, 48),
                        (30, 57),
                        (41, 56),
                        (53, 56),
                        (65, 58),
                        (38, 68),
                        (50, 68),
                        (61, 69),
                        (47, 79),
                    )
                )
            ),
            body(
                "leaf",
                p(
                    "M50 37 C44 31 36 28 29 30 C35 34 40 36 44 38 C40 40 37 44 37 47 C44 45 48 41 50 39 "
                    "C52 41 56 45 63 47 C63 44 60 40 56 38 C60 36 65 34 71 30 C64 28 56 31 50 37 Z"
                ),
            ),
            body("leaf", rect(48, 22, 4, 14, 2)),
            shine(e(30, 50, 2.5, 6, 15)),
        ),
        main=RED,
        leaf=LEAF,
    ),
    _pic(
        "balloon",
        "بالون",
        "balloon",
        "toy",
        (
            line(p("M50 78 C45 85 55 89 48 97")),
            body(
                "main",
                p("M50 76 C30 72 20 54 22 38 C24 22 36 12 50 12 C64 12 76 22 78 38 C80 54 70 72 50 76 Z"),
            ),
            body("main", p("M45.5 81 L50 75.5 L54.5 81 Z")),
            shine(e(36, 32, 5, 9, 25)),
        ),
        main=CORAL,
    ),
    _pic(
        "moon",
        "قَمَر",
        "moon",
        "sky",
        (
            body(
                "main",
                p(
                    "M60 10 C38 12 22 30 22 52 C22 74 40 91 62 90 C70 90 77 87 83 82 C64 83 47 68 47 48 "
                    "C47 32 56 18 69 11 C66 10 63 10 60 10 Z"
                ),
            ),
            ink(c(33, 50, 3)),
            glint(c(34, 48.8, 1.1)),
            line(p("M31 60 Q35 64 39 61")),
            cheeks((37, 56), (37, 56), 3.2),
        ),
        main=GOLD,
    ),
    _pic(
        "door",
        "باب",
        "door",
        "home",
        (
            body("frame", p("M23 92 L23 30 C23 13 77 13 77 30 L77 92 Z")),
            body("main", p("M30 92 L30 32 C30 20 70 20 70 32 L70 92 Z")),
            body("panel", p("M36 50 L36 36 C36 29 64 29 64 36 L64 50 Z"), rect(36, 58, 28, 26, 3)),
            body("knob", c(62, 69, 3.2)),
            body("frame", rect(16, 90, 68, 6, 2.5)),
        ),
        main="#5FA8A0",
        panel="#8CC5BE",
        frame=TAN,
        knob=YELLOW,
    ),
    _pic(
        "leaf",
        "وَرَقَة",
        "leaf",
        "plant",
        (
            body("main", p("M17 83 C13 50 34 19 85 15 C87 58 60 84 17 83 Z")),
            line(
                p("M17 83 C38 62 56 44 75 26"),
                p("M35 65 L33 51 M46 54 L46 40 M57 44 L59 32 M39 61 L53 63 M50 50 L64 52"),
            ),
        ),
        main=LEAF,
    ),
]

PICTURES: dict[str, Picture] = dict(_P)
