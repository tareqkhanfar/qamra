"""More pictures for «مغامراتي مع عائلتي» (Addendum 7, the whole book): the nature hunt, the weather, the
day's routine, toys, the professions' tools, the recipes and the family games. Same house style as
`icons.py` and `household.py` (flat colors, one outline weight, no text); merged into the library through
`household.HOUSEHOLD`.
"""

from __future__ import annotations

from qamra_workbook.pictures.icons import (
    BLUE,
    BROWN,
    CREAM,
    GOLD,
    GRAY,
    LEAF,
    LEAF_DARK,
    ORANGE,
    PINK_DEEP,
    PURPLE,
    RED,
    SKY,
    SLATE,
    TAN,
    TEAL,
    WHITE,
    YELLOW,
)
from qamra_workbook.pictures.model import Part, Picture, body, c, e, glint, ink, line, p, rect, shine

OLIVE = "#6F8F2F"
STONE = "#B8B2A7"


def _pic(
    id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str
) -> tuple[str, Picture]:
    return id, Picture(id, ar, en, category, parts, palette)


_F = [
    _pic(
        "yogurt",
        "لَبَن رائِب",
        "yogurt",
        "food",
        (
            body("cup", p("M22 34 L78 34 L72 88 C71.5 91 69 93 66 93 L34 93 C31 93 28.5 91 28 88 Z")),
            body("main", p("M24 34 C24 24 76 24 76 34 C76 40 24 40 24 34 Z")),
            line(p("M36 31 C42 27 52 27 58 30")),
            body("band", p("M25.5 50 L74.5 50 L73 64 L27 64 Z")),
            body("berry", c(62, 25, 5.5)),
            body("leafy", p("M62 20 C63 15 68 13 71 14 C69 18 66 20 62 20 Z")),
            shine(rect(31, 68, 3, 16, 1.5)),
        ),
        cup=WHITE,
        main=CREAM,
        band=SKY,
        berry=RED,
        leafy=LEAF,
    ),
    _pic(
        "lemon",
        "لَيْمونَة",
        "lemon",
        "fruit",
        (
            body(
                "main",
                p("M14 52 C14 32 32 22 50 22 C68 22 86 32 86 52 C86 72 68 82 50 82 C32 82 14 72 14 52 Z"),
            ),
            body("main", p("M10 52 C10 49 12 47 15 47 L15 57 C12 57 10 55 10 52 Z")),
            body("main", p("M90 52 C90 49 88 47 85 47 L85 57 C88 57 90 55 90 52 Z")),
            body("leaf", p("M52 22 C54 12 64 8 72 10 C68 18 60 22 52 22 Z")),
            shine(e(34, 38, 8, 4, -20)),
        ),
        main=YELLOW,
        leaf=LEAF,
    ),
    _pic(
        "pear",
        "إِجّاصَة",
        "pear",
        "fruit",
        (
            body(
                "main",
                p(
                    "M50 18 C60 18 62 30 64 40 C66 50 82 58 82 72 C82 86 68 94 50 94 C32 94 18 86 18 72 "
                    "C18 58 34 50 36 40 C38 30 40 18 50 18 Z"
                ),
            ),
            body("stem", rect(48, 6, 4, 14, 2)),
            body("leaf", p("M52 12 C56 4 66 2 72 5 C68 12 60 14 52 12 Z")),
            shine(e(34, 70, 5, 9, 20)),
        ),
        main="#B7D356",
        stem=BROWN,
        leaf=LEAF,
    ),
    _pic(
        "spoon",
        "مِلْعَقَة",
        "spoon",
        "home",
        (
            body("handle", p("M47 44 L53 44 L55 92 C55 95 45 95 45 92 Z")),
            body("main", e(50, 28, 17, 21)),
            body("food", p("M36 24 C38 14 62 14 64 24 C64 32 36 32 36 24 Z")),
            shine(e(43, 21, 3, 5, 20)),
        ),
        handle=TAN,
        main=GRAY,
        food=CREAM,
    ),
    _pic(
        "leaf-long",
        "وَرَقَة طَويلَة",
        "long leaf",
        "plant",
        (
            body("main", p("M50 8 C66 26 68 62 50 88 C32 62 34 26 50 8 Z")),
            line(
                p("M50 16 L50 94"),
                p("M50 36 L60 28 M50 50 L62 42 M50 64 L60 57 M50 36 L40 28 M50 50 L38 42 M50 64 L40 57"),
            ),
        ),
        main=LEAF_DARK,
    ),
    _pic(
        "olive-leaf",
        "غُصْن زَيْتون",
        "olive twig",
        "plant",
        (
            line(p("M14 86 C34 70 56 48 86 16")),
            body(
                "leaf",
                p("M32 70 C24 58 26 46 30 40 C36 48 38 60 32 70 Z"),
                p("M52 50 C62 40 72 40 78 42 C72 50 62 54 52 50 Z"),
                p("M62 36 C56 24 58 14 62 8 C68 16 68 28 62 36 Z"),
                p("M40 60 C52 56 62 60 66 64 C56 68 46 66 40 60 Z"),
            ),
            body("olive", e(46, 38, 6, 8, -30), e(30, 50, 5, 7, 20)),
            glint(c(44, 35, 1.6), c(29, 47, 1.4)),
        ),
        leaf="#8FAF6A",
        olive=OLIVE,
    ),
    _pic(
        "stone",
        "حَجَر",
        "stone",
        "nature",
        (
            body(
                "main",
                p("M14 70 C10 52 26 34 46 32 C66 30 88 42 88 62 C88 78 70 84 50 84 C30 84 16 80 14 70 Z"),
            ),
            line(p("M32 56 C36 52 42 52 46 54"), p("M60 66 C64 64 68 64 72 66")),
            shine(e(40, 44, 9, 4, -12)),
        ),
        main=STONE,
    ),
    _pic(
        "pinecone",
        "كوز صَنَوْبَر",
        "pine cone",
        "nature",
        (
            body(
                "main",
                p("M50 10 C66 22 72 44 68 64 C64 82 56 92 50 92 C44 92 36 82 32 64 C28 44 34 22 50 10 Z"),
            ),
            line(
                p(
                    "M36 34 L50 44 L64 34 M33 50 L50 60 L67 50 M34 66 L50 76 L66 66 "
                    "M50 20 L50 44 M42 28 L50 33 L58 28"
                )
            ),
            body("stem", rect(47, 3, 6, 10, 3)),
        ),
        main=BROWN,
        stem=LEAF_DARK,
    ),
]

