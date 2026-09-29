"""What «دوسية التأسيس» prints for the child on each page: a short title and a one-line instruction (≤ 7
words, in the guide's bubble), with `{masc/fem}` variants and `{child}`. The plan carries only the educator's
skill line (printed in the footer for grown-ups); these texts come from the page type and its params.

English pages carry the instruction in English with the Arabic under it (Addendum 5 §4).
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.letters import NAMES

# draft: educator review: every title and instruction below is new text the educator has not seen yet
Texts = tuple[str, str, str]  # title, Arabic instruction, English instruction ("" on Arabic pages)

NUMBER_NAMES = {0: "صفر", 1: "واحد", 2: "اثنان", 3: "ثلاثة", 4: "أربعة", 5: "خمسة", 6: "ستة", 7: "سبعة"}
NUMBER_NAMES |= {8: "ثمانية", 9: "تسعة", 10: "عشرة"}
COLOR_AR = {"أحمر": "red", "أزرق": "blue", "أصفر": "yellow", "أخضر": "green"}

PEN_TITLES = {
    "horizontal": "خطوط أفقية",
    "vertical": "خطوط عمودية",
    "diagonal": "خطوط مائلة",
    "zigzag": "أسنان المنشار",
    "curve": "أمواج البحر",
    "loops": "دوائر وحلقات",
    "letter-strokes": "ضربات الحروف",
    "spiral": "حلزونات",
}
COMPARE = {
    "big-small": ("كبير وصغير", "{لوّن/لوّني} الكبير في كل صف"),
    "long-short": ("طويل وقصير", "{ضع/ضعي} دائرة حول الطويل"),
    "many-few": ("كثير وقليل", "{ضع/ضعي} دائرة حول الكثير"),
    "more-less": ("أكثر وأقل", "{حوّط/حوّطي} الأكثر {وضع/وضعي} إشارة على الأقل"),
    "tall-short": ("طويل وقصير", "{ضع/ضعي} دائرة حول الأطول"),
    "heavy-light": ("ثقيل وخفيف", "{ضع/ضعي} دائرة حول الأثقل"),
}


def letter_name(char: str) -> str:
    """«الألف» for أ and ا: the letter's Arabic name."""
    return str(NAMES.get("ا" if char in "أإآ" else char, char))


def _pair(names: list[str]) -> str:
    return " و".join(names) if len(names) <= 2 else "، ".join(names[:-1]) + " و" + names[-1]


def arabic_texts(kind: str, params: dict[str, Any]) -> Texts | None:
    letter = str(params.get("letter", ""))
    letters = [str(x) for x in params.get("letters", [letter] if letter else [])]
    name = letter_name(letter) if letter else ""
    names = [letter_name(x) for x in letters]
    match kind:
        case "letter-intro":
            return f"حرف {name}", "{لوّن/لوّني} الحرف والصورتين", ""
        case "letter-trace":
            return f"أتتبّع حرف {name}", "{ابدأ/ابدئي} من النقطة الخضراء {واتبع/واتبعي} الأسهم", ""
        case "letter-write":
            return f"أكتب حرف {name}", "{اكتب/اكتبي} على النقاط، ثم وحدك", ""
        case "find-letter":
            title = f"أين {'حرفا' if len(names) == 2 else 'حروف'} {_pair(names)}؟"
            return title, "{لوّن/لوّني} الحرف {وحوّط/وحوّطي} الصحيح", ""
        case "match-letter-picture":
            return "الحرف والصورة والكلمة", "{صِل/صِلي} الحرف بالصورة ثم بالكلمة", ""
        case "classify":
            return "أين أضعها؟", "{صِل/صِلي} كل صورة بحرفها الأول", ""
        case "connect":
            return "الصوت الأول", "{صِل/صِلي} الصورتين اللتين تبدآن بالصوت نفسه", ""
    return None


def english_texts(kind: str, params: dict[str, Any]) -> Texts | None:
    letter = str(params.get("letter", "A")).upper()
    match kind:
        case "en-letter":
            return f"{letter} {letter.lower()}", "{تتبّع/تتبّعي} الحرف {واكتبه/واكتبيه}", "Trace and write."
        case "find-letter":
            return "Find the letter", "{حوّط/حوّطي} الحرف في كل صف", "Circle the letter in each row."
        case "match-letter-picture" if params.get("mode") == "capital-small":
            return "Big and small", "{صِل/صِلي} الحرف الكبير بالصغير", "Match the big and small letters."
        case "match-letter-picture":
            return "Letters and pictures", "{صِل/صِلي} الحرف بصورته", "Match each letter to its picture."
        case "unit-review":
            return "Review", "هيا نراجع الحروف", "Let's review the letters."
        case "assessment":
            return "What I know", "{أرِ/أري} الكبار ماذا {تعرف/تعرفين}", "Show what you know."
    return None


