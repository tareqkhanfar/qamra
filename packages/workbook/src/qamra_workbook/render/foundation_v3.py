"""Volume 3 of «دوسية التأسيس» on the plan → engine mapping (`foundation.py`): which plan pages go to the
Volume 3 builders (`engine_type_v3`, asked before Volume 2's) and the child-facing texts of its page types
(`texts_v3`).
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.curriculum import Page
from qamra_workbook.render.foundation_text import Texts, joined, vowelled_letter_name


def _numbers(params: dict[str, Any]) -> list[int]:
    raw = params.get("numbers", [params["number"]] if "number" in params else [])
    return [int(x) for x in raw]


def engine_type_v3(page: Page) -> str | None:
    """The Volume 3 builder for a plan page; None when Volume 2's or Volume 1's builder serves."""
    p = page.params
    teens = max(_numbers(p), default=0) > 10
    match page.type:
        case (
            "harakat"
            | "syllables"
            | "word-read"
            | "word-write"
            | "sentence-read"
            | "picture-add"
            | "picture-subtract"
        ):
            return page.type
        case "vocab-unit":
            return "vocab-cards"
        case "certificate":
            return "workbook-certificate"
        case "letter-trace" if "letters" in p:
            return "letters-trace"
        case "letter-write" if "letters" in p and page.unit.startswith("v3-"):
            return "letters-write-3"  # Volume 2's twin-letter page claims the letters differ only by dots
        case "number-quantity-match" if teens:
            return "teen-quantity-match"
        case "number-trace" if teens:
            return "teen-trace"
        case "count-and-circle" if teens:
            return "count-to-twenty"
        case "compare" if p.get("concept") == "bigger-smaller":
            return "compare-numbers"
        case "pattern-complete" if p.get("kind") == "number-line":
            return "number-line-fill"
        case "pattern-complete" if p.get("kind") == "picture-grid":
            return "picture-grid"
        case "pattern-complete" if p.get("pattern") == "growing":
            return "growing-pattern"
        case "pen-lines" if p.get("line") == "joins":
            return "join-strokes"
        case "trace-path" if p.get("path") == "complex":
            return "complex-path"
        case "classify" if isinstance(p.get("by"), list):
            return "classify-table"
        case "memory" if p.get("mode") == "order":
            return "memory-order"
        case "connect" if p.get("mode") == "cause-effect":
            return "cause-effect"
        case "connect" if page.subject == "mixed":
            return "mixed-connect"
        case "drawing" if p.get("mode") == "problem-solving":
            return "problem-drawing"
        case "cut-and-paste" if p.get("mode") == "build-words":
            return "build-words"
    return None


HARAKA_TITLE = {"فتحة": "الفَتْحَةُ", "ضمة": "الضَّمَّةُ", "كسرة": "الكَسْرَةُ", "سكون": "السُّكونُ"}
# the English unit as the child's instruction names it: «{اقْرَأِ/اقْرَئي} الأَلْوانَ بِالإِنْجِليزِيَّةِ»
UNIT_READ = {
    "Numbers": "الأَعْدادَ",
    "Colors": "الأَلْوانَ",
    "Shapes": "الأَشْكالَ",
    "Family": "العائِلَةَ",
    "Body Parts": "أَعْضاءَ الجِسْمِ",
    "Animals": "الحَيَواناتِ",
    "Fruits": "الفَواكِهَ",
    "Food": "الطَّعامَ",
    "Toys": "الأَلْعابَ",
    "School Objects": "أَدَواتِ المَدْرَسَةِ",
}
CUT = "{قُصَّ/قُصّي} المَقاطِعَ {وَأَلْصِقْها/وَأَلْصِقيها}"


def texts_v3(subject: str, kind: str, params: dict[str, Any], unit_title: str) -> Texts | None:
    """Titles and instructions of the Volume 3 pages (draft: educator review); None if earlier ones serve."""
    letters = [str(x) for x in params.get("letters", [])]
    match kind:
        case "harakat":
            h = str(params.get("haraka", "فتحة"))
            return HARAKA_TITLE.get(h, h), "{اقْرَأِ/اقْرَئي} الحَرْفَ مَعَ حَرَكَتِهِ", ""
        case "syllables" if params.get("mode") == "build":
            return "أُرَكِّبُ مَقْطَعًا", "{رَكِّبِ/رَكِّبي} الحَرْفَ مَعَ الحَرَكَةِ {وَاقْرَأْ/وَاقْرَئي}", ""
        case "syllables" if params.get("mode") == "long":
            return "مَقاطِعُ طَويلَةٌ", "{اقْرَأْ/اقْرَئي} كُلَّ صَفٍّ: بَا بُو بِي", ""
        case "syllables":
            return "مَقاطِعُ قَصيرَةٌ", "{اقْرَأْ/اقْرَئي} كُلَّ صَفٍّ مِنَ اليَمينِ", ""
        case "word-read" if subject == "english":
            return (
                "I can read",
                "{اقْرَأِ/اقْرَئي} الكَلِمَةَ {وَحَوِّطْ/وَحَوِّطي} صورَتَها",
                "Read the word and circle its picture.",
            )
        case "word-read" if params.get("mode") == "al":
            return "أَقْرَأُ مَعَ «ال»", "{اقْرَأِ/اقْرَئي} الكَلِمَةَ {وَحَوِّطْ/وَحَوِّطي} صورَتَها", ""
        case "word-read":
            return "أَقْرَأُ كَلِماتٍ", "{اقْرَأِ/اقْرَئي} الكَلِمَةَ {وَحَوِّطْ/وَحَوِّطي} صورَتَها", ""
        case "word-write" if params.get("mode") == "independent":
            return "أَكْتُبُ وَحْدي", "{انْظُرْ/انْظُري} إلى الصّورَةِ {وَاكْتُبِ/وَاكْتُبي} اسْمَها", ""
        case "word-write":
            return (
                "أَكْتُبُ كَلِماتٍ",
                "{اكْتُبِ/اكْتُبي} الكَلِمَةَ عَلى النِّقاطِ، ثُمَّ {وَحْدَكَ/وَحْدَكِ}",
                "",
            )
        case "sentence-read" if subject == "english":
            return "I can read", "{صِلْ/صِلي} كُلَّ جُمْلَةٍ بِصورَتِها", "Match each sentence to its picture."
        case "sentence-read" if params.get("personal"):
            return "أَنا أَقْرَأُ", "{صِلْ/صِلي} كُلَّ جُمْلَةٍ {بِصورَتِكَ/بِصورَتِكِ}", ""
        case "sentence-read":
            return "أَقْرَأُ جُمَلًا", "{صِلْ/صِلي} كُلَّ جُمْلَةٍ بِصورَتِها", ""
        case "vocab-unit":
            unit = str(params.get("unit", ""))
            what = UNIT_READ.get(unit, "الكَلِماتِ")
            read = "{اقْرَأِ/اقْرَئي}" if what.startswith("ال") else "{اقْرَأْ/اقْرَئي}"
            return f"{unit}", f"{read} {what} بِالإِنْجِليزِيَّةِ", f"Say the {unit.lower()}."
        case "picture-add" if params.get("mode") == "story":
            return "مَسْأَلَةُ جَمْعٍ", "{اقْرَأِ/اقْرَئي} القِصَّةَ {وَاحْسُبْ/وَاحْسُبي}", ""
        case "picture-add" if params.get("mode") == "number-line":
            return (
                "أَجْمَعُ عَلى خَطِّ الأَعْدادِ",
                "{اقْفِزْ/اقْفِزي} عَلى الخَطِّ {وَاكْتُبِ/وَاكْتُبي} النّاتِجَ",
                "",
            )
        case "picture-add" if params.get("mode") == "make-ten":
            return "أُكَوِّنُ العَشَرَةَ", "{أَكْمِلْ/أَكْمِلي} جُمْلَةَ الجَمْعِ لِتَصيرَ عَشَرَةً", ""
        case "picture-add" if params.get("mode") == "choose-operation":
            return (
                "أَجْمَعُ أَمْ أَطْرَحُ؟",
                "{حَوِّطِ/حَوِّطي} الإِشارَةَ الصَّحيحَةَ {وَاكْتُبِ/وَاكْتُبي} النّاتِجَ",
                "",
            )
        case "picture-add":
            return "أَجْمَعُ بِالصُّوَرِ", "{عُدَّ/عُدّي} الكُلَّ {وَاكْتُبِ/وَاكْتُبي} النّاتِجَ", ""
        case "picture-subtract" if params.get("mode") == "story":
            return "مَسْأَلَةُ طَرْحٍ", "{اقْرَأِ/اقْرَئي} القِصَّةَ {وَاحْسُبْ/وَاحْسُبي}", ""
        case "picture-subtract":
            return "أَطْرَحُ بِالصُّوَرِ", "{عُدَّ/عُدّي} الباقِيَ {وَاكْتُبِ/وَاكْتُبي} النّاتِجَ", ""
        case "number-quantity-match" if max(_numbers(params), default=0) > 10:
            return "عَشَرَةٌ وَآحادٌ", "{صِلْ/صِلي} كُلَّ عَدَدٍ بِعَشَرَتِهِ وَآحادِهِ", ""
        case "number-trace" if max(_numbers(params), default=0) > 10:
            return "أَتَتَبَّعُ الأَعْدادَ", "{تَتَبَّعِ/تَتَبَّعي} العَدَدَ ثُمَّ {اكْتُبْهُ/اكْتُبيهِ}", ""
        case "count-and-circle" if max(_numbers(params), default=0) > 10:
            return "أَعُدُّ حَتّى عِشْرينَ", "{عُدَّ/عُدّي} {وَحَوِّطِ/وَحَوِّطي} العَدَدَ الصَّحيحَ", ""
        case "compare" if params.get("concept") == "bigger-smaller":
            return "الأَكْبَرُ", "{حَوِّطِ/حَوِّطي} العَدَدَ الأَكْبَرَ", ""
        case "pattern-complete" if params.get("kind") == "number-line":
            return "خَطُّ الأَعْدادِ", "{اكْتُبِ/اكْتُبي} الأَعْدادَ النّاقِصَةَ", ""
        case "pattern-complete" if params.get("kind") == "picture-grid":
            return "جَدْوَلُ الصُّوَرِ", "{ارْسُمِ/ارْسُمي} الصّورَةَ النّاقِصَةَ في كُلِّ مُرَبَّعٍ", ""
        case "pattern-complete" if params.get("pattern") == "growing":
            return "النَّمَطُ المُتَزايِدُ", "{ارْسُمِ/ارْسُمي} الخُطْوَتَيْنِ التّالِيَتَيْنِ", ""
        case "pen-lines" if params.get("line") == "joins":
            return "خُطوطُ الوَصْلِ", "{تَتَبَّعِ/تَتَبَّعي} الحُروفَ المُتَّصِلَةَ عَلى السَّطْرِ", ""
        case "trace-path" if params.get("path") == "complex":
            return "الطَّريقُ الطَّويلُ", "{تَتَبَّعِ/تَتَبَّعي} الطَّريقَ بِمُنْعَطَفاتِهِ", ""
        case "letter-trace" if letters:
            names = joined([vowelled_letter_name(x, "a") for x in letters])
            return (
                f"أَتَتَبَّعُ {names}",
                "{ابْدَأْ/ابْدَئي} مِنَ النُّقْطَةِ الخَضْراءِ {وَاتْبَعِ/وَاتْبَعي} الأَسْهُمَ",
                "",
            )
        case "classify" if isinstance(params.get("by"), list):
            return "أُصَنِّفُ بِصِفَتَيْنِ", "{ارْسُمْ/ارْسُمي} كُلَّ شَكْلٍ في مَكانِهِ", ""
        case "memory" if params.get("mode") == "order":
            return (
                "أَتَذَكَّرُ التَّرْتيبَ",
                "{انْظُرْ/انْظُري}، ثُمَّ {غَطِّ/غَطّي} الصُّوَرَ {وَرَتِّبْ/وَرَتِّبي}",
                "",
            )
        case "connect" if params.get("mode") == "cause-effect":
            return "السَّبَبُ وَالنَّتيجَةُ", "{صِلْ/صِلي} كُلَّ سَبَبٍ بِنَتيجَتِهِ", ""
        case "connect" if subject == "mixed":
            return "أَصِلُ ما تَعَلَّمْتُ", "{صِلْ/صِلي} كُلَّ شَيْءٍ بِما يُناسِبُهُ", ""
        case "drawing" if params.get("mode") == "problem-solving":
            return "أُفَكِّرُ وَأَرْسُمُ حَلًّا", "{ارْسُمْ/ارْسُمي} كَيْفَ تَعْبُرُ البَطَّةُ النَّهْرَ", ""
        case "cut-and-paste" if params.get("mode") == "build-words":
            return "أَبْني الكَلِمَةَ", f"{CUT} {{لِتَبْنِيَ/لِتَبْني}} الكَلِمَةَ", ""
        case "certificate":
            return (
                "{أَحْسَنْتَ يا بَطَلُ/أَحْسَنْتِ يا بَطَلَةُ}!",
                "{لَوِّنِ/لَوِّني} النُّجومَ {وَاحْتَفِلْ/وَاحْتَفِلي}",
                "",
            )
    return None
