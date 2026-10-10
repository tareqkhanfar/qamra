"""Volume 3 of «دوسية التأسيس» on the plan → engine mapping (`foundation.py`): which plan pages go to the
Volume 3 builders (`engine_type_v3`, asked before Volume 2's) and the child-facing texts of its page types
(`texts_v3`).
"""

from __future__ import annotations

from typing import Any

from qamra_workbook.curriculum import Page
from qamra_workbook.render.foundation_text import (
    Texts,
    joined,
    letter_trace_say,
    pick,
    turn,
    vowelled_letter_name,
)


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
# draft: educator review: the titles and instructions below have not been through the educator yet
# as the page explains each mark: we open our mouth, round our lips, see the line under, stop the sound
HARAKA_SAY = {
    "فتحة": "{افْتَحْ فَمَكَ/افْتَحي فَمَكِ}، {وَاقْرَأِ/وَاقْرَئي} الحُروفَ بِالفَتْحَةِ",
    "ضمة": "{ضُمَّ شَفَتَيْكَ/ضُمّي شَفَتَيْكِ}، {وَاقْرَأِ/وَاقْرَئي} الحُروفَ بِالضَّمَّةِ",
    "كسرة": "{انْتَبِهْ/انْتَبِهي} لِلخَطِّ تَحْتَ الحَرْفِ، {وَاقْرَأْ/وَاقْرَئي} بِالكَسْرَةِ",
    "سكون": "عِنْدَ السُّكونِ يَقِفُ الصَّوْتُ: {اقْرَأْ/اقْرَئي} {وَتَوَقَّفْ/وَتَوَقَّفي}",
}
# the English vocabulary units (cards with the English word and the Arabic under it): Arabic, English
VOCAB_SAY = {
    "Numbers": ("{عُدَّ/عُدّي} {وَقُلِ/وَقولي} الأَعْدادَ بِالإِنْجِليزِيَّةِ", "Count and say the numbers."),
    "Colors": (
        "{اقْرَأِ/اقْرَئي} الأَلْوانَ، ثُمَّ {لَوِّنْ/لَوِّني} كُلَّ صورَةٍ بِلَوْنِها",
        "Read the colors, then color the pictures.",
    ),
    "Shapes": ("{أَشِرْ/أَشيري} إلى كُلِّ شَكْلٍ {وَقُلِ/وَقولي} اسْمَهُ", "Point to each shape and say it."),
    "Family": ("{اقْرَأْ/اقْرَئي} أَسْماءَ أَفْرادِ العائِلَةِ بِصَوْتٍ عالٍ", "Read the family words aloud."),
    "Body Parts": (
        "{اقْرَأِ/اقْرَئي} الاسْمَ، {وَأَشِرْ/وَأَشيري} إِلَيْهِ في {جِسْمِكَ/جِسْمِكِ}",
        "Read each word and point to it.",
    ),
    "Animals": ("{رَدِّدِ/رَدِّدي} اسْمَ كُلِّ حَيَوانٍ بِالإِنْجِليزِيَّةِ", "Say each animal's name in English."),
    "Fruits": ("{قُلْ/قولي} أَسْماءَ الفَواكِهِ واحِدًا واحِدًا", "Say the fruit names one by one."),
    "Food": ("{اسْمَعْ/اسْمَعي}، ثُمَّ {رَدِّدْ/رَدِّدي} أَسْماءَ الطَّعامِ", "Listen, then repeat the food words."),
    "Toys": (
        "ما اسْمُ كُلِّ لُعْبَةٍ؟ {اقْرَأْهُ/اقْرَئيهِ} بِالإِنْجِليزِيَّةِ",
        "Read the name of each toy.",
    ),
    "School Objects": ("{سَمِّ/سَمّي} كُلَّ أَداةٍ مَدْرَسِيَّةٍ بِالإِنْجِليزِيَّةِ", "Name each school object in English."),
}
VOCAB_DEFAULT = ("{اقْرَأِ/اقْرَئي} الكَلِماتِ بِالإِنْجِليزِيَّةِ", "Read the words in English.")
CUT = "{قُصَّ/قُصّي} البِطاقاتِ"
PICTURE_ADD = (
    "{اجْمَعِ/اجْمَعي} الصُّوَرَ، ثُمَّ {اكْتُبِ/اكْتُبي} الجَوابَ في المُرَبَّعِ",
    "{عُدَّ/عُدّي} المَجْموعَتَيْنِ مَعًا، {وَاكْتُبْ/وَاكْتُبي} كَمْ صارَ العَدَدُ",
)
PICTURE_SUBTRACT = (  # some pictures are crossed out: what is left?
    "{عُدَّ/عُدّي} الصُّوَرَ الباقِيَةَ، {وَاكْتُبْ/وَاكْتُبي} عَدَدَها",
    "كَمْ بَقِيَ بَعْدَ الشَّطْبِ؟ {اكْتُبْهُ/اكْتُبيهِ} في المُرَبَّعِ",
)
WORD_READ = (
    "{اقْرَأِ/اقْرَئي} الكَلِمَةَ حَرْفًا حَرْفًا، ثُمَّ {حَوِّطْ/حَوِّطي} صورَتَها",
    "{اقْرَأِ/اقْرَئي} الكَلِمَةَ، {وَابْحَثْ/وَابْحَثي} عَنْ صورَتِها {وَحَوِّطْها/وَحَوِّطيها}",
)


