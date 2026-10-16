"""Kitchen, market and home pictures for «مغامراتي مع عائلتي» (Addendum 7): food to count and choose, the
recipe's ingredients, round things to hunt in the kitchen. Same house style as `icons.py` (flat colors,
one outline weight, no text), so they recolor, turn into line art and mix with the vocabulary pictures.
"""

from __future__ import annotations

import math

from qamra_workbook.pictures.family_more import FAMILY_MORE
from qamra_workbook.pictures.icons import (
    BLUE,
    BROWN,
    CREAM,
    GRAY,
    LEAF,
    LEAF_DARK,
    ORANGE,
    PINK,
    PINK_DEEP,
    PURPLE,
    RED,
    SKY,
    SKY_LIGHT,
    SLATE,
    TAN,
    WHITE,
)
from qamra_workbook.pictures.model import (
    Part,
    Picture,
    body,
    c,
    e,
    glint,
    ink,
    line,
    p,
    rect,
    scallop_d,
    shine,
    tint,
)

OIL = "#D9BE3A"
OLIVE = "#6F8F2F"
ZAATAR = "#7E8F3C"
SUMAC = "#A13B2F"
BOWL_BLUE = "#4F8BC9"
TERRACOTTA = "#D98A5F"


def _pic(
    id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str
) -> tuple[str, Picture]:
    return id, Picture(id, ar, en, category, parts, palette)


_BOWL = "M12 52 L88 52 C88 74 71 88 50 88 C29 88 12 74 12 52 Z"
_MOUND = "M18 52 C22 36 37 29 50 30 C63 29 78 36 82 52 Z"
_SESAME = ((34, 46, 20), (43, 40, -30), (52, 44, 40), (60, 39, -10), (67, 46, 30), (47, 49, 0), (28, 50, -40))
# the labneh spread on its plate: a soft, slightly uneven round (a scalloped edge read as rice)
_SPREAD = (
    "M16 56 C16 49 20 46.5 25 45.5 S36 42.5 42 42.5 S58 42 63 43.5 S75 48 76 54 S73 64.5 66 67 "
    "S52 70 46 70 S30 69 24 66.5 S16 61 16 56 Z"
)
_GLASS_FOOT = "L86 88 C86 89.6 85 90.5 83.4 90.5 L69.6 90.5 C68 90.5 67 89.6 67 88 Z"  # the milk glass
_RIM = tuple((math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 30))
_GRAPES = (
    (29, 32),
    (43, 30),
    (57, 30),
    (71, 32),
    (36, 45),
    (50, 44),
    (64, 45),
    (43, 58),
    (57, 58),
    (50, 71),
)

