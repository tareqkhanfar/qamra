"""KG1 («دوسية التأسيس» for ages 4–5) on the same plan → engine mapping as KG2 (`foundation.py`): which plan
pages go to the KG1 builders (`engine_type_kg1`), the KG1 shape of a page's params (`params_kg1`: bigger
rows, fewer items, the plan's shorthand spelled out for the builders) and the child-facing texts of the page
types and modes only KG1 has (`texts_kg1`). `foundation.from_curriculum` asks here first for a KG1 plan;
a `None` means "as in KG2".
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.curriculum import Page
from qamra_workbook.pictures.model import strip_tashkeel
from qamra_workbook.puzzles.odd import BASIC_GROUPS
from qamra_workbook.render.foundation_text import (
    COLORING_SAY,
    COMPARE,
    SHAPES_SAY,
    Texts,
    counted,
    dot_to_dot_say,
    letters_head,
    path_say,
    pick,
    review_say,
    turn,
)
from qamra_workbook.render.foundation_v2 import hidden_say, letter_position_say

# the distractors of a KG1 find-the-letter page: the letters that look alike (dots, teeth, loops, tails)
LOOKALIKE_KG1 = {
    "أ": "لد",
    "ب": "تثن",
    "ت": "بثن",
    "ث": "بتن",
    "ج": "حخع",
    "ح": "جخع",
    "خ": "جحغ",
    "د": "ذرز",
    "ذ": "درز",
    "ر": "زدو",
    "ز": "رذو",
    "س": "شصن",
    "ش": "سضث",
    "ص": "ضسط",
    "ض": "صشظ",
    "ط": "ظصك",
    "ظ": "طضك",
    "ع": "غحخ",
    "غ": "عخج",
    "ف": "قون",
    "ق": "فنو",
    "ك": "لاط",
    "ل": "كاد",
    "م": "هوق",
    "ن": "بتث",
    "ه": "موة",
    "و": "هرز",
    "ي": "بنت",
}
# the picture words of each letter as the plan teaches them (its letter-intro and en-letter pages; a test
# keeps this table equal to the plan): the find pages and the reviews ask about these pictures first, so a
# child is only ever asked about words they have met
LETTER_PICTURES_KG1 = {
    "أ": ("rabbit", "lion"),
    "ب": ("duck", "house"),
    "ت": ("apple", "crown"),
    "ث": ("fox", "garlic"),
    "ج": ("camel", "carrot"),
    "ح": ("horse", "whale"),
    "خ": ("sheep", "cucumber"),
    "د": ("bear", "hen"),
    "ذ": ("corn",),
    "ر": ("pomegranate", "feather"),
    "ز": ("giraffe", "olive"),
    "س": ("fish", "car"),
    "ش": ("sun", "tree"),
    "ص": ("plate", "falcon"),
    "ض": ("frog",),
    "ط": ("kite", "table"),
    "ظ": ("envelope",),
    "ع": ("grapes", "bird"),
    "غ": ("gazelle", "cloud"),
    "ف": ("elephant", "butterfly"),
    "ق": ("moon", "pencil"),
    "ك": ("book", "ball"),
    "ل": ("lemon",),
    "م": ("banana", "key"),
    "ن": ("bee", "star"),
    "ه": ("hoopoe", "pyramid"),
    "و": ("rose", "leaf"),
    "ي": ("hand", "pumpkin"),
}
ENGLISH_PICTURES_KG1 = {
    "A": "apple",
    "B": "ball",
    "C": "cat",
    "D": "duck",
    "E": "egg",
    "F": "fish",
    "G": "grapes",
    "H": "hat",
    "I": "ice-cream",
    "J": "jacket",
    "K": "kite",
    "L": "lion",
    "M": "moon",
    "N": "nest",
    "O": "orange",
    "P": "pencil",
    "Q": "queen",
    "R": "rabbit",
    "S": "sun",
    "T": "tree",
    "U": "umbrella",
    "V": "van",
    "W": "window",
    "X": "box",
    "Y": "yo-yo",
    "Z": "zebra",
}
KG1_LINES = frozenset(
    {
        "horizontal",
        "vertical",
        "diagonal",
        "arc",
        "wave",
        "zigzag",
        "circle",
        "lane",
        "bridge",
        "loop",
        "teeth",
        "small-loop",
        "grid-copy",
        "connected",
    }
)


def engine_type_kg1(page: Page) -> str | None:
    """The KG1 builder for a plan page, by its type and params; None when the KG2 builders serve."""
    p = page.params
    match page.type:
        case "pen-lines" if p.get("line") == "shape":
            return "shapes"
        case "pen-lines" if str(p.get("line", "horizontal")) in KG1_LINES:
            return "kg1-pen-lines"
        case "trace-path" if p.get("path") in ("straight", "winding", "sharp-turns"):
            return "kg1-trace-path"
        case "coloring" if p.get("mode") == "hidden" and p.get("find") == "star":
            return "kg1-hidden-stars"
        case "coloring" if p.get("mode") == "hidden":
            return "hidden-pictures"
        case "coloring" if p.get("mode") == "color-by-code":
            return "kg1-color-by-code"
        case "coloring" if p.get("mode") == "color-by-letter":
            return "kg1-color-by-letter"
        case "coloring" if page.subject == "english":
            return "kg1-en-coloring"
        case "coloring" if "area" in p:
            return "kg1-coloring-area"
        case "coloring" if "colors" in p:
            return "kg1-colors"
        case "dot-to-dot":
            return "kg1-dot-to-dot"
        case "drawing" if p.get("task") == "self-portrait":
            return "kg1-self-portrait"
        case "letter-trace":
            return "kg1-letter-trace"
        case "letter-write":
            return "kg1-letters-write" if "letters" in p else "kg1-letter-write"
        case "harakat":
            return "kg1-harakat"
        case "word-read" | "word-write":
            return f"kg1-{page.type}"
        case "unit-review" if page.subject == "arabic" and "harakat" in p:
            return "kg1-harakat"
        case "unit-review" if page.subject == "arabic" and "words" in p:
            return "kg1-word-read"
        case "unit-review" if page.subject == "english" and "units" in p:
            return "kg1-vocab-review"
        case "unit-review":
            return "kg1-unit-review"
        case "assessment":
            return "kg1-assessment"
        case "compare" if p.get("concept") in ("order-size", "equal", "fewer"):
            return "kg1-compare"
        case "compare" if p.get("concept") == "more-less" and max(p.get("numbers", [9])) <= 5:
            return "kg1-compare"
        case "number-intro" if p.get("number") in (1, 2):
            return "kg1-number-intro"
        case "shapes" if p.get("mode") == "find":
            return "kg1-shape-find"
        case "pattern-complete" if p.get("kind") == "numbers":
            return "number-train"
        case "picture-add" | "picture-subtract":
            return f"kg1-{page.type}"
        case "en-letter":
            return "kg1-en-letter"
        case "vocab-unit":
            return "kg1-vocab-unit"
        case "connect" if p.get("mode") in ("related", "need", "sequence", "mixed-review"):
            return "kg1-connect"
        case "classify" if p.get("by") in ("kind", "habitat", "color"):
            return "kg1-classify"
        case "number-write" if "numbers" in p:
            return "kg1-number-write"
        case "count-and-circle" if len(p.get("numbers", [])) >= 4:
            return "kg1-count-and-circle"
        case "find-letter" if page.subject == "english":
            return "kg1-find-letter-en"
        case "find-letter":
            return "kg1-find-letter"
        case "match-letter-picture" if page.subject == "arabic" and len(p.get("words", [])) >= 5:
            return "kg1-match-letter-picture"
        case "memory" if int(p.get("items", 3)) >= 5:
            return "kg1-memory"
        case "position-words" if p.get("concept") == "inside-outside":
            return "kg1-inside-outside"
        case "cut-and-paste" if p.get("task") == "shadows":
            return "kg1-cut-shadows"
        case "cut-and-paste" if p.get("task") == "sequence":
            return "kg1-story-sequence"
    return None


def params_kg1(page: Page, params: dict[str, Any]) -> dict[str, Any]:
    """The merged params as the KG1 builders read them: the plan's shorthand spelled out (one `letter` as
    `letters`, a picture word as its library id, a level as rows and sizes) and KG1's smaller counts."""
    out = dict(params)
    p = page.params
    match page.type:
        case "find-letter" if page.subject == "arabic":
            targets = [str(x) for x in p.get("letters", [p.get("letter", "ب")])]
            others = [c for t in targets for c in LOOKALIKE_KG1.get(t, "") if c not in targets]
            out.setdefault("distractors", list(dict.fromkeys(others)))
        case "letter-position" if "letter" in p and "letters" not in p:
            out["letters"] = [str(p["letter"])]
        case "en-letter" if "word" in p:
            from qamra_workbook.render.pages.workbook_common import picture_id  # lazy: pages import this

            out["word"] = picture_id(str(p["word"]))
        case "coloring" if p.get("mode") == "hidden":
            out["hidden"] = int(p.get("count", 5))
        case "odd-one-out":  # a solved example row, then three rows of four; harder levels ask for the kind
            level = min(int(p.get("level", 1)), 3)
            rules = (["same"] * 3, ["same", "same", "category"], ["same", "category", "category"])
            out["rules"] = ["same", *rules[level - 1]]
            out["sizes"] = [4] * 4
            out["groups"] = list(BASIC_GROUPS)  # KG1: fruit, animals, clothes, what we ride
        case "pattern-complete" if p.get("kind") == "numbers":
            out["numbers"] = list(range(int(p.get("start", 1)), int(p.get("end", 10)) + 1))
    return out


