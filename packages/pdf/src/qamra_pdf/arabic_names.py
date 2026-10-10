"""A typed name inside an Arabic sentence: «أبو» and «ذو» change with the case (الأسماء الخمسة).

A name prints as the parent typed it, except that a name starting with «أبو» or «ذو» takes the case of its
slot (Fusha): «أبا» / «ذا» in the accusative («يا أبا بكر», «ساعِدْ أبا بكر», never «يا أبو بكر») and «أبي» /
«ذي» in the genitive («لِأبي بكر», «مَعَ أبي بكر», «رِحْلَةُ أبي بكر», never «مع أبو بكر»). The templates of
every product (story themes, activity books, certificates, covers, emails) fill names through `fill_name`:

- after «يا» the name is a vocative (منادى مضاف, منصوب): `يا {child}` fills «يا أبا بكر» with no mark in the
  template, so every greeting («رائِعٌ يا {child}!», «أَحْسَنْتَ يا {child}!», «أَهْلًا يا {name}») is right;
- an accusative slot that has no «يا» before it is marked in the template, `{child:acc}`: an object
  («{ساعِدْ/ساعِدي} {child:acc} لِلْوُصولِ», «وَضَمَّتْ {name:acc}»), a call without «يا» («{name:acc}!») or a
  greeting that calls a person by name («مرحبًا {name:acc}»);
- a genitive slot is marked `{child:gen}`: after a preposition («لِـ{child:gen}», «مَعَ {child:gen}», «إلى
  {name:gen}») or as the second term of an iḍāfa («دوسية {child:gen}», «رِحْلَةُ {child:gen}»). «لـ» / «لِـ»
  right before the name joins the name as Arabic writes it: «لِأبي بكر», «لِأحمد» (the لا ligature, never
  «لِـأبي»), «لِلمعتصم» (never «لِـالمعتصم»); before any other name the «ـ» stays («لِـسلمى»);
- every other slot (`{child}`, a subject or a title) prints the name as typed.

A name joins the word before it when it starts with hamzat al-wasl (`starts_with_wasl`): the article
(«الجود», «المعتصم») or the masdar of a derived verb typed with a bare alif («ابتسام», «انتصار»,
«ابتهال», «اعتدال», «امتثال», «انشراح»). A word-final sukun before it takes its helping vowel:
«قالَتْ» + «ابتسام» → «قالَتِ ابتسام», «{ساعِدْ/ساعِدي} {child:acc}» + «انتصار» → «ساعِدِ انتصار»,
and «مِنْ» → «مِنَ الجود» but «مِنِ ابتسام».

`accusative(name)` and `genitive(name)` change only a name whose first word is «أبو», «ابو» or «ذو» followed
by another word: «أبو بكر» → «أبا بكر» / «أبي بكر», «ابو بكر» → «ابا بكر» / «ابي بكر» (the parent's hamza
kept), «ذو الفقار» → «ذا الفقار» / «ذي الفقار», and with the parent's tashkeel «أَبُو بَكْر» → «أَبَا بَكْر» /
«أَبِي بَكْر» (a mark on the ب becomes the case's vowel, the marks on the و go, the new letter takes none).
Left as typed, on purpose:

- a one-word «أبوبكر»: the name is never split or respelled (we cannot tell a joined kunya from a name; the
  create flow suggests the two-word spelling instead);
- a name that does not start with «أبو» («محمد أبو بكر», «سلمى أبو غوش»): the first name takes the case, and
  the family part after it is a surname printed as the family writes it;
- the family's name (`{family_name}`, «عائلة أبو غوش»): a surname, never inflected.

AI-written story text cannot carry marks, so its vocatives and the genitive after a preposition are fixed
after the model writes them (`fix_vocatives`, `fix_genitives`), and the story prompts ask the model to
inflect the name itself (an iḍāfa, «كِتَابُ أَبِي بَكْرٍ», is the model's).
"""

from __future__ import annotations

import re
from collections.abc import Mapping

_ARABIC = "؀-ۿ"  # letters and marks: «يا» must not be the end of a longer word («هَيّا»)
_M = "[ً-ْٰ]"  # tashkeel: tanween, harakat, shadda, sukun, dagger alif
_FATHA = "َ"
_KASRA = "ِ"

