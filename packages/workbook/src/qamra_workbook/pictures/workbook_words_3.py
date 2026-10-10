"""Pictures for the words of «دوسية التأسيس» Volume 3 (letters ف–ي, the reading words, the English vocabulary
units S–Z), in the library's style. The number, colour and shape words are drawn by code (`counted`,
`swatch`, `plain_shape`); the rest by hand. Every picture also has a line-art version.
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
SKIN = "#F2C9A6"
SKIN_DARK = "#D9A277"
NAVY = "#3C468F"
BLACK = "#2B2E4A"
# the dice layouts up to five (as `puzzles.counting.LAYOUTS`; kept here so the library imports no puzzles)
DICE: dict[int, tuple[tuple[float, float], ...]] = {
    1: ((0.5, 0.5),),
    2: ((0.27, 0.5), (0.73, 0.5)),
    3: ((0.5, 0.26), (0.26, 0.72), (0.74, 0.72)),
    4: ((0.28, 0.28), (0.72, 0.28), (0.28, 0.72), (0.72, 0.72)),
    5: ((0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)),
}
STAR_PTS = "M50 8 L60 36 L90 36 L66 54 L75 84 L50 66 L25 84 L34 54 L10 36 L40 36 Z"


def _pic(id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str) -> Picture:
    return Picture(id, ar, en, category, parts, palette)


def _smile(x: float, y: float, w: float = 4.5) -> Part:
    return line(p(f"M{x - w} {y} Q{x} {y + w * 0.9} {x + w} {y}"))


# ---- drawn by code: numbers as stars in the dice layouts (up to five) or two rows, colours, shapes ---------
NUMBER_WORDS = (
    ("one", "واحِد"),
    ("two", "اثْنان"),
    ("three", "ثَلاثَة"),
    ("four", "أَرْبَعَة"),
    ("five", "خَمْسَة"),
    ("six", "سِتَّة"),
    ("seven", "سَبْعَة"),
    ("eight", "ثَمانِيَة"),
    ("nine", "تِسْعَة"),
    ("ten", "عَشَرَة"),
)


def _star(cx: float, cy: float, r: float) -> str:
    return p(
        " ".join(
            ("M" if i == 0 else "L") + f"{cx + r * dx:.1f} {cy + r * dy:.1f}"
            for i, (dx, dy) in enumerate(
                (
                    (0, -1),
                    (0.24, -0.31),
                    (0.95, -0.31),
                    (0.38, 0.12),
                    (0.59, 0.81),
                    (0, 0.38),
                    (-0.59, 0.81),
                    (-0.38, 0.12),
                    (-0.95, -0.31),
                    (-0.24, -0.31),
                )
            )
        )
        + " Z"
    )


def counted(n: int, word_en: str, word_ar: str) -> Picture:
    """`n` stars: the dice layout up to five, two rows of up to five above."""
    if n <= 5:
        spots = [(50 + (u - 0.5) * 70, 50 + (v - 0.5) * 70) for u, v in DICE[n]]
        r = 15.0
    else:
        top = n - 5
        spots = [(14.0 + k * 18, 32.0) for k in range(top)] + [(14.0 + k * 18, 68.0) for k in range(5)]
        r = 8.5
    return _pic(
        word_en, word_ar, word_en, "number", (body("main", *(_star(x, y, r) for x, y in spots)),), main=YELLOW
    )


COLOR_WORDS = (
    ("red", "أَحْمَر", RED),
    ("blue", "أَزْرَق", BLUE),
    ("yellow", "أَصْفَر", YELLOW),
    ("green", "أَخْضَر", LEAF),
    ("purple", "بَنَفْسَجِيّ", PURPLE),
    ("black", "أَسْوَد", BLACK),
    ("white", "أَبْيَض", WHITE),
)


def swatch(word_en: str, word_ar: str, color: str) -> Picture:
    """A crayon of the colour with a scribble of it beside."""
    return _pic(
        word_en,
        word_ar,
        word_en,
        "color",
        (
            body("main", p("M20 78 L62 36 L74 48 L32 90 Z")),
            body("main", p("M20 78 L32 90 L14 92 Z")),
            body("band", p("M56 42 L68 54 L62 60 L50 48 Z")),
            body("main", p("M62 36 L74 48 L86 36 L74 24 Z")),
            body("main", p("M54 20 C64 10 84 12 90 22 C84 30 66 26 60 36 Z")),
        ),
        main=color,
        band="#FFFFFF",
    )


SHAPE_WORDS = (
    ("circle", "دائِرَة", c(50, 50, 36)),
    ("square", "مُرَبَّع", rect(16, 16, 68, 68, 4)),
    ("rectangle", "مُسْتَطيل", rect(8, 28, 84, 44, 4)),
)


def plain_shape(word_en: str, word_ar: str, element: str, color: str) -> Picture:
    return _pic(
        word_en, word_ar, word_en, "shape", (body("main", element), shine(e(36, 38, 5, 9, 25))), main=color
    )


CODED: tuple[Picture, ...] = (
    *(counted(k + 1, en, ar) for k, (en, ar) in enumerate(NUMBER_WORDS)),
    *(swatch(en, ar, color) for en, ar, color in COLOR_WORDS),
    *(
        plain_shape(en, ar, el, color)
        for (en, ar, el), color in zip(SHAPE_WORDS, (CORAL, LEAF, SKY), strict=True)
    ),
)


# ---- drawn by hand: the letter words of ف–ي --------------------------------------------------------------
ARABIC_WORDS = (
    _pic(
        "mouse",
        "فَأْر",
        "mouse",
        "animal",
        (
            line(p("M72 70 C86 66 94 54 88 40")),
            body("main", c(30, 40, 12), c(66, 40, 12)),
            body("inner", c(30, 40, 6), c(66, 40, 6)),
            body(
                "main",
                p("M48 32 C66 32 78 46 76 62 C74 76 62 84 48 84 C34 84 20 76 20 62 C18 46 30 32 48 32 Z"),
            ),
            *eyes((40, 52), (56, 52), 3),
            body("nose", c(48, 66, 3.5)),
            line(p("M30 64 L16 60 M30 68 L16 72 M66 64 L80 60 M66 68 L80 72")),
            cheeks((36, 62), (60, 62), 3.5),
        ),
        main=GRAY,
        inner=PINK,
        nose="#E97A98",
    ),
    _pic(
        "dress",
        "فُسْتان",
        "dress",
        "clothes",
        (
            body("main", p("M38 8 L62 8 L66 28 L58 34 L58 44 L84 90 L16 90 L42 44 L42 34 L34 28 Z")),
            body("belt", rect(40, 40, 20, 6, 2)),
            line(p("M32 68 L68 68 M26 80 L74 80")),
            body("dots", c(46, 58, 2), c(58, 62, 2), c(38, 74, 2), c(64, 74, 2), c(52, 86, 2)),
        ),
        main=PINK,
        belt=PURPLE,
        dots=WHITE,
    ),
    _pic(
        "glass",
        "كَأْس",
        "glass",
        "home",
        (
            body("main", p("M28 12 L72 12 L66 90 L34 90 Z")),
            body("water", p("M33 50 L67 50 L64 87 L36 87 Z")),
            line(p("M38 56 C46 52 54 58 62 54")),
            shine(rect(40, 20, 4, 28, 2)),
        ),
        main=SKY_LIGHT,
        water=SKY,
    ),
    _pic(
        "chair",
        "كُرْسِيّ",
        "chair",
        "home",
        (
            body("leg", rect(24, 64, 6, 28, 2), rect(70, 64, 6, 28, 2)),
            body("main", p("M20 10 L30 10 L32 52 L20 52 Z")),
            line(p("M24 20 L28 20 M24 30 L28 30 M24 40 L28 40")),
            body("main", p("M30 14 L38 14 L38 52 L30 52 Z")),
            body("seat", p("M18 52 L82 52 L82 64 L18 64 Z")),
        ),
        main=CHESTNUT,
        seat=TAN,
        leg=BROWN,
    ),
    # draft: educator review: لُعبة (decision 7) is drawn as a toy train
    _pic(
        "toy",
        "لُعْبَة",
        "toy",
        "toy",
        (
            body("wheel", c(24, 78, 8), c(48, 78, 8), c(72, 78, 8)),
            body("main", rect(10, 48, 40, 24, 4)),
            body("cab", rect(50, 30, 34, 42, 4)),
            body("window", rect(58, 38, 18, 14, 2)),
            body("chimney", rect(18, 32, 12, 18, 2)),
            body("smoke", c(24, 22, 6), c(34, 14, 4.5)),
            line(p("M50 56 L84 56")),
        ),
        main=RED,
        cab=BLUE,
        window=SKY_LIGHT,
        chimney=SLATE,
        wheel=BLACK,
        smoke=GRAY,
    ),
    _pic(
        "almonds",
        "لَوْز",
        "almonds",
        "food",
        (
            body("main", e(34, 40, 12, 20, -25), e(64, 46, 12, 20, 20), e(50, 70, 12, 20, -5)),
            line(p("M30 26 L38 54 M60 32 L68 60 M50 56 L50 84")),
            shine(e(28, 34, 3, 6, -25), e(58, 40, 3, 6, 20)),
        ),
        main=TAN,
    ),
    _pic(
        "tiger",
        "نَمِر",
        "tiger",
        "animal",
        (
            body("main", c(28, 26, 10), c(72, 26, 10)),
            body("inner", c(28, 26, 5), c(72, 26, 5)),
            body(
                "main",
                p("M50 18 C72 18 84 34 82 54 C80 74 66 86 50 86 C34 86 20 74 18 54 C16 34 28 18 50 18 Z"),
            ),
            ink(
                p("M34 24 L40 36 L30 36 Z"),
                p("M66 24 L60 36 L70 36 Z"),
                p("M20 52 L30 50 L26 60 Z"),
                p("M80 52 L70 50 L74 60 Z"),
            ),
            body("inner", e(50, 66, 16, 12)),
            *eyes((40, 48), (60, 48), 3.2),
            ink(e(50, 60, 4, 3)),
            line(p("M50 63 L50 68 M44 70 Q50 74 56 70")),
            line(p("M32 64 L20 62 M32 68 L20 72 M68 64 L80 62 M68 68 L80 72")),
        ),
        main=ORANGE,
        inner=CREAM,
    ),
    _pic(
        "hoopoe",
        "هُدْهُد",
        "hoopoe",
        "bird",
        (
            body("crest", p("M54 30 L46 10 L52 28 L54 6 L58 28 L64 10 L60 30 Z")),
            line(p("M40 84 L36 94 M32 94 L42 94 M52 84 L54 94 M50 94 L58 94")),
            body(
                "main",
                p(
                    "M56 30 C68 30 74 42 70 56 C66 72 56 84 44 84 C30 84 20 72 22 58 "
                    "C24 44 38 36 48 36 C50 32 52 30 56 30 Z"
                ),
            ),
            body("wing", p("M30 58 C40 48 56 52 58 66 C50 72 38 70 30 58 Z")),
            line(p("M34 56 L52 64 M34 62 L50 68")),
            body("beak", p("M66 34 L92 30 L66 40 Z")),
            *eyes((60, 36), (60, 36), 2.4),
        ),
        main=CORAL,
        crest=CORAL,
        wing=BLACK,
        beak=SLATE,
    ),
    _pic(
        "crescent",
        "هِلال",
        "crescent",
        "sky",
        (
            body(
                "main",
                p("M62 8 C34 14 20 40 30 66 C36 82 50 92 66 92 C46 82 38 58 48 38 C52 26 56 16 62 8 Z"),
            ),
            body("star", _star(74, 30, 7)),
            shine(e(42, 50, 3, 12, 10)),
        ),
        main=YELLOW,
        star=GOLD,
    ),
    _pic(
        "goose",
        "وَزَّة",
        "goose",
        "bird",
        (
            line(p("M40 82 L38 94 M34 94 L44 94 M54 82 L56 94 M50 94 L60 94")),
            body(
                "main",
                p(
                    "M22 62 C22 46 34 40 50 40 L62 40 C70 40 76 52 74 64 "
                    "C72 76 62 84 48 84 C34 84 22 76 22 62 Z"
                ),
            ),
            body("neck", p("M60 44 C62 32 62 22 66 14 L76 16 C72 26 72 36 70 46 Z")),
            body("main", c(74, 14, 9)),
            body("beak", p("M82 12 L94 16 L82 20 Z")),
            *eyes((74, 12), (74, 12), 2.2),
            body("wing", p("M36 56 C44 48 58 50 62 62 C54 68 42 66 36 56 Z")),
        ),
        main=WHITE,
        neck=WHITE,
        wing="#E4E8F0",
        beak=ORANGE,
    ),
    _pic(
        "dove-y",
        "يَمامَة",
        "dove",
        "bird",
        (
            body("main", p("M24 58 L8 50 L11 66 Z")),
            body(
                "main",
                p(
                    "M20 60 C20 45 33 37 47 38 C53 30 63 26 71 30 C77 33 79 40 77 46 "
                    "C76 64 64 74 48 74 C36 74 22 70 20 60 Z"
                ),
            ),
            body("wing", p("M33 52 C41 43 58 45 62 58 C52 63 40 62 33 52 Z")),
            body("beak", p("M77 42 L88 45 L77 49 Z")),
            line(p("M44 74 L42 83 M40 83 L45 83 M54 74 L55 83 M52 83 L58 83")),
            *eyes((68, 36), (68, 36), 2.4),
            body("ring", p("M56 46 C62 44 70 44 74 48 L72 52 C68 50 62 50 57 51 Z")),
        ),
        main="#E9D9C2",
        wing="#D6C3A5",
        beak=ORANGE,
        ring=BLACK,
    ),
    _pic(
        "berries",
        "تُوت",
        "berries",
        "fruit",
        (
            body("leaf", p("M50 26 C40 12 26 12 20 20 C30 30 42 32 50 26 Z")),
            line(p("M50 26 L52 10")),
            body(
                "main",
                *(
                    c(x, y, 7)
                    for x, y in (
                        (50, 34),
                        (42, 46),
                        (58, 46),
                        (50, 58),
                        (40, 62),
                        (60, 62),
                        (46, 74),
                        (56, 74),
                        (50, 86),
                    )
                ),
            ),
            shine(c(44, 42, 2), c(52, 56, 2), c(58, 70, 2)),
        ),
        main=PURPLE,
        leaf=LEAF,
    ),
)


# ---- the reading words: a child writing, drawing, eating, playing (draft: educator review) --------------
def _child(hair: str, extra: tuple[Part, ...]) -> tuple[Part, ...]:
    return (
        body("shirt", p("M30 96 L30 72 C30 60 40 56 50 56 C60 56 70 60 70 72 L70 96 Z")),
        body("skin", c(50, 38, 16)),
        body("hair", p(hair)),
        *eyes((44, 38), (56, 38), 2.4),
        _smile(50, 45, 3.5),
        cheeks((41, 44), (59, 44), 2.8),
        *extra,
    )


HAIR_SHORT = "M34 36 C32 20 44 14 50 16 C58 12 70 20 66 36 C62 28 56 26 50 28 C44 26 38 28 34 36 Z"
# a girl's hair, worn with two pigtails
HAIR_GIRL = "M34 42 C30 22 44 14 50 16 C56 14 70 22 66 42 C60 32 56 28 50 28 C44 28 40 32 34 42 Z"
DRAWING = (
    body("paper", p("M6 66 L46 66 L46 96 L6 96 Z")),
    body("sun", c(20, 78, 6)),
    body("grass", p("M8 92 L44 92 L44 96 L8 96 Z")),
    body("crayon", p("M60 62 L76 78 L72 82 L56 66 Z")),
)
ACTIONS = (
    _pic(
        "writing",
        "كَتَبَ",
        "writing",
        "action",
        _child(
            HAIR_SHORT,
            (
                body("paper", p("M6 70 L46 70 L46 96 L6 96 Z")),
                line(p("M12 78 L38 78 M12 84 L34 84 M12 90 L30 90")),
                body("pencil", p("M60 62 L76 78 L72 82 L56 66 Z")),
                ink(p("M56 66 L52 62 L60 62 Z")),
            ),
        ),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=SKY,
        paper=WHITE,
        pencil=YELLOW,
    ),
    _pic(
        "drawing",
        "رَسَمَ",
        "drawing",
        "action",
        _child(HAIR_SHORT, DRAWING),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=LEAF,
        paper=WHITE,
        sun=YELLOW,
        grass=LEAF,
        crayon=RED,
    ),
    _pic(  # «رَسَمَتْ سَلْمَى»: a girl draws, never the boy of «رَسَمَ»
        "drawing-girl",
        "رَسَمَتْ",
        "drawing",
        "action",
        _child(HAIR_GIRL, (body("hair", c(30, 44, 6), c(70, 44, 6)), *DRAWING)),
        skin=SKIN,
        hair=CHESTNUT,
        shirt=PINK,
        paper=WHITE,
        sun=YELLOW,
        grass=LEAF,
        crayon=RED,
    ),
    _pic(
        "eating",
        "أَكَلَ",
        "eating",
        "action",
        _child(
            HAIR_SHORT,
            (
                body("apple", c(64, 62, 9)),
                body("leaf", p("M66 53 C68 48 74 47 77 49 C74 54 69 55 66 53 Z")),
                body("skin", e(60, 74, 7, 5)),
            ),
        ),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=CORAL,
        apple=RED,
        leaf=LEAF,
    ),
    _pic(
        "playing",
        "لَعِبَ",
        "playing",
        "action",
        _child(
            HAIR_SHORT,
            (
                body("ball", c(76, 78, 13)),
                body("stripe", p("M76 65 A13 13 0 0 0 76 91 C70 84 70 72 76 65 Z")),
                body("skin", e(62, 70, 7, 5)),
            ),
        ),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=PURPLE,
        ball=YELLOW,
        stripe=RED,
    ),
)


# ---- family (the English unit): busts told apart by hair, glasses and size -------------------------------
def _bust(hair: str, extra: tuple[Part, ...] = (), *, big: bool = True) -> tuple[Part, ...]:
    r = 22 if big else 16
    return (
        body(
            "shirt",
            p(
                f"M{50 - r - 8} 96 C{50 - r - 8} 70 {50 - r} 62 50 62 "
                f"C{50 + r} 62 {50 + r + 8} 70 {50 + r + 8} 96 Z"
            ),
        ),
        body("skin", c(50, 40, r)),
        body("hair", p(hair)),
        *eyes((50 - r * 0.38, 40), (50 + r * 0.38, 40), r * 0.12),
        _smile(50, 40 + r * 0.32, r * 0.18),
        cheeks((50 - r * 0.6, 40 + r * 0.25), (50 + r * 0.6, 40 + r * 0.25), r * 0.15),
        *extra,
    )


GLASSES = line(
    p("M32 40 A6 6 0 1 0 44 40 A6 6 0 1 0 32 40 M56 40 A6 6 0 1 0 68 40 A6 6 0 1 0 56 40 M44 40 L56 40")
)
SCARF = "M22 44 C20 18 40 8 50 12 C60 8 80 18 78 44 C74 30 62 26 50 30 C38 26 26 30 22 44 Z"
FAMILY = (
    _pic("mother", "أُمّ", "mother", "family", _bust(SCARF), skin=SKIN, hair=PURPLE, shirt=CORAL),
    _pic(
        "father",
        "أَب",
        "father",
        "family",
        _bust(HAIR_SHORT, (ink(p("M42 50 C46 47 54 47 58 50 L56 53 C52 51 48 51 44 53 Z")),)),
        skin=SKIN_DARK,
        hair=DARK_BROWN,
        shirt=BLUE,
    ),
    _pic(
        "brother",
        "أَخ",
        "brother",
        "family",
        _bust(HAIR_SHORT, big=False),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=LEAF,
    ),
    _pic(
        "sister",
        "أُخْت",
        "sister",
        "family",
        _bust(
            "M34 44 C30 24 44 16 50 18 C56 16 70 24 66 44 C60 34 56 30 50 30 C44 30 40 34 34 44 Z",
            (body("hair", c(30, 46, 6), c(70, 46, 6)),),
            big=False,
        ),
        skin=SKIN,
        hair=CHESTNUT,
        shirt=PINK,
    ),
    _pic(
        "grandmother",
        "جَدَّة",
        "grandmother",
        "family",
        _bust(SCARF, (GLASSES,)),
        skin=SKIN,
        hair=WHITE,
        shirt="#4FA89A",
    ),
    _pic(
        "grandfather",
        "جَدّ",
        "grandfather",
        "family",
        _bust(HAIR_SHORT, (GLASSES, body("hair", p("M36 50 C40 62 60 62 64 50 C58 56 42 56 36 50 Z")))),
        skin=SKIN_DARK,
        hair=GRAY,
        shirt=BROWN,
    ),
    _pic(
        "baby",
        "طِفْل",
        "baby",
        "family",
        _bust(
            "M40 30 C42 22 48 18 50 22 C52 18 58 22 60 30 Z", (body("skin", e(50, 62, 20, 14)),), big=False
        ),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=YELLOW,
    ),
)


# ---- the English vocabulary units ----------------------------------------------------------------------
ENGLISH_A = (
    _pic(
        "bus",
        "حافِلَة",
        "bus",
        "vehicle",
        (
            body("main", rect(6, 26, 88, 50, 8)),
            body(
                "window",
                rect(14, 34, 16, 16, 3),
                rect(36, 34, 16, 16, 3),
                rect(58, 34, 16, 16, 3),
                rect(80, 34, 8, 16, 3),
            ),
            line(p("M6 60 L94 60")),
            body("tire", c(26, 78, 9), c(74, 78, 9)),
            body("hub", c(26, 78, 3.5), c(74, 78, 3.5)),
            body("light", c(10, 68, 3)),
        ),
        main=YELLOW,
        window=SKY_LIGHT,
        tire=SLATE,
        hub=GRAY,
        light=RED,
    ),
    _pic(
        "cheese",
        "جُبْنَة",
        "cheese",
        "food",
        (
            body("main", p("M10 70 L50 22 L90 46 L90 76 L10 76 Z")),
            body("side", p("M10 70 L90 46 L90 76 L10 76 Z")),
            body("hole", c(40, 62, 4), c(66, 60, 5), c(54, 70, 3)),
        ),
        main=YELLOW,
        side=GOLD,
        hole="#D9A21B",
    ),
    _pic(
        "crayon",
        "قَلَم تَلْوين",
        "crayon",
        "school",
        (
            body("main", p("M20 78 L62 36 L74 48 L32 90 Z")),
            body("main", p("M20 78 L32 90 L14 92 Z")),
            body("band", p("M56 42 L68 54 L62 60 L50 48 Z")),
            body("main", p("M62 36 L74 48 L86 36 L74 24 Z")),
        ),
        main=BLUE,
        band="#FFFFFF",
    ),
    _pic(
        "ear",
        "أُذُن",
        "ear",
        "body",
        (
            body(
                "main",
                p(
                    "M36 20 C36 8 56 6 64 14 C76 26 74 46 66 58 C60 68 56 76 56 86 "
                    "C56 92 44 94 42 86 C40 78 44 66 40 54 C34 42 36 30 36 20 Z"
                ),
            ),
            line(p("M46 22 C56 18 64 30 60 40 C58 46 52 46 50 40")),
        ),
        main=SKIN,
    ),
    _pic(
        "eraser",
        "مِمْحاة",
        "eraser",
        "school",
        (
            body("main", p("M14 56 L52 22 L86 50 L48 84 Z")),
            body("side", p("M14 56 L48 84 L48 92 L14 64 Z"), p("M48 84 L86 50 L86 58 L48 92 Z")),
            line(p("M32 40 L66 66")),
        ),
        main=PINK,
        side="#E28CA4",
    ),
    _pic(
        "fig",
        "تين",
        "fig",
        "fruit",
        (
            body("stem", p("M48 6 L52 6 L54 22 L46 22 Z")),
            body(
                "main",
                p("M50 18 C68 22 82 44 80 64 C78 82 64 92 50 92 C36 92 22 82 20 64 C18 44 32 22 50 18 Z"),
            ),
            body("inner", e(50, 66, 14, 12)),
            ink(c(44, 64, 1.5), c(56, 64, 1.5), c(50, 72, 1.5)),
            shine(e(34, 44, 3, 8, 15)),
        ),
        main=PURPLE,
        inner=PINK,
        stem=LEAF_DARK,
    ),
    _pic(
        "foot",
        "قَدَم",
        "foot",
        "body",
        (
            body(
                "main",
                p(
                    "M30 92 C18 92 14 76 22 60 C28 48 34 30 42 22 C48 16 56 20 54 30 "
                    "L52 54 C60 54 74 56 80 62 C88 70 84 86 70 92 Z"
                ),
            ),
            body("main", c(22, 26, 6), c(32, 20, 5), c(42, 16, 4.5), c(51, 16, 4), c(59, 20, 3.5)),
            line(p("M40 70 C52 66 62 70 70 78")),
        ),
        main=SKIN,
    ),
    _pic(
        "head",
        "رَأْس",
        "head",
        "body",
        (
            body("shirt", p("M22 96 C22 78 34 72 50 72 C66 72 78 78 78 96 Z")),
            body("skin", c(50, 44, 26)),
            body(
                "hair",
                p("M24 42 C22 18 40 8 50 12 C60 8 78 18 76 42 C70 30 62 26 50 28 C38 26 30 30 24 42 Z"),
            ),
            *eyes((41, 44), (59, 44), 2.8),
            _smile(50, 52, 4),
            cheeks((36, 50), (64, 50), 3.2),
        ),
        skin=SKIN,
        hair=DARK_BROWN,
        shirt=SKY,
    ),
    _pic(
        "mouth",
        "فَم",
        "mouth",
        "body",
        (
            body(
                "main",
                p("M14 48 C26 36 40 40 50 44 C60 40 74 36 86 48 C76 70 60 82 50 82 C40 82 24 70 14 48 Z"),
            ),
            body("teeth", p("M22 50 C36 46 64 46 78 50 L76 58 C62 54 38 54 24 58 Z")),
            line(p("M14 48 C30 50 70 50 86 48")),
        ),
        main=CORAL,
        teeth=WHITE,
    ),
    _pic(
        "pen",
        "قَلَم حِبْر",
        "pen",
        "school",
        (
            body("main", p("M24 74 L66 32 L76 42 L34 84 Z")),
            body("cap", p("M66 32 L76 42 L90 28 L80 18 Z")),
            ink(p("M24 74 L34 84 L18 90 Z")),
            body("clip", p("M80 22 L92 10 L94 12 L82 24 Z")),
        ),
        main=BLUE,
        cap=NAVY,
        clip=GRAY,
    ),
)

ENGLISH_B = (
    _pic(
        "puzzle",
        "أُحْجِيَة",
        "puzzle",
        "toy",
        (
            body(
                "main",
                p(
                    "M14 14 L44 14 C42 6 54 6 52 14 L86 14 L86 44 C94 42 94 54 86 52 "
                    "L86 86 L52 86 C54 94 42 94 44 86 L14 86 L14 52 C6 54 6 42 14 44 Z"
                ),
            ),
            line(p("M50 14 L50 86 M14 50 L86 50")),
            body(
                "second", p("M14 14 L44 14 C42 6 54 6 52 14 L50 14 L50 50 L14 50 L14 44 C6 42 6 54 14 52 Z")
            ),
        ),
        main=SKY,
        second=CORAL,
    ),
    _pic(
        "rice",
        "أَرُزّ",
        "rice",
        "food",
        (
            body("bowl", p("M12 52 L88 52 C88 76 72 90 50 90 C28 90 12 76 12 52 Z")),
            body("main", p("M18 52 C24 34 76 34 82 52 Z")),
            line(p("M30 46 L34 44 M44 40 L48 42 M58 40 L62 42 M68 46 L72 44 M50 46 L54 48")),
            body("band", p("M12 60 L88 60 L86 66 L14 66 Z")),
        ),
        main=WHITE,
        bowl=BLUE,
        band=SKY_LIGHT,
    ),
    _pic(
        "ruler",
        "مِسْطَرَة",
        "ruler",
        "school",
        (
            body("main", p("M8 78 L78 8 L92 22 L22 92 Z")),
            line(
                p(
                    "M20 66 L26 72 M28 58 L38 68 M36 50 L42 56 M44 42 "
                    "L54 52 M52 34 L58 40 M60 26 L70 36 M68 18 L74 24"
                )
            ),
        ),
        main=YELLOW,
    ),
    _pic(
        "soup",
        "حَساء",
        "soup",
        "food",
        (
            body(
                "steam",
                p("M36 14 C32 22 40 24 36 32"),
                p("M50 10 C46 18 54 20 50 28"),
                p("M64 14 C60 22 68 24 64 32"),
            ),
            body("bowl", p("M10 46 L90 46 C90 72 74 90 50 90 C26 90 10 72 10 46 Z")),
            body("main", e(50, 46, 40, 8)),
            body("bits", c(36, 45, 3), c(58, 44, 3), c(48, 48, 2.5)),
            body("spoon", p("M70 40 L92 20 L96 24 L74 44 Z")),
        ),
        main=ORANGE,
        bowl=CREAM,
        bits=LEAF,
        spoon=GRAY,
        steam=GRAY,
    ),
    _pic(
        "uniform",
        "زِيّ مَدْرَسِيّ",
        "uniform",
        "clothes",
        (
            body("sleeve", p("M28 26 L10 52 L22 58 L30 44 Z"), p("M72 26 L90 52 L78 58 L70 44 Z")),
            body("main", p("M28 26 L42 20 L50 28 L58 20 L72 26 L72 92 L28 92 Z")),
            body("collar", p("M42 20 L50 32 L58 20 L54 18 L50 24 L46 18 Z")),
            body("tie", p("M47 30 L53 30 L55 52 L50 58 L45 52 Z")),
            body("pocket", rect(58, 60, 10, 10, 2)),
        ),
        main=SKY,
        sleeve=SKY,
        collar=WHITE,
        tie=NAVY,
        pocket=NAVY,
    ),
    _pic(
        "van",
        "شاحِنَة صَغيرَة",
        "van",
        "vehicle",
        (
            body("main", p("M6 40 L54 40 L54 26 L74 26 L92 44 L92 72 L6 72 Z")),
            body("window", p("M58 30 L72 30 L86 44 L58 44 Z")),
            body("tire", c(24, 74, 9), c(74, 74, 9)),
            body("hub", c(24, 74, 3.5), c(74, 74, 3.5)),
            line(p("M6 58 L92 58")),
        ),
        main=CORAL,
        window=SKY_LIGHT,
        tire=SLATE,
        hub=GRAY,
    ),
    _pic(
        "vase",
        "مَزْهَرِيَّة",
        "vase",
        "home",
        (
            body("flower", c(36, 18, 8), c(64, 18, 8), c(50, 10, 8)),
            body(
                "stem",
                p("M36 26 L44 48 L48 48 L40 26 Z"),
                p("M64 26 L56 48 L52 48 L60 26 Z"),
                p("M48 18 L48 48 L52 48 L52 18 Z"),
            ),
            body(
                "main",
                p(
                    "M34 46 L66 46 C64 58 78 66 78 78 C78 88 66 92 50 92 "
                    "C34 92 22 88 22 78 C22 66 36 58 34 46 Z"
                ),
            ),
            shine(e(34, 74, 3, 8, 10)),
        ),
        main="#4FA89A",
        flower=PINK,
        stem=LEAF,
    ),
    _pic(
        "xylophone",
        "إِكْسِيلوفون",
        "xylophone",
        "toy",
        (
            body("frame", p("M8 30 L92 30 L92 78 L8 78 Z")),
            body("bar1", rect(12, 34, 76, 8, 2)),
            body("bar2", rect(16, 44, 68, 8, 2)),
            body("bar3", rect(20, 54, 60, 8, 2)),
            body("bar4", rect(24, 64, 52, 8, 2)),
            line(p("M30 20 L62 14")),
            body("mallet", c(62, 14, 4)),
        ),
        frame=TAN,
        bar1=RED,
        bar2=YELLOW,
        bar3=LEAF,
        bar4=BLUE,
        mallet=RED,
    ),
    _pic(
        "yo-yo",
        "يويو",
        "yo-yo",
        "toy",
        (
            line(p("M50 10 C40 30 60 40 50 56")),
            body("main", c(50, 66, 26)),
            body("inner", c(50, 66, 12)),
            body("hub", c(50, 66, 4)),
            shine(e(38, 56, 4, 8, 30)),
            body("loop", c(50, 8, 3)),
        ),
        main=RED,
        inner=CORAL,
        hub=WHITE,
        loop=GRAY,
    ),
    _pic(
        "zebra",
        "حِمار وَحْشِيّ",
        "zebra",
        "animal",
        (
            body(
                "main",
                rect(30, 60, 7, 32, 2.5),
                rect(40, 60, 7, 32, 2.5),
                rect(58, 60, 7, 32, 2.5),
                rect(68, 60, 7, 32, 2.5),
            ),
            body(
                "main",
                p(
                    "M26 50 C26 42 32 38 40 38 L64 38 C72 38 76 44 76 52 "
                    "C76 60 70 66 62 66 L38 66 C30 66 26 58 26 50 Z"
                ),
            ),
            body("main", p("M64 42 C66 32 70 22 76 18 L86 22 C84 32 80 42 76 52 Z")),
            body("main", p("M72 16 C76 8 86 8 90 14 L96 24 C98 30 92 34 88 30 L78 26 C74 24 70 22 72 16 Z")),
            ink(
                p("M32 42 L34 62 L38 62 L36 42 Z"),
                p("M44 40 L46 62 L50 62 L48 40 Z"),
                p("M56 40 L58 62 L62 62 L60 40 Z"),
                p("M68 44 L70 62 L73 62 L72 44 Z"),
                p("M74 20 L80 20 L78 26 L73 26 Z"),
            ),
            ink(e(84, 16, 2, 2.4)),
            glint(c(84.7, 15.2, 0.8)),
        ),
        main=WHITE,
    ),
)

# drawn again elsewhere since this module was written; the library's own version wins
ALREADY_IN_LIBRARY = frozenset(
    (
        "bus",
        "cheese",
        "crescent",
        "ear",
        "eraser",
        "foot",
        "mouth",
        "pen",
        "rice",
        "ruler",
        "van",
        "yo-yo",
        "zebra",
    )
)
WORKBOOK_WORDS_3: dict[str, Picture] = {
    pic.id: pic
    for pic in (*CODED, *ARABIC_WORDS, *ACTIONS, *FAMILY, *ENGLISH_A, *ENGLISH_B)
    if pic.id not in ALREADY_IN_LIBRARY
}
# plan words spelled differently from the library word (the picture's own word is printed)
WORD_ALIASES_3 = {
    "ليمون": "lemon",
    "موز": "banana",
    "سمك": "fish",
    "قلم": "pencil",
    "ورد": "rose",
    "يمامة": "dove-y",
    "يقطين": "pumpkin",
    "نمر": "tiger",
    "فيل": "elephant",
}
