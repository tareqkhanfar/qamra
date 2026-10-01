"""Pictures for «رحلتي الأولى للتعلّم», stage 1 (Addendum 6 §4): the listening, shadow, colour and kindergarten
words the library did not have yet, drawn in its style (flat parts in a 100 × 100 box, no text, a colour and
a line-art version from the same parts). A picture another module already draws under the same id wins
(`pictures.PICTURES` adds these with `setdefault`). The educator reviews the word list.
"""

from __future__ import annotations

from qamra_workbook.pictures.icons import (
    BLUE,
    BROWN,
    CORAL,
    CREAM,
    GOLD,
    GRAY,
    LEAF,
    LEAF_DARK,
    ORANGE,
    PURPLE,
    RED,
    SKY,
    SLATE,
    TAN,
    WHITE,
    YELLOW,
)
from qamra_workbook.pictures.model import (
    Part,
    Picture,
    body,
    c,
    cheeks,
    e,
    glint,
    ink,
    line,
    p,
    rect,
    shine,
)


def _pic(id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str) -> Picture:
    return Picture(id, ar, en, category, parts, palette)


def _pencil(x: float, key: str) -> tuple[Part, Part, Part]:
    return (
        body(key, p(f"M{x} 18 L{x + 14} 18 L{x + 14} 72 L{x} 72 Z")),
        body("wood", p(f"M{x} 72 L{x + 14} 72 L{x + 7} 90 Z")),
        ink(p(f"M{x + 4.6} 84.5 L{x + 9.4} 84.5 L{x + 7} 90 Z")),
    )


ANIMALS = (
    _pic(
        "turtle",
        "سُلَحْفاة",
        "turtle",
        "animal",
        (
            body("skin", e(30, 78, 6.5, 5.5), e(64, 78, 6.5, 5.5), p("M16 70 L7 74 L16 77 Z")),
            body("shell", p("M15 72 C15 45 31 32 48 32 C66 32 80 46 80 72 Z")),
            line(p("M30 47 L38 57 L58 57 L66 47 M38 57 L34 71 M58 57 L62 71 M48 33 L48 57")),
            body("rim", rect(13, 68, 69, 7.5, 3.7)),
            body("skin", e(85, 62, 9.5, 8)),
            ink(e(88, 59.5, 2.2, 2.6)),
            glint(c(88.9, 58.6, 0.8)),
            line(p("M84 66.5 Q87.5 69 91 66.5")),
        ),
        shell=LEAF,  # nosec B604: the snail's shell colour, not a shell
        rim=LEAF_DARK,
        skin="#C5DC8E",
    ),
    _pic(
        "giraffe",
        "زَرافَة",
        "giraffe",
        "animal",
        (
            body("main", rect(31, 70, 5.5, 24, 2.5), rect(40, 72, 5.5, 22, 2.5)),
            body("main", rect(55, 72, 5.5, 22, 2.5), rect(63, 70, 5.5, 24, 2.5)),
            line(p("M27 62 C22 66 21 72 23 77")),
            body("main", e(49, 64, 23, 12)),
            body("main", p("M59 60 L64 22 L73 23 L70 63 Z")),
            body("horn", rect(66, 6, 2.6, 8, 1.3), rect(72, 6, 2.6, 8, 1.3)),
            body("main", e(71, 19, 11.5, 7.5, -12)),
            body("spot", c(40, 60, 3.6), c(52, 69, 3), c(60, 58, 2.8), c(66, 42, 2.4), c(66, 51, 2.2)),
            body("spot", c(46, 70, 2.4), c(33, 66, 2.2), c(68, 32, 2)),
            ink(e(73.5, 17, 1.9, 2.2)),
            glint(c(74.2, 16.2, 0.7)),
            line(p("M79 22 Q81 23 82.5 21.5")),
        ),
        main="#F5C25A",
        spot="#B7773E",
        horn=BROWN,
    ),
    _pic(
        "snail",
        "حَلَزون",
        "snail",
        "animal",
        (
            line(p("M82 50 L79 38 M88 50 L90 38")),
            ink(c(79, 37, 2.2), c(90, 37, 2.2)),
            body(
                "main",
                p(
                    "M10 86 C10 77 18 73 30 73 L68 73 C73 62 77 53 83 50 C90 47 95 53 91 60 C87 67 85 "
                    "76 80 86 Z"
                ),
            ),
            body("shell", c(46, 56, 22)),
            line(
                p(
                    "M47 57 C51 55 53 59 49 62 C44 65 39 60 41 54 C43 47 53 45 57 51 C62 58 57 69 47 "
                    "70 C37 71 29 63 30 54"
                )
            ),
            ink(c(86, 56, 1.9)),
            glint(c(86.6, 55.3, 0.7)),
        ),
        main="#E8C9A0",
        shell="#E09A5B",  # nosec B604: the turtle's shell colour, not a shell
    ),
    _pic(
        "frog",
        "ضِفْدَع",
        "frog",
        "animal",
        (
            body("main", e(22, 86, 13, 5.5), e(78, 86, 13, 5.5)),
            body("main", e(50, 64, 34, 24)),
            body("belly", e(50, 73, 19, 10)),
            body("main", c(33, 39, 11.5), c(67, 39, 11.5)),
            body("white", c(33, 38, 7.5), c(67, 38, 7.5)),
            ink(c(34, 39, 3.6), c(68, 39, 3.6)),
            glint(c(35.3, 37.6, 1.3), c(69.3, 37.6, 1.3)),
            line(p("M33 62 Q50 75 67 62")),
            cheeks((26, 64), (74, 64), 4.2),
        ),
        main=LEAF,
        belly="#D2E8A8",
        white=WHITE,
    ),
)