# the first word «أبو» / «ابو» / «ذو» (tashkeel allowed) when another word follows it
_HEAD = re.compile(f"^(\\s*(?:[أا]{_M}*ب|ذ))({_M}*)و{_M}*(?=\\s+\\S)")
# «يا» as a word of its own, and the spaces after it
_YA = f"(?<![{_ARABIC}])(?:[وف]{_M}*)?ي{_M}*ا{_M}*\\s+"  # «يا», «وَيا», «فَيا»
_YA_AT_END = re.compile(f"{_YA}$")
ACC = ":acc"  # the mark of an accusative slot: `{child:acc}`
GEN = ":gen"  # the mark of a genitive slot: `{child:gen}`
_ALIF = "اأإآٱ"  # a name that starts with an alif joins «لـ» as «لا» (the ligature), «ال» as «لل»
_SUKUN, _DAMMA = "ْ", "ُ"
# a word's last letter, its marks after it, and the sukun among them (a sukun before hamzat al-wasl)
_LAST = "[^\\s\u064b-\u0652\u0670]"
_SUKUN_END = f"({_LAST}){_M}*{_SUKUN}{_M}*"
# Names that start with «ال» with no article in them, typed without their hamza (أَلين، آلاء، إلهام،
# إلياس، أُلفت…): their alif is a hamzat al-qat', so «لـ» joins them as «لا» («لِالين», never «لِلين») and
# the word before them keeps its sukun. Every other name that starts with «ال» + two letters or more has
# the article («المعتصم»، «الحسن»، «الجود»، «الليث»): its alif is a hamzat al-wasl.
NOT_ARTICLE = frozenset(
    {"الين", "الاء", "الهام", "الياس", "الما", "اليسا", "اليسار"}
    | {"الينا", "اليانا", "الان", "الينور", "اليان"}
    | {"الفت", "الفة", "الماس", "الطاف", "الحان"}  # أُلفت، أُلفة، ألماس، ألطاف، ألحان
    | {"البير", "البرت", "الفريد", "الكسندر", "اليكس", "اليس", "اليف"}  # Albert, Alfred, Alexander, Alice…
)
# Names that start with hamzat al-wasl with no article: the masdar of the derived verb forms, typed
# with a bare alif. افْتِعال: «ابتسام», «انتصار», «ابتهال», «اعتدال», «امتثال», «اعتماد», «امتنان»,
# «اختيار», «ارتقاء» (and «اصطفاء», «ازدهار», where the ت becomes ط or د); انْفِعال: «انشراح»,
# «انطلاق»; اسْتِفْعال: «استقلال». Not these: a name with a hamzat al-qat' («أحمد», «إيمان», «آمنة»,
# «إسراء», «أنوار», «إستبرق»), even typed without its hamza («اسراء», «انعام», «استبرق»: not of these
# patterns; the foreign names that fit one are `NOT_WASL`), and a wasl name typed with a hamza
# («إبتسام»): it prints as the parent wrote it, so the sukun before it stays.
# foreign names that fit a pattern: أنطوان، أنستاس، إستيفان
NOT_WASL = frozenset({"انطوان", "انستاس", "استيفان"})
_WASL_MASDAR = re.compile(
    "^ا(?:[ء-ي]ت|[صضطظ]ط|زد)[ء-ي]ا[ء-ي]$"  # افتعال: ابتسام، انتصار، اصطفاء، ازدهار
    "|^ان[ء-ي]{2}ا[ء-ي](?<!ء)$"  # انفعال: انشراح، انطلاق (not a plural أنبياء، أنقياء)
    "|^است[ء-ي]{2}ا[ء-ي]$"  # استفعال: استقلال
)


def accusative(name: str) -> str:
    """The name in the accusative and after «يا»: «أبو بكر» → «أبا بكر», «ذو الفقار» → «ذا الفقار»; every
    other name is returned as typed."""
    return _HEAD.sub(lambda m: m.group(1) + (_FATHA if m.group(2) else "") + "ا", name, count=1)