def texts_v3(subject: str, kind: str, params: dict[str, Any], unit_title: str) -> Texts | None:
    """Titles and instructions of the Volume 3 pages (draft: educator review); None if earlier ones serve."""
    letters = [str(x) for x in params.get("letters", [])]
    match kind:
        case "harakat":
            h = str(params.get("haraka", "فتحة"))
            return HARAKA_TITLE.get(h, h), HARAKA_SAY.get(h, HARAKA_SAY["فتحة"]), ""
        case "syllables" if params.get("mode") == "build":
            return (
                "أُرَكِّبُ مَقْطَعًا",
                "{اجْمَعِ/اجْمَعي} الحَرْفَ وَالحَرَكَةَ، ثُمَّ {اكْتُبِ/اكْتُبي} المَقْطَعَ {وَاقْرَأْهُ/وَاقْرَئيهِ}",
                "",
            )
        case "syllables" if params.get("mode") == "long":
            return (
                "مَقاطِعُ طَويلَةٌ",
                "{مُدَّ صَوْتَكَ وَأَنْتَ تَقْرَأُ/مُدّي صَوْتَكِ وَأَنْتِ تَقْرَئينَ}: بَا، بُو، بِي",
                "",
            )
        case "syllables":
            return "مَقاطِعُ قَصيرَةٌ", "مِنَ اليَمينِ إلى اليَسارِ: {اقْرَأْ/اقْرَئي} كُلَّ صَفٍّ", ""
        case "word-read" if subject == "english":
            return (
                "I can read",
                "{اقْرَأِ/اقْرَئي} الكَلِمَةَ الإِنْجِليزِيَّةَ، ثُمَّ {حَوِّطْ/حَوِّطي} صورَتَها",
                "Read each word, then circle its picture.",
            )
        case "word-read" if params.get("mode") == "al":
            return (
                "أَقْرَأُ مَعَ «ال»",
                "{اقْرَأِ/اقْرَئي} الكَلِمَةَ مَعَ «ال»، ثُمَّ {حَوِّطْ/حَوِّطي} صورَتَها",
                "",
            )
        case "word-read":
            return "أَقْرَأُ كَلِماتٍ", pick(WORD_READ, turn(params)), ""
        case "word-write" if params.get("mode") == "independent":
            return (
                "أَكْتُبُ وَحْدي",
                "{قُلِ/قولي} اسْمَ الصّورَةِ، ثُمَّ {اكْتُبْهُ/اكْتُبيهِ} عَلى السَّطْرِ",
                "",
            )
        case "word-write":
            return (
                "أَكْتُبُ كَلِماتٍ",
                "{تَتَبَّعِ/تَتَبَّعي} الكَلِمَةَ، ثُمَّ {اكْتُبْها وَحْدَكَ/اكْتُبيها وَحْدَكِ}",
                "",
            )
        case "sentence-read" if subject == "english":
            return (
                "I can read",
                "{اقْرَأْ/اقْرَئي} كُلَّ جُمْلَةٍ، ثُمَّ {صِلْها/صِليها} بِصورَتِها",
                "Read each sentence, then match its picture.",
            )
        case "sentence-read" if params.get("personal"):
            return (
                "أَنا أَقْرَأُ",
                "ماذا {تَفْعَلُ/تَفْعَلينَ}؟ {اقْرَأْ/اقْرَئي}، ثُمَّ {صِلْ/صِلي} {بِصورَتِكَ/بِصورَتِكِ}",
                "",
            )
        case "sentence-read":
            return (
                "أَقْرَأُ جُمَلًا",
                "بَعْدَ أَنْ {تَقْرَأَ/تَقْرَئي}، {صِلْ/صِلي} كُلَّ جُمْلَةٍ بِصورَتِها",
                "",
            )
        case "vocab-unit":
            unit = str(params.get("unit", ""))
            return f"{unit}", *VOCAB_SAY.get(unit, VOCAB_DEFAULT)
        case "picture-add" if params.get("mode") == "story":
            return (
                "مَسْأَلَةُ جَمْعٍ",
                "{اقْرَأِ/اقْرَئي} المَسْأَلَةَ، ثُمَّ {اجْمَعْ/اجْمَعي} {وَاكْتُبِ/وَاكْتُبي} الجَوابَ",
                "",
            )
        case "picture-add" if params.get("mode") == "number-line":
            return (
                "أَجْمَعُ عَلى خَطِّ الأَعْدادِ",
                "{اقْفِزْ/اقْفِزي} عَلى خَطِّ الأَعْدادِ {لِتَصِلَ/لِتَصِلي} إلى الجَوابِ",
                "",
            )
        case "picture-add" if params.get("mode") == "make-ten":
            return "أُكَوِّنُ العَشَرَةَ", "{أَكْمِلْ/أَكْمِلي} كُلَّ جُمْلَةٍ لِيَصيرَ المَجْموعُ عَشَرَةً", ""
        case "picture-add" if params.get("mode") == "choose-operation":
            return (
                "أَجْمَعُ أَمْ أَطْرَحُ؟",
                "جَمْعٌ أَمْ طَرْحٌ؟ {حَوِّطِ/حَوِّطي} الإِشارَةَ، ثُمَّ {احْسُبْ/احْسُبي}",
                "",
            )
        case "picture-add":
            return "أَجْمَعُ بِالصُّوَرِ", pick(PICTURE_ADD, turn(params)), ""
        case "picture-subtract" if params.get("mode") == "story":
            return (
                "مَسْأَلَةُ طَرْحٍ",
                "{اقْرَأِ/اقْرَئي} المَسْأَلَةَ، ثُمَّ {اطْرَحْ/اطْرَحي} {وَاكْتُبْ/وَاكْتُبي} كَمْ بَقِيَ",
                "",
            )
        case "picture-subtract":
            return "أَطْرَحُ بِالصُّوَرِ", pick(PICTURE_SUBTRACT, turn(params)), ""
        case "number-quantity-match" if max(_numbers(params), default=0) > 10:
            return (
                "عَشَرَةٌ وَآحادٌ",
                "{اقْرَأِ/اقْرَئي} العَدَدَ، ثُمَّ {صِلْهُ/صِليهِ} بِعَشَرَتِهِ وَآحادِهِ",
                "",
            )
        case "number-trace" if max(_numbers(params), default=0) > 10:
            return (
                "أَتَتَبَّعُ الأَعْدادَ",
                "{مَرِّرِ/مَرِّري} القَلَمَ عَلى كُلِّ عَدَدٍ، ثُمَّ {اكْتُبْهُ/اكْتُبيهِ}",
                "",
            )
        case "count-and-circle" if max(_numbers(params), default=0) > 10:
            return (
                "أَعُدُّ حَتّى عِشْرينَ",
                "{عُدَّ/عُدّي} العَشَرَةَ ثُمَّ الآحادَ، {وَحَوِّطِ/وَحَوِّطي} العَدَدَ",
                "",
            )
        case "compare" if params.get("concept") == "bigger-smaller":
            return "الأَكْبَرُ", "{اقْرَأِ/اقْرَئي} العَدَدَيْنِ، ثُمَّ {حَوِّطِ/حَوِّطي} الأَكْبَرَ", ""
        case "pattern-complete" if params.get("kind") == "number-line":
            top = params.get("range", 20)
            return (
                "خَطُّ الأَعْدادِ",
                f"{{عُدَّ/عُدّي}} حَتّى {top}، {{وَاكْتُبِ/وَاكْتُبي}} الأَعْدادَ النّاقِصَةَ",
                "",
            )
        case "pattern-complete" if params.get("kind") == "picture-grid":
            return "جَدْوَلُ الصُّوَرِ", "{ارْسُمْ/ارْسُمي} في كُلِّ مُرَبَّعٍ فارِغٍ الصّورَةَ النّاقِصَةَ", ""
        case "pattern-complete" if params.get("pattern") == "growing":
            return (
                "النَّمَطُ المُتَزايِدُ",
                "كُلُّ خُطْوَةٍ تَزيدُ واحِدًا: {ارْسُمِ/ارْسُمي} الخُطْوَتَيْنِ التّالِيَتَيْنِ",
                "",
            )
        case "pen-lines" if params.get("line") == "joins":
            return "خُطوطُ الوَصْلِ", "{تَتَبَّعْ/تَتَبَّعي} خُطوطَ الوَصْلِ بَيْنَ الحُروفِ", ""
        case "trace-path" if params.get("path") == "complex":
            return "الطَّريقُ الطَّويلُ", "{اتْبَعِ/اتْبَعي} الطَّريقَ الطَّويلَ حَتّى آخِرِهِ", ""
        case "letter-trace" if letters:
            names = joined([vowelled_letter_name(x, "a") for x in letters])
            return f"أَتَتَبَّعُ {names}", letter_trace_say(params, len(letters)), ""
        case "classify" if isinstance(params.get("by"), list):
            return "أُصَنِّفُ بِصِفَتَيْنِ", "{ارْسُمْ/ارْسُمي} كُلَّ شَكْلٍ في خانَةِ شَكْلِهِ وَلَوْنِهِ", ""
        case "memory" if params.get("mode") == "order":
            return (
                "أَتَذَكَّرُ التَّرْتيبَ",
                "{احْفَظِ/احْفَظي} التَّرْتيبَ، ثُمَّ {غَطِّ/غَطّي} الصُّوَرَ {وَرَقِّمْها/وَرَقِّميها}",
                "",
            )
        case "connect" if params.get("mode") == "cause-effect":
            return "السَّبَبُ وَالنَّتيجَةُ", "{صِلْ/صِلي} كُلَّ سَبَبٍ بِما يَحْدُثُ بَعْدَهُ", ""
        case "connect" if subject == "mixed":
            return "أَصِلُ ما تَعَلَّمْتُ", "{صِلِ/صِلي} الحَرْفَ وَالعَدَدَ وَالكَلِمَةَ بِما يُناسِبُها", ""
        case "drawing" if params.get("mode") == "problem-solving":
            return "أُفَكِّرُ وَأَرْسُمُ حَلًّا", "كَيْفَ تَعْبُرُ البَطَّةُ النَّهْرَ؟ {فَكِّرْ/فَكِّري}، ثُمَّ {ارْسُمْ/ارْسُمي}", ""
        case "cut-and-paste" if params.get("mode") == "build-words":
            return "أَبْني الكَلِمَةَ", f"{CUT}، {{وَأَلْصِقْها/وَأَلْصِقيها}} {{لِتَبْنِيَ/لِتَبْني}} اسْمَ كُلِّ صورَةٍ", ""
        case "certificate":
            return (
                "{أَحْسَنْتَ يا بَطَلُ/أَحْسَنْتِ يا بَطَلَةُ}!",
                "{لَوِّنِ/لَوِّني} النُّجومَ، ثُمَّ {احْتَفِلْ/احْتَفِلي} مَعَ {أَهْلِكَ/أَهْلِكِ}",
                "",
            )
    return None