_W = [  # weather clothes and the day's routine
    _pic(
        "sun-hat",
        "قُبَّعَة",
        "sun hat",
        "clothes",
        (
            body("brim", e(50, 66, 42, 14)),
            body("main", p("M26 64 C26 36 38 26 50 26 C62 26 74 36 74 64 C66 70 34 70 26 64 Z")),
            body("band", p("M27 56 C40 61 60 61 73 56 L74 64 C62 69 38 69 26 64 Z")),
            body("flower", c(64, 56, 6)),
            ink(c(64, 56, 2)),
            shine(e(40, 40, 4, 7, 20)),
        ),
        brim=YELLOW,
        main=YELLOW,
        band=PINK_DEEP,
        flower=WHITE,
    ),
    _pic(
        "boots",
        "جَزْمَة مَطَر",
        "rain boots",
        "clothes",
        (
            body("main", p("M14 18 L38 18 L38 70 L52 74 C56 76 56 88 50 88 L14 88 Z")),
            body("main", p("M52 18 L76 18 L76 70 L90 74 C94 76 94 88 88 88 L52 88 Z")),
            body("sole", rect(12, 84, 44, 6, 3), rect(50, 84, 44, 6, 3)),
            body("top", rect(12, 14, 28, 8, 3), rect(50, 14, 28, 8, 3)),
            shine(rect(18, 26, 4, 30, 2), rect(56, 26, 4, 30, 2)),
        ),
        main=YELLOW,
        sole=SLATE,
        top=ORANGE,
    ),
    _pic(
        "kite",
        "طائِرَة وَرَقِيَّة",
        "kite",
        "toy",
        (
            body("a", p("M50 6 L80 38 L50 52 Z")),
            body("b", p("M50 6 L20 38 L50 52 Z")),
            body("c", p("M20 38 L50 52 L50 72 Z")),
            body("d", p("M80 38 L50 52 L50 72 Z")),
            line(p("M50 72 C44 80 56 84 48 94"), p("M20 38 L80 38 M50 6 L50 72")),
            body("bow", p("M44 80 L50 84 L44 88 Z"), p("M52 88 L58 84 L58 92 Z")),
        ),
        a=RED,
        b=YELLOW,
        c=BLUE,
        d=LEAF,
        bow=PINK_DEEP,
    ),
    _pic(
        "scarf",
        "كوفِيَّة صوف",
        "scarf",
        "clothes",
        (
            body(
                "main",
                p("M20 30 C30 20 70 20 80 30 C82 40 76 46 70 44 C60 38 40 38 30 44 C24 46 18 40 20 30 Z"),
            ),
            body("main", p("M58 42 L72 44 L66 88 L50 86 Z")),
            line(p("M52 84 L50 94 M57 85 L56 95 M62 86 L62 95 M67 87 L68 95")),
            body("stripe", p("M55 58 L69 60 L68 66 L54 64 Z"), p("M53 72 L67 74 L66 80 L52 78 Z")),
        ),
        main=RED,
        stripe=WHITE,
    ),
    _pic(
        "backpack",
        "حَقيبَة مَدْرَسَة",
        "school bag",
        "home",
        (
            line(p("M38 24 C38 10 62 10 62 24")),
            body(
                "main",
                p(
                    "M22 34 C22 26 30 22 38 22 L62 22 C70 22 78 26 78 34 L78 86 C78 90 75 92 72 92 L28 92 "
                    "C25 92 22 90 22 86 Z"
                ),
            ),
            body("pocket", p("M32 60 L68 60 L68 82 C68 85 66 86 64 86 L36 86 C34 86 32 85 32 82 Z")),
            body("flap", p("M22 34 C22 26 30 22 38 22 L62 22 C70 22 78 26 78 34 L78 44 L22 44 Z")),
            body("clip", rect(46, 40, 8, 8, 2)),
            shine(rect(27, 50, 3, 30, 1.5)),
        ),
        main=BLUE,
        pocket=SKY,
        flap="#4A6FC0",
        clip=YELLOW,
    ),
    _pic(
        "bed",
        "سَرير",
        "bed",
        "home",
        (
            body("frame", rect(10, 34, 10, 56, 3), rect(80, 50, 10, 40, 3)),
            body("base", rect(14, 64, 72, 14, 3)),
            body("sheet", p("M18 64 C18 56 24 52 32 52 L84 52 L84 64 Z")),
            body("pillow", e(30, 50, 12, 7)),
            body("cover", p("M42 50 L86 50 L86 70 L42 70 C38 70 38 50 42 50 Z")),
            line(p("M52 58 L78 58")),
        ),
        frame=BROWN,
        base=TAN,
        sheet=WHITE,
        pillow=WHITE,
        cover=PURPLE,
    ),
    _pic(
        "toothbrush",
        "فُرْشاة أَسْنان",
        "toothbrush",
        "home",
        (
            body(
                "handle",
                p(
                    "M16 84 L66 34 C69 31 74 31 76 34 C78 36 78 40 76 42 L26 92 C23 95 19 95 16 92 "
                    "C13 89 13 87 16 84 Z"
                ),
            ),
            body("head", p("M64 26 L80 10 C82 8 86 8 88 10 L90 12 C92 14 92 18 90 20 L74 36 Z")),
            body("paste", p("M70 14 C74 6 84 4 88 8 C82 10 78 14 76 20 Z")),
            shine(rect(30, 72, 3, 14, 1.5)),
        ),
        handle=TEAL,
        head=WHITE,
        paste=SKY,
    ),
]

