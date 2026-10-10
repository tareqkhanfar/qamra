"""What «دوسية التأسيس» prints for the child on each page: a short title and a one-line instruction (≤ 7
words once personalized, in the guide's bubble), with `{masc/fem}` variants and `{child}`. The plan carries
only the educator's skill line (printed in the footer for grown-ups); these texts come from the page type and
its params.

How an instruction reads (the product owner's brief of 6 October 2026): one clear step, or two short steps
in order («…، ثُمَّ …»), with the exercise's own action verbs, in easy fully vowelized Arabic for a child of
4–6 who is read to; the exercise's idea and goal stay exactly as the page asks. A recurring exercise has a
few wordings and turns through them page by page (`pick` with the page's `turn`, the number of pages of its
kind before it in the volume), so the same exercise does not read the same way twice in a row; a test keeps
any two neighbouring pages from opening with the same word (docs/review/foundation-instructions.md).

English pages carry the instruction in English with the Arabic under it (Addendum 5 §4).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from qamra_workbook.letters import NAMES

# draft: educator review: the titles and instructions below have not been through the educator yet
Texts = tuple[str, str, str]  # title, Arabic instruction, English instruction ("" on Arabic pages)

# the number words as the child reads them under a numeral (and in «العَدَدُ خَمْسَةٌ ٥»)
NUMBER_NAMES = {0: "صِفْرٌ", 1: "واحِدٌ", 2: "اثْنانِ", 3: "ثَلاثَةٌ", 4: "أَرْبَعَةٌ", 5: "خَمْسَةٌ", 6: "سِتَّةٌ"}
NUMBER_NAMES |= {7: "سَبْعَةٌ", 8: "ثَمانِيَةٌ", 9: "تِسْعَةٌ", 10: "عَشَرَةٌ"}
COLOR_AR = {"أحمر": "red", "أزرق": "blue", "أصفر": "yellow", "أخضر": "green"}


def pick[T](options: Sequence[T], key: Any = 0) -> T:
    """The wording for this page out of a recurring exercise's wordings: `key` is the page's `turn` (or the
    volume, for a page that comes once a volume), so neighbours of one kind never read alike."""
    return options[int(key or 0) % len(options)]


def turn(params: Mapping[str, Any]) -> int:
    """How many pages of this kind came before this one in its volume (`foundation.from_curriculum`), moved on
    by the volume, so a page that comes once a volume also reads differently in each volume."""
    return int(params.get("turn", 0)) + volume_key(params)


def volume_key(params: Mapping[str, Any]) -> int:
    """0, 1 or 2 for the volume: the key of the pages that come once a volume (openers, name pages, tests)."""
    return int(params.get("volume", 1)) - 1


PEN_TITLES = {
    "horizontal": "خُطوطٌ أُفُقِيَّةٌ",
    "vertical": "خُطوطٌ عَمودِيَّةٌ",
    "diagonal": "خُطوطٌ مائِلَةٌ",
    "zigzag": "أَسْنانُ المِنْشارِ",
    "curve": "أَمْواجُ البَحْرِ",
    "loops": "دَوائِرُ وَحَلَقاتٌ",
    "letter-strokes": "ضَرَباتُ الحُروفِ",
    "spiral": "حَلَزوناتٌ",
}
PEN_SAY = {  # what the pen draws on each line page (the KG1 lines have their own, `foundation_kg1`)
    "horizontal": "{ارْسُمْ/ارْسُمي} عَلى النِّقاطِ مِنَ اليَمينِ إلى اليَسارِ",
    "vertical": "{انْزِلْ/انْزِلي} بِالقَلَمِ مِنْ فَوْقُ إلى تَحْتُ",
    "diagonal": "{اتْبَعِ/اتْبَعي} النِّقاطَ المائِلَةَ مِنَ النُّقْطَةِ الخَضْراءِ",
    "zigzag": "مِنَ النُّقْطَةِ الخَضْراءِ: {اصْعَدْ/اصْعَدي} {وَانْزِلْ/وَانْزِلي} عَلى النِّقاطِ",
    "curve": "{ارْسُمِ/ارْسُمي} المَوْجَ عَلى النِّقاطِ، وَلا {تَرْفَعِ/تَرْفَعي} القَلَمَ",
    "loops": "{لُفَّ/لُفّي} بِالقَلَمِ حَلْقَةً بَعْدَ حَلْقَةٍ",
    "letter-strokes": "مِنَ النُّقْطَةِ الخَضْراءِ: {ارْسُمْ/ارْسُمي} أَجْزاءَ الحُروفِ",
    "spiral": "مِنَ الخارِجِ إلى الوَسَطِ: {لُفَّ/لُفّي} بِالقَلَمِ",
}
COMPARE = {
    "big-small": ("كَبيرٌ وَصَغيرٌ", "في كُلِّ صَفٍّ {حَوِّطِ/حَوِّطي} الصّورَةَ الكَبيرَةَ"),
    "long-short": ("طَويلٌ وَقَصيرٌ", "أَيُّهُما أَطْوَلُ؟ {ضَعْ/ضَعي} حَوْلَهُ دائِرَةً"),
    "many-few": ("كَثيرٌ وَقَليلٌ", "{انْظُرْ/انْظُري} إلى المَجْموعَتَيْنِ، {وَحَوِّطِ/وَحَوِّطي} الكَثيرَةَ"),
    "more-less": ("أَكْثَرُ وَأَقَلُّ", "{عُدَّ/عُدّي}، ثُمَّ {حَوِّطِ/حَوِّطي} الأَكْثَرَ {وَاشْطُبِ/وَاشْطُبي} الأَقَلَّ"),
    "tall-short": ("طَويلٌ وَقَصيرٌ", "مَنِ الأَطْوَلُ؟ {حَوِّطْهُ/حَوِّطيهِ} في كُلِّ صَفٍّ"),
    "heavy-light": ("ثَقيلٌ وَخَفيفٌ", "أَيُّهُما أَثْقَلُ؟ {حَوِّطْهُ/حَوِّطيهِ} في كُلِّ صَفٍّ"),
}

# the letters' names vowelised for the child's pages (`NAMES` stays plain for the educator's sheets); each
# word takes the case ending `vowelled_letter_name` adds
_VOWELLED_NAMES = {
    "ا": "الأَلِف",
    "ب": "الباء",
    "ت": "التّاء",
    "ث": "الثّاء",
    "ج": "الجيم",
    "ح": "الحاء",
    "خ": "الخاء",
    "د": "الدّال",
    "ذ": "الذّال",
    "ر": "الرّاء",
    "ز": "الزّاي",
    "س": "السّين",
    "ش": "الشّين",
    "ص": "الصّاد",
    "ض": "الضّاد",
    "ط": "الطّاء",
    "ظ": "الظّاء",
    "ع": "العَيْن",
    "غ": "الغَيْن",
    "ف": "الفاء",
    "ق": "القاف",
    "ك": "الكاف",
    "ل": "اللّام",
    "م": "الميم",
    "ن": "النّون",
    "ه": "الهاء",
    "و": "الواو",
    "ي": "الياء",
    "ة": "التّاء المَرْبوطَة",
    "ى": "الأَلِف المَقْصورَة",
    "ء": "الهَمْزَة",
}
_CASE = {"u": "ُ", "a": "َ", "i": "ِ"}  # damma, fatha, kasra


def letter_name(char: str) -> str:
    """«الألف» for أ and ا: the letter's Arabic name."""
    return str(NAMES.get("ا" if char in "أإآ" else char, char))