_H = [
    _pic(  # labneh as it is served at home: spread on a plate, a spoon's swirl, olive oil in the middle,
        # mint and olives on the side (the old bowl with a white mound read as yogurt or rice)
        "labneh",
        "لَبْنَة",
        "labneh",
        "food",
        (
            body("plate", e(50, 60, 46, 26)),
            body("well", e(50, 61, 37, 19)),
            body("side", f'<path d="{_SPREAD}" transform="translate(0 3.5)"/>'),
            body("main", p(_SPREAD)),
            line(
                p("M54.5 56.5 A8.5 4.2 0 0 0 37.5 56.5 A12.5 6.2 0 0 0 62.5 56.5 A17 8.4 0 0 0 28.5 56.5"),
            ),
            body(
                "oil",
                p(
                    "M37 56.5 C37 52.5 43 51.5 47 51.8 C52 52 56 53.5 55.5 56.5 C55 59.5 50 60.5 45.5 60.3 "
                    "C40.5 60 37 59 37 56.5 Z"
                ),
            ),
            shine(e(42.5, 54.6, 3.2, 1.2)),
            body("olive", e(80, 67, 5.2, 4, 20), e(72, 75, 5.2, 4, -15)),
            glint(c(78.3, 65.6, 1.2), c(70.3, 73.8, 1.2)),
            body("leaf", p("M58 47 C60 40 68 37 73 39 C71 45 64 49 58 47 Z")),
            body("leaf", p("M57 47 C52 41 54 35 58 33 C61 38 61 43 57 47 Z")),
            shine(e(24, 52, 3, 7, 60)),
        ),
        plate=BOWL_BLUE,
        well="#DCEBF7",
        side="#E9E1CC",
        main="#FFFDF7",
        oil=OIL,
        olive=OLIVE,
        leaf=LEAF,
    ),
    _pic(
        "olive-oil",
        "زَيْت زَيْتون",
        "olive oil",
        "food",
        (
            body("cork", rect(42, 7, 16, 9, 2.5)),
            body(
                "glass",
                p(
                    "M44 15 L56 15 L56 27 C56 33 70 37 70 50 L70 84 C70 88 66 91 62 91 L38 91 C34 91 30 88 "
                    "30 84 L30 50 C30 37 44 33 44 27 Z"
                ),
            ),
            body(
                "main",
                p("M31.5 50 L68.5 50 L68.5 84 C68.5 87 66 89.5 62 89.5 L38 89.5 C34 89.5 31.5 87 31.5 84 Z"),
            ),
            body("label", rect(36, 58, 28, 22, 3)),
            line(p("M42 76 C46 71 53 67 59 64")),
            body("olive", e(46, 69, 4.6, 3.3, -25), e(54.5, 66.5, 4, 2.9, 25)),
            shine(rect(34.5, 36, 3.5, 44, 1.75)),
        ),
        cork=BROWN,
        glass="#EEF5E4",
        main=OIL,
        label=CREAM,
        olive=OLIVE,
    ),
    _pic(
        "zaatar",
        "زَعْتَر",
        "zaatar",
        "food",
        (
            body("bowl", p(_BOWL)),
            body("main", p(_MOUND)),
            glint(*(e(x, y, 1.9, 1.1, r) for x, y, r in _SESAME)),
            tint(SUMAC, c(38, 44, 1.3), c(56, 40, 1.3), c(63, 44, 1.3), c(33, 48, 1.2), c(50, 47, 1.2)),
            line(p("M63 31 C67 25 72 21 79 18")),
            body("leaf", e(67, 26, 3.4, 1.9, -40), e(72, 21.5, 3.2, 1.8, -35), e(77, 18.5, 2.8, 1.6, -25)),
            shine(e(24, 64, 3, 6, 25)),
        ),
        bowl=TERRACOTTA,
        main=ZAATAR,
        leaf=LEAF_DARK,
    ),
    _pic(  # a crusty loaf with its scores before a round of Arabic bread (a spotted oval read as a potato)
        "bread",
        "خُبْز",
        "bread",
        "food",
        (
            body("flat", e(42, 43, 34, 14)),
            tint("#B06A2E", e(26, 40, 4, 2, -8), e(46, 35, 5, 2.2, 6), e(62, 41, 4, 1.8, 0)),
            body(
                "main",
                p(
                    "M21 82 C16.5 82 14 79 14 75 L14 66 C14 53 29 46 50 46 C71 46 86 53 86 66 L86 75 "
                    "C86 79 83.5 82 79 82 Z"
                ),
            ),
            body("score", e(33, 59, 7.5, 2.4, -32), e(50, 56, 7.5, 2.4, -32), e(67, 59, 7.5, 2.4, -32)),
            line(p("M16 73 C35 77 65 77 84 73")),
            shine(e(30, 52, 9, 2.4, -12)),
        ),
        flat="#EBCB98",
        main="#C98A44",
        score="#F3D7A6",
    ),
    _pic(  # a carton with cow spots and a glass of white milk (a blue carton with a drop read as water)
        "milk",
        "حَليب",
        "milk",
        "drink",
        (
            body("cap", rect(43, 11, 8, 7, 2)),
            body("top", p("M28 18 L54 18 L60 33 L22 33 Z")),
            body("main", p("M22 33 L60 33 L60 86 C60 88.5 58 90 56 90 L26 90 C24 90 22 88.5 22 86 Z")),
            ink(
                p("M27 43 C30 39 37 40 38 44 C39 48 34 51 30 50 C27 49 25 46 27 43 Z"),
                p("M45 52 C49 49 56 51 56 56 C56 61 50 62 47 60 C44 58 43 55 45 52 Z"),
                p("M28 66 C31 63 36 65 35 69 C34 72 30 73 28 71 C26 70 26 68 28 66 Z"),
                p("M47 74 C50 72 55 74 54 78 C53 81 49 81 47 79 C46 78 46 76 47 74 Z"),
            ),
            body("glass", p(f"M64 46 L89 46 {_GLASS_FOOT}")),
            body("main", p(f"M64.8 57 L88.2 57 {_GLASS_FOOT}")),
            shine(rect(26, 36, 3, 9, 1.5), rect(70, 60, 2.6, 24, 1.3)),
        ),
        cap=BLUE,
        top="#DCE9F7",
        main=WHITE,
        glass="#D5E4F1",
    ),
    _pic(
        "candy",
        "حَلْوى",
        "candy",
        "sweet",
        (
            body("stick", rect(47, 55, 6, 38, 3)),
            body("main", c(50, 36, 26)),
            line(
                p(
                    "M50 36 C50 32.5 55.5 32.5 55.5 36.5 C55.5 42 46 43.5 43.5 37 C41 29.5 53.5 25 60 31 C67 "
                    "37.5 62 50 50 50.5 C37.5 51 30 40 34.5 29"
                )
            ),
            shine(e(37, 25, 4, 7, 35)),
        ),
        stick=WHITE,
        main=PINK_DEEP,
    ),
    _pic(
        "soda",
        "مَشْروب غازِيّ",
        "soda",
        "sweet",
        (
            body("lid", rect(37, 11, 26, 7, 3)),
            body(
                "main",
                p(
                    "M33 22 C33 18 36 16 40 16 L60 16 C64 16 67 18 67 22 L67 84 C67 88 64 90 60 90 L40 90 "
                    "C36 90 33 88 33 84 Z"
                ),
            ),
            body("band", p("M33 46 C42 52 58 40 67 46 L67 64 C58 58 42 70 33 64 Z")),
            glint(c(45, 30, 2.2), c(53, 25.5, 1.6), c(57, 33, 1.9)),
            shine(rect(38, 22, 3.5, 60, 1.75)),
        ),
        lid=GRAY,
        main=RED,
        band=WHITE,
    ),
    _pic(
        "orange",
        "بُرْتُقالَة",
        "orange",
        "fruit",
        (
            body("stem", rect(48, 18, 4, 9, 2)),
            body("main", c(50, 57, 33)),
            tint("#C8651A", c(38, 50, 1.3), c(56, 45, 1.3), c(64, 62, 1.3), c(46, 70, 1.3), c(70, 50, 1.2)),
            body("leaf", p("M52 25 C56 15 68 13 76 17 C71 26 60 29 52 25 Z")),
            line(p("M56 23 C62 20 67 18 72 18")),
            shine(e(36, 45, 5, 9, 25)),
        ),
        stem=BROWN,
        main=ORANGE,
        leaf=LEAF,
    ),
    _pic(
        "tomato",
        "بَنَدورَة",
        "tomato",
        "vegetable",
        (
            body(
                "main",
                p("M50 31 C72 28 88 42 88 60 C88 78 70 90 50 90 C30 90 12 78 12 60 C12 42 28 28 50 31 Z"),
            ),
            body(
                "leaf",
                p(
                    "M50 36 L41 29 L47 28 L45 21 L51 26 L57 20 L56 27 L63 27 L58 31 L67 35 L57 36 "
                    "L53 43 L50 37 L46 43 L43 36 L33 36 Z"
                ),
            ),
            shine(e(31, 52, 5, 9, 25)),
        ),
        main=RED,
        leaf=LEAF,
    ),
    _pic(  # a long, bent, striped cucumber with its bumps and a yellow flower at the tip (a smooth capsule
        # read as a pill)
        "cucumber",
        "خِيارَة",
        "cucumber",
        "vegetable",
        (
            body(
                "main",
                p(
                    "M14 78 C8 72 10 62 19 56 C33 47 47 36 60 25 C68 18 80 17 86 24 C91 31 88 39 80 44 "
                    "C66 53 51 65 36 76 C28 82 19 83 14 78 Z"
                ),
            ),
            tint(
                "#C9E59A",
                p("M20 68 C34 58 50 46 66 33 C68 32 69 34 67 35 C51 48 35 60 22 70 C20 71 19 69 20 68 Z"),
            ),
            ink(
                c(26, 63, 1.4),
                c(38, 56, 1.4),
                c(50, 47, 1.4),
                c(62, 38, 1.4),
                c(74, 30, 1.4),
                c(31, 72, 1.4),
                c(44, 64, 1.4),
                c(57, 54, 1.4),
                c(70, 44, 1.4),
            ),
            body("stem", p("M85 24 C88 20 90 17 93 16 C94 18 92 22 88 26 Z")),
            body("flower", p(scallop_d(15, 79, 6.5, 6.5, 5, 0.7))),
            body("heart", c(15, 79, 2.2)),
        ),
        main="#4F9A3A",
        stem=LEAF_DARK,
        flower="#F6D04D",
        heart="#E3A21A",
    ),
    _pic(
        "grapes",
        "عِنَب",
        "grapes",
        "fruit",
        (
            body("stem", p("M49 22 L50 11 L54 11 L53 22 Z")),
            body("leaf", p("M54 16 C60 6 73 6 80 11 C74 19 62 22 54 16 Z")),
            *(body("main", c(x, y, 8.6)) for x, y in _GRAPES),
            shine(*(e(x - 3, y - 3, 1.6, 2.6, 30) for x, y in _GRAPES[:7])),
        ),
        stem=BROWN,
        leaf=LEAF,
        main=PURPLE,
    ),
    _pic(
        "plate",
        "صَحْن",
        "plate",
        "home",
        (
            body("main", e(50, 55, 41, 31)),
            body("inner", e(50, 57, 27, 19)),
            tint("#4F8BC9", *(c(50 + 34 * x, 56 + 25 * y, 2) for x, y in _RIM)),
            shine(e(29, 44, 6, 3, -25)),
        ),
        main="#EEF3FA",
        inner=WHITE,
    ),
    _pic(
        "clock",
        "ساعَة",
        "clock",
        "home",
        (
            body("bell", c(28, 22, 8), c(72, 22, 8)),
            body("main", c(50, 56, 36)),
            body("face", c(50, 56, 28)),
            ink(
                rect(48.5, 30, 3, 6, 1.5),
                rect(48.5, 76, 3, 6, 1.5),
                rect(24, 54.5, 6, 3, 1.5),
                rect(70, 54.5, 6, 3, 1.5),
            ),
            line(p("M50 56 L50 40 M50 56 L62 63")),
            ink(c(50, 56, 3.2)),
            shine(e(31, 44, 4, 7, 30)),
        ),
        bell=RED,
        main=ORANGE,
        face=CREAM,
    ),
    _pic(
        "shopping-bag",
        "كيس التَّسَوُّق",
        "shopping bag",
        "home",
        (
            body("bread", p("M26 44 L40 12 C42 8 48 9 47 14 L38 44 Z")),
            body(
                "leaf",
                p("M52 44 C48 30 52 18 60 14 C64 24 62 34 58 44 Z"),
                p("M60 44 C62 32 70 24 78 24 C76 34 70 40 66 44 Z"),
            ),
            line(p("M34 44 C34 30 66 30 66 44")),
            body("main", p("M20 40 L80 40 L86 90 L14 90 Z")),
            body("fold", p("M20 40 L80 40 L79.2 48 L20.8 48 Z")),
            body(
                "heart",
                p(
                    "M50 76 C44 72 40 68 40 63.5 C40 59.5 44 57.5 47 59.5 C48 60.5 49 61.5 50 62.5 "
                    "C51 61.5 52 60.5 53 59.5 C56 57.5 60 59.5 60 63.5 C60 68 56 72 50 76 Z"
                ),
            ),
        ),
        bread=TAN,
        leaf=LEAF,
        main="#E8B06A",
        fold="#D6964C",
        heart=RED,
    ),
    _pic(
        "soap",
        "صابونَة",
        "soap",
        "home",
        (
            body("bubble", c(72, 30, 10), c(56, 20, 6.5), c(82, 13, 5.5), c(40, 32, 5)),
            shine(e(69, 26, 2.6, 4, 35), e(54.5, 18, 1.6, 2.6, 35)),
            body(
                "main",
                p(
                    "M16 60 C16 51 22 46 31 46 L71 46 C80 46 86 51 86 60 L86 74 C86 82 80 86 71 86 L31 86 "
                    "C22 86 16 82 16 74 Z"
                ),
            ),
            body("top", p("M24 55 C24 52 26 51 29 51 L73 51 C76 51 78 52 78 55 L78 61 L24 61 Z")),
        ),
        bubble=SKY_LIGHT,
        main=PINK,
        top="#F9C9D5",
    ),
    _pic(
        "kitchen",
        "مَطْبَخ",
        "kitchen",
        "home",
        (
            body("pot", p("M30 36 L30 25 C30 21 33 19 37 19 L63 19 C67 19 70 21 70 25 L70 36 Z")),
            body("pot", rect(22, 23, 9, 5, 2.5), rect(69, 23, 9, 5, 2.5)),
            body("lid", p("M28 20 C30 12 70 12 72 20 Z"), c(50, 11, 3)),
            body("top", rect(10, 36, 80, 8, 3)),
            body("main", rect(15, 44, 70, 48, 4)),
            body("knob", c(28, 52, 3.6), c(42, 52, 3.6), c(58, 52, 3.6), c(72, 52, 3.6)),
            body("window", rect(26, 61, 48, 24, 4)),
            line(p("M34 66 L42 66")),
            shine(e(40, 70, 6, 2.6, -20)),
        ),
        pot=RED,
        lid="#F08A7E",
        top=GRAY,
        main="#F4F1EA",
        knob=SLATE,
        window="#5A6078",
    ),
]

