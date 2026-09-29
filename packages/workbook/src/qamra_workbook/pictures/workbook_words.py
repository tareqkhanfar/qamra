"""Pictures for the words of «دوسية التأسيس» (Addendum 5 §4): the letter words of the curriculum plan, drawn
in the library's style (flat parts in a 100 × 100 box, no text, a color and a line-art version from the same
parts). The educator reviews the word list; replaced words (decision 7: ذيل، ظِلّ، لُعبة، طائرة ورقية،
طاولة) are drawn here too.
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
    shine,
)

SAND = "#E6C28E"
CHESTNUT = "#B07A4F"
DARK_BROWN = "#6B4428"
DATE_BROWN = "#8A4B2A"
FOX = "#EE8B3A"
COPPER = "#E39A55"
HEN = "#F3D19C"
GRAY_ELEPHANT = "#B9C0D2"


def _pic(id: str, ar: str, en: str, category: str, parts: tuple[Part, ...], **palette: str) -> Picture:
    return Picture(id, ar, en, category, parts, palette)


def _smile(x: float, y: float, w: float = 4.5) -> Part:
    return line(p(f"M{x - w} {y} Q{x} {y + w * 0.9} {x + w} {y}"))


ANIMALS = (
    _pic(
        "elephant",
        "فيل",
        "elephant",
        "animal",
        (
            body("main", rect(31, 76, 11, 18, 4), rect(58, 76, 11, 18, 4), e(50, 74, 26, 17)),
            body("main", e(25, 44, 15, 19, -8), e(75, 44, 15, 19, 8)),
            body("inner", e(26, 45, 9, 12, -8), e(74, 45, 9, 12, 8)),
            body("main", c(50, 42, 21)),
            body("main", p("M44 50 C43 63 43 74 47 82 C49 87 57 87 57 81 C54 76 54 66 56 50 Z")),
            *eyes((42, 38), (58, 38), 3.2),
            cheeks((35, 47), (65, 47), 4),
            line(p("M47 62 L53 62 M46.5 70 L52.5 70")),
        ),
        main=GRAY_ELEPHANT,
        inner=PINK,
    ),
    _pic(
        "fox",
        "ثَعْلَب",
        "fox",
        "animal",
        (
            body("main", p("M22 32 L27 10 L42 38 Z"), p("M78 32 L73 10 L58 38 Z")),
            body("inner", p("M27 20 L29 14 L37 34 L30 34 Z"), p("M73 20 L71 14 L63 34 L70 34 Z")),
            body(
                "main",
                p(
                    "M21 32 L38 41 C45 38 55 38 62 41 L79 32 C82 48 78 60 70 68 C64 74 57 80 50 82 "
                    "C43 80 36 74 30 68 C22 60 18 48 21 32 Z"
                ),
            ),
            body(
                "cheek",
                p("M28 58 C36 58 45 66 50 82 C40 80 31 71 28 58 Z"),
                p("M72 58 C64 58 55 66 50 82 C60 80 69 71 72 58 Z"),
            ),
            ink(e(50, 76, 4.2, 3.2)),
            *eyes((40, 52), (60, 52), 3.3),
        ),
        main=FOX,
        inner=DARK_BROWN,
        cheek=WHITE,
    ),
    _pic(
        "ant",
        "نَمْلَة",
        "ant",
        "insect",
        (
            line(p("M44 58 L36 76 M52 60 L52 80 M58 58 L68 76"), p("M44 52 L34 40 M56 50 L64 38")),
            line(p("M78 42 C80 30 86 26 91 26"), p("M72 41 C71 31 75 24 80 22")),
            body("main", e(27, 56, 17, 13), e(52, 54, 10, 8), c(74, 51, 12)),
            ink(c(91, 26, 2.2), c(80, 22, 2.2)),
            *eyes((72, 48), (80, 48), 2.4),
            _smile(76, 55, 3),
            shine(e(22, 51, 5, 3, -20)),
        ),
        main="#C0563E",
    ),
    _pic(
        "camel",
        "جَمَل",
        "camel",
        "animal",
        (
            body("main", rect(27, 60, 6, 32, 2.5), rect(36, 60, 6, 32, 2.5), rect(57, 60, 6, 32, 2.5)),
            body("main", rect(66, 60, 6, 32, 2.5)),
            line(p("M20 52 C15 55 14 62 16 68")),
            body(
                "main",
                p(
                    "M19 52 C19 42 27 38 35 38 C38 24 58 22 62 38 C68 40 73 45 74 52 L74 60 C74 65 70 67 "
                    "65 67 L25 67 C21 67 19 60 19 52 Z"
                ),
            ),
            body("main", p("M63 50 C67 40 69 30 72 22 L81 23 C81 32 78 44 73 56 Z")),
            body("main", p("M70 21 C72 14 83 13 88 17 C93 20 94 27 89 30 L78 30 C73 30 70 26 70 21 Z")),
            body("main", p("M73 16 L72 10 L78 14 Z")),
            ink(e(82, 20, 2, 2.4)),
            glint(c(82.7, 19.2, 0.8)),
            line(p("M89 25 L91 25")),
        ),
        main=SAND,
    ),
    _pic(
        "horse",
        "حِصان",
        "horse",
        "animal",
        (
            body("mane", p("M23 46 C12 48 10 62 14 72 C18 64 21 57 26 53 Z")),
            body("main", rect(28, 58, 6, 32, 2.5), rect(37, 58, 6, 32, 2.5), rect(56, 58, 6, 32, 2.5)),
            body("main", rect(65, 58, 6, 32, 2.5)),
            body("hoof", rect(28, 86, 6, 5, 1.5), rect(37, 86, 6, 5, 1.5), rect(56, 86, 6, 5, 1.5)),
            body("hoof", rect(65, 86, 6, 5, 1.5)),
            body(
                "main",
                p(
                    "M23 50 C23 42 29 38 39 38 L62 38 C70 38 74 44 74 52 "
                    "C74 60 68 64 60 64 L35 64 C27 64 23 58 23 50 Z"
                ),
            ),
            body("main", p("M60 44 C62 33 66 24 72 18 L81 22 C79 31 75 41 72 52 Z")),
            body("main", p("M69 16 C73 9 82 9 86 14 L94 26 C96 31 91 35 87 32 L77 28 C71 26 67 22 69 16 Z")),
            body("main", p("M73 12 L75 4 L80 11 Z")),
            body("mane", p("M70 13 C63 18 59 28 58 41 L64 41 C66 31 69 23 75 18 Z")),
            ink(e(81, 17, 2, 2.4), c(91, 28, 1.1)),
            glint(c(81.7, 16.2, 0.8)),
        ),
        main=CHESTNUT,
        mane=DARK_BROWN,
        hoof=SLATE,
    ),
    _pic(
        "dove",
        "حَمامَة",
        "dove",
        "bird",
        (
            body("main", p("M24 58 L8 50 L11 66 Z")),
            body(
                "main",
                p(
                    "M20 60 C20 45 33 37 47 38 C53 30 63 26 71 30 C77 33 79 40 77 46 C76 64 64 74 48 74 "
                    "C36 74 22 70 20 60 Z"
                ),
            ),
            body("wing", p("M33 52 C41 43 58 45 62 58 C52 63 40 62 33 52 Z")),
            body("beak", p("M77 42 L88 45 L77 49 Z")),
            line(p("M44 74 L42 83 M40 83 L45 83 M54 74 L55 83 M52 83 L58 83")),
            *eyes((68, 36), (68, 36), 2.4),
            cheeks((63, 45), (63, 45), 3),
        ),
        main=WHITE,
        wing="#DDE3EE",
        beak=ORANGE,
    ),
)

FARM = (
    _pic(
        "bear",
        "دُبّ",
        "bear",
        "animal",
        (
            body("main", c(31, 24, 9), c(69, 24, 9)),
            body("inner", c(31, 24, 4.5), c(69, 24, 4.5)),
            body("main", e(50, 74, 25, 20), e(36, 90, 10, 6), e(64, 90, 10, 6)),
            body("inner", e(50, 76, 14, 12)),
            body("main", e(28, 70, 7, 11, -15), e(72, 70, 7, 11, 15)),
            body("main", c(50, 39, 21)),
            body("inner", e(50, 47, 10, 8)),
            ink(e(50, 43.5, 4, 3)),
            line(p("M50 46.5 L50 50 M46 51 Q50 54 54 51")),
            *eyes((42, 35), (58, 35), 3),
        ),
        main=BROWN,
        inner=TAN,
    ),
    _pic(
        "hen",
        "دَجاجَة",
        "hen",
        "bird",
        (
            body("tail", p("M28 58 L14 40 L20 56 L11 50 L22 68 Z")),
            line(p("M44 80 L44 92 M39 93 L49 93 M57 80 L57 92 M52 93 L62 93")),
            body(
                "main",
                p(
                    "M24 60 C24 44 36 37 50 39 C52 28 58 22 66 22 C74 22 80 28 80 36 C80 42 78 46 76 48 "
                    "C80 56 78 70 68 78 C58 86 36 84 28 76 C25 72 24 66 24 60 Z"
                ),
            ),
            body(
                "comb",
                p("M61 23 C60 16 65 13 67 18 C69 12 74 12 75 18 C78 16 81 19 78 24 Z"),
                e(79, 42, 2.6, 4),
            ),
            body("beak", p("M80 31 L89 34 L80 37 Z")),
            body("wing", p("M36 56 C44 49 57 53 59 64 C50 69 40 67 36 56 Z")),
            *eyes((70, 30), (70, 30), 2.6),
        ),
        main=HEN,
        tail=CHESTNUT,
        comb=RED,
        beak=ORANGE,
        wing="#E9B879",
    ),
    _pic(
        "rooster",
        "دِيك",
        "rooster",
        "bird",
        (
            body("feather", p("M30 58 C16 50 11 34 17 20 C23 34 30 42 38 48 Z")),
            body("feather2", p("M31 56 C20 42 22 24 33 14 C33 30 37 40 42 48 Z")),
            body("feather3", p("M30 62 C18 60 8 52 6 42 C16 50 26 52 36 54 Z")),
            line(p("M46 80 L46 92 M41 93 L51 93 M58 80 L58 92 M53 93 L63 93")),
            body(
                "main",
                p(
                    "M26 60 C26 46 38 40 51 41 C52 30 58 22 66 22 C74 22 80 28 80 36 C80 42 78 46 76 48 "
                    "C80 56 78 70 68 78 C58 86 38 84 30 76 C27 72 26 66 26 60 Z"
                ),
            ),
            body(
                "comb",
                p("M58 24 C55 16 60 11 63 16 C64 8 70 7 72 14 C75 9 81 12 79 19 C83 18 84 23 80 26 Z"),
                e(79, 43, 3, 5.5),
            ),
            body("beak", p("M80 31 L90 34 L80 37 Z")),
            body("wing", p("M38 58 C46 50 59 54 61 66 C52 71 42 69 38 58 Z")),
            *eyes((70, 30), (70, 30), 2.6),
        ),
        main=COPPER,
        feather=LEAF_DARK,
        feather2=BLUE,
        feather3=RED,
        comb=RED,
        beak=YELLOW,
        wing="#C9733A",
    ),
    _pic(
        "goat",
        "عَنْزَة",
        "goat",
        "animal",
        (
            body(
                "horn",
                p("M41 24 C35 13 27 10 21 13 C28 15 34 21 37 30 Z"),
                p("M59 24 C65 13 73 10 79 13 C72 15 66 21 63 30 Z"),
            ),
            body("main", e(28, 38, 11, 5, 25), e(72, 38, 11, 5, -25)),
            body("main", p("M46 72 L50 90 L54 72 Z")),
            body(
                "main",
                p(
                    "M36 30 C36 21 42 17 50 17 C58 17 64 21 64 30 "
                    "L62 60 C62 70 56 77 50 77 C44 77 38 70 38 60 Z"
                ),
            ),
            body("nose", e(50, 67, 8, 6)),
            ink(e(47, 66.5, 1.2, 1.6), e(53, 66.5, 1.2, 1.6)),
            *eyes((43, 41), (57, 41), 3),
            cheeks((41, 53), (59, 53), 3.5),
        ),
        main="#F4F0E8",
        horn="#C9A47A",
        nose=PINK,
    ),
    # draft: educator review: ذيل is drawn as a cat whose big tail is in another color
    _pic(
        "tail",
        "ذَيْل",
        "tail",
        "animal",
        (
            body(
                "tail",
                p(
                    "M62 70 C80 72 92 58 90 40 C89 28 80 18 70 20 C62 22 60 32 66 36 C70 30 78 31 80 40 "
                    "C82 52 74 60 60 60 Z"
                ),
            ),
            line(p("M81 30 L88 27 M84 44 L91 45 M77 57 L83 63")),
            body("main", rect(22, 70, 8, 20, 3), rect(48, 70, 8, 20, 3)),
            body("main", e(38, 64, 24, 15)),
            body("main", p("M12 34 L14 20 L22 30 Z"), p("M26 30 L32 18 L35 32 Z")),
            body("main", c(22, 42, 14)),
            *eyes((17, 40), (27, 40), 2.4),
            _smile(22, 47, 3),
        ),
        main=GRAY,
        tail=FOX,
    ),
    _pic(
        "nest",
        "عُشّ",
        "nest",
        "nature",
        (
            body("egg", e(37, 50, 9, 11, -10), e(63, 50, 9, 11, 10)),
            body("egg", e(50, 47, 9.5, 12)),
            body("main", p("M12 54 C12 76 29 88 50 88 C71 88 88 76 88 54 Z")),
            body("rim", e(50, 55, 38, 8)),
            line(p("M20 66 L40 72 M58 74 L82 63 M26 78 L48 82 M52 64 L70 68")),
        ),
        main=CHESTNUT,
        rim="#9A6440",
        egg=SKY_LIGHT,
    ),
)

THINGS = (
    # draft: educator review: إبريق is drawn as a teapot-shaped ewer
    _pic(
        "jug",
        "إِبْريق",
        "jug",
        "home",
        (
            body("main", p("M69 54 C80 51 86 43 90 33 L95 35 C91 50 84 62 69 70 Z")),
            body(
                "main",
                p(
                    "M32 49 C15 45 10 62 17 71 C21 76 28 76 32 72 "
                    "L32 66 C27 69 23 68 21 64 C18 58 22 52 32 55 Z"
                ),
            ),
            body("main", p("M31 44 C28 62 32 82 50 86 C68 82 72 62 69 44 Z")),
            body("lid", e(50, 43, 20, 5.5)),
            body("lid", c(50, 35, 4.5)),
            body("band", p("M31 60 C44 64 56 64 69 60 L68.5 66 C56 70 44 70 31.5 66 Z")),
            shine(e(40, 54, 3, 8, 12)),
        ),
        main=COPPER,
        lid="#C9733A",
        band=GOLD,
    ),
    _pic(
        "rose",
        "وَرْدَة",
        "rose",
        "plant",
        (
            body("stem", p("M48.3 54 L48.3 94 L51.7 94 L51.7 54 Z")),
            body(
                "leaf",
                p("M50 80 C40 66 26 68 21 72 C29 82 42 84 50 80 Z"),
                p("M50 70 C60 58 74 58 79 62 C71 72 58 74 50 70 Z"),
            ),
            body("inner", p("M32 36 C31 22 41 14 50 14 C59 14 69 22 68 36 C62 31 38 31 32 36 Z")),
            body(
                "main",
                p(
                    "M27 32 C26 50 37 61 50 61 C63 61 74 50 73 32 C67 37 60 37 56 30 C53 37 47 37 44 30 "
                    "C40 37 33 37 27 32 Z"
                ),
            ),
            line(p("M52 21 C46 19 42 24 45 28 C48 32 55 30 55 25"), p("M35 41 C39 50 45 55 52 57")),
        ),
        main=RED,
        inner="#F07C6C",
        leaf=LEAF,
        stem=LEAF_DARK,
    ),
    _pic(
        "crown",
        "تاج",
        "crown",
        "thing",
        (
            body("main", p("M20 70 L15 32 L34 50 L50 22 L66 50 L85 32 L80 70 Z")),
            body("band", rect(19, 66, 62, 15, 4)),
            body("gem", c(15, 32, 4.5), c(85, 32, 4.5), c(50, 22, 5)),
            body("gem2", c(35, 73.5, 3.6), c(65, 73.5, 3.6)),
            body("gem", c(50, 73.5, 4)),
            shine(p("M30 56 L36 52 L38 62 L32 64 Z")),
        ),
        main=YELLOW,
        band=GOLD,
        gem=RED,
        gem2=BLUE,
    ),
    _pic(
        "garlic",
        "ثُوم",
        "garlic",
        "vegetable",
        (
            body("stem", p("M46.5 24 L47.5 9 L52.5 9 L53.5 24 Z")),
            body(
                "main",
                p("M50 22 C57 31 77 40 77 61 C77 77 65 87 50 87 C35 87 23 77 23 61 C23 40 43 31 50 22 Z"),
            ),
            line(p("M50 30 C45 45 43 66 46 85"), p("M50 30 C55 45 57 66 54 85")),
            line(p("M38 43 C31 56 31 73 37 83"), p("M62 43 C69 56 69 73 63 83")),
            line(p("M44 87 L42 93 M50 87 L50 94 M56 87 L58 93")),
            shine(e(34, 60, 3, 8, 10)),
        ),
        main="#F4EEE2",
        stem=TAN,
    ),
    _pic(
        "bag",
        "حَقيبَة",
        "bag",
        "thing",
        (
            body("strap", p("M35 40 C35 20 65 20 65 40 L58 40 C58 28 42 28 42 40 Z")),
            body("main", rect(18, 38, 64, 48, 9)),
            body(
                "flap",
                p(
                    "M18 47 C18 41 22 38 28 38 L72 38 C78 38 82 41 82 47 "
                    "L82 58 C82 62 78 65 74 65 L26 65 C22 65 18 62 18 58 Z"
                ),
            ),
            body("buckle", rect(45, 58, 10, 11, 2.5)),
            shine(p("M24 70 L30 70 L30 80 L24 80 Z")),
        ),
        main=BLUE,
        flap="#4A6FC0",
        strap="#4A6FC0",
        buckle=GOLD,
    ),
    # draft: educator review: تمر (dates on a plate) can look like beans at small sizes
    _pic(
        "dates",
        "تَمْر",
        "dates",
        "food",
        (
            body("plate", e(50, 78, 38, 11)),
            body("inner", e(50, 76, 30, 7)),
            body("main", e(33, 68, 10, 6, -18), e(67, 69, 10, 6, 14), e(50, 71, 10, 6, 4)),
            body("main", e(41, 58, 10, 6, 12), e(59, 57, 10, 6, -10)),
            line(p("M29 66 L37 70 M46 69 L54 72 M63 67 L71 71 M37 57 L45 60 M55 58 L63 56")),
            shine(e(56, 55, 3, 1.5, -10), e(38, 56, 3, 1.5, 12)),
        ),
        main=DATE_BROWN,
        plate=WHITE,
        inner=CREAM,
    ),
    _pic(
        "fridge",
        "ثَلّاجَة",
        "fridge",
        "home",
        (
            body("foot", rect(32, 88, 7, 5, 1.5), rect(61, 88, 7, 5, 1.5)),
            body("main", rect(26, 8, 48, 82, 7)),
            line(p("M26 38 L74 38")),
            body("handle", rect(32, 20, 4.5, 13, 2.2), rect(32, 45, 4.5, 20, 2.2)),
            body("magnet", c(62, 22, 4)),
            body("magnet2", p("M58 52 L62 46 L66 52 L62 58 Z")),
            shine(rect(66, 44, 3, 36, 1.5)),
        ),
        main=SKY_LIGHT,
        handle=GRAY,
        foot=SLATE,
        magnet=RED,
        magnet2=YELLOW,
    ),
)

MORE = (
    _pic(
        "egg",
        "بَيْضَة",
        "egg",
        "food",
        (
            body("shadow", e(50, 90, 22, 3.5)),
            body(
                "main",
                p("M50 11 C66 11 78 39 78 60 C78 78 66 89 50 89 C34 89 22 78 22 60 C22 39 34 11 50 11 Z"),
            ),
            shine(e(38, 44, 5, 11, 15)),
        ),
        main="#FFF4DC",
        shadow="#E4D6BC",
    ),
    _pic(
        "tent",
        "خَيْمَة",
        "tent",
        "thing",
        (
            line(p("M13 84 L3 90 M87 84 L97 90")),
            body("flag", p("M50 20 L50 8 L62 12 L50 16")),
            body("main", p("M12 85 L50 20 L88 85 Z")),
            body("door", p("M50 42 L35 85 L65 85 Z")),
            line(p("M50 42 L50 85"), p("M24 64 L30 58 M76 64 L70 58")),
            body("ground", rect(6, 85, 88, 5, 2.5)),
        ),
        main=CORAL,
        door="#B8442F",
        flag=YELLOW,
        ground=LEAF,
    ),
    _pic(
        "bell",
        "جَرَس",
        "bell",
        "thing",
        (
            body("main", c(50, 13, 5.5)),
            body("clapper", c(50, 80, 6.5)),
            body(
                "main",
                p(
                    "M50 18 C34 18 28 32 28 50 C28 62 24 68 17 74 "
                    "L83 74 C76 68 72 62 72 50 C72 32 66 18 50 18 Z"
                ),
            ),
            body("band", p("M26 64 C42 68 58 68 74 64 L76 70 C58 74 42 74 24 70 Z")),
            shine(e(38, 40, 4, 10, 12)),
        ),
        main=YELLOW,
        band=GOLD,
        clapper=ORANGE,
    ),
    _pic(
        "fan",
        "مِرْوَحَة",
        "fan",
        "home",
        (
            body("base", e(50, 88, 22, 6)),
            body("neck", rect(46.5, 60, 7, 28, 2)),
            body("grille", c(50, 38, 28)),
            body("blade", p("M50 38 C44 26 46 14 54 13 C60 15 58 28 50 38 Z")),
            body("blade", p("M50 38 C63 36 72 44 69 51 C65 56 55 49 50 38 Z")),
            body("blade", p("M50 38 C44 50 33 55 29 49 C27 43 38 37 50 38 Z")),
            body("hub", c(50, 38, 5)),
            line(p("M50 10 L50 18 M22 38 L30 38 M78 38 L70 38 M50 66 L50 58")),
        ),
        grille=WHITE,
        blade=SKY,
        hub=BLUE,
        neck=GRAY,
        base=SLATE,
    ),
    _pic(
        "corn",
        "ذُرَة",
        "corn",
        "vegetable",
        (
            body(
                "main",
                p("M50 10 C61 10 67 25 67 46 C67 66 61 81 50 86 C39 81 33 66 33 46 C33 25 39 10 50 10 Z"),
            ),
            line(p("M36 30 L64 30 M34 42 L66 42 M34 54 L66 54 M36 66 L64 66 M40 77 L60 77")),
            line(p("M44 12 C41 34 41 60 44 83 M56 12 C59 34 59 60 56 83")),
            body(
                "leaf",
                p("M50 92 C34 86 23 66 26 42 C35 58 42 72 50 92 Z"),
                p("M50 92 C66 86 77 66 74 42 C65 58 58 72 50 92 Z"),
            ),
        ),
        main=YELLOW,
        leaf=LEAF,
    ),
    _pic(
        "hat",
        "قُبَّعَة",
        "hat",
        "clothes",
        (
            body("brim", e(50, 66, 42, 11)),
            body("main", p("M28 64 C28 38 37 28 50 28 C63 28 72 38 72 64 Z")),
            body("band", p("M28.5 54 L71.5 54 L72 64 L28 64 Z")),
            shine(e(40, 40, 3, 7, 15)),
        ),
        main=BLUE,
        brim="#4A6FC0",
        band=RED,
    ),
    _pic(
        "bucket",
        "دَلْو",
        "bucket",
        "thing",
        (
            body("handle", p("M24 38 C24 8 76 8 76 38 L71 38 C71 16 29 16 29 38 Z")),
            body("main", p("M24 38 L31 85 C31.5 88 34 90 38 90 L62 90 C66 90 68.5 88 69 85 L76 38 Z")),
            body("rim", e(50, 38, 27, 6.5)),
            body("water", e(50, 38, 21, 3.8)),
            shine(p("M34 50 L39 50 L42 80 L37 80 Z")),
        ),
        main=RED,
        handle=SLATE,
        rim="#C94A3A",
        water=SKY,
    ),
)

WORKBOOK_WORDS: dict[str, Picture] = {pic.id: pic for pic in (*ANIMALS, *FARM, *THINGS, *MORE)}