def vowelled_letter_name(char: str, case: str = "i") -> str:
    """«الباءِ» (case "i", after حَرْفُ or a preposition), «الباءَ» ("a"), «الباءُ» ("u"): the name as the
    child's page prints it, fully vowelised."""
    key = "ا" if char in "أإآ" else char
    if key == "لا":
        return "لامْ أَلِفْ"
    plain = _VOWELLED_NAMES.get(key)
    if plain is None:
        return letter_name(char)
    return " ".join(w + _CASE[case] for w in plain.split())


def joined(names: list[str]) -> str:
    """«الباءِ وَالتّاءِ», «الباءِ وَالتّاءِ وَالثّاءِ»: Arabic joins every name with «وَ» (never «الباءِ، التّاءِ…»)."""
    return " وَ".join(names)


SHAPE_NAMES = {"circle": "الدّائِرَةُ", "square": "المُرَبَّعُ", "triangle": "المُثَلَّثُ", "rectangle": "المُسْتَطيلُ"}


def shapes_title(shapes: Any = None) -> str:
    """«الدّائِرَةُ وَالمُرَبَّعُ وَالمُثَلَّثُ»: the shapes a page teaches (the first three by default)."""
    names = [str(x) for x in shapes] if shapes else ["circle", "square", "triangle"]
    return " وَ".join(SHAPE_NAMES.get(x, x) for x in names)


def letters_head(letters: list[str]) -> str:
    """«حَرْفُ الباءِ», «حَرْفا الباءِ وَالتّاءِ», «حُروفُ …»: the letters a title asks about."""
    names = joined([vowelled_letter_name(x) for x in letters])
    return f"{'حَرْفُ' if len(letters) == 1 else 'حَرْفا' if len(letters) == 2 else 'حُروفُ'} {names}"


def counted(n: Any, plural: str, singular: str) -> str:
    """«٥ نُجومٍ», «١٢ نَجْمَةً»: a counted noun after a numeral (3–10: a plural in the genitive; 11 and up: a
    singular in the accusative)."""
    return f"{n} {plural if 3 <= int(n) <= 10 else singular}"


def stars(n: int) -> str:
    """«نَجْمَةً واحِدَةً», «نَجْمَتَيْنِ», «٥ نُجومٍ»: the stars a number page colors (the object of «لَوِّنْ»)."""
    return {1: "نَجْمَةً واحِدَةً", 2: "نَجْمَتَيْنِ"}.get(n) or counted(n, "نُجومٍ", "نَجْمَةً")


# ---- the instructions of the recurring exercises, shared by both levels and all volumes ----


def letter_intro_say(params: Mapping[str, Any]) -> str:
    """Meet the letter: color it and its picture(s) (one picture for ذ ض ظ ل in KG1)."""
    two = len(params.get("words", [])) != 1
    pics = "الصّورَتَيْنِ" if two else "الصّورَةَ"
    each = "كُلِّ صورَةٍ" if two else "الصّورَةِ"
    return pick(
        (
            "{لَوِّنِ/لَوِّني} الحَرْفَ الكَبيرَ، ثُمَّ " + pics,
            "{قُلِ/قولي} اسْمَ " + each + "، {وَلَوِّنْها/وَلَوِّنيها} مَعَ الحَرْفِ",
            "{أَشِرْ/أَشيري} إلى الحَرْفِ، ثُمَّ {لَوِّنْهُ/لَوِّنيهِ} مَعَ " + pics[:-1] + "ِ",
            "{بِأَلْوانِكَ الزّاهِيَةِ لَوِّنِ/بِأَلْوانِكِ الزّاهِيَةِ لَوِّني} الحَرْفَ وَ" + pics,
        ),
        turn(params),
    )


def letter_trace_say(params: Mapping[str, Any], count: int = 1) -> str:
    """Trace the dotted letter(s) from the green dot along the arrows, big first and then smaller."""
    sizes = (
        "أَوَّلًا {تَتَبَّعِ/تَتَبَّعي} الحَرْفَ الكَبيرَ، ثُمَّ الأَصْغَرَ"
        if count == 1
        else "أَوَّلًا {تَتَبَّعِ/تَتَبَّعي} الحَرْفَيْنِ الكَبيرَيْنِ، ثُمَّ الحُروفَ الصَّغيرَةَ"
    )
    return pick(
        (
            "{ابْدَأْ/ابْدَئي} مِنَ النُّقْطَةِ الخَضْراءِ، ثُمَّ {اتْبَعِ/اتْبَعي} الأَسْهُمَ",
            "{مَرِّرِ/مَرِّري} القَلَمَ عَلى النِّقاطِ مَعَ الأَسْهُمِ",
            sizes,
            "{سِرْ/سيري} بِالقَلَمِ مَعَ السَّهْمِ مِنَ النُّقْطَةِ الخَضْراءِ",
        ),
        turn(params),
    )


def letter_write_say(params: Mapping[str, Any], count: int = 1) -> str:
    """Write the letter(s) on the dots first (guided rows), then alone (the independent row)."""
    if count == 1:
        options = (
            "{اكْتُبْ/اكْتُبي} عَلى النِّقاطِ، ثُمَّ {جَرِّبْ وَحْدَكَ/جَرِّبي وَحْدَكِ}",
            "{تَتَبَّعِ/تَتَبَّعي} الحَرْفَ أَوَّلًا، ثُمَّ {اكْتُبْهُ وَحْدَكَ/اكْتُبيهِ وَحْدَكِ}",
            "عَلى السَّطْرِ: {تَتَبَّعِ/تَتَبَّعي} النِّقاطَ، ثُمَّ {اكْتُبْ وَحْدَكَ/اكْتُبي وَحْدَكِ}",
        )
    else:
        options = (  # a row of dots, then an empty row, for each letter
            "{اكْتُبْ/اكْتُبي} عَلى النِّقاطِ، ثُمَّ {جَرِّبْ وَحْدَكَ/جَرِّبي وَحْدَكِ}",
            "لِكُلِّ حَرْفٍ سَطْرٌ: {تَتَبَّعْهُ/تَتَبَّعيهِ}، ثُمَّ {اكْتُبْهُ وَحْدَكَ/اكْتُبيهِ وَحْدَكِ}",
            "{اكْتُبْ/اكْتُبي} كُلَّ حَرْفٍ عَلى النِّقاطِ، ثُمَّ {وَحْدَكَ/وَحْدَكِ}",
        )
    return pick(options, turn(params))