def math_texts(kind: str, params: dict[str, Any]) -> Texts | None:
    number = params.get("number")
    match kind:
        case "number-intro" if number == 0:
            return "الصفر: لا شيء", "{انظر/انظري} إلى الصحن كيف صار فارغًا", ""
        case "number-intro":
            return f"العدد {NUMBER_NAMES.get(int(number or 1), '')} {number}", "{عُدّ/عُدّي} {ولوّن/ولوّني}", ""
        case "number-trace":
            return f"أتتبّع العدد {number}", "{ابدأ/ابدئي} من النقطة الخضراء", ""
        case "number-write":
            return f"أكتب العدد {number}", "{اكتب/اكتبي} على النقاط، ثم وحدك", ""
        case "count-and-circle":
            return "أعدّ وأحوّط", "{عُدّ/عُدّي} {وحوّط/وحوّطي} العدد الصحيح", ""
        case "number-quantity-match":
            return "العدد والكمية", "{صِل/صِلي} كل عدد بمجموعته", ""
        case "compare":
            title, say = COMPARE.get(str(params.get("concept", "big-small")), COMPARE["big-small"])
            return title, say, ""
        case "coloring":
            return "ألوان جميلة", "{لوّن/لوّني} كل صورة بلونها", ""
    return None


def general_texts(kind: str, params: dict[str, Any], unit_title: str) -> Texts | None:
    match kind:
        case "owner-page":
            return "هذا الكتاب لـ{child}", "{اكتب/اكتبي} اسمك {واطبع/واطبعي} كفّك", ""
        case "name-trace" if params.get("script") == "en":
            return "My name", "{تتبّع/تتبّعي} اسمك بالإنجليزية", "Trace your name."
        case "name-trace":
            return "اسمي", "{تتبّع/تتبّعي} اسمك ثم {اكتبه/اكتبيه}", ""
        case "toc":
            return "ماذا في كتابي؟", "هيا نتعرّف على أقسام الكتاب", ""
        case "unit-opener":
            return unit_title, "هيا نبدأ رحلة جديدة!", ""
        case "pen-lines":
            title = PEN_TITLES.get(str(params.get("line", "horizontal")), "خطوط")
            return title, "{ارسم/ارسمي} على النقاط من النقطة الخضراء", ""
        case "trace-path":
            return "الطريق الصحيح", "{تتبّع/تتبّعي} الطريق بالقلم", ""
        case "dot-to-dot":
            return f"من 1 إلى {params.get('to', 10)}", "{صِل/صِلي} النقاط بالترتيب", ""
        case "shapes":
            return "الدائرة والمربع والمثلث", "{تتبّع/تتبّعي} الأشكال ثم {لوّنها/لوّنيها}", ""
        case "coloring":
            return "ألوّن بعناية", "{لوّن/لوّني} داخل الحدود", ""
        case "connect":
            return "صور متشابهة", "{صِل/صِلي} كل صورة بمثيلتها", ""
        case "classify":
            return "لكل لون سلّة", "{صِل/صِلي} كل شيء بسلّة لونه", ""
        case "odd-one-out":
            return "مَن المختلف؟", "{ضع/ضعي} دائرة حول المختلف", ""
        case "maze":
            return "متاهة", "{ارسم/ارسمي} الطريق من البداية إلى النهاية", ""
        case "spot-difference":
            return "أين الفروق؟", f"{{جِد/جِدي}} {params.get('count', 3)} فروق {{وضع/وضعي}} دائرة حولها", ""
        case "memory":
            return "أنظر وأتذكّر", "{انظر/انظري}، ثم {غطِّ/غطّي} الصور {وتذكّر/وتذكّري}", ""
        case "pattern-complete":
            return "أكمل النمط", "{ارسم/ارسمي} ما يأتي بعد ذلك", ""
        case "cut-and-paste":
            return "أقصّ وألصق", "{قُصّ/قُصّي} القطع {والصقها/والصقيها} في مكانها", ""
        case "blank":
            return "ظهر صفحة القصّ", "هذه الصفحة فارغة", ""
        case "drawing":
            return "أكمل الرسم", "{ارسم/ارسمي} النصف الآخر مثل الأول", ""
        case "unit-review":
            return f"مراجعة: {unit_title}", "هيا نراجع ما {تعلّمتَ/تعلّمتِ}", ""
        case "assessment":
            return unit_title, "{أرِ/أري} الكبار ماذا {تعرف/تعرفين}", ""
    return None


def page_texts(subject: str, kind: str, params: dict[str, Any], unit_title: str) -> Texts:
    """The title and instruction printed on a plan page (English pages add the English instruction)."""
    found: Texts | None = None
    if subject == "english":
        found = english_texts(kind, params)
    elif subject == "arabic":
        found = arabic_texts(kind, params)
    elif subject == "math":
        found = math_texts(kind, params)
    found = found or general_texts(kind, params, unit_title)
    if found is None:
        raise KeyError(f"no child-facing text for {kind!r} ({subject}) yet")
    return found