def genitive(name: str) -> str:
    """The name in the genitive (after a preposition, or owning a noun): «أبو بكر» → «أبي بكر», «ذو الفقار» →
    «ذي الفقار», «أَبُو بَكْر» → «أَبِي بَكْر»; every other name is returned as typed."""
    return _HEAD.sub(lambda m: m.group(1) + (_KASRA if m.group(2) else "") + "ي", name, count=1)


def vocative(name: str) -> str:
    """The name after «يا» (a vocative of a construct name is accusative): the same as `accusative`."""
    return accusative(name)


def in_case(name: str, case: str) -> str:
    """The name for a slot's mark: `:acc` (or `acc`) the accusative, `:gen` the genitive, else as typed."""
    mark = case if case.startswith(":") else ":" + case
    return accusative(name) if mark == ACC else genitive(name) if mark == GEN else name


def case_forms(name: str) -> tuple[str, ...]:
    """The ways `name` can be printed: as typed, then its accusative and genitive when they differ («أبو بكر»,
    «أبا بكر», «أبي بكر»), to find the name inside a filled text (a cover title, «يوم تخرّج أبي بكر»)."""
    return tuple(dict.fromkeys((name, accusative(name), genitive(name))))


def after(before: str, name: str) -> str:
    """The name as printed right after `before`: accusative when `before` ends with «يا», else as typed (for
    a title set in pieces: «…يا» + the name in its own color)."""
    return accusative(name) if _YA_AT_END.search(before) else name


def has_article(name: str) -> bool:
    """The name starts with the article «ال» (a hamzat al-wasl): «المعتصم», «الْحَسَن», «الليث»; not «الين»,
    «الاء», «الهام», «الياس» (`NOT_ARTICLE`), «أحمد» or «سلمى»."""
    words = re.sub(_M, "", name).split()
    return bool(words) and words[0].startswith("ال") and len(words[0]) >= 4 and words[0] not in NOT_ARTICLE


def starts_with_wasl(name: str) -> bool:
    """The name starts with hamzat al-wasl, so the word before it joins it (`with_helping_vowel`): the article
    («المعتصم», «الْحَسَن», `has_article`) or the masdar of a derived verb typed with a bare alif («ابتسام»,
    «انتصار», «ابتهال», «اعتدال», «امتثال», «انشراح», «استقلال»); not «أحمد», «إيمان», «آمنة», «إبتسام» (typed
    with a hamza), «الين» or «سلمى»."""
    words = re.sub(_M, "", name).split()
    if not words or words[0] in NOT_WASL:
        return False
    return has_article(name) or _WASL_MASDAR.match(words[0]) is not None


def after_lam(form: str) -> str | None:
    """The name written onto a «ل» before it, when they join: «أبي بكر» → «أبي بكر» («لِأبي بكر», the لا
    ligature), «المعتصم» → «لمعتصم» («لِلمعتصم»: the article's alif goes), «الليث» → «ليث» («لِليث»: «ل» + «الل»
    is written «لل»), «الين» → «الين» («لِالين»). None when the «ـ» stays («سلمى»: «لِـسلمى»)."""
    if not form[:1] or form[0] not in _ALIF:
        return None
    if not has_article(form):
        return form
    article = re.match(f"ا{_M}*(ل{_M}*)", form)
    assert article is not None  # has_article: the name starts with «ال»
    rest = form[article.end() :]
    return rest if rest.startswith("ل") else article.group(1) + rest


def _join_lam(text: str, marked: str, form: str) -> str:
    """«لـ» / «لِـ» right before a genitive slot, joined to a name that starts with an alif (`after_lam`):
    «لِأبي بكر», «لِلمعتصم», «لِليث». Before any other letter the «ـ» stays («لِـسلمى»)."""
    joined = after_lam(form)
    if joined is None:
        return text
    return re.sub(f"(ل{_M}*)ـ" + re.escape(marked), lambda m: m.group(1) + joined, text)