# color each target letter in the grid with its color, then circle the letter a picture starts with
FIND_LETTER = (
    "{لَوِّنِ/لَوِّني} الحُروفَ. بِأَيِّ حَرْفٍ تَبْدَأُ الصّورَةُ؟ {حَوِّطْهُ/حَوِّطيهِ}",
    "{انْظُرْ/انْظُري} جَيِّدًا: {لَوِّنِ/لَوِّني} الحُروفَ، ثُمَّ {حَوِّطِ/حَوِّطي} الصَّحيحَ",
    "{جِدِ/جِدي} الحُروفَ {وَلَوِّنْها/وَلَوِّنيها}، ثُمَّ {حَوِّطْ/حَوِّطي} حَرْفَ الصّورَةِ",
)
MATCH_LETTER = (  # three columns: the letter, its picture, the picture's word
    "{صِلِ/صِلي} الحَرْفَ بِالصّورَةِ، ثُمَّ الصّورَةَ بِالكَلِمَةِ",
    "{قُلِ/قولي} اسْمَ الصّورَةِ، ثُمَّ {صِلْها/صِليها} بِحَرْفِها وَكَلِمَتِها",
    "{صِلْ/صِلي} كُلَّ حَرْفٍ بِصورَتِهِ، وَكُلَّ صورَةٍ بِكَلِمَتِها",
)


def arabic_texts(kind: str, params: dict[str, Any]) -> Texts | None:
    letter = str(params.get("letter", ""))
    letters = [str(x) for x in params.get("letters", [letter] if letter else [])]
    name = vowelled_letter_name(letter) if letter else ""
    match kind:
        case "letter-intro":
            return f"حَرْفُ {name}", letter_intro_say(params), ""
        case "letter-trace":
            return f"أَتَتَبَّعُ حَرْفَ {name}", letter_trace_say(params), ""
        case "letter-write":
            return f"أَكْتُبُ حَرْفَ {name}", letter_write_say(params), ""
        case "find-letter":
            return f"أَيْنَ {letters_head(letters)}؟", pick(FIND_LETTER, turn(params)), ""
        case "match-letter-picture":
            return "الحَرْفُ وَالصّورَةُ وَالكَلِمَةُ", pick(MATCH_LETTER, turn(params)), ""
        case "classify":
            return "أَيْنَ أَضَعُها؟", "{قُلِ/قولي} اسْمَ الصّورَةِ، {وَصِلْها/وَصِليها} بِحَرْفِها الأَوَّلِ", ""
        case "connect":
            return "الصَّوْتُ الأَوَّلُ", "{صِلْ/صِلي} كُلَّ صورَتَيْنِ تَبْدَآنِ بِالصَّوْتِ نَفْسِهِ", ""
    return None


# (Arabic, English) pairs: on an English page the English line leads and the Arabic sits under it
EN_TRACE = (  # KG1 Volume 1: the letter is traced only, and its picture colored
    ("الحَرْفُ الكَبيرُ وَالصَّغيرُ: {تَتَبَّعْهُما/تَتَبَّعيهِما} بِالقَلَمِ", "Trace the big and small letters."),
    ("{تَتَبَّعِ/تَتَبَّعي} الحَرْفَ، ثُمَّ {لَوِّنِ/لَوِّني} الصّورَةَ", "Trace the letter, then color the picture."),
    ("صَوْتُ الحَرْفِ أَوَّلًا: {قُلْهُ/قوليهِ}، ثُمَّ {تَتَبَّعْهُ/تَتَبَّعيهِ}", "Say the sound, then trace the letter."),
)
EN_WRITE = (  # traced, written on a row, and the picture colored
    ("{تَتَبَّعِ/تَتَبَّعي} الحَرْفَ، ثُمَّ {اكْتُبْهُ/اكْتُبيهِ} عَلى السَّطْرِ", "Trace the letter, then write it."),
    ("{تَتَبَّعْ/تَتَبَّعي} {وَاكْتُبْ/وَاكْتُبي}، ثُمَّ {لَوِّنِ/لَوِّني} الصّورَةَ", "Trace, write, then color the picture."),
    (
        "{رَدِّدْ/رَدِّدي} صَوْتَ الحَرْفِ، ثُمَّ {تَتَبَّعْهُ وَاكْتُبْهُ/تَتَبَّعيهِ وَاكْتُبيهِ}",
        "Say the sound, then trace and write.",
    ),
    ("بَعْدَ التَّتَبُّعِ: {اكْتُبِ/اكْتُبي} الحَرْفَ كَبيرًا وَصَغيرًا", "Trace, then write it big and small."),
)
EN_FIND = (
    ("في كُلِّ صَفٍّ {حَوِّطِ/حَوِّطي} الحَرْفَ المَطْلوبَ", "Circle the letter in each row."),
    ("{ابْحَثْ/ابْحَثي} عَنِ الحَرْفِ، ثُمَّ {حَوِّطْهُ/حَوِّطيهِ}", "Find the letter, then circle it."),
    ("صَفًّا صَفًّا: {حَوِّطِ/حَوِّطي} الحَرْفَ كُلَّما {رَأَيْتَهُ/رَأَيْتِهِ}", "Circle the letter wherever you see it."),
)
EN_MATCH = (
    ("أَيُّ صورَةٍ تَبْدَأُ بِهذا الحَرْفِ؟ {صِلْهُما/صِليهِما}", "Match each letter to its picture."),
    ("{قُلِ/قولي} اسْمَ الصّورَةِ، ثُمَّ {صِلْها/صِليها} بِحَرْفِها", "Name the picture, then match it."),
)
EN_REVIEW = (
    ("هَلْ {تَذْكُرُ/تَذْكُرينَ} هذِهِ الحُروفَ؟ هَيّا نَبْدَأْ!", "Do you remember these letters? Let's begin!"),
    ("{أَكْمِلِ/أَكْمِلي} التَّمارينَ واحِدًا بَعْدَ واحِدٍ", "Do the exercises one by one."),
    ("هَيّا نُراجِعِ الحُروفَ مَعًا!", "Let's review the letters together!"),
)
EN_REVIEW_WORDS = (
    ("{اقْرَأِ/اقْرَئي} الكَلِماتِ، ثُمَّ {صِلْها/صِليها} بِصُوَرِها", "Read the words, then match them."),
    ("{تَذَكَّرِ/تَذَكَّري} الكَلِماتِ، {وَصِلْ/وَصِلي} كُلًّا بِصورَتِها", "Match each word to its picture."),
)
EN_ASSESSMENT = (  # one a volume
    ("{أَرِ/أَري} الكِبارَ ما {تَعْرِفُهُ/تَعْرِفينَهُ} بِالإِنْجِليزِيَّةِ", "Show the grown-ups what you know."),
    ("{اقْرَأْ/اقْرَئي}، {وَصِلْ/وَصِلي}، {وَحَوِّطْ/وَحَوِّطي} {وَحْدَكَ/وَحْدَكِ}", "Read, match and circle on your own."),
    ("{جَرِّبْ/جَرِّبي} كُلَّ تَمْرينٍ {وَحْدَكَ/وَحْدَكِ}", "Try every exercise on your own."),
)


