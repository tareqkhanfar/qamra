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
from qamra_workbook.render.foundation_text import COMPARE, Texts, counted, letters_head

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
        case "pattern-complete" if p.get("kind") == "numbers":
            out["numbers"] = list(range(int(p.get("start", 1)), int(p.get("end", 10)) + 1))
    return out


# draft: educator review: every title and instruction below is new text
PEN_TITLES_KG1 = {
    "horizontal": ("خُطوطٌ أُفُقِيَّةٌ", "{ارْسُمِ/ارْسُمي} الخَطَّ مِنَ النُّقْطَةِ الخَضْراءِ إلى اليَسارِ"),
    "vertical": ("خُطوطٌ عَمودِيَّةٌ", "{ارْسُمِ/ارْسُمي} الخَطَّ مِنْ فَوْقُ إلى تَحْتُ"),
    "diagonal": ("خُطوطٌ مائِلَةٌ", "{ارْسُمْ/ارْسُمي} عَلى النِّقاطِ مِنَ النُّقْطَةِ الخَضْراءِ"),
    "arc": ("أَقْواسُ قُزَحَ", "{ارْسُمِ/ارْسُمي} القَوْسَ مِنَ النُّقْطَةِ الخَضْراءِ"),
    "wave": ("أَمْواجُ البَحْرِ", "{ارْسُمِ/ارْسُمي} المَوْجَ عَلى النِّقاطِ"),
    "zigzag": ("أَسْنانُ المِنْشارِ", "{ارْسُمِ/ارْسُمي} الخَطَّ المُتَعَرِّجَ عَلى النِّقاطِ"),
    "circle": (
        "دَوائِرُ كَبيرَةٌ",
        "{ابْدَأْ/ابْدَئي} مِنَ النُّقْطَةِ الخَضْراءِ {وَدُرْ/وَدوري} حَوْلَ الدّائِرَةِ",
    ),
    "lane": ("داخِلَ المَمَرِّ", "{ارْسُمْ/ارْسُمي} خَطًّا داخِلَ المَمَرِّ دونَ لَمْسِ الحَوافِّ"),
    "bridge": ("جُسورٌ صَغيرَةٌ", "{ارْسُمِ/ارْسُمي} الجُسورَ عَلى النِّقاطِ"),
    "loop": ("حَلَقاتٌ", "{ارْسُمِ/ارْسُمي} الحَلَقاتِ عَلى النِّقاطِ"),
    "teeth": ("أَسْنانُ السّينِ", "{ارْسُمِ/ارْسُمي} الأَسْنانَ الصَّغيرَةَ عَلى النِّقاطِ"),
    "small-loop": ("حَلَقاتٌ صَغيرَةٌ مُغْلَقَةٌ", "{ارْسُمِ/ارْسُمي} الحَلْقَةَ {وَأَغْلِقْها/وَأَغْلِقيها}"),
    "grid-copy": ("أَرْسُمُ مِثْلَهُ", "{انْظُرْ/انْظُري} إلى الرَّسْمِ {وَارْسُمْ/وَارْسُمي} مِثْلَهُ عَلى النِّقاطِ"),
    "connected": ("خُطوطٌ مُتَّصِلَةٌ", "{ارْسُمِ/ارْسُمي} الخَطَّ كُلَّهُ دونَ أَنْ {تَرْفَعَ/تَرْفَعي} القَلَمَ"),
}
SHAPE_NAMES_KG1 = {"circle": "الدّائِرَةُ", "square": "المُرَبَّعُ", "triangle": "المُثَلَّثُ", "rectangle": "المُسْتَطيلُ"}
TRACE_TITLES_KG1 = {
    "straight": ("الطَّريقُ المُسْتَقيمُ", "{تَتَبَّعِ/تَتَبَّعي} الطَّريقَ بِالقَلَمِ"),
    "winding": ("الطَّريقُ المُتَعَرِّجُ", "{تَتَبَّعِ/تَتَبَّعي} الطَّريقَ بِالقَلَمِ"),
    "sharp-turns": (
        "مُنْعَطَفاتٌ حادَّةٌ",
        "{تَتَبَّعِ/تَتَبَّعي} الطَّريقَ {وَانْتَبِهْ/وَانْتَبِهي} عِنْدَ كُلِّ مُنْعَطَفٍ",
    ),
}
HARAKA_AR = {"fatha": "الفتحة", "damma": "الضمة", "kasra": "الكسرة"}
HARAKA_HEARD = {"fatha": "الفَتْحَةَ", "damma": "الضَّمَّةَ", "kasra": "الكَسْرَةَ"}  # «أَسْمَعُ الفَتْحَةَ»
CONNECT_KG1 = {
    "related": ("ما الَّذي يُناسِبُهُ؟", "{صِلْ/صِلي} كُلَّ صورَةٍ بِما يُناسِبُها"),
    "need": ("مَتى نَحْتاجُهُ؟", "{صِلْ/صِلي} كُلَّ شَيْءٍ بِما نَحْتاجُهُ لَهُ"),
    "sequence": ("ماذا يَحْدُثُ أَوَّلًا؟", "{صِلْ/صِلي} كُلَّ صورَةٍ بِرَقْمِ تَرْتيبِها"),
    "mixed-review": ("أَصِلُ ما تَعَلَّمْتُ", "{صِلْ/صِلي} كُلَّ شَيْءٍ بِما يُناسِبُهُ"),
}
CLASSIFY_KG1 = {
    "kind": ("حَيَواناتٌ وَفَواكِهُ", "{صِلْ/صِلي} كُلَّ صورَةٍ بِمَجْموعَتِها"),
    "habitat": ("في البَرِّ أَمْ في البَحْرِ؟", "{صِلْ/صِلي} كُلَّ حَيَوانٍ بِمَكانِهِ"),
}
COMPARE_KG1 = {
    "order-size": ("مِنَ الأَصْغَرِ إلى الأَكْبَرِ", "{اكْتُبْ/اكْتُبي} ١ تَحْتَ الأَصْغَرِ وَ٣ تَحْتَ الأَكْبَرِ"),
    "equal": ("العَدَدُ نَفْسُهُ", "{صِلْ/صِلي} واحِدًا بِواحِدٍ {وَحَوِّطِ/وَحَوِّطي} الصَّفَّ المُتَساوِيَ"),
    "fewer": ("أَقَلُّ", "{حَوِّطِ/حَوِّطي} المَجْموعَةَ الأَقَلَّ في كُلِّ صَفٍّ"),
}
CUT_KG1 = "{قُصَّ/قُصّي} الصُّوَرَ {وَأَلْصِقْها/وَأَلْصِقيها}"


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
            return _shapes(p.get("shapes", ["square"])), "{تَتَبَّعِ/تَتَبَّعي} الأَشْكالَ عَلى النِّقاطِ", ""
        case "pen-lines" if str(p.get("line", "horizontal")) in PEN_TITLES_KG1 and p.get("line") != "spiral":
            title, say = PEN_TITLES_KG1[str(p.get("line", "horizontal"))]
            return title, say, ""
        case "trace-path" if p.get("path") in TRACE_TITLES_KG1:
            return (*TRACE_TITLES_KG1[str(p["path"])], "")
        case "coloring" if p.get("mode") == "hidden" and p.get("find") == "star":
            stars = counted(p.get("count", 5), "نُجومٍ", "نَجْمَةً")
            return "أَيْنَ اخْتَبَأَتِ النُّجومُ؟", f"{{جِدْ/جِدي}} {stars} {{وَلَوِّنْها/وَلَوِّنيها}}", ""
        case "coloring" if p.get("mode") == "hidden":
            things = counted(p.get("count", 5), "أَشْياءَ مَخْفِيَّةٍ", "شَيْئًا مَخْفِيًّا")
            return "أَيْنَ اخْتَبَأَتْ؟", f"{{جِدْ/جِدي}} {things} {{وَلَوِّنْها/وَلَوِّنيها}}", ""
        case "coloring" if p.get("mode") == "color-by-code":
            return "أُلَوِّنُ حَسَبَ الرَّمْزِ", "لِكُلِّ حَرْفٍ وَعَدَدٍ لَوْنٌ: {لَوِّنِ/لَوِّني} الصّورَةَ", ""
        case "coloring" if subject == "english":
            return (
                "Color and say",
                "{لَوِّنِ/لَوِّني} الصُّوَرَ {وَقُلْ/وَقولي} كَلِماتِها",
                "Color the pictures and say the words.",
            )
        case "coloring" if "area" in p:
            return "أُلَوِّنُ بِعِنايَةٍ", "{لَوِّنْ/لَوِّني} داخِلَ الحُدودِ", ""
        case "dot-to-dot":
            return f"مِنْ 1 إلى {p.get('to', 5)}", "{صِلِ/صِلي} النِّقاطَ بِالتَّرْتيبِ", ""
        case "drawing" if p.get("task") == "self-portrait":
            return (
                "أَنا وَأَصْدِقائي",
                "{ارْسُمْ نَفْسَكَ مَعَ أَصْدِقائِكَ/ارْسُمي نَفْسَكِ مَعَ أَصْدِقائِكِ} في الرَّوْضَةِ",
                "",
            )
        case "letter-position" if len(letters) == 1:
            return (
                f"أَيْنَ {letters_head(letters)} في الكَلِمَةِ؟",
                "{لَوِّنِ/لَوِّني} الحَرْفَ {وَضَعْ/وَضَعي} عَلامَةً عَلى مَكانِهِ",
                "",
            )
        case "unit-review" if subject == "arabic" and letters and len(strip_tashkeel(unit_title)) > 30:
            # «حرفا السين والشين، ومراجعة ر ز س ش» is too long for a title: the letters themselves do
            # (letters counted without their marks, so a vowelized title takes the same branch)
            return "مُراجَعَةُ حُروفي: " + " ".join(letters), "هَيّا نُراجِعْ ما {تَعَلَّمْتَ/تَعَلَّمْتِ}", ""
        case "harakat" | "unit-review" if "haraka" in p or "harakat" in p:
            return _harakat_title(p), "{اسْمَعْ/اسْمَعي} {وَحَوِّطْ/وَحَوِّطي} ما {تَسْمَعُ/تَسْمَعينَ}", ""
        case "word-read" if p.get("mode") == "first-letter":
            return (
                "الحَرْفُ الأَوَّلُ",
                "{اسْمَعِ/اسْمَعي} اسْمَ الصّورَةِ {وَحَوِّطْ/وَحَوِّطي} حَرْفَهُ الأَوَّلَ",
                "",
            )
        case "word-read" | "unit-review" if "words" in p:
            return "أَسْمَعُ الكَلِمَةَ", "{اسْمَعِ/اسْمَعي} الكَلِمَةَ {وَأَشِرْ/وَأَشيري} إلى صورَتِها", ""
        case "word-write":
            return "أَتَتَبَّعُ الكَلِمَةَ", "{تَتَبَّعِ/تَتَبَّعي} الكَلِمَةَ عَلى النِّقاطِ", ""
        case "unit-review" if "units" in p:
            return "Review: my words", "هَيّا نُراجِعِ الكَلِماتِ", "Let's review the words."
        case "vocab-unit":
            unit = str(p.get("unit", "Words"))
            return (
                unit,
                "{قُلِ/قولي} الكَلِمَةَ {وَلَوِّنِ/وَلَوِّني} الصّورَةَ",
                "Say the word and color the picture.",
            )
        case "picture-add":
            return "أَجْمَعُ بِالصُّوَرِ", "{عُدَّ/عُدّي} الكُلَّ {وَحَوِّطِ/وَحَوِّطي} العَدَدَ الصَّحيحَ", ""
        case "picture-subtract":
            return "أَطْرَحُ بِالصُّوَرِ", "{عُدَّ/عُدّي} ما بَقِيَ {وَحَوِّطِ/وَحَوِّطي} العَدَدَ الصَّحيحَ", ""
        case "compare" if p.get("concept") in COMPARE_KG1:
            return (*COMPARE_KG1[str(p["concept"])], "")
        case "compare" if p.get("concept") == "more-less":
            return COMPARE["more-less"][0], "{حَوِّطِ/حَوِّطي} الأَكْثَرَ في كُلِّ صَفٍّ", ""
        case "shapes" if p.get("mode") == "find":
            return "أَجِدُ الأَشْكالَ", "{لَوِّنْ/لَوِّني} كُلَّ شَكْلٍ بِلَوْنِهِ", ""
        case "shapes" if p.get("shapes"):
            return _shapes(p["shapes"]), "{تَتَبَّعِ/تَتَبَّعي} الأَشْكالَ ثُمَّ {لَوِّنْها/لَوِّنيها}", ""
        case "number-write" if p.get("numbers"):
            listed = " وَ".join(str(n) for n in p["numbers"])
            return (
                f"أَكْتُبُ الأَعْدادَ {listed}",
                "{اكْتُبْ/اكْتُبي} عَلى النِّقاطِ، ثُمَّ {وَحْدَكَ/وَحْدَكِ}",
                "",
            )
        case "pattern-complete" if p.get("kind") == "numbers":
            return "قِطارُ الأَعْدادِ", "{اكْتُبِ/اكْتُبي} العَدَدَ النّاقِصَ في كُلِّ عَرَبَةٍ", ""
        case "position-words" if p.get("concept") == "inside-outside":
            return "داخِلَ الصُّنْدوقِ أَمْ خارِجَهُ؟", "{حَوِّطْ/حَوِّطي} ما داخِلَ الصُّنْدوقِ", ""
        case "connect" if p.get("mode") in CONNECT_KG1:
            return (*CONNECT_KG1[str(p["mode"])], "")
        case "classify" if p.get("by") in CLASSIFY_KG1:
            return (*CLASSIFY_KG1[str(p["by"])], "")
        case "cut-and-paste" if p.get("task") == "shadows":
            return "كُلُّ صورَةٍ فَوْقَ ظِلِّها", f"{CUT_KG1} فَوْقَ ظِلِّها", ""
        case "cut-and-paste" if p.get("task") == "sequence":
            return "أُرَتِّبُ القِصَّةَ", f"{CUT_KG1} بِالتَّرْتيبِ", ""
        case "cut-and-paste":
            return "أُرَكِّبُ الصّورَةَ", "{قُصَّ/قُصّي} القِطَعَ {وَأَلْصِقْها/وَأَلْصِقيها} في مَكانِها", ""
        case "certificate":
            return "شَهادَةُ إِنْجازٍ", "{أَنْهى/أَنْهَتْ} {child} دوسِيَّةَ التَّأْسيسِ: مَبْروكٌ!", ""
    return None