THINGS = (
    _pic(
        "drum",
        "طَبْل",
        "drum",
        "toy",
        (
            body("stick", p("M58 25 L82 8 L85 11.5 L61 28 Z"), p("M42 25 L18 8 L15 11.5 L39 28 Z")),
            body("knob", c(83.5, 9.5, 4.2), c(16.5, 9.5, 4.2)),
            body("main", p("M16 38 L16 76 C16 87 84 87 84 76 L84 38 Z")),
            line(p("M16 45 L29 79 L42 47 L55 81 L68 47 L80 79")),
            body("rim", p("M16 72 C16 83 84 83 84 72 L84 78 C84 89 16 89 16 78 Z")),
            body("top", e(50, 38, 34, 10.5)),
        ),
        main=RED,
        rim=GOLD,
        top=CREAM,
        stick=TAN,
        knob=CORAL,
    ),
    _pic(
        "phone",
        "هاتِف",
        "phone",
        "home",
        (
            body(
                "main",
                p(
                    "M19 82 L26 50 C27 46 30 44 34 44 L66 44 C70 44 73 46 74 50 L81 82 C82 86 79 88 "
                    "76 88 L24 88 C21 88 18 86 19 82 Z"
                ),
            ),
            body(
                "handset",
                p("M10 38 C10 25 19 20 28 20 L72 20 C81 20 90 25 90 38 L77 41 L73 32 L27 32 L23 41 Z"),
            ),
            body("dial", c(50, 66, 13)),
            ink(
                c(50, 56, 1.7),
                c(58.5, 61, 1.7),
                c(58.5, 71, 1.7),
                c(50, 76, 1.7),
                c(41.5, 71, 1.7),
                c(41.5, 61, 1.7),
            ),
            body("hub", c(50, 66, 4)),
        ),
        main=CORAL,
        handset="#D9644F",
        dial=CREAM,
        hub=GOLD,
    ),
    _pic(
        "faucet",
        "حَنَفِيَّة",
        "tap",
        "home",
        (
            body("main", rect(8, 18, 14, 34, 3)),
            body(
                "main",
                p("M22 26 L62 26 C73 26 80 33 80 43 L80 52 L68 52 L68 43 C68 40 66 38 62 38 L22 38 Z"),
            ),
            body("handle", rect(38, 13, 12, 13, 2), rect(29, 8, 30, 6.5, 3.2)),
            body(
                "water",
                p("M70 55 C70 64 67 70 67 78 C67 84 70 88 74 88 C78 88 81 84 81 78 C81 70 78 64 78 55 Z"),
            ),
            body("water", e(62, 92, 2.6, 3.6), e(86, 90, 2.6, 3.6)),
            shine(p("M12 22 L15 22 L15 46 L12 46 Z")),
        ),
        main="#C3C8D4",
        handle=BLUE,
        water=SKY,
    ),
    _pic(
        "whistle",
        "صَفّارَة",
        "whistle",
        "toy",
        (
            line(c(19, 34, 7.5)),
            body(
                "main",
                p(
                    "M20 44 L62 44 C76 44 86 54 86 66 C86 78 76 87 64 87 C52 87 44 79 42 68 L20 68 "
                    "C16 68 14 64 14 60 L14 52 C14 48 16 44 20 44 Z"
                ),
            ),
            body("hole", c(64, 66, 9)),
            body("top", rect(26, 38, 16, 7, 2)),
            shine(e(56, 54, 7, 3, -10)),
        ),
        main=RED,
        hole=WHITE,
        top=GOLD,
    ),
    _pic(
        "sock",
        "جَوارِب",
        "socks",
        "clothes",
        (
            body(
                "main",
                p("M34 10 L60 10 L60 56 L78 69 C87 76 85 90 72 90 L46 90 C35 90 29 82 31 72 L34 60 Z"),
            ),
            body("band", rect(33, 10, 28, 12, 2)),
            body("stripe", rect(34, 32, 26, 7)),
            body("stripe", p("M60 60 L66 64 C60 70 50 74 40 74 L33 74 L34 66 C44 66 54 64 60 60 Z")),
        ),
        main="#7FB4E0",
        band=WHITE,
        stripe=YELLOW,
    ),
    _pic(
        "shoe",
        "حِذاء",
        "shoe",
        "clothes",
        (
            body(
                "main", p("M10 74 C10 62 14 50 22 45 L36 39 C40 51 52 54 58 47 L64 53 C77 57 89 62 91 74 Z")
            ),
            body("sole", p("M7 72 L93 72 C96 72 96 84 91 84 L12 84 C7 84 5 79 7 72 Z")),
            line(p("M40 47 L47 57 M47 44 L54 54 M36 52 L44 50")),
            body("toe", p("M70 58 C80 61 88 66 90 72 L66 72 C66 66 67 61 70 58 Z")),
        ),
        main=RED,
        sole=WHITE,
        toe=WHITE,
    ),
)