def english_texts(kind: str, params: dict[str, Any]) -> Texts | None:
    letter = str(params.get("letter", "A")).upper()
    say: tuple[str, str]
    match kind:
        case "en-letter":
            traced_only = params.get("level") == "kg1" and int(params.get("volume", 1)) == 1
            say = pick(EN_TRACE if traced_only else EN_WRITE, turn(params))
            return f"{letter} {letter.lower()}", *say
        case "find-letter":
            return "Find the letter", *pick(EN_FIND, turn(params))
        case "match-letter-picture" if params.get("mode") == "capital-small":
            return (
                "Big and small",
                "{صِلْ/صِلي} كُلَّ حَرْفٍ كَبيرٍ بِحَرْفِهِ الصَّغيرِ",
                "Match big letters to small letters.",
            )
        case "match-letter-picture":
            return "Letters and pictures", *pick(EN_MATCH, turn(params))
        case "unit-review":
            return "Review", *pick(EN_REVIEW_WORDS if "units" in params else EN_REVIEW, turn(params))
        case "assessment":
            return "What I know", *pick(EN_ASSESSMENT, volume_key(params))
    return None


NUMBER_INTRO_ZERO = "الصَّحْنُ فارِغٌ: لا شَيْءَ! {حَوِّطِ/حَوِّطي} الصِّفْرَ"


def number_intro_say(params: Mapping[str, Any]) -> str:
    """Meet a number: count the pictures, color as many stars, circle the numeral."""
    n = int(params.get("number", 1))
    options = [
        "{عُدَّ/عُدّي} الصُّوَرَ، ثُمَّ {لَوِّنْ/لَوِّني} " + stars(n),
        "كَمْ صورَةً؟ {عُدَّ/عُدّي}، ثُمَّ {لَوِّنْ/لَوِّني} " + stars(n),
        "{عُدَّ بِإِصْبَعِكَ/عُدّي بِإِصْبَعِكِ}، ثُمَّ {لَوِّنْ/لَوِّني} " + stars(n),
    ]
    return pick(options, turn(params))


def number_trace_say(params: Mapping[str, Any]) -> str:
    n = params.get("number", 1)
    return pick(
        (
            f"مِنَ النُّقْطَةِ الخَضْراءِ: {{تَتَبَّعِ/تَتَبَّعي}} العَدَدَ {n}",
            f"{{اتْبَعِ/اتْبَعي}} السَّهْمَ {{لِتَرْسُمَ/لِتَرْسُمي}} العَدَدَ {n}",
            f"{{مَرِّرِ/مَرِّري}} القَلَمَ عَلى نِقاطِ العَدَدِ {n}",
        ),
        turn(params),
    )


def number_write_say(params: Mapping[str, Any]) -> str:
    n = params.get("number", 1)
    return pick(
        (
            f"{{اكْتُبِ/اكْتُبي}} العَدَدَ {n} عَلى النِّقاطِ، ثُمَّ بِدونِها",
            f"{{جَرِّبْ/جَرِّبي}} كِتابَةَ {n}: عَلى النِّقاطِ، ثُمَّ {{وَحْدَكَ/وَحْدَكِ}}",
            f"العَدَدُ {n}: {{تَتَبَّعْهُ/تَتَبَّعيهِ}}، ثُمَّ {{اكْتُبْهُ وَحْدَكَ/اكْتُبيهِ وَحْدَكِ}}",
        ),
        turn(params),
    )


COUNT_AND_CIRCLE = (
    "{عُدَّ/عُدّي} الأَشْياءَ، ثُمَّ {حَوِّطِ/حَوِّطي} العَدَدَ الصَّحيحَ",
    "كَمْ صورَةً {تَرى/تَرَيْنَ}؟ {حَوِّطْ/حَوِّطي} عَدَدَها",
    "{عُدَّ بِإِصْبَعِكَ/عُدّي بِإِصْبَعِكِ}، ثُمَّ {حَوِّطِ/حَوِّطي} العَدَدَ",
)
QUANTITY_MATCH = (
    "{عُدَّ/عُدّي} كُلَّ مَجْموعَةٍ، ثُمَّ {صِلْها/صِليها} بِعَدَدِها",
    "{اقْرَأِ/اقْرَئي} العَدَدَ، ثُمَّ {صِلْهُ/صِليهِ} بِمَجْموعَتِهِ",
)
COLORS_SAY = (  # a row of pictures beside each crayon
    "{لَوِّنْ/لَوِّني} صُوَرَ كُلِّ صَفٍّ بِلَوْنِ قَلَمِهِ",
    "{قُلِ/قولي} اسْمَ اللَّوْنِ، ثُمَّ {لَوِّنْ/لَوِّني} صُوَرَ صَفِّهِ",
)


def math_texts(kind: str, params: dict[str, Any]) -> Texts | None:
    number = params.get("number")
    match kind:
        case "number-intro" if number == 0:
            return "الصِّفْرُ: لا شَيْءَ", NUMBER_INTRO_ZERO, ""
        case "number-intro":
            return f"العَدَدُ {NUMBER_NAMES.get(int(number or 1), '')} {number}", number_intro_say(params), ""
        case "number-trace":
            return f"أَتَتَبَّعُ العَدَدَ {number}", number_trace_say(params), ""
        case "number-write":
            return f"أَكْتُبُ العَدَدَ {number}", number_write_say(params), ""
        case "count-and-circle":
            return "أَعُدُّ وَأُحَوِّطُ", pick(COUNT_AND_CIRCLE, turn(params)), ""
        case "number-quantity-match":
            return "العَدَدُ وَالكَمِّيَّةُ", pick(QUANTITY_MATCH, turn(params)), ""
        case "compare":
            title, say = COMPARE.get(str(params.get("concept", "big-small")), COMPARE["big-small"])
            return title, say, ""
        case "coloring":
            return "أَلْوانٌ جَميلَةٌ", pick(COLORS_SAY, turn(params)), ""
    return None