def _helping_vowel(m: re.Match[str], article: bool = True) -> str:
    """The vowel a word-final sukun takes before hamzat al-wasl: «مِنَ» before the article (`article`) and
    «مِنِ» before any other wasl («مِنِ ابتسام»), «هُمُ» / «كُمُ» / «تُمُ», else «ِ» («هَمَسَتِ», «أَوِ», «مَنِ»); a
    long vowel («فِيْ») keeps its letter and loses the sukun."""
    word, letter = m.group(1), m.group(2)
    plain = re.sub(_M, "", word + letter)
    if letter in "اى" or (letter in "وي" and not re.search(f"َ{_M}*$", word)):
        return word + letter + m.group(3)  # a long vowel: no helping vowel, the sukun goes
    if plain in ("من", "ومن", "فمن") and article and _KASRA in word:
        vowel = _FATHA  # «مِنَ الجود»; «مَنْ» (who) takes the kasra: «مَنِ الجود»
    elif letter == "م" and re.search(f"{_DAMMA}{_M}*$", word):
        vowel = _DAMMA
    else:
        vowel = _KASRA
    return word + letter + vowel + m.group(3)


def with_helping_vowel(before: str, name: str) -> str:
    """`before`, the text right before `name`, with the sukun on its last word turned into the helping vowel
    when the name starts with hamzat al-wasl (`starts_with_wasl`): «هَمَسَتْ» + «الجود» → «هَمَسَتِ الجود»,
    «وَضَمَّتْ» + «الحسن» → «وَضَمَّتِ الحسن», «مِنْ» + «المعتصم» → «مِنَ المعتصم», «قالَتْ» + «ابتسام» →
    «قالَتِ ابتسام», «مِنْ» + «ابتسام» → «مِنِ ابتسام»; unchanged for any other name."""
    if not starts_with_wasl(name):
        return before
    article = has_article(name)
    return re.sub(f"(\\S*?){_SUKUN_END}(\\}}?\\s+)$", lambda m: _helping_vowel(m, article), before)


def fill_name(text: str, slot: str, name: str) -> str:
    """`{slot}`, `{slot:acc}` and `{slot:gen}` filled with `name`: accusative at `{slot:acc}` and right after
    «يا», genitive at `{slot:gen}` (joined to a «لـ» before it), as typed everywhere else. `slot` is the bare
    placeholder name («child», «name», «adult»)."""
    plain, acc, gen = "{" + slot + "}", "{" + slot + ACC + "}", "{" + slot + GEN + "}"
    if plain not in text and acc not in text and gen not in text:
        return text
    if starts_with_wasl(name):  # «هَمَسَتْ {name}» + «الجود» → «هَمَسَتِ الجود», + «ابتسام» → «هَمَسَتِ ابتسام»
        any_slot = f"(?=\\{{{re.escape(slot)}(?:{ACC}|{GEN})?\\}})"
        pattern = f"(\\S*?){_SUKUN_END}(\\}}?\\s+){any_slot}"
        article = has_article(name)
        text = re.sub(pattern, lambda m: _helping_vowel(m, article), text)
    form = accusative(name)
    text = text.replace(acc, form)
    if gen in text:
        text = _join_lam(text, gen, genitive(name)).replace(gen, genitive(name))
    if form != name:
        text = re.sub(f"({_YA})" + re.escape(plain), lambda m: m.group(1) + form, text)
    return text.replace(plain, name)


def fill_names(text: str, names: Mapping[str, str]) -> str:
    """Every slot of `names` ({slot: name}) filled with `fill_name`."""
    for slot, name in names.items():
        text = fill_name(text, slot, name)
    return text


def unmark(text: str, slots: tuple[str, ...]) -> str:
    """`{slot:acc}`, `{slot:gen}` → `{slot}`: the text as it was before the case marks (to keep a cached
    text's key)."""
    for slot in slots:
        for mark in (ACC, GEN):
            text = text.replace("{" + slot + mark + "}", "{" + slot + "}")
    return text


def remark(text: str, template: str, slots: tuple[str, ...]) -> str:
    """The case marks of `template` put back on `text`, slot by slot in order. `text` is `template` with its
    marks removed and only diacritics added (a cached vowelization), so their slots line up; when the slot
    names do not line up the text is returned as it is."""
    pattern = re.compile("\\{(" + "|".join(map(re.escape, slots)) + f")(?:{ACC}|{GEN})?\\}}")
    marks = list(pattern.finditer(template))
    if [m.group(1) for m in marks] != [m.group(1) for m in pattern.finditer(text)]:
        return text
    it = iter(m.group(0) for m in marks)
    return pattern.sub(lambda _: next(it), text)


