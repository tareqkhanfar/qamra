"""Pictures for the words of «دوسية التأسيس» Volume 2 (letters ر–غ, English I–R, the position-word scenes),
in the library's style: flat parts in a 100 × 100 box, no text, a color and a line-art version from the same
parts.
The educator reviews the word list (decision 7: ظِلّ and طاولة are drawn here).
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
    PURPLE,
    RED,
    SKY,
    SKY_LIGHT,
    SLATE,
    TAN,
    TEAL,
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

DARK_BROWN = "#6B4428"
CHESTNUT = "#B07A4F"
OLIVE = "#6E8B3D"
SAND = "#E6C28E"
NAVY = "#3C468F"
SKIN = "#F2C9A6"


def _pic(id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str) -> Picture:
    return Picture(id, ar, en, category, parts, palette)


def _smile(x: float, y: float, w: float = 4.5) -> Part:
    return line(p(f"M{x - w} {y} Q{x} {y + w * 0.9} {x + w} {y}"))


# draft: educator review: the letter words of Volume 2 as drawn
LETTER_WORDS_A = (
    _pic(
        "pomegranate",
        "رُمّان",
        "pomegranate",
        "fruit",
        (
            body("crown", p("M42 22 L40 10 L47 16 L50 8 L53 16 L60 10 L58 22 Z")),
            body(
                "main",
                p("M50 22 C70 22 82 38 82 58 C82 76 68 88 50 88 C32 88 18 76 18 58 C18 38 30 22 50 22 Z"),
            ),
            shine(e(34, 44, 4, 9, 20)),
        ),
        main=RED,
        crown="#B8442F",
    ),
    _pic(
        "feather",
        "ريشَة",
        "feather",
        "nature",
        (  # a quill below the vane and two splits in it: the old leaf shape read as «وَرَقَة»
            body(
                "main",
                p(
                    "M26 77 C22 64 26 52 34 44 L40 46 L38 38 C44 30 50 25 56 22 C64 16 72 12 78 12 "
                    "C80 20 78 30 72 40 L64 41 L70 47 C62 60 48 72 34 78 Z"
                ),
            ),
            line(p("M12 94 C34 66 56 38 78 12")),
            line(p("M36 64 L28 58 M44 54 L36 46 M54 42 L48 32 M40 70 L48 72 M50 60 L58 62 M60 48 L68 50")),
        ),
        main=SKY,
    ),
    _pic(
        "bottle",
        "زُجاجَة",
        "bottle",
        "home",
        (
            body("cap", rect(42, 6, 16, 10, 2.5)),
            body(
                "main",
                p(
                    "M43 16 L57 16 L57 30 C66 36 68 44 68 54 L68 84 C68 89 65 92 60 92 "
                    "L40 92 C35 92 32 89 32 84 L32 54 C32 44 34 36 43 30 Z"
                ),
            ),
            body("water", p("M35 58 L65 58 L65 84 C65 87 63 89 60 89 L40 89 C37 89 35 87 35 84 Z")),
            shine(rect(38, 40, 4, 40, 2)),
        ),
        main=SKY_LIGHT,
        water=SKY,
        cap=BLUE,
    ),
    _pic(
        "olive",
        "زَيْتون",
        "olive",
        "food",
        (
            body("stem", p("M50 30 L60 14 L64 17 L54 33 Z")),
            body("leaf", p("M60 14 C70 4 84 6 88 14 C78 20 66 20 60 14 Z")),
            body("main", e(38, 56, 16, 21, -12), e(66, 62, 15, 20, 15)),
            body("inner", e(38, 56, 5, 7, -12), e(66, 62, 4.5, 6.5, 15)),
            shine(e(30, 46, 3, 6, -12)),
        ),
        main=OLIVE,
        inner="#4E6A2A",
        leaf=LEAF,
        stem=BROWN,
    ),
    _pic(
        "ship",
        "سَفينَة",
        "ship",
        "vehicle",
        (
            body("water", p("M4 82 C14 76 24 88 34 82 C44 76 54 88 64 82 C74 76 84 88 96 82 L96 96 L4 96 Z")),
            body("funnel", rect(40, 30, 10, 18, 2), rect(56, 34, 8, 14, 2)),
            body("cabin", rect(30, 46, 40, 16, 3)),
            body("main", p("M12 62 L88 62 L78 84 L22 84 Z")),
            body("window", c(36, 73, 3.5), c(50, 73, 3.5), c(64, 73, 3.5)),
            line(p("M42 26 C46 20 50 26 54 20")),
        ),
        main=RED,
        cabin=WHITE,
        funnel=NAVY,
        window=SKY_LIGHT,
        water=SKY,
    ),
    _pic(
        "candle",
        "شَمْعَة",
        "candle",
        "home",
        (
            body("holder", e(50, 88, 26, 7), rect(34, 74, 32, 14, 3)),
            body("main", rect(40, 30, 20, 46, 3)),
            line(p("M50 30 L50 22")),
            body("flame", p("M50 4 C56 12 60 18 58 24 C56 30 44 30 42 24 C40 18 44 12 50 4 Z")),
            body("glow", e(50, 21, 3, 4.5)),
            shine(rect(43, 34, 3, 36, 1.5)),
        ),
        main=CREAM,
        holder=GOLD,
        flame=ORANGE,
        glow=YELLOW,
    ),
)

LETTER_WORDS_B = (
    _pic(
        "fork",
        "شَوْكَة",
        "fork",
        "home",
        (
            body(
                "main",
                p(
                    "M32 8 L38 8 L38 30 L44 30 L44 8 L50 8 L50 30 L56 30 L56 8 L62 8 "
                    "L62 36 C62 44 56 48 50 50 L50 92 L44 92 L44 50 C38 48 32 44 32 36 Z"
                ),
            ),
            shine(rect(45, 54, 2.5, 34, 1)),
        ),
        main=GRAY,
    ),
    _pic(
        "falcon",
        "صَقْر",
        "falcon",
        "bird",
        (
            body(
                "wing",
                p("M44 48 C30 36 12 34 4 42 C16 44 26 50 34 60 Z"),
                p("M56 48 C70 36 88 34 96 42 C84 44 74 50 66 60 Z"),
            ),
            body(
                "main",
                p("M50 22 C62 22 70 34 68 50 C66 66 60 80 50 86 C40 80 34 66 32 50 C30 34 38 22 50 22 Z"),
            ),
            body(
                "belly",
                p("M50 50 C57 50 61 58 60 68 C59 78 55 84 50 86 C45 84 41 78 40 68 C39 58 43 50 50 50 Z"),
            ),
            line(p("M44 60 L56 60 M45 68 L55 68 M46 76 L54 76")),
            body("main", c(50, 22, 12)),
            *eyes((45, 20), (55, 20), 2.4),
            body("beak", p("M46 27 L54 27 L50 34 Z")),
            line(p("M44 86 L42 94 M50 86 L50 94 M56 86 L58 94")),
        ),
        main=CHESTNUT,
        belly=CREAM,
        wing=DARK_BROWN,
        beak=GOLD,
    ),
    _pic(
        "box",
        "صُنْدوق",
        "box",
        "home",
        (
            body("lid", p("M12 38 L50 26 L88 38 L50 50 Z")),
            body("side", p("M12 38 L50 50 L50 88 L12 76 Z")),
            body("main", p("M50 50 L88 38 L88 76 L50 88 Z")),
            line(p("M31 44 L31 82"), p("M69 44 L69 82")),
            shine(p("M56 54 L62 52 L62 82 L56 84 Z")),
        ),
        main=SAND,
        side="#CFA872",
        lid=TAN,
    ),
    _pic(
        "tooth",
        "ضِرْس",
        "tooth",
        "body",
        (
            body(
                "main",
                p(
                    "M28 30 C28 14 44 12 50 22 C56 12 72 14 72 30 C72 44 68 52 66 66 C65 78 60 90 55 90 "
                    "C50 90 50 76 50 68 C50 76 50 90 45 90 C40 90 35 78 34 66 C32 52 28 44 28 30 Z"
                ),
            ),
            shine(e(40, 30, 3.5, 7, 15)),
            *eyes((43, 40), (57, 40), 2.6),
            _smile(50, 48, 4),
        ),
        main=WHITE,
    ),
    _pic(
        "table",
        "طاوِلَة",
        "table",
        "home",
        (
            body("leg", rect(16, 48, 8, 42, 2), rect(76, 48, 8, 42, 2)),
            body(
                "main",
                p(
                    "M8 34 L92 34 C95 34 96 36 96 39 L96 46 C96 49 95 50 92 50 "
                    "L8 50 C5 50 4 49 4 46 L4 39 C4 36 5 34 8 34 Z"
                ),
            ),
            line(p("M8 42 L92 42")),
            shine(rect(12, 37, 30, 2.5, 1.2)),
        ),
        main=TAN,
        leg=BROWN,
    ),
    _pic(
        "peacock",
        "طاووس",
        "peacock",
        "bird",
        (
            body(
                "tail",
                p("M50 62 C22 62 6 44 8 18 C24 26 34 40 40 56 Z"),
                p("M50 62 C34 46 34 22 50 6 C66 22 66 46 50 62 Z"),
                p("M50 62 C78 62 94 44 92 18 C76 26 66 40 60 56 Z"),
            ),
            body("eye", c(20, 30, 4.5), c(50, 20, 4.5), c(80, 30, 4.5)),
            body("eye2", c(20, 30, 2), c(50, 20, 2), c(80, 30, 2)),
            body(
                "main",
                p("M50 40 C60 40 66 50 66 64 C66 78 58 90 50 90 C42 90 34 78 34 64 C34 50 40 40 50 40 Z"),
            ),
            body("main", c(50, 40, 10)),
            line(p("M50 30 L46 20 M50 30 L50 18 M50 30 L54 20")),
            ink(c(46, 20, 1.8), c(50, 18, 1.8), c(54, 20, 1.8)),
            *eyes((46, 39), (54, 39), 2.2),
            body("beak", p("M47 45 L53 45 L50 50 Z")),
        ),
        main=TEAL,
        tail=LEAF,
        eye=BLUE,
        eye2=GOLD,
        beak=GOLD,
    ),
    _pic(
        "envelope",
        "ظَرْف",
        "envelope",
        "home",
        (
            body("main", rect(10, 28, 80, 54, 4)),
            body("flap", p("M10 32 L50 62 L90 32")),
            line(p("M10 82 L40 56 M90 82 L60 56")),
            body("stamp", rect(70, 34, 12, 12, 1.5)),
        ),
        main=CREAM,
        flap="#F6E5C4",
        stamp=CORAL,
    ),
)

LETTER_WORDS_C = (
    # draft: educator review: ظِلّ is a tree with its shadow on the ground
    _pic(
        "shadow",
        "ظِلّ",
        "shadow",
        "nature",
        (
            body("shade", p("M52 84 C70 82 92 84 96 90 L60 92 C50 92 44 90 42 86 Z")),
            body("trunk", p("M40 84 L42 56 L50 56 L52 84 Z")),
            body(
                "main",
                p(
                    "M30 58 C16 58 12 40 22 34 C18 20 32 10 44 16 C50 4 70 6 72 20 "
                    "C84 20 90 36 82 44 C90 54 78 66 66 60 C58 68 40 68 30 58 Z"
                ),
            ),
            body("sun", c(84, 14, 7)),
        ),
        main=LEAF,
        trunk=BROWN,
        shade="#B8B2A6",
        sun=YELLOW,
    ),
    _pic(
        "honey",
        "عَسَل",
        "honey",
        "food",
        (
            body("lid", rect(30, 12, 40, 12, 3)),
            body("main", p("M28 24 L72 24 L72 82 C72 87 68 90 63 90 L37 90 C32 90 28 87 28 82 Z")),
            body("honey", p("M31 40 L69 40 L69 82 C69 85 67 87 63 87 L37 87 C33 87 31 85 31 82 Z")),
            body("label", rect(38, 50, 24, 18, 3)),
            body("bee", e(50, 59, 5, 3.5)),
            line(p("M47 57 L47 61 M50 56 L50 62 M53 57 L53 61")),
            shine(rect(34, 44, 3, 36, 1.5)),
        ),
        main=SKY_LIGHT,
        honey=GOLD,
        lid=BROWN,
        label=WHITE,
        bee=YELLOW,
    ),
    _pic(
        "eye",
        "عَيْن",
        "eye",
        "body",
        (
            body("main", p("M8 50 C22 26 78 26 92 50 C78 74 22 74 8 50 Z")),
            body("iris", c(50, 50, 16)),
            ink(c(50, 50, 8)),
            glint(c(55, 45, 3)),
            line(p("M20 34 L16 28 M36 26 L34 19 M50 24 L50 16 M64 26 L66 19 M80 34 L84 28")),
        ),
        main=WHITE,
        iris=TEAL,
    ),
    _pic(
        "forest",
        "غابَة",
        "forest",
        "nature",
        (
            body("ground", p("M4 92 L96 92 L96 84 C70 80 30 80 4 84 Z")),
            body("trunk", rect(18, 66, 6, 22, 2), rect(47, 60, 7, 28, 2), rect(76, 66, 6, 22, 2)),
            body("main", p("M21 14 L40 52 L2 52 Z"), p("M21 32 L44 70 L-2 70 Z")),
            body("main", p("M79 14 L98 52 L60 52 Z"), p("M79 32 L102 70 L56 70 Z")),
            body("second", p("M50 6 L74 46 L26 46 Z"), p("M50 26 L78 66 L22 66 Z")),
        ),
        main=LEAF_DARK,
        second=LEAF,
        trunk=BROWN,
        ground="#DDEFD6",
    ),
    _pic(
        "washer",
        "غَسّالَة",
        "washing machine",
        "home",
        (
            body("main", rect(16, 8, 68, 84, 6)),
            line(p("M16 24 L84 24")),
            body("knob", c(28, 16, 3.5), c(40, 16, 3.5)),
            body("panel", rect(58, 12, 20, 8, 2)),
            body("door", c(50, 58, 24)),
            body("glass", c(50, 58, 17)),
            body(
                "water",
                p("M35 62 C40 58 45 66 50 62 C55 58 60 66 65 62 C66 70 60 75 50 75 C40 75 34 70 35 62 Z"),
            ),
            shine(e(42, 50, 3, 5, 30)),
        ),
        main=WHITE,
        door=GRAY,
        glass=SKY_LIGHT,
        water=SKY,
        knob=SLATE,
        panel=SKY,
    ),
    _pic(
        "submarine",
        "غَوّاصَة",
        "submarine",
        "vehicle",
        (
            body("tower", rect(42, 28, 20, 18, 3)),
            line(p("M52 28 L52 16 L62 16")),
            body(
                "main",
                p(
                    "M14 60 C14 46 26 42 40 42 L70 42 C84 42 92 50 92 60 "
                    "C92 70 84 78 70 78 L40 78 C26 78 14 74 14 60 Z"
                ),
            ),
            body("fin", p("M14 54 L4 46 L4 74 L14 66 Z")),
            body("window", c(34, 60, 6), c(52, 60, 6), c(70, 60, 6)),
            body("bubble", c(80, 24, 3), c(88, 14, 2.2), c(76, 10, 1.6)),
        ),
        main=YELLOW,
        tower=GOLD,
        fin=GOLD,
        window=SKY_LIGHT,
        bubble=SKY_LIGHT,
    ),
    _pic(
        "triangle",
        "مُثَلَّث",
        "triangle",
        "shape",
        (
            body("main", p("M50 14 L90 84 L10 84 Z")),
            shine(p("M46 34 L52 34 L36 62 L30 62 Z")),
        ),
        main=BLUE,
    ),
)

LETTER_WORDS_D = (
    _pic(
        "key",
        "مِفْتاح",
        "key",
        "home",
        (
            body(
                "main",
                p(
                    "M28 26 C28 14 38 8 48 8 C58 8 68 14 68 26 C68 34 62 40 56 44 L56 84 L48 84 "
                    "L48 78 L40 78 L40 70 L48 70 L48 64 L40 64 L40 56 L48 56 L48 44 C36 40 28 34 28 26 Z"
                ),
            ),
            body("hole", c(48, 24, 6)),
            shine(e(38, 22, 3, 5, 20)),
        ),
        main=GOLD,
        hole=WHITE,
    ),
    _pic(
        "palm",
        "نَخْلَة",
        "palm tree",
        "plant",
        (
            body("trunk", p("M46 92 L44 40 L56 40 L54 92 Z")),
            line(p("M45 52 L55 52 M45 62 L55 62 M45 72 L55 72 M45 82 L55 82")),
            body("date", c(44, 42, 3.5), c(56, 42, 3.5), c(50, 46, 3.5)),
            body(
                "main",
                p("M50 38 C36 30 18 30 8 40 C22 36 36 38 50 44 Z"),
                p("M50 38 C64 30 82 30 92 40 C78 36 64 38 50 44 Z"),
            ),
            body(
                "main",
                p("M50 38 C38 26 30 12 34 4 C42 12 48 24 50 38 Z"),
                p("M50 38 C62 26 70 12 66 4 C58 12 52 24 50 38 Z"),
            ),
            body(
                "main",
                p("M50 38 C40 20 22 14 12 20 C26 22 38 30 50 42 Z"),
                p("M50 38 C60 20 78 14 88 20 C74 22 62 30 50 42 Z"),
            ),
        ),
        main=LEAF,
        trunk=CHESTNUT,
        date=DARK_BROWN,
    ),
    _pic(
        "ostrich",
        "نَعامَة",
        "ostrich",
        "bird",
        (
            line(p("M44 82 L40 96 M36 96 L44 96 M56 82 L60 96 M56 96 L64 96")),
            body("main", e(50, 66, 22, 18)),
            body("wing", p("M36 62 C42 54 56 54 62 64 C54 70 44 70 36 62 Z")),
            body("neck", p("M58 52 C62 40 64 28 66 18 L72 20 C70 32 68 44 66 56 Z")),
            body("main", c(70, 14, 8)),
            *eyes((68, 12), (68, 12), 2.2),
            body("beak", p("M77 12 L86 15 L77 18 Z")),
            line(p("M64 6 L66 2 M70 5 L71 1")),
        ),
        main=SLATE,
        wing=GRAY,
        neck=SKIN,
        beak=ORANGE,
    ),
    _pic(
        "hand",
        "يَد",
        "hand",
        "body",
        (
            body(
                "main",
                p(
                    "M30 92 L30 60 C30 52 24 44 22 36 C21 30 28 28 31 34 L36 48 L36 22 C36 16 44 16 44 22 "
                    "L44 44 L46 14 C46 8 54 8 54 14 L54 44 L57 20 C58 14 66 15 65 21 L63 46 L66 30 "
                    "C68 24 76 26 74 32 L70 60 C70 72 66 80 62 92 Z"
                ),
            ),
            line(p("M44 44 L44 54 M54 44 L54 54")),
            cheeks((50, 72), (50, 72), 5),
        ),
        main=SKIN,
    ),
    _pic(
        "parrot",
        "بَبَّغاء",
        "parrot",
        "bird",
        (
            line(p("M40 84 L36 92 M34 92 L42 92 M54 84 L58 92 M52 92 L60 92")),
            body("tail", p("M42 78 C34 88 26 94 20 92 C24 84 30 78 40 72 Z")),
            body(
                "main",
                p("M48 26 C64 26 72 40 70 56 C68 72 60 84 48 84 C38 84 32 74 32 60 C32 44 36 26 48 26 Z"),
            ),
            body("wing", p("M42 46 C50 42 62 46 64 60 C60 68 50 70 42 64 Z")),
            body("belly", e(48, 70, 9, 10)),
            body("main", c(50, 24, 12)),
            *eyes((54, 21), (54, 21), 2.6),
            body("beak", p("M60 22 C70 22 70 34 60 36 C64 30 64 26 60 22 Z")),
        ),
        main=RED,
        wing=BLUE,
        belly=YELLOW,
        tail=LEAF,
        beak=GRAY,
    ),
    _pic(
        "rope",
        "حَبْل",
        "rope",
        "tool",
        (
            body(
                "main",
                p(
                    "M14 40 C24 24 40 24 50 40 C60 56 76 56 86 40 "
                    "L90 46 C78 64 58 64 46 46 C38 34 28 34 20 46 Z"
                ),
            ),
            body(
                "main",
                p(
                    "M14 60 C24 44 40 44 50 60 C60 76 76 76 86 60 "
                    "L90 66 C78 84 58 84 46 66 C38 54 28 54 20 66 Z"
                ),
            ),
            line(
                p(
                    "M24 38 L28 44 M36 31 L38 36 M56 48 L60 54 M70 53 "
                    "L72 48 M24 58 L28 64 M56 68 L60 74 M70 73 L72 68"
                )
            ),
        ),
        main=SAND,
    ),
    _pic(
        "stairs",
        "دَرَج",
        "stairs",
        "home",
        (
            body("main", p("M10 90 L10 74 L30 74 L30 58 L50 58 L50 42 L70 42 L70 26 L90 26 L90 90 Z")),
            line(p("M14 74 L26 74 M34 58 L46 58 M54 42 L66 42 M74 26 L86 26")),
            body("rail", p("M8 66 L88 10 L92 14 L12 70 Z")),
            line(p("M30 52 L30 58 M50 38 L50 42 M70 24 L70 26")),
        ),
        main=TAN,
        rail=BROWN,
    ),
    _pic(
        "loaf",
        "رَغيف",
        "loaf",
        "food",
        (
            body("main", e(50, 54, 40, 22)),
            body("inner", e(50, 52, 28, 12)),
            line(p("M30 50 C36 44 44 46 50 50 C56 54 64 56 70 50")),
            shine(e(30, 44, 5, 3, -20)),
        ),
        main=SAND,
        inner="#F4E2C0",
    ),
)

ENGLISH_WORDS = (
    _pic(
        "ice-cream",
        "بوظَة",
        "ice cream",
        "sweet",
        (
            body("cone", p("M30 50 L70 50 L50 94 Z")),
            line(p("M38 58 L58 66 M34 66 L50 76 M46 58 L64 58")),
            body("main", c(50, 40, 20)),
            body("top", c(42, 28, 12), c(58, 26, 12)),
            body("cherry", c(52, 12, 5)),
            line(p("M52 8 C54 4 56 4 58 2")),
            shine(e(38, 40, 3, 5, 20)),
        ),
        main=PINK,
        top=CREAM,
        cone=SAND,
        cherry=RED,
    ),
    _pic(
        "insect",
        "دَعْسوقَة",
        "insect",
        "insect",
        (
            line(p("M40 24 L34 12 M60 24 L66 12 M22 52 L10 48 M22 62 L10 66 M78 52 L90 48 M78 62 L90 66")),
            ink(c(34, 12, 2.4), c(66, 12, 2.4)),
            body(
                "main",
                p("M50 30 C72 30 84 46 84 62 C84 78 68 90 50 90 C32 90 16 78 16 62 C16 46 28 30 50 30 Z"),
            ),
            line(p("M50 32 L50 90")),
            ink(c(36, 50, 4.5), c(64, 50, 4.5), c(30, 70, 4), c(70, 70, 4), c(50, 62, 3.5)),
            body("head", e(50, 30, 14, 9)),
            *eyes((45, 29), (55, 29), 2.2),
        ),
        main=RED,
        head=SLATE,
    ),
    _pic(
        "jacket",
        "سُتْرَة",
        "jacket",
        "clothes",
        (
            body("sleeve", p("M26 30 L10 62 L22 68 L32 46 Z"), p("M74 30 L90 62 L78 68 L68 46 Z")),
            body("main", p("M26 30 L40 22 L50 30 L60 22 L74 30 L74 88 L26 88 Z")),
            body("collar", p("M40 22 L50 34 L60 22 L54 20 L50 26 L46 20 Z")),
            line(p("M50 34 L50 88")),
            ink(c(46, 48, 1.8), c(46, 62, 1.8), c(46, 76, 1.8)),
            body("pocket", rect(30, 62, 12, 12, 2), rect(58, 62, 12, 12, 2)),
        ),
        main=TEAL,
        sleeve="#3E8C80",
        collar="#3E8C80",
        pocket="#3E8C80",
    ),
    _pic(
        "jar",
        "مَرْطَبان",
        "jar",
        "home",
        (
            body("lid", rect(28, 12, 44, 12, 3)),
            body("main", p("M26 26 L74 26 L74 82 C74 88 70 92 64 92 L36 92 C30 92 26 88 26 82 Z")),
            body("jam", p("M29 44 L71 44 L71 82 C71 86 69 89 64 89 L36 89 C31 89 29 86 29 82 Z")),
            body("label", rect(38, 54, 24, 16, 3)),
            shine(rect(32, 32, 3, 50, 1.5)),
        ),
        main=SKY_LIGHT,
        jam=PURPLE,
        lid=RED,
        label=WHITE,
    ),
    _pic(
        "monkey",
        "قِرْد",
        "monkey",
        "animal",
        (
            line(p("M70 70 C86 66 92 50 84 40")),
            body("main", c(26, 42, 10), c(74, 42, 10)),
            body("inner", c(26, 42, 5), c(74, 42, 5)),
            body("main", e(50, 74, 22, 18)),
            body("inner", e(50, 78, 12, 10)),
            body("main", c(50, 42, 24)),
            body(
                "inner",
                p("M32 44 C32 30 42 26 50 34 C58 26 68 30 68 44 C68 58 58 64 50 64 C42 64 32 58 32 44 Z"),
            ),
            *eyes((42, 40), (58, 40), 3),
            ink(e(46, 50, 1.4, 1.1), e(54, 50, 1.4, 1.1)),
            _smile(50, 55, 4),
            cheeks((38, 50), (62, 50), 3.5),
        ),
        main=BROWN,
        inner=SKIN,
    ),
    _pic(
        "nose",
        "أَنْف",
        "nose",
        "body",
        (
            body(
                "main",
                p(
                    "M52 14 C54 30 58 46 66 58 C72 68 66 80 54 80 C48 80 46 76 44 74 "
                    "C42 76 40 80 34 80 C24 80 20 68 28 58 C30 56 32 54 34 50 Z"
                ),
            ),
            line(p("M38 72 C40 76 44 76 44 74 M64 72 C62 76 58 76 56 74")),
            shine(e(48, 36, 3, 8, 10)),
        ),
        main=SKIN,
    ),
)

ENGLISH_WORDS_B = (
    _pic(
        "octopus",
        "أُخْطُبوط",
        "octopus",
        "animal",
        (
            body(
                "main",
                p("M22 60 C14 70 12 84 20 90 C26 84 26 74 30 66 Z"),
                p("M34 66 C30 78 30 90 40 94 C42 84 40 76 42 68 Z"),
            ),
            body(
                "main",
                p("M78 60 C86 70 88 84 80 90 C74 84 74 74 70 66 Z"),
                p("M66 66 C70 78 70 90 60 94 C58 84 60 76 58 68 Z"),
            ),
            body("main", p("M50 68 C46 78 48 88 50 94 C52 88 54 78 50 68 Z")),
            body(
                "main",
                p("M50 10 C70 10 82 26 82 44 C82 60 68 70 50 70 C32 70 18 60 18 44 C18 26 30 10 50 10 Z"),
            ),
            *eyes((42, 40), (58, 40), 3.4),
            _smile(50, 50, 4),
            cheeks((36, 50), (64, 50), 4),
            shine(e(36, 26, 4, 7, 20)),
        ),
        main=PURPLE,
    ),
    _pic(
        "pencil",
        "قَلَم رَصاص",
        "pencil",
        "school",
        (
            body("eraser", p("M60 8 L80 28 L74 34 L54 14 Z")),
            body("band", p("M54 14 L74 34 L68 40 L48 20 Z")),
            body("main", p("M48 20 L68 40 L32 76 L12 56 Z")),
            line(p("M40 28 L60 48 M42 26 L62 46")),
            body("wood", p("M12 56 L32 76 L14 84 L4 74 Z")),
            ink(p("M9 79 L4 74 L14 84 Z")),
        ),
        main=YELLOW,
        eraser=PINK,
        band=GRAY,
        wood=SAND,
    ),
    _pic(
        "queen",
        "مَلِكَة",
        "queen",
        "person",
        (
            body("dress", p("M30 92 C30 70 36 60 50 58 C64 60 70 70 70 92 Z")),
            body("main", c(50, 40, 17)),
            body(
                "hair",
                p("M33 40 C30 22 44 16 50 22 C56 16 70 22 67 40 C64 36 60 30 50 30 C40 30 36 36 33 40 Z"),
            ),
            body("crown", p("M36 22 L34 8 L42 16 L50 6 L58 16 L66 8 L64 22 Z")),
            body("gem", c(50, 14, 2.6), c(37, 12, 2), c(63, 12, 2)),
            *eyes((44, 40), (56, 40), 2.6),
            _smile(50, 47, 3.5),
            cheeks((40, 46), (60, 46), 3),
        ),
        main=SKIN,
        hair=DARK_BROWN,
        dress=PURPLE,
        crown=GOLD,
        gem=RED,
    ),
    _pic(
        "quilt",
        "لِحاف",
        "quilt",
        "home",
        (
            body("main", rect(12, 16, 76, 68, 5)),
            body(
                "patch",
                rect(12, 16, 19, 17, 2),
                rect(50, 16, 19, 17, 2),
                rect(31, 33, 19, 17, 2),
                rect(69, 33, 19, 17, 2),
            ),
            body(
                "patch",
                rect(12, 50, 19, 17, 2),
                rect(50, 50, 19, 17, 2),
                rect(31, 67, 19, 17, 2),
                rect(69, 67, 19, 17, 2),
            ),
            line(p("M12 33 L88 33 M12 50 L88 50 M12 67 L88 67 M31 16 L31 84 M50 16 L50 84 M69 16 L69 84")),
        ),
        main=SKY_LIGHT,
        patch=CORAL,
    ),
    _pic(
        "ring",
        "خاتَم",
        "ring",
        "thing",
        (
            body("gem", p("M50 6 L64 20 L50 34 L36 20 Z")),
            body("main", c(50, 58, 28)),
            body("hole", c(50, 58, 19)),
            shine(e(36, 48, 3, 7, 40)),
        ),
        main=GOLD,
        hole="#FFFDF9",
        gem=SKY,
    ),
)

EXTRA = (
    _pic(
        "sprout",
        "نَبْتَة",
        "sprout",
        "plant",
        (
            body(
                "soil", p("M14 76 C30 70 70 70 86 76 L86 88 C86 91 84 92 81 92 L19 92 C16 92 14 91 14 88 Z")
            ),
            body("stem", p("M48.5 76 L48.5 46 L51.5 46 L51.5 76 Z")),
            body(
                "main",
                p("M50 48 C40 34 24 34 18 40 C28 50 42 52 50 48 Z"),
                p("M50 48 C60 34 76 34 82 40 C72 50 58 52 50 48 Z"),
            ),
            line(p("M50 48 C40 44 32 42 24 40 M50 48 C60 44 68 42 76 40")),
        ),
        main=LEAF,
        stem=LEAF_DARK,
        soil=BROWN,
    ),
)

WORKBOOK_WORDS_2: dict[str, Picture] = {
    pic.id: pic
    for pic in (
        *LETTER_WORDS_A,
        *LETTER_WORDS_B,
        *LETTER_WORDS_C,
        *LETTER_WORDS_D,
        *ENGLISH_WORDS,
        *ENGLISH_WORDS_B,
        *EXTRA,
    )
}
# plan words spelled differently from the library word (the picture's own word is printed)
WORD_ALIASES_2 = {"صابون": "soap", "مثلث": "triangle", "طائرة ورقية": "kite", "ice cream": "ice-cream"}
