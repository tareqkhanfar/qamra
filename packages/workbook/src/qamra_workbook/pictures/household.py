"""Kitchen, market and home pictures for «مغامراتي مع عائلتي» (Addendum 7): food to count and choose, the
recipe's ingredients, round things to hunt in the kitchen. Same house style as `icons.py` (flat colors,
one outline weight, no text), so they recolor, turn into line art and mix with the vocabulary pictures.
"""

from __future__ import annotations

import math

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
    SKY_LIGHT,
    SLATE,
    TAN,
    WHITE,
)
from qamra_workbook.pictures.model import Part, Picture, body, c, e, glint, ink, line, p, rect, shine, tint

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
    _pic(
        "labneh",
        "لَبْنَة",
        "labneh",
        "food",
        (
            body("bowl", p(_BOWL)),
            body("main", p(_MOUND)),
            line(p("M33 45 C38 37 57 36 63 43"), p("M42 47 C46 42 53 42 57 46")),
            body("oil", p("M39 50 C45 47.5 55 47.5 61 50 C55 52 45 52 39 50 Z")),
            body("leaf", p("M60 33 C63 24 73 22 78 25 C75 32 67 35 60 33 Z")),
            glint(c(30, 68, 2.6), c(50, 76, 2.6), c(70, 68, 2.6), c(40, 63, 1.8), c(60, 63, 1.8)),
            shine(e(24, 64, 3, 6, 25)),
        ),
        bowl=BOWL_BLUE,
        main="#FFFBF0",
        oil=OIL,
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
    _pic(
        "bread",
        "خُبْز",
        "bread",
        "food",
        (
            body(
                "main",
                p("M10 58 C10 41 29 31 50 31 C71 31 90 41 90 58 C90 74 71 82 50 82 C29 82 10 74 10 58 Z"),
            ),
            line(p("M22 56 C30 47 70 47 78 56")),
            tint(
                "#B06A2E",
                e(33, 47, 5, 2.6, -10),
                e(60, 44, 6, 3, 8),
                e(70, 63, 5, 2.6, 0),
                e(40, 68, 6, 3, 5),
            ),
            shine(e(36, 40, 10, 3, -8)),
        ),
        main="#EBC285",
    ),
    _pic(
        "milk",
        "حَليب",
        "milk",
        "drink",
        (
            body("cap", rect(54, 10, 9, 8, 2)),
            body("top", p("M40 17 L60 17 L70 35 L30 35 Z")),
            body("main", p("M30 35 L70 35 L70 88 C70 90.5 68 92 66 92 L34 92 C32 92 30 90.5 30 88 Z")),
            body("band", rect(30, 50, 40, 27)),
            body(
                "drop", p("M50 54 C50 54 42.5 62.5 42.5 67 A7.5 7.5 0 0 0 57.5 67 C57.5 62.5 50 54 50 54 Z")
            ),
            shine(rect(35, 38, 3.5, 10, 1.75), rect(35, 80, 3.5, 8, 1.75)),
        ),
        cap=BLUE,
        top="#DCE9F7",
        main=WHITE,
        band="#7FB2E5",
        drop=WHITE,
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
    _pic(
        "cucumber",
        "خِيارَة",
        "cucumber",
        "vegetable",
        (
            body(
                "main",
                p(
                    "M17 75 C11 69 13 58 22 52 L65 22 C74 16 84 19 87 28 C89 36 85 42 77 47 L33 77 "
                    "C27 80 21 79 17 75 Z"
                ),
            ),
            tint(LEAF_DARK, c(30, 64, 1.6), c(42, 55, 1.6), c(55, 47, 1.6), c(67, 38, 1.6), c(47, 62, 1.5)),
            body("tip", e(82, 28, 4.4, 3.4, -35)),
            shine(p("M24 60 C38 50 54 39 70 29 C72 28 73 30 71 31 C56 41 40 52 26 62 C24 63 23 61 24 60 Z")),
        ),
        main="#6FAE4E",
        tip="#B7D97A",
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

HOUSEHOLD: dict[str, Picture] = dict(_H)
