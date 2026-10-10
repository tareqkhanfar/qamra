"""Pictures for stages 2 and 3 of «رحلتي الأولى للتعلّم» (Addendum 6 §4.9, §4.11): the letter words, the body
parts, the English vocabulary units and the challenge scenes the library did not have yet, drawn in its style
(flat parts in a 100 × 100 box, no text, a colour and a line-art version from the same parts). A picture
another module already draws under the same id wins. The educator reviews the word list.
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
    shine,
)

SKIN = "#F4C9A6"


def _pic(id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str) -> Picture:
    return Picture(id, ar, en, category, parts, palette)


BODY = (
    _pic(
        "face",
        "وَجْه",
        "face",
        "body",
        (
            body("hair", p("M22 46 C18 18 82 18 78 46 C74 30 26 30 22 46 Z")),
            body("skin", c(50, 52, 30)),
            body("hair", p("M22 48 C20 30 30 22 50 22 C70 22 80 30 78 48 C70 38 30 38 22 48 Z")),
            *eyes((40, 50), (60, 50), 3.4),
            line(p("M43 63 Q50 69 57 63")),
            line(p("M50 52 L48 58 L52 58")),
            cheeks((34, 60), (66, 60), 4),
        ),
        skin=SKIN,
        hair=BROWN,
    ),
    _pic(
        "eye",
        "عَيْن",
        "eye",
        "body",
        (
            body("white", p("M8 50 C24 24 76 24 92 50 C76 76 24 76 8 50 Z")),
            body("iris", c(50, 50, 15)),
            ink(c(50, 50, 7)),
            glint(c(54, 45, 2.6)),
            line(p("M14 44 C30 22 70 22 86 44")),
            line(p("M26 32 L22 26 M50 26 L50 19 M74 32 L78 26")),
        ),
        white=WHITE,
        iris=SKY,
    ),
    _pic(
        "ear",
        "أُذُن",
        "ear",
        "body",
        (
            body(
                "skin",
                p(
                    "M36 22 C60 8 82 30 70 56 C64 70 54 74 52 88 C50 94 38 92 38 84 C38 72 30 66 30 "
                    "50 C30 38 30 28 36 22 Z"
                ),
            ),
            line(p("M44 34 C58 28 66 40 60 52 C56 60 48 60 46 68")),
            line(p("M48 42 C56 42 58 50 52 54")),
        ),
        skin=SKIN,
    ),
    _pic(
        "nose",
        "أَنْف",
        "nose",
        "body",
        (
            body(
                "skin",
                p("M50 16 C46 40 30 54 30 68 C30 80 40 86 50 84 C60 86 70 80 70 68 C70 54 54 40 50 16 Z"),
            ),
            line(p("M38 74 Q44 80 50 76 Q56 80 62 74")),
            ink(e(41, 73, 3, 2), e(59, 73, 3, 2)),
        ),
        skin=SKIN,
    ),
    _pic(
        "mouth",
        "فَم",
        "mouth",
        "body",
        (
            body("lip", p("M10 50 C24 34 40 40 50 44 C60 40 76 34 90 50 C76 72 24 72 10 50 Z")),
            body("teeth", p("M22 50 L78 50 L74 58 L26 58 Z")),
            body("tongue", p("M32 62 C40 58 60 58 68 62 C60 70 40 70 32 62 Z")),
            line(p("M10 50 L90 50")),
        ),
        lip=CORAL,
        teeth=WHITE,
        tongue=PINK,
    ),
    _pic(
        "tongue",
        "لِسان",
        "tongue",
        "body",
        (
            body("lip", p("M12 40 C26 26 74 26 88 40 C80 54 70 58 62 58 L38 58 C30 58 20 54 12 40 Z")),
            body("teeth", p("M24 40 L76 40 L72 47 L28 47 Z")),
            body("tongue", p("M36 52 C36 84 64 84 64 52 Z")),
            line(p("M50 56 L50 78")),
        ),
        lip=CORAL,
        teeth=WHITE,
        tongue=PINK,
    ),
    _pic(
        "hand",
        "يَد",
        "hand",
        "body",
        (
            body(
                "skin",
                p(
                    "M30 92 L30 56 C30 50 22 46 18 38 C15 32 22 28 26 34 L32 46 L32 22 C32 16 40 16 40 22"
                    " L40 44 L42 14 C42 8 50 8 50 14 L50 44 L52 18 C52 12 60 12 60 18 L60 46 L62 28"
                    " C62 22 70 22 70 28 L70 62 C70 78 62 92 50 92 Z"
                ),
            ),
            line(p("M40 44 L40 56 M50 44 L50 56 M60 46 L60 58")),
        ),
        skin=SKIN,
    ),
    _pic(
        "foot",
        "قَدَم",
        "foot",
        "body",
        (
            body(
                "skin",
                p(
                    "M28 12 L58 12 C64 12 66 18 66 26 L66 56 C66 62 72 64 78 66 C88 70 90 84 78 88 L34 88"
                    " C26 88 22 82 22 74 L22 20 C22 15 24 12 28 12 Z"
                ),
            ),
            body("skin", c(28, 86, 6), c(40, 88, 5.5), c(52, 90, 5), c(64, 90, 4.6), c(76, 88, 4.2)),
            line(p("M30 20 L30 60 M58 20 L58 52")),
        ),
        skin=SKIN,
    ),
)

WORDS = (
    _pic(
        "plane",
        "طائِرَة",
        "plane",
        "vehicle",
        (
            body("wing", p("M40 50 L14 24 L26 22 L60 46 Z"), p("M40 58 L18 82 L30 84 L62 60 Z")),
            body(
                "main",
                p(
                    "M8 54 C8 46 20 44 34 44 L78 44 C90 44 96 50 92 56 C88 62 78 64 66 64 L34 64 C20 "
                    "64 8 62 8 54 Z"
                ),
            ),
            body("tail", p("M14 50 L4 26 L16 26 L28 46 Z")),
            body("glass", c(80, 51, 4), c(66, 51, 4), c(52, 51, 4)),
            shine(p("M20 48 L60 48 L60 51 L20 51 Z")),
        ),
        main=WHITE,
        wing=SKY,
        tail=RED,
        glass=SKY,
    ),
    _pic(
        "gazelle",
        "غَزال",
        "gazelle",
        "animal",
        (
            body(
                "main",
                rect(30, 62, 5, 30, 2),
                rect(41, 64, 5, 28, 2),
                rect(60, 64, 5, 28, 2),
                rect(70, 62, 5, 30, 2),
            ),
            body("main", e(52, 56, 26, 13)),
            body("main", p("M70 52 L78 26 L86 27 L80 56 Z")),
            body(
                "horn",
                p("M80 26 C78 14 84 6 88 4 L86 12 C84 18 84 22 84 26 Z"),
                p("M86 26 C90 16 94 10 98 8 L94 16 C92 22 90 24 90 27 Z"),
            ),
            body("main", e(84, 28, 9, 6, -10)),
            body("belly", e(52, 60, 16, 6)),
            ink(e(87, 26, 1.8, 2)),
            glint(c(87.6, 25.3, 0.7)),
            line(p("M92 30 L94 31 M32 54 L28 46")),
        ),
        main=TAN,
        belly=CREAM,
        horn=BROWN,
    ),
    _pic(
        "crescent",
        "هِلال",
        "crescent",
        "sky",
        (
            body(
                "main",
                p("M62 12 C36 18 22 42 30 66 C36 84 52 92 68 90 C48 84 36 66 40 46 C43 30 52 18 62 12 Z"),
            ),
            body("star", p("M78 30 L81 38 L89 38 L82 43 L85 51 L78 46 L71 51 L74 43 L67 38 L75 38 Z")),
            shine(e(40, 44, 2.6, 7, 15)),
        ),
        main=GOLD,
        star=YELLOW,
    ),
    _pic(
        "watch",
        "ساعَة يَد",
        "watch",
        "thing",
        (
            body("strap", rect(38, 4, 24, 92, 6)),
            body("main", c(50, 50, 28)),
            body("face", c(50, 50, 22)),
            ink(
                rect(48.5, 30, 3, 5, 1.5),
                rect(48.5, 65, 3, 5, 1.5),
                rect(30, 48.5, 5, 3, 1.5),
                rect(65, 48.5, 5, 3, 1.5),
            ),
            line(p("M50 50 L50 36 M50 50 L60 56")),
            ink(c(50, 50, 2.4)),
            body("strap", rect(76, 45, 8, 10, 2)),
        ),
        strap=BLUE,
        main=SLATE,
        face=WHITE,
    ),
    _pic(
        "van",
        "شاحِنَة صَغيرَة",
        "van",
        "vehicle",
        (
            body("main", p("M8 66 L8 40 C8 34 12 30 18 30 L64 30 L84 46 L92 48 C95 49 96 52 96 56 L96 66 Z")),
            body("glass", p("M66 34 L80 46 L66 46 Z"), rect(20, 34, 16, 12, 2), rect(42, 34, 16, 12, 2)),
            body("tire", c(26, 68, 10), c(76, 68, 10)),
            body("hub", c(26, 68, 4), c(76, 68, 4)),
            body("light", e(93, 60, 2.4, 3.2)),
            line(p("M8 56 L64 56")),
        ),
        main=ORANGE,
        glass=SKY_LIGHT,
        tire=SLATE,
        hub=GRAY,
        light=YELLOW,
    ),
    _pic(
        "yo-yo",
        "يُويُو",
        "yo-yo",
        "toy",
        (
            line(p("M50 12 L50 34 M50 12 C40 8 32 14 34 22")),
            body("main", c(50, 60, 28)),
            body("ring", c(50, 60, 18)),
            body("hub", c(50, 60, 6)),
            shine(e(38, 48, 5, 8, 30)),
        ),
        main=RED,
        ring=YELLOW,
        hub=WHITE,
    ),
    _pic(
        "zebra",
        "حِمار وَحْشِيّ",
        "zebra",
        "animal",
        (
            body(
                "main",
                rect(28, 62, 6, 30, 2.5),
                rect(40, 64, 6, 28, 2.5),
                rect(58, 64, 6, 28, 2.5),
                rect(70, 62, 6, 30, 2.5),
            ),
            body("main", e(50, 54, 28, 16)),
            body("main", p("M72 50 L80 24 L92 26 L86 54 Z")),
            body("main", e(88, 26, 10, 7)),
            body("mane", p("M78 24 C82 12 92 12 94 20 L84 26 Z")),
            ink(p("M34 42 L36 62 M44 40 L44 66 M54 40 L54 68 M64 42 L62 64 M76 42 L80 30 M82 46 L86 34")),
            ink(e(90, 24, 1.8, 2)),
            glint(c(90.6, 23.3, 0.7)),
            line(p("M96 30 L98 31")),
        ),
        main=WHITE,
        mane=SLATE,
    ),
    _pic(
        "juice",
        "عَصير",
        "juice",
        "drink",
        (
            body("straw", p("M56 6 L62 8 L52 44 L46 42 Z")),
            body("glass", p("M28 26 L72 26 L66 90 L34 90 Z")),
            body("main", p("M31 44 L69 44 L66 90 L34 90 Z")),
            body("slice", c(74, 26, 11)),
            line(p("M74 15 L74 37 M63 26 L85 26")),
            shine(p("M36 48 L40 48 L38 84 L34 84 Z")),
        ),
        glass=SKY_LIGHT,
        main=ORANGE,
        straw=RED,
        slice=YELLOW,
    ),
    _pic(
        "bus",
        "حافِلَة",
        "bus",
        "vehicle",
        (
            body("main", rect(6, 26, 88, 46, 8)),
            body(
                "glass",
                rect(12, 32, 16, 14, 2),
                rect(34, 32, 16, 14, 2),
                rect(56, 32, 16, 14, 2),
                rect(78, 32, 10, 14, 2),
            ),
            body("stripe", rect(6, 52, 88, 5)),
            body("tire", c(24, 74, 9), c(76, 74, 9)),
            body("hub", c(24, 74, 3.5), c(76, 74, 3.5)),
            body("light", c(10, 64, 2.6), c(90, 64, 2.6)),
        ),
        main=YELLOW,
        glass=SKY_LIGHT,
        stripe=RED,
        tire=SLATE,
        hub=GRAY,
        light=WHITE,
    ),
)

MORE = (
    _pic(
        "pen",
        "قَلَم حِبْر",
        "pen",
        "school",
        (
            body("cap", p("M64 10 L78 24 L34 68 L20 54 Z")),
            body("main", p("M34 68 L20 54 L14 74 L12 88 L26 86 Z")),
            ink(p("M16 84 L12 88 L18 80 Z")),
            body("clip", p("M70 12 L84 26 L80 30 L66 16 Z")),
            shine(p("M60 16 L66 22 L40 48 L34 42 Z")),
        ),
        cap=BLUE,
        main=SKY,
        clip=GOLD,
    ),
    _pic(
        "ruler",
        "مِسْطَرَة",
        "ruler",
        "school",
        (
            body("main", p("M10 68 L70 8 L90 28 L30 88 Z")),
            line(
                p(
                    "M22 66 L28 60 M30 74 L40 64 M38 82 L44 76 M46 58 L52 52 M54 66 L64 56 M62 42 L68 "
                    "36 M70 50 L80 40 M78 26 L84 20"
                )
            ),
        ),
        main=YELLOW,
    ),
    _pic(
        "eraser",
        "مِمْحاة",
        "eraser",
        "school",
        (
            body("main", p("M14 60 L52 22 L86 56 L48 94 Z")),
            body("band", p("M32 42 L52 22 L86 56 L66 76 Z")),
            shine(p("M22 60 L30 52 L58 80 L50 88 Z")),
        ),
        main=PINK,
        band=BLUE,
    ),
    _pic(
        "rice",
        "أَرُزّ",
        "rice",
        "food",
        (
            body("bowl", p("M10 50 L90 50 C88 74 72 88 50 88 C28 88 12 74 10 50 Z")),
            body("main", p("M14 52 C20 34 36 28 50 30 C64 28 80 34 86 52 Z")),
            ink(
                e(30, 42, 2.4, 1.4, -20),
                e(44, 38, 2.4, 1.4, 15),
                e(58, 40, 2.4, 1.4, -10),
                e(72, 44, 2.4, 1.4, 20),
            ),
            line(p("M24 64 L76 64")),
        ),
        bowl=SKY,
        main=WHITE,
    ),
    _pic(
        "cheese",
        "جُبْنَة",
        "cheese",
        "food",
        (
            body("side", p("M12 46 L12 78 L88 78 L88 46 Z")),
            body("main", p("M12 46 L54 24 L88 46 Z")),
            body("hole", c(40, 62, 5), c(64, 66, 4), c(30, 72, 2.6), c(52, 72, 2.4)),
            shine(p("M20 44 L52 30 L54 34 L26 46 Z")),
        ),
        main=YELLOW,
        side=GOLD,
        hole="#E1A83A",
    ),
    _pic(
        "water",
        "ماء",
        "water",
        "drink",
        (
            body("glass", p("M28 16 L72 16 L66 90 L34 90 Z")),
            body("main", p("M31 40 L69 40 L66 90 L34 90 Z")),
            line(p("M34 48 Q40 44 46 48 T58 48 T68 48")),
            shine(p("M36 44 L40 44 L38 84 L34 84 Z")),
        ),
        glass=SKY_LIGHT,
        main=SKY,
    ),
    _pic(
        "rocket",
        "صاروخ",
        "rocket",
        "thing",
        (
            body("flame", p("M40 82 C40 96 50 98 50 92 C50 98 60 96 60 82 Z")),
            body("fin", p("M32 62 L18 82 L32 82 Z"), p("M68 62 L82 82 L68 82 Z")),
            body("main", p("M50 6 C66 20 68 50 66 82 L34 82 C32 50 34 20 50 6 Z")),
            body("nose", p("M50 6 C58 12 62 20 64 30 L36 30 C38 20 42 12 50 6 Z")),
            body("window", c(50, 48, 8)),
            body("glass", c(50, 48, 5)),
        ),
        main=WHITE,
        nose=RED,
        fin=RED,
        window=SLATE,
        glass=SKY,
        flame=ORANGE,
    ),
    _pic(
        "castle",
        "قَلْعَة",
        "castle",
        "place",
        (
            body("main", rect(10, 40, 80, 50, 2)),
            body("main", rect(10, 26, 18, 16), rect(72, 26, 18, 16), rect(38, 18, 24, 24)),
            body(
                "main",
                p(
                    "M10 26 L10 20 L15 20 L15 26 M19 26 L19 20 L24 20 L24 26 M72 26 L72 20 L77 20 L77 "
                    "26 M81 26 L81 20 L86 20 L86 26 M38 18 L38 12 L44 12 L44 18 M50 18 L50 12 L56 12 "
                    "L56 18"
                ),
            ),
            body("door", p("M42 90 L42 68 C42 60 58 60 58 68 L58 90 Z")),
            body("flag", p("M50 12 L50 2 L60 5 L50 8 Z")),
            ink(rect(18, 48, 5, 8, 2), rect(77, 48, 5, 8, 2), rect(47, 30, 6, 9, 3)),
        ),
        main=GRAY,
        door=BROWN,
        flag=RED,
    ),
    _pic(
        "knight",
        "فارِس",
        "knight",
        "people",
        (
            body("armor", rect(28, 46, 44, 40, 8)),
            body("armor", rect(34, 84, 12, 12, 3), rect(54, 84, 12, 12, 3)),
            body("shield", p("M6 46 L34 46 L34 66 C34 76 26 82 20 84 C14 82 6 76 6 66 Z")),
            body("cross", p("M18 52 L22 52 L22 76 L18 76 Z M10 60 L30 60 L30 64 L10 64 Z")),
            body("helmet", p("M32 40 C32 14 68 14 68 40 Z")),
            body("skin", rect(36, 30, 28, 12, 2)),
            ink(e(44, 36, 2.2, 2.6), e(56, 36, 2.2, 2.6)),
            body("plume", p("M50 14 C56 4 66 4 72 10 C64 12 58 16 54 20 Z")),
            line(p("M72 60 L92 40 M88 44 L96 36")),
        ),
        armor=GRAY,
        shield=RED,
        cross=YELLOW,
        helmet=SLATE,
        skin=SKIN,
        plume=RED,
    ),
    _pic(
        "library",
        "مَكْتَبَة",
        "library",
        "place",
        (
            body("main", rect(10, 8, 80, 84, 3)),
            body("shelf", rect(14, 34, 72, 3), rect(14, 62, 72, 3), rect(14, 88, 72, 3)),
            body("b1", rect(18, 14, 8, 20, 1)),
            body("b2", rect(28, 12, 9, 22, 1)),
            body("b3", rect(39, 16, 7, 18, 1)),
            body("b1", rect(48, 12, 10, 22, 1)),
            body("b2", rect(60, 15, 8, 19, 1)),
            body("b3", rect(70, 12, 12, 22, 1)),
            body("b3", rect(18, 42, 9, 20, 1)),
            body("b1", rect(29, 40, 8, 22, 1)),
            body("b2", rect(39, 44, 11, 18, 1)),
            body("b1", rect(52, 40, 8, 22, 1)),
            body("b3", rect(62, 42, 9, 20, 1)),
            body("b2", rect(73, 40, 9, 22, 1)),
            body("b2", rect(18, 70, 12, 18, 1)),
            body("b3", rect(32, 68, 8, 20, 1)),
            body("b1", rect(42, 72, 10, 16, 1)),
            body("b2", rect(54, 68, 8, 20, 1)),
            body("b3", rect(64, 70, 9, 18, 1)),
            body("b1", rect(75, 68, 8, 20, 1)),
        ),
        main=TAN,
        shelf=BROWN,
        b1=RED,
        b2=BLUE,
        b3=LEAF,
    ),
    _pic(
        "can",
        "عُلْبَة",
        "can",
        "home",
        (
            body("main", p("M24 24 L76 24 L76 84 C76 90 24 90 24 84 Z")),
            body("label", rect(24, 40, 52, 30)),
            body("lid", e(50, 24, 26, 7)),
            line(p("M32 24 L68 24")),
            body("dot", c(50, 55, 8)),
            shine(p("M28 30 L32 30 L32 82 L28 82 Z")),
        ),
        main=GRAY,
        lid=SLATE,
        label=RED,
        dot=YELLOW,
    ),
)


def _child(id: str, ar: str, en: str, hair: str, outfit: str, skirt: bool) -> Picture:
    """A simple child: round head, short hair, a shirt (or a dress) and legs, facing the reader."""
    legs = (
        (body("outfit", p("M30 56 L70 56 L74 84 L26 84 Z")),)
        if skirt
        else (body("outfit", rect(30, 54, 40, 26, 4)),)
    )
    return _pic(
        id,
        ar,
        en,
        "people",
        (
            body("skin", rect(36, 78, 9, 16, 3), rect(55, 78, 9, 16, 3)),
            *legs,
            body("skin", rect(18, 54, 9, 22, 4), rect(73, 54, 9, 22, 4)),
            body("skin", c(50, 32, 18)),
            body(
                "hair",
                p("M32 30 C32 8 68 8 68 30 C60 22 40 22 32 30 Z")
                if not skirt
                else p("M30 34 C30 6 70 6 70 34 L66 44 C64 28 36 28 34 44 Z"),
            ),
            *eyes((43, 33), (57, 33), 2.6),
            line(p("M45 41 Q50 45 55 41")),
            cheeks((39, 40), (61, 40), 3),
        ),
        skin=SKIN,
        hair=hair,
        outfit=outfit,
    )


PEOPLE = (
    _child("boy", "وَلَد", "boy", BROWN, BLUE, False),
    _child("girl", "بِنْت", "girl", "#3A2A20", PINK, True),
)

JOURNEY_WORDS2: dict[str, Picture] = {pic.id: pic for pic in (*BODY, *WORDS, *MORE, *PEOPLE)}