_T = [  # toys
    _pic(
        "blocks",
        "مُكَعَّبات",
        "blocks",
        "toy",
        (
            body("a", rect(12, 56, 34, 34, 3)),
            body("b", rect(54, 56, 34, 34, 3)),
            body("c", rect(33, 20, 34, 34, 3)),
            ink(p("M24 66 L34 66 L29 80 Z"), c(71, 73, 6)),
            line(p("M41 30 L59 30 M50 30 L50 46")),
        ),
        a=RED,
        b=BLUE,
        c=YELLOW,
    ),
    _pic(
        "doll",
        "دُمْيَة",
        "doll",
        "toy",
        (
            body("dress", p("M34 50 L66 50 L80 90 L20 90 Z")),
            body("skin", c(50, 32, 16), rect(24, 54, 8, 22, 4), rect(68, 54, 8, 22, 4)),
            body("hair", p("M33 30 C33 12 67 12 67 30 C62 22 54 20 50 24 C46 20 38 22 33 30 Z")),
            ink(c(44, 33, 2), c(56, 33, 2)),
            line(p("M45 40 C48 43 52 43 55 40")),
            body("bow", p("M60 16 L70 10 L70 22 Z"), p("M60 16 L52 10 L52 22 Z")),
        ),
        dress=PINK_DEEP,
        skin="#F4C9A6",
        hair=BROWN,
        bow=YELLOW,
    ),
    _pic(
        "teddy",
        "دُبّ",
        "teddy bear",
        "toy",
        (
            body("main", c(26, 22, 10), c(74, 22, 10), e(50, 72, 26, 22), c(50, 38, 22)),
            body("light", c(26, 22, 5), c(74, 22, 5), e(50, 46, 10, 7), e(50, 76, 14, 12)),
            ink(c(42, 34, 2.6), c(58, 34, 2.6), e(50, 43, 3.6, 2.6)),
            line(p("M46 49 C48 51 52 51 54 49")),
        ),
        main=BROWN,
        light=TAN,
    ),
]

