"""Pictures for the words of «دوسية التأسيس» KG1 that the library did not have yet (the letter words حوت،
خلية، غزال، هدهد، هرم، يقطين…, the English words van, yo-yo, zebra, the vocabulary units' family, body and
food words), in the library's style: flat parts in a 100 × 100 box, no text, a color and a line-art version
from the same parts. The educator reviews the word list.
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
    PINK,
    RED,
    SKY,
    SKY_LIGHT,
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
    eyes,
    glint,
    ink,
    line,
    p,
    rect,
    scallop_d,
    shine,
)

TEAL_VAN = "#3FA7A0"
SKIN = "#F3C9A6"
HAIR = "#4A2F1E"
NAVY = "#3C468F"


def _pic(id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str) -> Picture:
    return Picture(id, ar, en, category, parts, palette)


def _smile(x: float, y: float, w: float = 4.5) -> Part:
    return line(p(f"M{x - w} {y} Q{x} {y + w * 0.9} {x + w} {y}"))


def _person(hair: str, top: str, skirt: bool, tall: float, pigtails: bool = False) -> tuple[Part, ...]:
    """A standing figure: head at the top, a shirt or a dress, legs; `tall` scales the whole figure."""
    s = tall
    cy = 50 - 40 * s  # the head's centre
    head = c(50, cy + 14 * s, 13 * s)
    hair_shape = p(
        f"M{50 - 14 * s} {cy + 12 * s} C{50 - 14 * s} {cy - 4 * s} {50 + 14 * s} {cy - 4 * s} "
        f"{50 + 14 * s} {cy + 12 * s} L{50 + 10 * s} {cy + 6 * s} L{50 - 10 * s} {cy + 6 * s} Z"
    )
    parts: list[Part] = [body("hair", hair_shape)]
    if pigtails:
        parts.append(
            body("hair", e(50 - 17 * s, cy + 18 * s, 4 * s, 7 * s), e(50 + 17 * s, cy + 18 * s, 4 * s, 7 * s))
        )
    parts.append(body("skin", head))
    top_y = cy + 27 * s
    if skirt:
        parts.append(
            body(
                "top",
                p(
                    f"M{50 - 10 * s} {top_y} L{50 + 10 * s} {top_y} L{50 + 20 * s} {top_y + 44 * s} "
                    f"L{50 - 20 * s} {top_y + 44 * s} Z"
                ),
            )
        )
    else:
        parts.append(body("top", rect(50 - 13 * s, top_y, 26 * s, 26 * s, 4 * s)))
        parts.append(
            body(
                "pants",
                rect(50 - 12 * s, top_y + 26 * s, 11 * s, 18 * s, 2),
                rect(50 + 1 * s, top_y + 26 * s, 11 * s, 18 * s, 2),
            )
        )
    parts.append(
        body(
            "skin",
            rect(50 - 22 * s, top_y + 2 * s, 8 * s, 22 * s, 4 * s),
            rect(50 + 14 * s, top_y + 2 * s, 8 * s, 22 * s, 4 * s),
        )
    )
    if skirt:
        parts.append(
            body(
                "skin",
                rect(50 - 9 * s, top_y + 44 * s, 6 * s, 8 * s, 2),
                rect(50 + 3 * s, top_y + 44 * s, 6 * s, 8 * s, 2),
            )
        )
    foot = top_y + (53 if skirt else 45) * s  # under the legs or the trousers, never floating below them
    parts.append(body("shoe", e(50 - 6 * s, foot, 6 * s, 3 * s), e(50 + 6 * s, foot, 6 * s, 3 * s)))
    parts += [
        *eyes((50 - 5 * s, cy + 13 * s), (50 + 5 * s, cy + 13 * s), 2.2 * s),
        _smile(50, cy + 19 * s, 3.5 * s),
    ]
    parts.append(cheeks((50 - 8 * s, cy + 18 * s), (50 + 8 * s, cy + 18 * s), 2.6 * s))
    return tuple(parts)


FAMILY = (
    _pic(
        "mother",
        "أُمّ",
        "mother",
        "person",
        _person(HAIR, "top", True, 1.0),
        hair=HAIR,
        skin=SKIN,
        top=CORAL,
        shoe=SLATE,
    ),
    _pic(
        "father",
        "أَب",
        "father",
        "person",
        _person(HAIR, "top", False, 1.0),
        hair=HAIR,
        skin=SKIN,
        top=BLUE,
        pants=SLATE,
        shoe=BROWN,
    ),
    _pic(
        "brother",
        "أَخ",
        "brother",
        "person",
        _person(HAIR, "top", False, 0.78),
        hair=HAIR,
        skin=SKIN,
        top=LEAF,
        pants=NAVY,
        shoe=BROWN,
    ),
    _pic(
        "sister",
        "أُخْت",
        "sister",
        "person",
        _person(HAIR, "top", True, 0.78, pigtails=True),
        hair=HAIR,
        skin=SKIN,
        top=PINK,
        shoe=RED,
    ),
)

# draft: educator review: the letter words of KG1 as drawn
LETTER_WORDS = (
    _pic(
        "whale",
        "حوت",
        "whale",
        "animal",
        (
            body(
                "main",
                p(
                    "M12 56 C12 34 34 24 58 26 C80 28 92 40 92 56 C92 70 78 80 58 80 "
                    "L30 80 C20 80 12 70 12 56 Z"
                ),
            ),
            body("main", p("M84 44 L96 30 L98 46 Z M84 44 L98 54 L92 62 Z")),
            body("belly", p("M20 66 C36 74 60 76 82 66 C76 78 44 82 20 66 Z")),
            line(p("M30 34 L30 22 M24 30 L28 22 M36 30 L32 22")),
            ink(e(28, 52, 3, 3.4)),
            glint(c(29, 51, 1.2)),
            _smile(20, 62, 5),
        ),
        main=SKY,
        belly=SKY_LIGHT,
    ),
    _pic(
        "beehive",
        "خَلِيَّة",
        "beehive",
        "nature",
        (
            body(
                "main",
                e(50, 76, 34, 12),
                e(50, 62, 32, 12),
                e(50, 48, 27, 11),
                e(50, 36, 20, 9),
                e(50, 27, 12, 6),
            ),
            ink(e(50, 78, 8, 6)),
            body("bee", e(80, 24, 8, 6)),
            ink(rect(76, 18, 2.4, 12), rect(82, 18, 2.4, 12)),
            body("wing", e(78, 15, 5, 3.5), e(84, 15, 5, 3.5)),
            body("stand", rect(30, 86, 40, 6, 3)),
        ),
        main=GOLD,
        bee=YELLOW,
        wing=WHITE,
        stand=BROWN,
    ),
    _pic(
        "lettuce",
        "خَسَّة",
        "lettuce",
        "vegetable",
        (
            body("main", p(scallop_d(50, 54, 38, 34, 9))),
            body("inner", p(scallop_d(50, 58, 24, 20, 7))),
            line(p("M50 78 L50 44 M50 62 L38 52 M50 66 L62 54")),
        ),
        main=LEAF,
        inner="#A9D46A",
    ),
    _pic(
        "gazelle",
        "غَزال",
        "gazelle",
        "animal",
        (
            body("main", p("M22 50 C22 40 34 36 50 38 L66 40 C74 40 78 46 78 54 L78 62 L22 62 Z")),
            body(
                "main",
                rect(26, 60, 7, 28, 3),
                rect(40, 60, 7, 28, 3),
                rect(58, 60, 7, 28, 3),
                rect(70, 60, 7, 28, 3),
            ),
            body(
                "main",
                p("M70 44 L82 26 C84 22 90 22 92 26 L92 34 L84 44 Z"),
                p("M78 54 L90 60 L88 66 L76 60 Z"),
            ),
            line(p("M84 26 L80 10 M88 26 L90 8")),
            body("belly", e(50, 58, 22, 6)),
            ink(e(85, 32, 2.4, 2.8)),
            glint(c(85.6, 31.2, 0.9)),
        ),
        main=TAN,
        belly=CREAM,
    ),
    _pic(
        "hoopoe",
        "هُدْهُد",
        "hoopoe",
        "bird",
        (
            body("crest", p("M44 34 L36 12 L46 28 L48 8 L54 28 L60 10 L58 30 Z")),
            body("main", e(46, 56, 28, 20)),
            body("main", c(52, 36, 12)),
            body("wing", p("M30 56 C40 44 66 46 70 60 C58 70 40 70 30 56 Z")),
            line(p("M40 52 L60 52 M38 58 L62 58 M40 64 L60 64")),
            ink(p("M62 34 L88 40 L62 38 Z")),
            ink(e(56, 33, 2.4, 2.8)),
            glint(c(56.8, 32.2, 0.9)),
            body("crest", p("M18 60 L30 66 L26 76 Z")),
            ink(rect(40, 74, 2.4, 14), rect(50, 74, 2.4, 14)),
        ),
        main=ORANGE,
        crest=CORAL,
        wing=CREAM,
    ),
)

MORE_WORDS = (
    _pic(
        "pyramid",
        "هَرَم",
        "pyramid",
        "place",
        (
            # seen from a corner (a front face and a narrow side), a small one behind and a dune: the old
            # two halves on a slab with a line up the middle read as a sailboat
            body("sky", c(82, 22, 9)),
            body("dark", p("M24 50 L6 86 L42 86 Z")),
            body("light", p("M56 16 L20 86 L82 86 Z")),
            body("dark", p("M56 16 L82 86 L96 74 Z")),
            line(p("M38 51 L69 51 M29 68 L75 68")),
            body("sand", p("M2 88 C25 84 45 90 70 86 C82 84 92 86 98 88 L98 94 L2 94 Z")),
        ),
        sky=YELLOW,
        sand=CREAM,
        light=GOLD,
        dark=TAN,
    ),
    _pic(
        "pumpkin",
        "يَقْطين",
        "pumpkin",
        "vegetable",
        (
            body("stem", p("M46 22 L54 22 L56 10 C56 6 48 6 46 12 Z")),
            body("main", e(50, 58, 40, 32)),
            body("rib", e(50, 58, 14, 32)),
            line(p("M30 30 C22 44 22 72 30 86 M70 30 C78 44 78 72 70 86")),
            shine(e(38, 44, 4, 8, -20)),
        ),
        stem=LEAF_DARK,
        main=ORANGE,
        rib="#F5A65B",
    ),
    _pic(
        "coat",
        "مِعْطَف",
        "coat",
        "clothes",
        (
            body("main", p("M32 18 L68 18 L84 30 L78 58 L70 56 L70 90 L30 90 L30 56 L22 58 L16 30 Z")),
            body("collar", p("M40 18 L50 34 L60 18 Z")),
            line(p("M50 34 L50 90")),
            ink(c(58, 48, 2.4), c(58, 62, 2.4), c(58, 76, 2.4)),
            body("cuff", rect(16, 52, 12, 8, 2), rect(72, 52, 12, 8, 2)),
        ),
        main=RED,
        collar="#B8442F",
        cuff="#B8442F",
    ),
    _pic(
        "water",
        "ماء",
        "water",
        "drink",
        (
            body("glass", p("M30 14 L70 14 L64 90 L36 90 Z")),
            body("main", p("M33 44 C40 40 46 48 52 44 C58 40 62 46 67 44 L63 88 L37 88 Z")),
            shine(rect(40, 50, 4, 30, 2)),
            body("drop", p("M84 20 C84 12 90 8 90 8 C90 8 96 12 96 20 A6 6 0 0 1 84 20 Z")),
        ),
        glass=WHITE,
        main=SKY,
        drop=SKY,
    ),
    _pic(
        "lamp",
        "مِصْباح",
        "lamp",
        "home",
        (
            line(p("M22 36 L12 30 M78 36 L88 30 M50 12 L50 4")),
            body("shade", p("M30 18 L70 18 L82 50 L18 50 Z")),
            body("stand", rect(46, 50, 8, 30)),
            body("base", e(50, 84, 24, 7)),
            body("bulb", e(50, 46, 10, 6)),
        ),
        shade=YELLOW,
        stand=SLATE,
        base=SLATE,
        bulb="#FFF3B0",
    ),
    _pic(
        "van",
        "شاحِنَة صَغيرَة",
        "van",
        "vehicle",
        (
            body("main", p("M8 40 L8 74 L92 74 L92 52 L78 34 L20 34 C12 34 8 36 8 40 Z")),
            body("window", p("M66 40 L78 40 L88 52 L66 52 Z"), rect(14, 40, 44, 14, 2)),
            body("wheel", c(26, 76, 9), c(74, 76, 9)),
            ink(c(26, 76, 3.5), c(74, 76, 3.5)),
            line(p("M8 62 L92 62")),
        ),
        main=TEAL_VAN,
        window=SKY_LIGHT,
        wheel=SLATE,
    ),
    _pic(
        "yo-yo",
        "يويو",
        "yo-yo",
        "toy",
        (
            line(p("M50 8 L50 30 M50 8 C40 8 40 4 46 4 C52 4 52 10 50 8")),
            body("main", c(50, 58, 30)),
            body("rim", c(50, 58, 20)),
            ink(c(50, 58, 4)),
            shine(e(38, 46, 5, 8, -30)),
        ),
        main=RED,
        rim=CORAL,
    ),
    _pic(
        "zebra",
        "حِمار وَحْشِيّ",
        "zebra",
        "animal",
        (
            body("main", p("M18 48 C18 40 28 36 46 38 L66 40 C74 40 80 44 80 52 L80 62 L18 62 Z")),
            body(
                "main",
                rect(22, 60, 8, 28, 3),
                rect(36, 60, 8, 28, 3),
                rect(58, 60, 8, 28, 3),
                rect(70, 60, 8, 28, 3),
            ),
            body("main", p("M72 46 L82 24 C86 20 94 22 94 30 L92 46 Z")),
            ink(rect(30, 40, 4, 22), rect(42, 40, 4, 22), rect(54, 40, 4, 22), rect(66, 42, 4, 20)),
            ink(p("M78 28 L92 22 L92 30 Z"), rect(80, 34, 10, 3), rect(82, 40, 10, 3)),
            ink(e(87, 31, 2.2, 2.6)),
            glint(c(87.6, 30.4, 0.8)),
            line(p("M18 52 L8 60 L12 66")),
        ),
        main=WHITE,
    ),
)

BODY_AND_FOOD = (
    _pic(
        "head",
        "رَأْس",
        "head",
        "body",
        (
            body("hair", p("M22 46 C22 18 78 18 78 46 L72 40 L60 46 L48 38 L36 46 L28 40 Z")),
            body("skin", c(50, 54, 28)),
            body("hair", p("M22 46 C22 24 78 24 78 46 C70 36 30 36 22 46 Z")),
            *eyes((40, 52), (60, 52), 3.2),
            _smile(50, 64, 6),
            cheeks((34, 62), (66, 62), 4),
        ),
        hair=HAIR,
        skin=SKIN,
    ),
    _pic(
        "mouth",
        "فَم",
        "mouth",
        "body",
        (
            body("lip", p("M14 50 C26 34 40 36 50 44 C60 36 74 34 86 50 C74 72 26 72 14 50 Z")),
            body("teeth", p("M22 50 L78 50 L74 58 L26 58 Z")),
            line(p("M30 50 L30 57 M40 50 L40 58 M50 50 L50 58 M60 50 L60 58 M70 50 L70 57")),
            body("tongue", p("M32 60 C40 70 60 70 68 60 Z")),
        ),
        lip=CORAL,
        teeth=WHITE,
        tongue=PINK,
    ),
    _pic(
        "rice",
        "أَرُزّ",
        "rice",
        "food",
        (
            body("main", p("M20 56 C20 36 80 36 80 56 Z")),
            body("bowl", p("M12 56 L88 56 C86 76 74 88 50 88 C26 88 14 76 12 56 Z")),
            line(p("M30 48 L34 46 M44 42 L48 42 M58 44 L62 42 M38 52 L42 50 M52 50 L56 52 M66 52 L70 50")),
            body("spoon", p("M78 30 L94 14 L96 18 L82 34 Z"), e(76, 35, 6, 4)),
        ),
        main=WHITE,
        bowl=SKY,
        spoon=GRAY,
    ),
    _pic(
        "cheese",
        "جُبْن",
        "cheese",
        "food",
        (
            body("main", p("M10 74 L60 28 L90 44 L90 84 L10 84 Z")),
            body("top", p("M10 74 L60 28 L90 44 L40 74 Z")),
            ink(c(30, 78, 0.1)),
            body("hole", c(64, 66, 5), c(78, 74, 3.5), c(52, 78, 3)),
        ),
        main=YELLOW,
        top="#FFE58A",
        hole=GOLD,
    ),
    _pic(
        "crayon",
        "قَلَم تَلْوين",
        "crayon",
        "school",
        (
            body("main", p("M30 22 L50 6 L70 22 L70 90 L30 90 Z")),
            body("band", rect(30, 34, 40, 12), rect(30, 78, 40, 8)),
            line(p("M30 22 L70 22")),
            shine(rect(36, 48, 5, 26, 2)),
        ),
        main=RED,
        band="#B8442F",
    ),
)

# the first picture of the seed → sprout → flower story (a seed resting on the soil)
STORY_WORDS = (
    _pic(
        "seed",
        "بَذْرَة",
        "seed",
        "plant",
        (
            body("soil", p("M8 92 C8 70 28 62 50 62 C72 62 92 70 92 92 Z")),
            body("main", e(50, 54, 15, 10)),
            line(p("M40 52 Q50 46 60 52")),
            shine(e(44, 50, 3, 2)),
        ),
        soil=BROWN,
        main=TAN,
    ),
)

WORKBOOK_WORDS_KG1: dict[str, Picture] = {
    pic.id: pic for pic in (*FAMILY, *LETTER_WORDS, *MORE_WORDS, *BODY_AND_FOOD, *STORY_WORDS)
}
# plan words spelled differently from the library word (the picture's own word is printed)
WORD_ALIASES_KG1 = {"قلم": "pencil", "ليمون": "lemon", "موز": "banana", "خسة": "lettuce", "حوت": "whale"}