TOC_SAY = (  # one a volume
    "{تَعَرَّفْ مَعَ الكِبارِ عَلى أَقْسامِ كِتابِكَ/تَعَرَّفي مَعَ الكِبارِ عَلى أَقْسامِ كِتابِكِ}",
    "{اكْتَشِفْ مَعَ الكِبارِ ماذا سَتَتَعَلَّمُ/اكْتَشِفي مَعَ الكِبارِ ماذا سَتَتَعَلَّمينَ}",
    "هَيّا نَتَعَرَّفْ مَعًا عَلى أَقْسامِ الكِتابِ",
)
NAME_AR = (  # one a volume: the dotted rows, then the empty row the child writes alone
    "{تَتَبَّعِ اسْمَكَ، ثُمَّ اكْتُبْهُ وَحْدَكَ/تَتَبَّعي اسْمَكِ، ثُمَّ اكْتُبيهِ وَحْدَكِ}",
    "{مَرِّرْ قَلَمَكَ عَلى اسْمِكَ، ثُمَّ اكْتُبْهُ وَحْدَكَ/مَرِّري قَلَمَكِ عَلى اسْمِكِ، ثُمَّ اكْتُبيهِ وَحْدَكِ}",
    "{اسْمُكَ جَميلٌ! تَتَبَّعْهُ، ثُمَّ اكْتُبْهُ وَحْدَكَ/اسْمُكِ جَميلٌ! تَتَبَّعيهِ، ثُمَّ اكْتُبيهِ وَحْدَكِ}",
)
NAME_EN = (  # opens unlike the Arabic name page before it
    (
        "{اكْتُبِ اسْمَكَ بِالإِنْجِليزِيَّةِ: عَلى النِّقاطِ، ثُمَّ وَحْدَكَ/اكْتُبي اسْمَكِ بِالإِنْجِليزِيَّةِ: عَلى النِّقاطِ، ثُمَّ وَحْدَكِ}",
        "Trace your name, then write it alone.",
    ),
    (
        "{تَتَبَّعِ اسْمَكَ بِالإِنْجِليزِيَّةِ، ثُمَّ اكْتُبْهُ وَحْدَكَ/تَتَبَّعي اسْمَكِ بِالإِنْجِليزِيَّةِ، ثُمَّ اكْتُبيهِ وَحْدَكِ}",
        "Trace your name, then write it.",
    ),
    (
        "{حُروفُ اسْمِكَ بِالإِنْجِليزِيَّةِ: تَتَبَّعْها، ثُمَّ اكْتُبْها/حُروفُ اسْمِكِ بِالإِنْجِليزِيَّةِ: تَتَبَّعيها، ثُمَّ اكْتُبيها}",
        "Trace your name's letters, then write them.",
    ),
)
OPENER_SAY = {  # one a volume: the unit openers greet the subject
    "arabic": ("هَيّا نَبْدَأْ رِحْلَةَ الحُروفِ!", "هَيّا نَلْتَقِ بِحُروفٍ جَديدَةٍ!", "هَيّا نُكْمِلْ رِحْلَةَ الحُروفِ!"),
    "math": ("هَيّا نَدْخُلْ عالَمَ الأَعْدادِ!", "هَيّا نَعُدَّ وَنَلْعَبْ بِالأَعْدادِ!", "هَيّا نَجْمَعْ وَنَطْرَحْ مَعًا!"),
    "english": (
        "هَيّا نَتَعَلَّمِ الإِنْجِليزِيَّةَ مَعًا!",
        "هَيّا نَتَعَرَّفْ عَلى حُروفٍ جَديدَةٍ!",
        "هَيّا نَقْرَأْ أَوَّلَ كَلِماتِنا!",
    ),
}
OPENER_DEFAULT = "هَيّا نَبْدَأْ رِحْلَةً جَديدَةً!"

# The plan's objectives are written for the educator about «the child», in the masculine («يتعرّف على تسعة
# حروف…», «يكتب وحده…»). Under the opener's «في هذا الجزء سأتعلّم» the child says them, so they print in
# the first person, which reads the same for a boy and a girl (`objective_as_child`). A verb about the child
# is one of `_CHILD_VERBS` (maybe with «و»/«ف» before it and an object pronoun after it); every other word
# that starts like a third-person verb is one of `_NOT_THE_CHILD` (a test keeps the plan inside both lists).
_CHILD_VERBS = frozenset(
    {
        "يمسك",
        "يرسم",
        "يتتبّع",
        "يحلّ",
        "يخرج",
        "يلوّن",
        "يصل",
        "يتعرّف",
        "يربط",
        "يكتب",
        "يميّز",
        "يسمّي",
        "يقارن",
        "يعدّ",
        "يجد",
        "يطابق",
        "يصنّف",
        "يكمل",
        "يتذكّر",
        "يقصّ",
        "يلصق",
        "ينقل",
        "يحدّد",
        "يرتّب",
        "يستعمل",
        "يستخدم",
        "يختار",
        "يسمع",
        "يعرف",
        "يجمع",
        "يطرح",
        "يشير",
        "يشرح",
        "يركّب",
        "يلاحظ",
        "يلمس",
        "يقرأ",
        "يقرؤ",
        "يرى",
    }
)
_OBJECT_PRONOUNS = ("هما", "ها", "ه")
# places («يمين ويسار»), what each situation needs («ما يحتاجه كل موقف»), the odd thing («لا ينتمي»)
_NOT_THE_CHILD = frozenset({"يمين", "يسار", "ويسار", "يحتاجه", "ينتمي", "في", "فيها", "فيه"})
# the child's other words in the first person; a ḥāl about «أنا» would still be gendered («مبتدئًا»)
_CHILD_PHRASES = (
    ("فيكتمل عنده", "فتكتمل عندي"),
    ("نفسه وأصدقاءه", "نفسي وأصدقائي"),
    ("ما رآه", "ما رأيته"),
    ("التي تعلّمها", "التي تعلّمتها"),
    ("مبتدئًا من", "بدءًا من"),
    ("مستقلًّا", "وحدي"),  # «أكتب الحرف مستقلًّا … بعد الكتابة الموجّهة»: on my own
    ("وحده", "وحدي"),
)
_EDGE = "«»().،:؛!؟"


def _child_verb(word: str) -> str | None:
    """`word` (a verb about the child, maybe «و»/«ف» + verb + object pronoun) in the first person, or None."""
    core = word.strip(_EDGE)
    for prefix in ("", "و", "ف"):
        if not core.startswith(prefix + "ي"):
            continue
        stem = core[len(prefix) :]
        for suffix in ("", *_OBJECT_PRONOUNS):
            if stem.endswith(suffix) and stem[: len(stem) - len(suffix)] in _CHILD_VERBS:
                return word.replace(core, prefix + "أ" + stem[1:], 1)
    return None


