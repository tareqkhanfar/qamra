"""Volume 2 of «دوسية التأسيس» on the same plan → engine mapping as Volume 1 (`foundation.py`): which plan
pages go to the Volume 2 builders (`engine_type_v2`), and the child-facing texts of the new page types and
modes (`texts_v2`). `foundation.from_curriculum` asks here first; a `None` means "as in Volume 1".
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.curriculum import Page
from qamra_workbook.render.foundation_text import (
    COMPARE,
    PEN_SAY,
    Texts,
    counted,
    joined,
    letter_write_say,
    letters_head,
    math_texts,
    pick,
    turn,
    vowelled_letter_name,
)

NUMBER_TYPES = ("number-intro", "number-trace", "number-write", "count-and-circle", "number-quantity-match")


def _numbers(params: dict[str, Any]) -> list[int]:
    raw = params.get("numbers", [params["number"]] if "number" in params else [])
    return [int(x) for x in raw]


def engine_type_v2(page: Page) -> str | None:
    """The Volume 2 builder for a plan page, by its type and params; None when Volume 1's builder serves."""
    p = page.params
    match page.type:
        case "position-words":
            return "place-words"
        case "shapes" if len(p.get("shapes", [])) >= 4:
            return "shapes-four"
        case "letter-write" if "letters" in p:
            return "letters-write"
        case "pen-lines":
            return {"spiral": "spiral-lines", "between-lines": "between-lines"}.get(str(p.get("line", "")))
        case "trace-path" if p.get("path") == "narrow":
            return "narrow-path"
        case "dot-to-dot" if p.get("sequence") == "letters":
            return "letter-dot-to-dot"
        case "coloring" if p.get("mode") == "color-by-letter":
            return "color-by-letter"
        case "coloring" if "hidden" in p:
            return "hidden-pictures"
        case "classify" if p.get("by") == "category":
            return "classify-category"
        case "memory" if int(p.get("items", 4)) >= 6:
            return "memory-gone"
        case "cut-and-paste" if p.get("mode") == "sequence":
            return "story-sequence"
        case "drawing" if p.get("mode") == "missing-part":
            return "missing-part"
        case "connect" if not p.get("words") and int(p.get("pairs", 4)) >= 5:
            return "connect-related"
        case "pattern-complete" if p.get("kind") == "number-sequence":
            return "number-train"
        case "pattern-complete" if str(p.get("pattern", "AB")) == "ABC":
            return "pattern-abc"
        case "compare" if max(_numbers(p), default=0) > 5:
            return "compare-ten"
    if page.type in NUMBER_TYPES and max(_numbers(p), default=0) > 5:
        return f"{page.type}-ten"
    return None


# draft: educator review: the titles and instructions below have not been through the educator yet
POSITION_TEXTS = {
    "above-below": ("فَوْقَ وَتَحْتَ", "{لَوِّنْ/لَوِّني} ما فَوْقُ بِالأَحْمَرِ، وَما تَحْتُ بِالأَزْرَقِ"),
    "front-behind": ("أَمامَ وَخَلْفَ", "ما الَّذي في الأَمامِ؟ {حَوِّطْهُ/حَوِّطيهِ}"),
    "right-left": ("يَمينٌ وَيَسارٌ", "{لَوِّنِ/لَوِّني} الصّورَةَ اليُمْنى بِالأَحْمَرِ، وَاليُسْرى بِالأَزْرَقِ"),
}
LETTER_POSITION = (  # color the letter inside each word, then mark where it sits: first, middle or last
    "{لَوِّنِ/لَوِّني} الحَرْفَ، {وَضَعْ/وَضَعي} عَلامَةً عَلى مَكانِهِ",
    "{لَوِّنِ/لَوِّني} الحَرْفَ، ثُمَّ {اخْتَرْ/اخْتاري}: أَوَّلٌ، وَسَطٌ، آخِرٌ",
)
COLOR_BY_LETTER = (  # a picture in cells, each cell a letter; the legend gives each letter its color
    "لِكُلِّ حَرْفٍ لَوْنٌ: {لَوِّنِ/لَوِّني} الصّورَةَ جُزْءًا جُزْءًا",
    "{انْظُرْ/انْظُري} إلى الحَرْفِ، ثُمَّ {لَوِّنْ/لَوِّني} مَكانَهُ بِلَوْنِهِ",
    "{سَمِّ/سَمّي} الحَرْفَ، ثُمَّ {لَوِّنْ/لَوِّني} ما حَوْلَهُ بِلَوْنِهِ",
)
CUT = "{قُصَّ/قُصّي} الصُّوَرَ"


def letter_position_say(params: dict[str, Any]) -> str:
    return pick(LETTER_POSITION, turn(params))


