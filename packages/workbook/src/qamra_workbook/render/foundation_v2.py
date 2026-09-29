"""Volume 2 of «دوسية التأسيس» on the same plan → engine mapping as Volume 1 (`foundation.py`): which plan
pages go to the Volume 2 builders (`engine_type_v2`), and the child-facing texts of the new page types and
modes (`texts_v2`). `foundation.from_curriculum` asks here first; a `None` means "as in Volume 1".
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.curriculum import Page
from qamra_workbook.render.foundation_text import COMPARE, Texts, letter_name, math_texts

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


# draft: educator review: every title and instruction below is new text
POSITION_TEXTS = {
    "above-below": ("فوق وتحت", "{لوّن/لوّني} ما فوق بالأحمر وما تحت بالأزرق"),
    "front-behind": ("أمام وخلف", "{حوّط/حوّطي} ما أمام الشجرة أو البيت"),
    "right-left": ("يمين ويسار", "{لوّن/لوّني} اليمين بالأحمر واليسار بالأزرق"),
}


def texts_v2(subject: str, kind: str, params: dict[str, Any], unit_title: str) -> Texts | None:
    """Titles and instructions for the Volume 2 pages; None when Volume 1's texts serve."""
    letters = [str(x) for x in params.get("letters", [])]
    names = [letter_name(x) for x in letters]
    match kind:
        case "letter-position":
            head = (
                f"حرفا {names[0]} و{names[1]}"
                if len(names) == 2
                else "حروف " + "، ".join(names[:-1]) + " و" + names[-1]
            )
            return f"أين {head} في الكلمة؟", "{لوّن/لوّني} الحرف {وضع/وضعي} علامة على مكانه", ""
        case "position-words":
            raw = params.get("concept", "above-below")
            first = str(raw[0] if isinstance(raw, list) else raw)
            title, say = POSITION_TEXTS.get(first, POSITION_TEXTS["above-below"])
            return ("فوق وتحت، داخل وخارج" if isinstance(raw, list) else title), say, ""
        case "letter-write" if letters:
            return f"أكتب {names[0]} و{names[1]}", "{اكتب/اكتبي} على النقاط، ثم وحدك", ""
        case "pen-lines" if params.get("line") == "spiral":
            return "حلزونات", "{ابدأ/ابدئي} من الخارج {ولفّ/ولفّي} إلى الداخل", ""
        case "pen-lines" if params.get("line") == "between-lines":
            return "بين السطرين", "{ارسم/ارسمي} الأشكال بين السطرين", ""
        case "trace-path" if params.get("path") == "narrow":
            return "الطريق الضيّق", "{امشِ/امشي} بالقلم دون أن {تلمس/تلمسي} الحواف", ""
        case "dot-to-dot" if params.get("sequence") == "letters":
            return (
                f"من الألف إلى {letter_name(str(params.get('to', 'ش')))[2:]}",
                "{صِل/صِلي} الحروف بالترتيب",
                "",
            )
        case "coloring" if params.get("mode") == "color-by-letter":
            return "ألوّن حسب الحرف", "لكل حرف لون: {لوّن/لوّني} السمكة", ""
        case "coloring" if "hidden" in params:
            return "أين اختبأت؟", f"{{جِد/جِدي}} {params.get('hidden', 5)} أشياء مخفية {{ولوّنها/ولوّنيها}}", ""
        case "classify" if params.get("by") == "category":
            return "أصنّف في مجموعات", "{صِل/صِلي} كل صورة بمجموعتها", ""
        case "memory" if int(params.get("items", 4)) >= 6:
            return "ماذا اختفى؟", "{انظر/انظري}، ثم {غطِّ/غطّي} الصور {وجِد/وجِدي} ما اختفى", ""
        case "cut-and-paste" if params.get("mode") == "sequence":
            return "أرتّب القصة", "{قُصّ/قُصّي} الصور {والصقها/والصقيها} بالترتيب", ""
        case "drawing" if params.get("mode") == "missing-part":
            return "ماذا ينقص؟", "{ارسم/ارسمي} الجزء الناقص", ""
        case "connect" if not params.get("words") and int(params.get("pairs", 4)) >= 5:
            return "ما الذي يناسبه؟", "{صِل/صِلي} كل شيء بما يرتبط به", ""
        case "pattern-complete" if params.get("kind") == "number-sequence":
            return "قطار الأعداد", "{اكتب/اكتبي} العدد الناقص في كل قطار", ""
        case "compare" if max(_numbers(params), default=0) > 5:
            return COMPARE["more-less"][0], "{حوّط/حوّطي} الأكثر {واكتب/واكتبي} العددين", ""
    if kind in NUMBER_TYPES and subject == "math":
        return math_texts(kind, params)
    return None