def objective_as_child(objective: str) -> str:
    """«يكتب وحده الحروف…» → «أكتب وحدي الحروف…»: a plan objective as the child says it on the opener."""
    for said, mine in _CHILD_PHRASES:
        objective = objective.replace(said, mine)
    return " ".join(_child_verb(w) or w for w in objective.split(" "))


def third_person_left(text: str) -> list[str]:
    """Words of `text` that still read like a third-person verb (not one `objective_as_child` knows is about
    something else): what a test keeps out of the openers."""
    out = []
    for word in re.split(r"[\s/]+", text):
        core = word.strip(_EDGE)
        if core in _NOT_THE_CHILD:
            continue
        if any(core.startswith(p + "ي") for p in ("", "و", "ف")):
            out.append(core)
    return out


# a trace-path page walks a picture to its goal (the plan's two words): who (accusative, genitive), where to
PATH_WHO = {
    "نحلة": ("النَّحْلَةَ", "النَّحْلَةِ"),
    "أرنب": ("الأَرْنَبَ", "الأَرْنَبِ"),
    "سلحفاة": ("السُّلَحْفاةَ", "السُّلَحْفاةِ"),
}
PATH_TO = {"وردة": "الوَرْدَةِ", "جزرة": "الجَزَرَةِ", "خسة": "الخَسَّةِ"}


def path_say(params: Mapping[str, Any]) -> str:
    """«أَوْصِلِ النَّحْلَةَ إلى الوَرْدَةِ عَلى الطَّريقِ»: each walker has its own wording, so the volume's
    paths read differently."""
    words = [str(w) for w in params.get("words", [])]
    if len(words) == 2 and words[0] in PATH_WHO and words[1] in PATH_TO:
        acc, gen = PATH_WHO[words[0]]
        to = PATH_TO[words[1]]
        options = (
            f"{{أَوْصِلِ/أَوْصِلي}} {acc} إلى {to} عَلى الطَّريقِ",
            f"{{امْشِ/امْشي}} بِالقَلَمِ مِنَ {gen} إلى {to}",
            f"{{ساعِدِ/ساعِدي}} {acc} عَلى الوُصولِ إلى {to}",
        )
        return pick(options, list(PATH_WHO).index(words[0]))
    return "{سِرْ/سيري} بِالقَلَمِ عَلى الطَّريقِ حَتّى النِّهايَةِ"


def dot_to_dot_say(params: Mapping[str, Any]) -> str:
    return pick(
        (
            "{اتْبَعِ/اتْبَعي} الأَعْدادَ بِالتَّرْتيبِ لِتَظْهَرَ الصّورَةُ",
            f"{{ابْدَأْ/ابْدَئي}} مِنْ 1 {{وَصِلْ/وَصِلي}} حَتّى {params.get('to', 10)}",
            "{عُدَّ/عُدّي} {وَصِلْ/وَصِلي}: نُقْطَةً بَعْدَ نُقْطَةٍ",
        ),
        turn(params),
    )


COLORING_SAY = (
    "{لَوِّنْ/لَوِّني} بِهُدوءٍ، وَلا {تَخْرُجْ/تَخْرُجي} عَنِ الخَطِّ",
    "{امْلَأْ/امْلَئي} كُلَّ جُزْءٍ بِاللَّوْنِ داخِلَ حُدودِهِ",
    "{اخْتَرْ/اخْتاري} أَلْوانًا جَميلَةً، {وَلَوِّنْ/وَلَوِّني} داخِلَ الحُدودِ",
)
SHAPES_SAY = (
    "{قُلِ/قولي} اسْمَ كُلِّ شَكْلٍ، ثُمَّ {تَتَبَّعْهُ وَلَوِّنْهُ/تَتَبَّعيهِ وَلَوِّنيهِ}",
    "{مَرِّرِ/مَرِّري} القَلَمَ عَلى الأَشْكالِ، ثُمَّ {لَوِّنْها/لَوِّنيها}",
)
ODD_ONE_OUT = (
    "في كُلِّ صَفٍّ صورَةٌ مُخْتَلِفَةٌ: {حَوِّطْها/حَوِّطيها}",
    "{حَوِّطِ الصّورَةَ المُخْتَلِفَةَ، وَقُلْ لِماذا اخْتَرْتَها/حَوِّطي الصّورَةَ المُخْتَلِفَةَ، وَقولي لِماذا اخْتَرْتِها}",
    "أَيُّ صورَةٍ مُخْتَلِفَةٌ؟ {حَوِّطْها، وَقُلْ لِماذا/حَوِّطيها، وَقولي لِماذا}",
)
ODD_ONE_OUT_GROUPS = (  # pages with named-group rows (each row's chip names it); fits seen rows too
    "ثَلاثُ صُوَرٍ تَتَشابَهُ: {حَوِّطِ/حَوِّطي} المُخْتَلِفَةَ",
    "أَيُّ صورَةٍ لا تُشْبِهُ البَقِيَّةَ؟ {حَوِّطْها/حَوِّطيها}",
    "في كُلِّ صَفٍّ صورَةٌ مُخْتَلِفَةٌ: {حَوِّطْها/حَوِّطيها}",
)
MAZE_RUNNERS = {  # a maze's walker when it is not the child (the plan's runner and goal)
    ("bird", "nest"): "{ساعِدِ/ساعِدي} العُصْفورَ لِيَصِلَ إلى عُشِّهِ",
    ("cat", "ball"): "{ساعِدِ/ساعِدي} القِطَّةَ لِتَصِلَ إلى الكُرَةِ",
}
MAZE_SAY = (  # the child's own character walks into the garden
    "{جِدْ طَريقَكَ/جِدي طَريقَكِ} إلى الحَديقَةِ",
    "{ادْخُلْ/ادْخُلي} مِنَ البِدايَةِ، {وَاخْرُجْ/وَاخْرُجي} مِنَ النِّهايَةِ",
    "{فَكِّرْ/فَكِّري} في الطَّريقِ، ثُمَّ {ارْسُمْهُ/ارْسُميهِ} حَتّى الحَديقَةِ",
    "{سِرْ/سيري} في المَتاهَةِ حَتّى {تَصِلَ/تَصِلي} إلى الحَديقَةِ",
)


def maze_say(params: Mapping[str, Any]) -> str:
    runner = (str(params.get("runner", "")), str(params.get("goal", "")))
    return MAZE_RUNNERS.get(runner) or pick(MAZE_SAY, turn(params))