_J = [  # the professions' tools, the plant, the fruit salad, the games, the stage
    _pic(
        "stethoscope",
        "سَمّاعَة الطَّبيب",
        "stethoscope",
        "tool",
        (
            line(p("M30 14 L30 40 C30 56 46 62 50 62 C54 62 70 56 70 40 L70 14"), p("M50 62 L50 74")),
            body("tips", c(30, 12, 4), c(70, 12, 4)),
            body("main", c(50, 82, 12)),
            body("inner", c(50, 82, 6)),
        ),
        tips=SLATE,
        main=GRAY,
        inner=SKY,
    ),
    _pic(
        "hammer",
        "مِطْرَقَة",
        "hammer",
        "tool",
        (
            body("handle", p("M44 36 L56 36 L58 90 C58 94 42 94 42 90 Z")),
            body(
                "head",
                p("M18 18 L74 18 C82 18 86 24 86 30 L86 34 L18 34 C14 34 12 30 12 26 C12 22 14 18 18 18 Z"),
            ),
            shine(rect(24, 21, 30, 3, 1.5)),
        ),
        handle=TAN,
        head=SLATE,
    ),
    _pic(
        "scissors",
        "مِقَصّ",
        "scissors",
        "tool",
        (
            body(
                "blade",
                p("M46 52 L84 12 C86 10 89 12 87 15 L54 58 Z"),
                p("M54 52 L16 12 C14 10 11 12 13 15 L46 58 Z"),
            ),
            body("ring", c(34, 76, 13), c(66, 76, 13)),
            body("hole", c(34, 76, 7), c(66, 76, 7)),
            ink(c(50, 55, 3)),
        ),
        blade=GRAY,
        ring=RED,
        hole=WHITE,
    ),
    _pic(
        "watering-can",
        "إِبْريق سِقايَة",
        "watering can",
        "tool",
        (
            body("main", p("M22 40 L66 40 L62 88 L26 88 Z")),
            body("spout", p("M64 70 L90 34 L94 38 L68 80 Z")),
            body("rose", p("M86 30 L96 26 L98 40 L90 40 Z")),
            line(p("M30 40 C30 20 58 20 58 40")),
            body("drop", p("M84 50 C86 54 88 56 86 58 C84 60 82 58 82 56 C82 54 84 52 84 50 Z")),
            shine(rect(28, 48, 3, 30, 1.5)),
        ),
        main=TEAL,
        spout=TEAL,
        rose=SLATE,
        drop=SKY,
    ),
    _pic(
        "broom",
        "مِكْنَسَة",
        "broom",
        "tool",
        (
            body("handle", p("M46 6 L54 6 L54 58 L46 58 Z")),
            body("main", p("M34 58 L66 58 L78 92 C78 94 76 95 74 95 L26 95 C24 95 22 94 22 92 Z")),
            line(p("M38 66 L34 92 M50 66 L50 93 M62 66 L66 92")),
            body("band", rect(32, 56, 36, 7, 3)),
        ),
        handle=BROWN,
        main=YELLOW,
        band=RED,
    ),
    _pic(
        "pot-plant",
        "نَبْتَة",
        "potted plant",
        "plant",
        (
            body(
                "leaf",
                p("M50 56 C44 40 30 34 20 36 C24 48 36 56 50 56 Z"),
                p("M50 50 C54 32 68 24 80 26 C76 40 64 48 50 50 Z"),
            ),
            line(p("M50 64 L50 40")),
            body("bud", c(50, 34, 7)),
            body("pot", p("M28 60 L72 60 L66 92 L34 92 Z")),
            body("rim", rect(24, 56, 52, 10, 3)),
            shine(rect(34, 70, 3, 16, 1.5)),
        ),
        leaf=LEAF,
        bud=PINK_DEEP,
        pot="#D98A5F",
        rim="#C9774C",
    ),
    _pic(
        "fruit-bowl",
        "سَلَطَة فَواكِه",
        "fruit salad",
        "food",
        (
            body("f1", c(30, 46, 10), c(46, 40, 9)),
            body("f2", c(62, 42, 10), c(74, 48, 8)),
            body("f3", c(40, 52, 7), c(58, 52, 7)),
            body("bowl", p("M10 52 L90 52 C90 76 72 90 50 90 C28 90 10 76 10 52 Z")),
            glint(c(28, 43, 2), c(60, 39, 2)),
            shine(e(22, 66, 3, 7, 25)),
        ),
        f1=RED,
        f2=YELLOW,
        f3="#9BC45A",
        bowl=SKY,
    ),
    _pic(
        "dice",
        "حَجَر نَرْد",
        "dice",
        "toy",
        (
            body("main", rect(14, 14, 72, 72, 16)),
            ink(c(32, 32, 6), c(68, 32, 6), c(50, 50, 6), c(32, 68, 6), c(68, 68, 6)),
            shine(rect(22, 20, 24, 4, 2)),
        ),
        main=WHITE,
    ),
    _pic(
        "theatre",
        "مَسْرَح",
        "stage",
        "place",
        (
            body("floor", rect(6, 78, 88, 14, 3)),
            body("back", rect(14, 20, 72, 58)),
            body(
                "curtain",
                p("M6 10 L34 10 C30 36 32 60 40 78 L6 78 Z"),
                p("M94 10 L66 10 C70 36 68 60 60 78 L94 78 Z"),
            ),
            body(
                "top",
                p(
                    "M4 6 L96 6 L96 18 C88 24 80 24 74 18 C68 24 60 24 54 18 C48 24 40 24 34 18 "
                    "C28 24 20 24 14 18 "
                    "C10 22 6 22 4 18 Z"
                ),
            ),
            body("star", p("M50 36 L54 46 L64 46 L56 52 L60 62 L50 56 L40 62 L44 52 L36 46 L46 46 Z")),
        ),
        floor=TAN,
        back="#FFF1D6",
        curtain=RED,
        top="#B8483D",
        star=GOLD,
    ),
]