def _loose(word: str) -> str:
    """A regex for `word` with any tashkeel between and after its letters."""
    return "".join(re.escape(c) + f"{_M}*" for c in word)


def fix_vocatives(text: str, name: str) -> str:
    """AI-written text: «يا أبو بكر» → «يا أبا بكر» for the child's own name, with or without tashkeel
    («يَا أَبُو بَكْرٍ» → «يَا أَبَا بَكْرٍ»). Other names and other cases are left to the model."""
    words = name.split()
    if len(words) < 2 or accusative(name) == name:
        return text
    head = re.compile(f"({_YA})((?:[أا]{_M}*ب|ذ))({_M}*)و{_M}*(?=\\s+{_loose(re.sub(_M, '', words[1]))})")
    return head.sub(lambda m: m.group(1) + m.group(2) + (_FATHA if m.group(3) else "") + "ا", text)


# The words after which a name is genitive in AI text: prepositions and the adverbs that own the next noun,
# each one a word of its own (an «و» / «ف» may lead it: «وَمَعَ», «فَإِلَى»). «مِنْ» counts only with its kasra
# («من أبو بكر؟» may be «مَنْ», who). Left out, since the same letters can be a verb or start a clause whose
# subject is the name: «حتى», «قبل» (قَبَّلَ), «بعد» (بَعُدَ), «مثل» (مَثَّلَ), «حول» (حَوَّلَ), «بين» (بَيَّنَ), «دون» (دَوَّنَ),
# «عبر» (عَبَرَ), «قرب» (قَرُبَ).
_GOVERNORS = (
    "مع", "إلى", "الى", "عن", "في", "عند", "على", "لدى", "نحو", "أمام", "امام", "خلف", "وراء", "فوق", "تحت",
    "بجانب", "بقرب",
)  # fmt: skip
_MIN = f"م{_M}*{_KASRA}{_M}*ن{_M}*"  # «مِنْ» / «مِن» only: a bare «من» may be «مَنْ» (who), left to the model
_PROCLITIC = f"(?:[وف]{_M}*)?"
_ATTACHED = f"[لبك]{_M}*ـ?"  # «لِـ», «بِـ», «كَـ» written onto the name


def fix_genitives(text: str, name: str) -> str:
    """AI-written text: the child's own «أبو بكر» after a preposition takes «أبي بكر», with or without
    tashkeel: «لأبو بكر» / «لِـأَبُو بَكْرٍ» → «لأبي بكر» / «لِأَبِي بَكْرٍ» (the «ـ» before an alif goes: the لا
    ligature), «مَعَ أبو بكر» → «مَعَ أبي بكر», «إلى أبو بكر» → «إلى أبي بكر». Other names, an iḍāfa
    («كتاب أبو بكر») and every other case are left to the model."""
    words = name.split()
    if len(words) < 2 or genitive(name) == name:
        return text
    head = f"((?:[أا]{_M}*ب|ذ))({_M}*)و{_M}*(?=\\s+{_loose(re.sub(_M, '', words[1]))})"
    governor = "|".join(_loose(w) for w in _GOVERNORS) + "|" + _MIN
    separate = re.compile(f"(?<![{_ARABIC}])({_PROCLITIC}(?:{governor})\\s+){head}")
    attached = re.compile(f"(?<![{_ARABIC}])({_PROCLITIC}{_ATTACHED}){head}")

    def to_gen(m: re.Match[str]) -> str:
        lead = m.group(1)
        if m.group(2)[0] in _ALIF and re.search(f"ل{_M}*ـ$", lead):
            lead = lead[:-1]  # «لـأبي» → «لأبي»: the لا ligature
        return lead + m.group(2) + (_KASRA if m.group(3) else "") + "ي"

    return attached.sub(to_gen, separate.sub(to_gen, text))