def spot_difference_say(params: Mapping[str, Any]) -> str:
    found = counted(params.get("count", 3), "فُروقٍ", "فَرْقًا")
    return pick(
        (
            f"{{قارِنْ/قارِني}} بَيْنَ الصّورَتَيْنِ، {{وَحَوِّطْ/وَحَوِّطي}} {found}",
            f"بَيْنَ الصّورَتَيْنِ {found}: {{جِدْها/جِديها}} {{وَحَوِّطْها/وَحَوِّطيها}}",
            f"{{ابْحَثْ/ابْحَثي}} عَنْ {found}، {{وَضَعْ/وَضَعي}} حَوْلَها دَوائِرَ",
        ),
        turn(params),
    )


MEMORY_SAY = (
    "{احْفَظِ/احْفَظي} الصُّوَرَ، ثُمَّ {غَطِّها/غَطّيها} {وَحَوِّطْ/وَحَوِّطي} ما {رَأَيْتَ/رَأَيْتِ}",
    "{انْظُرْ/انْظُري} إلى الصُّوَرِ، ثُمَّ {غَطِّها/غَطّيها} {وَتَذَكَّرْ/وَتَذَكَّري} أَماكِنَها",
)
PATTERN_SAY = (
    "{لاحِظْ/لاحِظي} ما يَتَكَرَّرُ، ثُمَّ {أَكْمِلِ/أَكْمِلي} الصَّفَّ",
    "ماذا يَأْتي بَعْدَ ذلِكَ؟ {ارْسُمْهُ/ارْسُميهِ} في مَكانِهِ",
    "{قُلِ/قولي} النَّمَطَ بِصَوْتٍ عالٍ، ثُمَّ {أَكْمِلْهُ/أَكْمِليهِ}",
)
REVIEW_SAY = {  # a review page holds a few exercise cards, each with its own short label
    "pen": (
        "{أَمْسِكِ/أَمْسِكي} القَلَمَ جَيِّدًا، {وَأَكْمِلْ/وَأَكْمِلي} كُلَّ تَمْرينٍ",
        "{ابْدَأْ/ابْدَئي} بِالتَّمْرينِ الأَوَّلِ، ثُمَّ {أَكْمِلِ/أَكْمِلي} الباقِيَ",
        "{ارْسُمْ/ارْسُمي} بِهُدوءٍ في كُلِّ تَمْرينٍ",
    ),
    "letters": (
        "{تَذَكَّرْ حُروفَكَ/تَذَكَّري حُروفَكِ}، ثُمَّ {ابْدَأِ/ابْدَئي} المُراجَعَةَ",
        "{سَمِّ/سَمّي} كُلَّ حَرْفٍ، ثُمَّ {أَكْمِلِ/أَكْمِلي} التَّمارينَ",
        "{أَكْمِلِ/أَكْمِلي} التَّمارينَ، {وَتَذَكَّرْ/وَتَذَكَّري} شَكْلَ كُلِّ حَرْفٍ",
    ),
    "reading": (
        "هَلْ {تَذْكُرُ/تَذْكُرينَ} ما {قَرَأْتَهُ/قَرَأْتِهِ}؟ {أَجِبْ/أَجيبي} عَنِ الأَسْئِلَةِ",
        "{راجِعْ/راجِعي} ما {قَرَأْتَهُ/قَرَأْتِهِ}، {وَأَكْمِلِ/وَأَكْمِلي} التَّمارينَ",
    ),
    "numbers": (
        "{عُدَّ/عُدّي} جَيِّدًا قَبْلَ أَنْ {تَكْتُبَ/تَكْتُبي} الجَوابَ",
        "{حُلَّ/حُلّي} تَمارينَ الأَعْدادِ واحِدًا بَعْدَ واحِدٍ",
    ),
    "math": ("{راجِعْ/راجِعي} ما {تَعَلَّمْتَ/تَعَلَّمْتِ}، ثُمَّ {حُلَّ/حُلّي} التَّمارينَ",),
    "thinking": (
        "{فَكِّرْ/فَكِّري} جَيِّدًا، ثُمَّ {حُلَّ/حُلّي} كُلَّ تَمْرينٍ",
        "لُغْزٌ بَعْدَ لُغْزٍ: {فَكِّرْ/فَكِّري}، ثُمَّ {أَجِبْ/أَجيبي}",
        "{رَكِّزْ/رَكِّزي} عَلى كُلِّ صورَةٍ، ثُمَّ {أَجِبْ/أَجيبي}",
    ),
}
MIXED_REVIEW = (  # the volume's last, cross-subject review: one a volume
    "{راجِعْ/راجِعي} ما {تَعَلَّمْتَهُ/تَعَلَّمْتِهِ} في هذا الجُزْءِ",
    "حُروفٌ وَأَعْدادٌ وَأَشْكالٌ: هَيّا نُراجِعْها!",
    "{راجِعْ/راجِعي} ما {تَعَلَّمْتَهُ/تَعَلَّمْتِهِ} هذا العامَ",
)
ASSESSMENT_SAY = {  # one a volume; the score box under the exercises is the grown-up's
    "pen": (
        "{تَتَبَّعْ/تَتَبَّعي} عَلى مَهْلٍ، كَما {تَعَلَّمْتَ/تَعَلَّمْتِ}",
        "{أَمْسِكِ/أَمْسِكي} القَلَمَ جَيِّدًا، {وَتَتَبَّعْ/وَتَتَبَّعي} عَلى النِّقاطِ",
        "{أَرِ/أَري} الكِبارَ كَيْفَ {تُمْسِكُ/تُمْسِكينَ} القَلَمَ {وَتَرْسُمُ/وَتَرْسُمينَ}",
    ),
    "arabic": (
        "{أَرِ/أَري} الكِبارَ ما {تَعْرِفُهُ/تَعْرِفينَهُ} عَنِ الحُروفِ",
        "{اقْرَأْ/اقْرَئي} {وَاكْتُبْ/وَاكْتُبي} {وَحْدَكَ/وَحْدَكِ}، ثُمَّ {أَرِ/أَري} الكِبارَ",
        "{أَنْتَ تَعْرِفُ الكَثيرَ! أَجِبْ بِنَفْسِكَ/أَنْتِ تَعْرِفينَ الكَثيرَ! أَجيبي بِنَفْسِكِ}",
    ),
    "math": (
        "{عُدَّ/عُدّي} {وَأَجِبْ/وَأَجيبي} {وَحْدَكَ/وَحْدَكِ}، ثُمَّ {أَرِ/أَري} الكِبارَ",
        "{أَرِنا/أَرينا} ما {تَعْرِفُهُ/تَعْرِفينَهُ} عَنِ الأَعْدادِ وَالأَشْكالِ",
        "{احْسُبْ عَلى مَهْلِكَ/احْسُبي عَلى مَهْلِكِ}، {وَأَجِبْ/وَأَجيبي} عَنْ كُلِّ سُؤالٍ",
    ),
    "thinking": (
        "{فَكِّرْ/فَكِّري} {وَحْدَكَ/وَحْدَكِ}، ثُمَّ {أَرِ/أَري} الكِبارَ {حُلولَكَ/حُلولَكِ}",
        "{رَكِّزْ/رَكِّزي}، {وَحُلَّ/وَحُلّي} التَّمارينَ {وَحْدَكَ/وَحْدَكِ}",
        "{فَكِّرْ قَبْلَ أَنْ تُجيبَ، وَخُذْ وَقْتَكَ/فَكِّري قَبْلَ أَنْ تُجيبي، وَخُذي وَقْتَكِ}",
    ),
}