_J.append(
    _pic(
        "briefcase",
        "حَقيبَة عَمَل",
        "briefcase",
        "tool",
        (
            line(p("M38 30 L38 22 C38 18 41 16 44 16 L56 16 C59 16 62 18 62 22 L62 30")),
            body("main", rect(12, 30, 76, 56, 8)),
            body("band", rect(12, 50, 76, 8)),
            body("clasp", rect(44, 46, 12, 16, 3)),
            shine(rect(18, 36, 3, 12, 1.5)),
        ),
        main=BROWN,
        band="#8A5A3C",
        clasp=GOLD,
    )
)

_J += [
    _pic(
        "snowflake",
        "ثَلْج",
        "snowflake",
        "sky",
        (
            line(
                p("M50 10 L50 90 M15 30 L85 70 M15 70 L85 30"),
                p(
                    "M42 16 L50 24 L58 16 M42 84 L50 76 L58 84 M18 40 L28 38 L24 28 M82 60 L72 62 L76 72 "
                    "M18 60 L28 62 L24 72 M82 40 L72 38 L76 28"
                ),
            ),
            body("main", c(50, 50, 8)),
        ),
        main=SKY,
    ),
    _pic(
        "wind",
        "ريح",
        "wind",
        "sky",
        (
            line(
                p("M10 38 L62 38 C74 38 78 26 70 20 C64 16 56 20 58 28"),
                p("M10 56 L76 56 C88 56 92 68 84 74 C78 78 70 74 72 66"),
                p("M20 74 L48 74"),
            ),
            body("leaf", p("M74 34 C80 26 90 26 94 30 C88 36 80 38 74 34 Z")),
        ),
        leaf=LEAF,
    ),
]

FAMILY_MORE: dict[str, Picture] = dict(_F + _W + _T + _J)