_H += [
    _pic(
        "stall",
        "بَسْطَة",
        "market stall",
        "place",
        (
            body("pole", rect(14, 30, 5, 58, 2), rect(81, 30, 5, 58, 2)),
            body("main", p("M8 32 L92 32 L88 18 C70 12 30 12 12 18 Z")),
            body(
                "stripe",
                p("M26 32 L30 15 L40 14 L38 32 Z"),
                p("M50 32 L50 13 L60 14 L62 32 Z"),
                p("M74 32 L70 15 L79 17 L86 32 Z"),
            ),
            body(
                "scallop",
                p(
                    "M8 32 Q13 40 18 32 Q23 40 29 32 Q34 40 40 32 Q45 40 50 32 Q55 40 61 32 "
                    "Q66 40 71 32 Q76 40 82 32 Q87 40 92 32 Z"
                ),
            ),
            body("crate", rect(10, 64, 80, 24, 3)),
            line(p("M10 76 L90 76"), p("M36 64 L36 88"), p("M64 64 L64 88")),
            body("apple", c(20, 60, 6), c(29, 61, 6)),
            body("orange", c(45, 60, 6), c(55, 61, 6)),
            body("banana", p("M68 62 C72 52 82 52 86 56 C80 57 74 60 70 66 Z")),
            shine(e(18, 58, 1.6, 2.6, 25), e(43, 58, 1.6, 2.6, 25)),
        ),
        pole=BROWN,
        main=RED,
        stripe=WHITE,
        scallop=RED,
        crate=TAN,
        apple=RED,
        orange=ORANGE,
        banana="#F7C84A",
    ),
    _pic(
        "basket",
        "سَلَّة",
        "basket",
        "home",
        (
            line(p("M24 52 C24 18 76 18 76 52")),
            body("main", p("M12 50 L88 50 L80 86 C79 89 76 90 73 90 L27 90 C24 90 21 89 20 86 Z")),
            body("rim", rect(9, 45, 82, 10, 5)),
            line(
                p("M22 62 L78 62"),
                p("M25 74 L75 74"),
                p("M38 55 L40 90"),
                p("M50 55 L50 90"),
                p("M62 55 L60 90"),
            ),
        ),
        main=TAN,
        rim=BROWN,
    ),
]