def review_say(subject: str, params: Mapping[str, Any]) -> str:
    """A review page: remember, then do its exercise cards one by one (the wording by subject and turn)."""
    if subject == "mixed":
        return pick(MIXED_REVIEW, volume_key(params))
    if subject == "arabic":
        pool = REVIEW_SAY["letters" if params.get("letters") else "reading"]
    elif subject == "math":
        pool = REVIEW_SAY["numbers" if "numbers" in params or "max" in params else "math"]
    else:
        pool = REVIEW_SAY.get(subject, REVIEW_SAY["thinking"])
    return pick(pool, turn(params))


_MARKS = re.compile("[ً-ْٰ]")


def review_title(unit_title: str, params: Mapping[str, Any]) -> str:
    """A review page's title, «مُراجَعَةٌ: <the unit>», never saying «مراجعة» twice: a unit that is itself a
    review («مُراجَعَةٌ شامِلَةٌ لِلجُزْءِ الأَوَّلِ») keeps its own title, a letters unit that ends with its
    review week («حَرْفا السّينِ وَالشّينِ، وَمُراجَعَةُ ر ز س ش») names its letters, and a titled unit
    («الحَرَكاتُ: الفَتْحَةُ …») does not get a second colon."""
    plain = _MARKS.sub("", unit_title)
    if plain.startswith(("مراجعة", "المراجعة")):
        return unit_title
    letters = [str(c) for c in params.get("letters", ())]
    if "مراجعة" in plain and letters:
        return "مُراجَعَةُ حُروفي: " + " ".join(letters)
    if ": " in unit_title:
        return "مُراجَعَةٌ: " + unit_title.partition(": ")[2]
    return f"مُراجَعَةٌ: {unit_title}"


def assessment_say(subject: str, params: Mapping[str, Any]) -> str:
    return pick(ASSESSMENT_SAY.get(subject, ASSESSMENT_SAY["thinking"]), volume_key(params))


def general_texts(kind: str, params: dict[str, Any], unit_title: str, subject: str = "") -> Texts | None:
    match kind:
        case "owner-page":  # not printed: the page's own label asks for the handprint
            return (
                "هذا الكِتابُ لِـ{child:gen}",
                "{ضَعْ كَفَّكَ عَلى الصَّفْحَةِ وَارْسُمْ حَوْلَها/ضَعي كَفَّكِ عَلى الصَّفْحَةِ وَارْسُمي حَوْلَها}",
                "",
            )
        case "name-trace" if params.get("script") == "en":
            return "My name", *pick(NAME_EN, volume_key(params))
        case "name-trace":
            return "اسْمي", pick(NAME_AR, volume_key(params)), ""
        case "toc":
            return "ماذا في كِتابي؟", pick(TOC_SAY, volume_key(params)), ""
        case "unit-opener":
            options = OPENER_SAY.get(subject)
            return unit_title, (pick(options, volume_key(params)) if options else OPENER_DEFAULT), ""
        case "pen-lines":
            line = str(params.get("line", "horizontal"))
            title = PEN_TITLES.get(line, "خُطوطٌ")
            return title, PEN_SAY.get(line, "{ارْسُمْ/ارْسُمي} عَلى النِّقاطِ مِنَ النُّقْطَةِ الخَضْراءِ"), ""
        case "trace-path":
            return "الطَّريقُ الصَّحيحُ", path_say(params), ""
        case "dot-to-dot":
            return f"مِنْ 1 إلى {params.get('to', 10)}", dot_to_dot_say(params), ""
        case "shapes":
            return shapes_title(params.get("shapes")), pick(SHAPES_SAY, turn(params)), ""
        case "coloring":
            return "أُلَوِّنُ بِعِنايَةٍ", pick(COLORING_SAY, turn(params)), ""
        case "connect":
            return "صُوَرٌ مُتَشابِهَةٌ", "لِكُلِّ صورَةٍ صورَةٌ تُشْبِهُها: {صِلْهُما/صِليهِما}", ""
        case "classify":
            return "لِكُلِّ لَوْنٍ سَلَّةٌ", "ما لَوْنُ كُلِّ شَيْءٍ؟ {صِلْهُ/صِليهِ} بِسَلَّةِ لَوْنِهِ", ""
        case "odd-one-out":
            pool = ODD_ONE_OUT_GROUPS if "category" in params.get("rules", ()) else ODD_ONE_OUT
            return "ما المُخْتَلِفُ؟", pick(pool, turn(params)), ""  # things: «ما», never «مَنِ»
        case "maze":
            return "مَتاهَةٌ", maze_say(params), ""
        case "spot-difference":
            return "أَيْنَ الفُروقُ؟", spot_difference_say(params), ""
        case "memory":
            return "أَنْظُرُ وَأَتَذَكَّرُ", pick(MEMORY_SAY, turn(params)), ""
        case "pattern-complete":
            return "أُكْمِلُ النَّمَطَ", pick(PATTERN_SAY, turn(params)), ""
        case "cut-and-paste":
            return (
                "أَقُصُّ وَأُلْصِقُ",
                "{قُصَّ/قُصّي} القِطَعَ، {وَأَلْصِقْها/وَأَلْصِقيها} {لِتُكْمِلَ/لِتُكْمِلي} الصّورَةَ",
                "",
            )
        case "blank":  # not printed: the back of a cut-out sheet
            return "ظَهْرُ صَفْحَةِ القَصِّ", "هذِهِ الصَّفْحَةُ فارِغَةٌ", ""
        case "drawing":
            return "أُكْمِلُ الرَّسْمَ", "{ارْسُمِ/ارْسُمي} النِّصْفَ النّاقِصَ لِيُشْبِهَ النِّصْفَ الآخَرَ", ""
        case "unit-review":
            return review_title(unit_title, params), review_say(subject, params), ""
        case "assessment":
            return unit_title, assessment_say(subject, params), ""
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
    found = found or general_texts(kind, params, unit_title, subject)
    if found is None:
        raise KeyError(f"no child-facing text for {kind!r} ({subject}) yet")
    return found