# draft: educator review: the titles and instructions below have not been through the educator yet
PEN_TITLES_KG1 = {
    "horizontal": ("خُطوطٌ أُفُقِيَّةٌ", "{ارْسُمْ/ارْسُمي} عَلى النِّقاطِ مِنَ اليَمينِ إلى اليَسارِ"),
    "vertical": ("خُطوطٌ عَمودِيَّةٌ", "{انْزِلْ/انْزِلي} بِالقَلَمِ مِنْ فَوْقُ إلى تَحْتُ"),
    "diagonal": ("خُطوطٌ مائِلَةٌ", "{اتْبَعِ/اتْبَعي} النِّقاطَ المائِلَةَ مِنَ النُّقْطَةِ الخَضْراءِ"),
    "arc": ("أَقْواسُ قُزَحَ", "{ارْسُمْ/ارْسُمي} كُلَّ قَوْسٍ مِنَ النُّقْطَةِ الخَضْراءِ"),
    "wave": ("أَمْواجُ البَحْرِ", "{ارْسُمِ/ارْسُمي} المَوْجَ عَلى النِّقاطِ، وَلا {تَرْفَعِ/تَرْفَعي} القَلَمَ"),
    "zigzag": ("أَسْنانُ المِنْشارِ", "{اصْعَدْ/اصْعَدي} {وَانْزِلْ/وَانْزِلي} بِالقَلَمِ مِثْلَ قِمَمِ الجِبالِ"),
    "circle": ("دَوائِرُ كَبيرَةٌ", "{دُرْ/دوري} بِالقَلَمِ عَلى الدّائِرَةِ مِنَ النُّقْطَةِ الخَضْراءِ"),
    "lane": ("داخِلَ المَمَرِّ", "{ارْسُمْ/ارْسُمي} في وَسَطِ المَمَرِّ، بَعيدًا عَنِ الحافَّتَيْنِ"),
    "bridge": ("جُسورٌ صَغيرَةٌ", "{ارْسُمِ/ارْسُمي} الجُسورَ مُتَّصِلَةً عَلى النِّقاطِ"),
    "loop": ("حَلَقاتٌ", "{لُفَّ/لُفّي} بِالقَلَمِ حَلْقَةً بَعْدَ حَلْقَةٍ"),
    "teeth": ("أَسْنانُ السّينِ", "{تَتَبَّعِ/تَتَبَّعي} الأَسْنانَ الصَّغيرَةَ واحِدَةً تِلْوَ الأُخْرى"),
    "small-loop": ("حَلَقاتٌ صَغيرَةٌ مُغْلَقَةٌ", "{ارْسُمْ/ارْسُمي} حَلَقاتٍ صَغيرَةً، {وَأَغْلِقْ/وَأَغْلِقي} كُلَّ حَلْقَةٍ"),
    "grid-copy": ("أَرْسُمُ مِثْلَهُ", "{ارْسُمْ/ارْسُمي} مِثْلَ الرَّسْمِ تَمامًا عَلى النِّقاطِ"),
    "connected": ("خُطوطٌ مُتَّصِلَةٌ", "{ارْسُمْ/ارْسُمي} نَحْوَ اليَسارِ دونَ أَنْ {تَرْفَعَ/تَرْفَعي} القَلَمَ"),
}
# the second connected-lines page goes the other way (its plan direction is ltr)
CONNECTED_LTR = "نَحْوَ اليَمينِ الآنَ: {ارْسُمْ/ارْسُمي} دونَ رَفْعِ القَلَمِ"
SHAPE_NAMES_KG1 = {"circle": "الدّائِرَةُ", "square": "المُرَبَّعُ", "triangle": "المُثَلَّثُ", "rectangle": "المُسْتَطيلُ"}
TRACE_TITLES_KG1 = {
    "straight": "الطَّريقُ المُسْتَقيمُ",
    "winding": "الطَّريقُ المُتَعَرِّجُ",
    "sharp-turns": "مُنْعَطَفاتٌ حادَّةٌ",
}
SHARP_TURNS = "{سِرْ/سيري} عَلى الطَّريقِ بِبُطْءٍ عِنْدَ كُلِّ مُنْعَطَفٍ"
HARAKA_AR = {"fatha": "الفتحة", "damma": "الضمة", "kasra": "الكسرة"}
HARAKA_HEARD = {"fatha": "الفَتْحَةَ", "damma": "الضَّمَّةَ", "kasra": "الكَسْرَةَ"}  # «أَسْمَعُ الفَتْحَةَ»
HARAKA_LISTEN = {  # listen to the grown-up say a syllable, say it back, circle the one heard
    "fatha": "{اسْمَعْ/اسْمَعي} {وَرَدِّدْ/وَرَدِّدي}، ثُمَّ {حَوِّطْ/حَوِّطي} ما {تَسْمَعُهُ/تَسْمَعينَهُ}",
    "damma": "{قُلِ/قولي} الصَّوْتَ مَعَ الكِبارِ، ثُمَّ {حَوِّطِ/حَوِّطي} الضَّمَّةَ",
    "kasra": "{رَدِّدِ/رَدِّدي} الصَّوْتَ، ثُمَّ {حَوِّطِ/حَوِّطي} الحَرْفَ بِحَرَكَتِهِ",
    "review": "فَتْحَةٌ أَمْ ضَمَّةٌ أَمْ كَسْرَةٌ؟ {اسْمَعْ/اسْمَعي} {وَحَوِّطْ/وَحَوِّطي}",
}
CONNECT_KG1 = {
    "related": ("ما الَّذي يُناسِبُهُ؟", "{صِلْ/صِلي} كُلَّ حَيَوانٍ بِبَيْتِهِ"),
    "need": ("مَتى نَحْتاجُهُ؟", "{صِلْ/صِلي} كُلَّ شَيْءٍ بِالوَقْتِ الَّذي نَحْتاجُهُ فيهِ"),
    "sequence": (
        "ماذا يَحْدُثُ أَوَّلًا؟",
        "{رَتِّبِ/رَتِّبي} القِصَّةَ: {صِلْ/صِلي} كُلَّ صورَةٍ بِرَقْمِها",
    ),
    "mixed-review": ("أَصِلُ ما تَعَلَّمْتُ", "{صِلِ/صِلي} الحَرْفَ وَالعَدَدَ بِالصّورَةِ المُناسِبَةِ"),
}
CLASSIFY_KG1 = {
    "kind": ("حَيَواناتٌ وَفَواكِهُ", "حَيَوانٌ أَمْ فاكِهَةٌ؟ {صِلْ/صِلي} كُلَّ صورَةٍ بِمَجْموعَتِها"),
    "habitat": (
        "في البَرِّ أَمْ في البَحْرِ؟",
        "{صِلْ/صِلي} حَيَواناتِ البَرِّ بِالبَرِّ، وَحَيَواناتِ البَحْرِ بِالبَحْرِ",
    ),
}
COMPARE_KG1 = {
    "order-size": ("مِنَ الأَصْغَرِ إلى الأَكْبَرِ", "{رَقِّمِ/رَقِّمي} الأَشْياءَ مِنَ الأَصْغَرِ إلى الأَكْبَرِ"),
    "equal": (
        "العَدَدُ نَفْسُهُ",
        "{صِلْ/صِلي} واحِدًا بِواحِدٍ، ثُمَّ {حَوِّطِ/حَوِّطي} الصَّفَّيْنِ المُتَساوِيَيْنِ",
    ),
    "fewer": ("أَقَلُّ", "أَيُّ مَجْموعَةٍ أَقَلُّ؟ {حَوِّطْها/حَوِّطيها} في كُلِّ صَفٍّ"),
}
MORE_KG1 = (
    "في كُلِّ صَفٍّ: أَيُّ مَجْموعَةٍ أَكْثَرُ؟ {حَوِّطْها/حَوِّطيها}",
    "{عُدَّ/عُدّي} المَجْموعَتَيْنِ، ثُمَّ {حَوِّطِ/حَوِّطي} الأَكْثَرَ",
)
VOCAB_KG1 = (  # the vocabulary cards: the picture to color, the English word, the Arabic under it
    ("{قُلْ/قولي} كُلَّ كَلِمَةٍ، ثُمَّ {لَوِّنْ/لَوِّني} صورَتَها", "Say each word, then color it."),
    ("{اسْمَعْ/اسْمَعي} {وَرَدِّدِ/وَرَدِّدي} الكَلِمَةَ، ثُمَّ {لَوِّنْ/لَوِّني}", "Listen, say the word, then color."),
    ("{لَوِّنْ/لَوِّني} كُلَّ صورَةٍ {وَقُلِ/وَقولي} اسْمَها", "Color each picture and say its name."),
    ("{أَشِرْ/أَشيري} إلى الصّورَةِ {وَقُلِ/وَقولي} الكَلِمَةَ، ثُمَّ {لَوِّنْها/لَوِّنيها}", "Point, say the word, then color."),
    ("{سَمِّ/سَمّي} كُلَّ صورَةٍ بِالإِنْجِليزِيَّةِ، ثُمَّ {لَوِّنْها/لَوِّنيها}", "Name each picture in English, then color."),
)
VOCAB_REVIEW_KG1 = (
    ("{صِلِ/صِلي} الكَلِماتِ، ثُمَّ {حَوِّطِ/حَوِّطي} الصُّوَرَ", "Match the words, then circle the pictures."),
    ("{اقْرَأْ/اقْرَئي} مَعَ الكِبارِ، ثُمَّ {صِلْ/صِلي} {وَحَوِّطْ/وَحَوِّطي}", "Read along, then match and circle."),
)
PICTURE_ADD_KG1 = (
    "{عُدَّ/عُدّي} الصُّوَرَ مَعًا، ثُمَّ {حَوِّطِ/حَوِّطي} المَجْموعَ",
    "كَمْ صارَتْ كُلُّها؟ {عُدَّ/عُدّي} {وَحَوِّطِ/وَحَوِّطي} الجَوابَ",
)
PICTURE_SUBTRACT_KG1 = (  # the pictures that go are crossed out already
    "{عُدَّ/عُدّي} الصُّوَرَ الَّتي لَمْ تُشْطَبْ، {وَحَوِّطِ/وَحَوِّطي} الجَوابَ",
    "كَمْ بَقِيَ بَعْدَ الشَّطْبِ؟ {عُدَّ/عُدّي} {وَحَوِّطْ/وَحَوِّطي}",
)
STORY_KG1 = "{اسْمَعِ/اسْمَعي} القِصَّةَ، ثُمَّ {حَوِّطِ/حَوِّطي} الجَوابَ"  # a grown-up reads the little story
CUT_KG1 = "{قُصَّ/قُصّي} الصُّوَرَ"