_H += [
    _pic(
        "gift",
        "هَدِيَّة",
        "gift",
        "toy",
        (
            body("main", rect(18, 38, 64, 50, 4)),
            body("lid", rect(13, 28, 74, 14, 4)),
            body("ribbon", rect(44, 28, 12, 60)),
            body(
                "ribbon",
                p("M50 28 C40 12 24 14 28 24 C31 30 42 30 50 28 Z"),
                p("M50 28 C60 12 76 14 72 24 C69 30 58 30 50 28 Z"),
            ),
            shine(rect(22, 45, 4, 36, 2)),
        ),
        main=BLUE,
        lid="#7FA2E8",
        ribbon=PINK_DEEP,
    ),
    _pic(
        "window",
        "شُبّاك",
        "window",
        "home",
        (
            body("frame", rect(16, 16, 68, 68, 5)),
            body(
                "glass",
                rect(23, 23, 25, 25, 2),
                rect(52, 23, 25, 25, 2),
                rect(23, 52, 25, 25, 2),
                rect(52, 52, 25, 25, 2),
            ),
            body("sill", rect(10, 82, 80, 7, 3)),
            shine(p("M27 42 L40 27 L44 27 L27 46 Z"), p("M56 71 L69 56 L73 56 L56 75 Z")),
        ),
        frame=WHITE,
        glass=SKY,
        sill=BROWN,
    ),
    _pic(
        "watermelon",
        "بَطّيخ",
        "watermelon",
        "fruit",
        (
            body("rind", p("M10 30 L90 30 L50 92 Z")),
            body("main", p("M18 36 L82 36 L50 84 Z")),
            ink(
                e(38, 46, 1.8, 2.8),
                e(55, 48, 1.8, 2.8),
                e(46, 60, 1.8, 2.8),
                e(62, 40, 1.8, 2.8),
                e(30, 40, 1.8, 2.8),
            ),
            shine(e(35, 42, 2, 5, -30)),
        ),
        rind=LEAF_DARK,
        main="#F2676E",
    ),
    _pic(
        "book",
        "كِتاب",
        "book",
        "home",
        (
            body("pages", rect(26, 14, 54, 74, 3)),
            body("main", rect(20, 10, 54, 76, 4)),
            body("band", rect(20, 22, 54, 8)),
            body(
                "star",
                p("M47 46 L50.5 53 L58 54 L52.5 59 L54 66.5 L47 63 L40 66.5 L41.5 59 L36 54 L43.5 53 Z"),
            ),
        ),
        pages=CREAM,
        main=PURPLE,
        band="#C9B6EE",
        star="#F7C84A",
    ),
]

HOUSEHOLD: dict[str, Picture] = dict(_H) | FAMILY_MORE  # and the whole book's (family_more.py)