def hidden_say(params: dict[str, Any], plural: str, singular: str) -> str:
    """«ابْحَثْ عَنْ ٥ أَشْياءَ مَخْفِيَّةٍ، وَلَوِّنْها» (the count from the plan)."""
    things = counted(params.get("hidden", params.get("count", 5)), plural, singular)
    return pick(
        (
            "{ابْحَثْ/ابْحَثي} عَنْ " + things + "، {وَلَوِّنْها/وَلَوِّنيها}",
            "في الصّورَةِ " + things + ": {جِدْها/جِديها} {وَلَوِّنْها/وَلَوِّنيها}",
        ),
        turn(params),
    )


def texts_v2(subject: str, kind: str, params: dict[str, Any], unit_title: str) -> Texts | None:
    """Titles and instructions for the Volume 2 pages; None when Volume 1's texts serve."""
    letters = [str(x) for x in params.get("letters", [])]
    match kind:
        case "letter-position":
            return f"أَيْنَ {letters_head(letters)} في الكَلِمَةِ؟", letter_position_say(params), ""
        case "position-words":
            raw = params.get("concept", "above-below")
            first = str(raw[0] if isinstance(raw, list) else raw)
            title, say = POSITION_TEXTS.get(first, POSITION_TEXTS["above-below"])
            return ("فَوْقَ وَتَحْتَ، داخِلَ وَخارِجَ" if isinstance(raw, list) else title), say, ""
        case "letter-write" if letters:
            names = joined([vowelled_letter_name(x, "a") for x in letters])
            return f"أَكْتُبُ {names}", letter_write_say(params, len(letters)), ""
        case "pen-lines" if params.get("line") == "spiral":
            return "حَلَزوناتٌ", PEN_SAY["spiral"], ""
        case "pen-lines" if params.get("line") == "between-lines":
            return (
                "بَيْنَ السَّطْرَيْنِ",
                "{ارْسُمِ/ارْسُمي} الأَشْكالَ، وَلا {تَخْرُجْ/تَخْرُجي} عَنِ السَّطْرَيْنِ",
                "",
            )
        case "trace-path" if params.get("path") == "narrow":
            return "الطَّريقُ الضَّيِّقُ", "{امْشِ/امْشي} بِالقَلَمِ بِهُدوءٍ، بَعيدًا عَنِ الحَوافِّ", ""
        case "dot-to-dot" if params.get("sequence") == "letters":
            return (
                f"مِنَ الأَلِفِ إلى {vowelled_letter_name(str(params.get('to', 'ش')))}",
                "{صِلِ/صِلي} النِّقاطَ بِتَرْتيبِ الحُروفِ: أ، ب، ت…",
                "",
            )
        case "coloring" if params.get("mode") == "color-by-letter":
            return "أُلَوِّنُ حَسَبَ الحَرْفِ", pick(COLOR_BY_LETTER, turn(params)), ""
        case "coloring" if "hidden" in params:
            return "أَيْنَ اخْتَبَأَتْ؟", hidden_say(params, "أَشْياءَ مَخْفِيَّةٍ", "شَيْئًا مَخْفِيًّا"), ""
        case "classify" if params.get("by") == "category":
            return (
                "أُصَنِّفُ في مَجْموعاتٍ",
                "{انْظُرْ/انْظُري} إلى كُلِّ صورَةٍ، {وَصِلْها/وَصِليها} بِمَجْموعَتِها",
                "",
            )
        case "memory" if int(params.get("items", 4)) >= 6:
            return (
                "ماذا اخْتَفى؟",
                "{احْفَظِ/احْفَظي} الصُّوَرَ السِّتَّ، ثُمَّ {غَطِّها/غَطّيها}: أَيُّها اخْتَفى؟",
                "",
            )
        case "cut-and-paste" if params.get("mode") == "sequence":
            return "أُرَتِّبُ القِصَّةَ", f"{CUT}، ثُمَّ {{رَتِّبْها/رَتِّبيها}} {{وَأَلْصِقْها/وَأَلْصِقيها}}", ""
        case "drawing" if params.get("mode") == "missing-part":
            return "ماذا يَنْقُصُ؟", "{أَكْمِلْ/أَكْمِلي} كُلَّ صورَةٍ بِرَسْمِ ما يَنْقُصُها", ""
        case "connect" if not params.get("words") and int(params.get("pairs", 4)) >= 5:
            return "ما الَّذي يُناسِبُهُ؟", "{صِلْ/صِلي} كُلَّ صورَةٍ بِما يُناسِبُها", ""
        case "pattern-complete" if params.get("kind") == "number-sequence":
            return "قِطارُ الأَعْدادِ", "أَيُّ عَدَدٍ ناقِصٌ؟ {اكْتُبْهُ/اكْتُبيهِ} في كُلِّ قِطارٍ", ""
        case "compare" if max(_numbers(params), default=0) > 5:
            return (
                COMPARE["more-less"][0],
                "{عُدَّ/عُدّي} {وَاكْتُبِ/وَاكْتُبي} العَدَدَيْنِ، ثُمَّ {حَوِّطِ/حَوِّطي} الأَكْثَرَ",
                "",
            )
    if kind in NUMBER_TYPES and subject == "math":
        return math_texts(kind, params)
    return None