MORE = (
    _pic(
        "pumpkin",
        "يَقْطينَة",
        "pumpkin",
        "vegetable",
        (
            body("stem", p("M46 34 L47 19 C48 16 53 16 54 19 L55 34 Z")),
            body("leaf", p("M54 23 C60 13 72 13 77 19 C69 26 60 28 54 23 Z")),
            body("main", e(50, 61, 38, 28)),
            line(p("M50 34 C42 46 42 76 50 88 M50 34 C58 46 58 76 50 88")),
            line(p("M31 37 C22 51 22 72 31 85 M69 37 C78 51 78 72 69 85")),
            shine(e(30, 54, 3.5, 8, 15)),
        ),
        main=ORANGE,
        stem=LEAF_DARK,
        leaf=LEAF,
    ),
    _pic(
        "eggplant",
        "باذِنْجان",
        "eggplant",
        "vegetable",
        (
            body(
                "main",
                p("M30 30 C44 24 58 34 66 48 C76 64 85 78 77 88 C68 97 52 88 42 74 C32 60 22 40 30 30 Z"),
            ),
            body("cap", p("M28 24 L21 11 L26.5 10 L33.5 22 Z")),
            body("cap", p("M21 35 C23 24 34 19 43 24 C45 31 38 37 30 38 C26 38 22 37.5 21 35 Z")),
            shine(e(49, 53, 4, 11, -35)),
        ),
        main="#7E5BB5",
        cap=LEAF,
    ),
    _pic(
        "pillow",
        "وِسادَة",
        "pillow",
        "home",
        (
            body(
                "main",
                p(
                    "M14 34 C14 26 20 22 28 24 C42 27 58 27 72 24 C80 22 86 26 86 34 L86 66"
                    " C86 74 80 78 72 76 C58 73 42 73 28 76 C20 78 14 74 14 66 Z"
                ),
            ),
            line(p("M28 40 C40 44 60 44 72 40")),
            body("dot", c(35, 56, 3.2), c(50, 53, 3.2), c(65, 56, 3.2)),
        ),
        main="#B9D7F2",
        dot=WHITE,
    ),
    _pic(
        "crayons",
        "أَلْوان خَشَبِيَّة",
        "crayons",
        "school",
        (*_pencil(20, "p0"), *_pencil(43, "p1"), *_pencil(66, "p2")),
        p0=RED,
        p1=YELLOW,
        p2=BLUE,
        wood=TAN,
    ),
    _pic(
        "lunchbox",
        "عُلْبَة طَعام",
        "lunchbox",
        "school",
        (
            body("handle", p("M36 31 C36 16 64 16 64 31 L58 31 C58 23 42 23 42 31 Z")),
            body("main", rect(13, 30, 74, 54, 8)),
            body("lid", rect(13, 30, 74, 15, 6)),
            body("clip", rect(44, 40, 12, 9, 2)),
            body("fruit", c(33, 65, 7.5)),
            line(p("M33 57.5 L35 53 M58 60 L74 60 M58 68 L70 68")),
        ),
        main="#6CC3B5",
        lid="#4FA89A",
        clip=YELLOW,
        handle=SLATE,
        fruit=RED,
    ),
    _pic(
        "school",
        "رَوْضَة",
        "kindergarten",
        "place",
        (
            line(p("M50 21 L50 5")),
            body("flag", p("M50 5 L65 9.5 L50 14 Z")),
            body("wall", rect(16, 44, 68, 48, 3)),
            body("roof", p("M9 47 L50 20 L91 47 C92 49 91 51 89 51 L11 51 C9 51 8 49 9 47 Z")),
            body("sign", c(50, 38, 6.5)),
            body("door", p("M42 92 L42 73 C42 65 58 65 58 73 L58 92 Z")),
            body("glass", rect(22, 58, 12, 12, 2), rect(66, 58, 12, 12, 2)),
            line(p("M28 58 L28 70 M22 64 L34 64 M72 58 L72 70 M66 64 L78 64")),
        ),
        wall=CREAM,
        roof=RED,
        flag=LEAF,
        sign=YELLOW,
        door=BROWN,
        glass=SKY,
    ),
    _pic(
        "grass",
        "عُشْب",
        "grass",
        "plant",
        (
            body("main", p("M14 88 C18 70 22 60 31 50 C28 64 30 74 34 88 Z")),
            body("main", p("M30 88 C32 66 38 50 49 35 C44 56 44 72 48 88 Z")),
            body("main", p("M44 88 C46 64 54 46 67 34 C60 54 58 72 62 88 Z")),
            body("main", p("M58 88 C62 70 70 58 83 50 C74 64 72 76 76 88 Z")),
            body("ground", rect(8, 86, 84, 8, 4)),
        ),
        main=LEAF,
        ground="#C9A77C",
    ),
    _pic(
        "sea",
        "بَحْر",
        "sea",
        "nature",
        (
            body(
                "main",
                p("M6 40 C18 32 30 32 42 40 C54 48 66 48 78 40 C84 36 90 34 94 36 L94 88 C94 92 92 94 88 94"),
            ),
            body("main", p("M88 94 L12 94 C8 94 6 92 6 88 Z")),
            line(p("M16 58 Q24 52 32 58 Q40 64 48 58 M52 72 Q60 66 68 72 Q76 78 84 72 M14 82 Q20 78 26 82")),
        ),
        main=BLUE,
    ),
)

# the colours a colour page names (Addendum 6 §4.6): id → (colour, Arabic name, English name)
COLORS: dict[str, tuple[str, str, str]] = {
    "red": (RED, "الأَحْمَرُ", "red"),
    "yellow": (YELLOW, "الأَصْفَرُ", "yellow"),
    "blue": (BLUE, "الأَزْرَقُ", "blue"),
    "green": (LEAF, "الأَخْضَرُ", "green"),
    "orange": (ORANGE, "البُرْتُقالِيُّ", "orange"),
    "purple": (PURPLE, "البَنَفْسَجِيُّ", "purple"),
    "pink": ("#F4A6B8", "الوَرْدِيُّ", "pink"),
    "black": ("#3A3A48", "الأَسْوَدُ", "black"),
    "white": (WHITE, "الأَبْيَضُ", "white"),
    "brown": (BROWN, "البُنِّيُّ", "brown"),
    "gray": (GRAY, "الرَّمادِيُّ", "gray"),
}

JOURNEY_WORDS: dict[str, Picture] = {pic.id: pic for pic in (*ANIMALS, *THINGS, *MORE)}