def _harakat_title(params: dict[str, Any]) -> str:
    if "harakat" in params:
        return "أَسْمَعُ الحَرَكاتِ الثَّلاثَ"
    return f"أَسْمَعُ {HARAKA_HEARD.get(str(params.get('haraka', 'fatha')), 'الفَتْحَةَ')}"


def _shapes(shapes: Any) -> str:
    """«الدّائِرَةُ وَالمُرَبَّعُ»."""
    return " وَ".join(SHAPE_NAMES_KG1.get(str(s), str(s)) for s in shapes)


def texts_kg1(subject: str, kind: str, params: dict[str, Any], unit_title: str) -> Texts | None:
    """Titles and instructions for the KG1 pages; None when the KG2 texts serve."""
    p = params
    letters = [str(x) for x in p.get("letters", [])]
    match kind:
        case "pen-lines" if p.get("line") == "shape":
            return _shapes(p.get("shapes", ["square"])), "{مَرِّرِ/مَرِّري} القَلَمَ عَلى حُدودِ كُلِّ شَكْلٍ", ""
        case "pen-lines" if p.get("line") == "connected" and p.get("direction") == "ltr":
            return PEN_TITLES_KG1["connected"][0], CONNECTED_LTR, ""
        case "pen-lines" if str(p.get("line", "horizontal")) in PEN_TITLES_KG1 and p.get("line") != "spiral":
            title, say = PEN_TITLES_KG1[str(p.get("line", "horizontal"))]
            return title, say, ""
        case "trace-path" if p.get("path") == "sharp-turns":
            return TRACE_TITLES_KG1["sharp-turns"], SHARP_TURNS, ""
        case "trace-path" if p.get("path") in TRACE_TITLES_KG1:
            return TRACE_TITLES_KG1[str(p["path"])], path_say(p), ""
        case "coloring" if p.get("mode") == "hidden" and p.get("find") == "star":
            found = counted(p.get("count", 5), "نُجومٍ مُخْتَبِئَةٍ", "نَجْمَةً مُخْتَبِئَةً")
            return "أَيْنَ اخْتَبَأَتِ النُّجومُ؟", f"في الصّورَةِ {found}: {{لَوِّنْها/لَوِّنيها}}", ""
        case "coloring" if p.get("mode") == "hidden":
            return "أَيْنَ اخْتَبَأَتْ؟", hidden_say(p, "أَشْياءَ مَخْفِيَّةٍ", "شَيْئًا مَخْفِيًّا"), ""
        case "coloring" if p.get("mode") == "color-by-code":
            return (
                "أُلَوِّنُ حَسَبَ الرَّمْزِ",
                "{لَوِّنْ/لَوِّني} كُلَّ جُزْءٍ بِلَوْنِ رَمْزِهِ",
                "",
            )
        case "coloring" if subject == "english":
            return (
                "Color and say",
                "{لَوِّنْ/لَوِّني} كُلَّ صورَةٍ، {وَقُلِ/وَقولي} اسْمَها بِالإِنْجِليزِيَّةِ",
                "Say each word, then color its picture.",
            )
        case "coloring" if "area" in p:
            return "أُلَوِّنُ بِعِنايَةٍ", pick(COLORING_SAY, turn(p)), ""
        case "dot-to-dot":
            return f"مِنْ 1 إلى {p.get('to', 5)}", dot_to_dot_say(p), ""
        case "drawing" if p.get("task") == "self-portrait":
            return (
                "أَنا وَأَصْدِقائي",
                "{ارْسُمْ نَفْسَكَ/ارْسُمي نَفْسَكِ} في الرَّوْضَةِ، ثُمَّ {ارْسُمْ أَصْدِقاءَكَ/ارْسُمي أَصْدِقاءَكِ}",
                "",
            )
        case "letter-position" if len(letters) == 1:
            return f"أَيْنَ {letters_head(letters)} في الكَلِمَةِ؟", letter_position_say(p), ""
        case "unit-review" if subject == "arabic" and letters and len(strip_tashkeel(unit_title)) > 30:
            # «حرفا السين والشين، ومراجعة ر ز س ش» is too long for a title: the letters themselves do
            # (letters counted without their marks, so a vowelized title takes the same branch)
            return "مُراجَعَةُ حُروفي: " + " ".join(letters), review_say(subject, p), ""
        case "harakat" | "unit-review" if "haraka" in p or "harakat" in p:
            heard = "review" if "harakat" in p else str(p.get("haraka", "fatha"))
            return _harakat_title(p), HARAKA_LISTEN.get(heard, HARAKA_LISTEN["fatha"]), ""
        case "word-read" if p.get("mode") == "first-letter":
            return (
                "الحَرْفُ الأَوَّلُ",
                "ما أَوَّلُ حَرْفٍ في اسْمِ الصّورَةِ؟ {حَوِّطْهُ/حَوِّطيهِ}",
                "",
            )
        case "word-read":
            return (
                "أَسْمَعُ الكَلِمَةَ",
                "حينَ {تَسْمَعُ/تَسْمَعينَ} الكَلِمَةَ، {أَشِرْ/أَشيري} إلى صورَتِها",
                "",
            )
        case "unit-review" if "words" in p:
            return "أَسْمَعُ الكَلِمَةَ", "كَلِمَةٌ {تَسْمَعُها/تَسْمَعينَها}: {حَوِّطْ/حَوِّطي} صورَتَها أَوْ حَرْفَها الأَوَّلَ", ""
        case "word-write":
            return "أَتَتَبَّعُ الكَلِمَةَ", "{تَتَبَّعْ/تَتَبَّعي} كُلَّ كَلِمَةٍ حَرْفًا حَرْفًا", ""
        case "unit-review" if "units" in p:
            return "Review: my words", *pick(VOCAB_REVIEW_KG1, turn(p))
        case "vocab-unit":
            unit = str(p.get("unit", "Words"))
            return unit, *pick(VOCAB_KG1, turn(p))
        case "picture-add" if p.get("mode") == "story":
            return "أَجْمَعُ بِالصُّوَرِ", STORY_KG1, ""
        case "picture-add":
            return "أَجْمَعُ بِالصُّوَرِ", pick(PICTURE_ADD_KG1, turn(p)), ""
        case "picture-subtract" if p.get("mode") == "story":
            return "أَطْرَحُ بِالصُّوَرِ", STORY_KG1, ""
        case "picture-subtract":
            return "أَطْرَحُ بِالصُّوَرِ", pick(PICTURE_SUBTRACT_KG1, turn(p)), ""
        case "compare" if p.get("concept") in COMPARE_KG1:
            return (*COMPARE_KG1[str(p["concept"])], "")
        case "compare" if p.get("concept") == "more-less":
            return COMPARE["more-less"][0], pick(MORE_KG1, turn(p)), ""
        case "shapes" if p.get("mode") == "find":
            return "أَجِدُ الأَشْكالَ", "{جِدْ/جِدي} كُلَّ شَكْلٍ، {وَلَوِّنْهُ/وَلَوِّنيهِ} بِلَوْنِهِ في الأَعْلى", ""
        case "shapes" if p.get("shapes"):
            return _shapes(p["shapes"]), pick(SHAPES_SAY, turn(p)), ""
        case "number-write" if p.get("numbers"):
            listed = " وَ".join(str(n) for n in p["numbers"])
            return (
                f"أَكْتُبُ الأَعْدادَ {listed}",
                pick(
                    (
                        "{تَتَبَّعِ/تَتَبَّعي} الأَعْدادَ، ثُمَّ {اكْتُبْها وَحْدَكَ/اكْتُبيها وَحْدَكِ}",
                        "{اكْتُبْ/اكْتُبي} كُلَّ عَدَدٍ عَلى النِّقاطِ، ثُمَّ {وَحْدَكَ/وَحْدَكِ}",
                    ),
                    turn(p),
                ),
                "",
            )
        case "pattern-complete" if p.get("kind") == "numbers":
            return "قِطارُ الأَعْدادِ", "{عُدَّ/عُدّي}، {وَاكْتُبِ/وَاكْتُبي} العَدَدَ النّاقِصَ في كُلِّ قِطارٍ", ""
        case "position-words" if p.get("concept") == "inside-outside":
            return (
                "داخِلَ الصُّنْدوقِ أَمْ خارِجَهُ؟",
                "{انْظُرْ/انْظُري} إلى الصُّنْدوقِ، {وَحَوِّطْ/وَحَوِّطي} ما فيهِ",
                "",
            )
        case "memory" if int(p.get("items", 3)) >= 5:
            return (
                "أَنْظُرُ وَأَتَذَكَّرُ",
                "{احْفَظِ/احْفَظي} الصُّوَرَ، ثُمَّ {غَطِّها/غَطّيها}: ماذا اخْتَفى؟",
                "",
            )
        case "connect" if p.get("mode") in CONNECT_KG1:
            return (*CONNECT_KG1[str(p["mode"])], "")
        case "classify" if p.get("by") in CLASSIFY_KG1:
            return (*CLASSIFY_KG1[str(p["by"])], "")
        case "cut-and-paste" if p.get("task") == "shadows":
            return (
                "كُلُّ صورَةٍ فَوْقَ ظِلِّها",
                "{قُصَّ/قُصّي} كُلَّ صورَةٍ، ثُمَّ {أَلْصِقْها/أَلْصِقيها} عَلى ظِلِّها",
                "",
            )
        case "cut-and-paste" if p.get("task") == "sequence":
            return (
                "أُرَتِّبُ القِصَّةَ",
                f"{CUT_KG1}، {{وَأَلْصِقْها/وَأَلْصِقيها}} بِتَرْتيبِ القِصَّةِ",
                "",
            )
        case "cut-and-paste":
            return (
                "أُرَكِّبُ الصّورَةَ",
                "{قُصَّ/قُصّي} القِطَعَ، {وَأَلْصِقْها/وَأَلْصِقيها} {لِتُكْمِلَ/لِتُكْمِلي} الصّورَةَ",
                "",
            )
        case "certificate":
            return "شَهادَةُ إِنْجازٍ", "مَبْروكٌ يا {child}! {لَوِّنِ/لَوِّني} النُّجومَ {وَاحْتَفِلْ/وَاحْتَفِلي}", ""
    return None
