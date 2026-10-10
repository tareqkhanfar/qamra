"""«تحقق من التذكير والتأنيث»: a deterministic second look at the hero's gender in a story's words.

Magic and custom stories are written by the text model (prompts `story_adapt`, `story_custom`), which is told
the hero is a boy or a girl and gets it right almost always. This check reads the finished words the way a
careful reviewer would and lists the few places worth a second look. It never fails or blocks a book: the
book gets the `gender_check` flag for the staff text review (every story book waits there before print
anyway), with hints that point at the words. Words the family or the staff change are checked again when the
book's files are rebuilt.

What it reads, in Arabic (a mark decides only where it is written: an unvowelized «معك» reads right for both
and is never flagged):

- **The hero's verb next to the name**: «قالَتْ يوسفُ», «ضَحِكَ ليان» (before the name), «ليان يَضْحَكُ» (after
  it). The verb's gender comes from a lexicon: common story verbs plus every one-word `{m/f}` pair in the
  theme files. A verb that can take a person as its object («ضَمَّتْ يوسفَ», mama hugged him) counts only when
  the name is marked as the subject (a damma), and a word that is also a common noun («شَعْرُ ليان», her hair)
  only when its marks make it a verb («شَعَرَ»).
- **A quote that speaks to the hero** («… يا يوسف …», or one said «لِيوسف:»): its second-person words must be
  the hero's. «أَحْسَنْتِ», «مَعَكِ», «أَنْتِ», «لا تَخافي», «تَعالَيْ», «تُحِبّينَ» are a girl's; «أَحْسَنْتَ»,
  «مَعَكَ», «أَنْتَ», «لا تَخَفْ», «تَعالَ» a boy's.
- **«يا بطل / يا بطلة»** anywhere, and «يا حبيبي / يا حبيبتي»… in a quote that speaks to the hero.
- **A theme story's own other-gender words** on the same page: «حقيبتها» on a boy's page whose base text has
  «{حَقِيبَتَهُ/حَقِيبَتَهَا}».

In English: «herself» in a sentence about a boy, and «she» / «her» when no other girl or woman is in the
sentence or the one before (and the other way round for a girl; the companion is a «he»).
"""

import re
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from functools import cache
from pathlib import Path

import yaml

from qamra_ai.pipeline.models import Gender, Lang, StoryOut
from qamra_ai.pipeline.theme import CONTENT_DIR, Theme, render_template
from qamra_pdf.arabic_names import case_forms

FLAG = "gender_check"
RULES = (
    "verb_before_name",
    "verb_after_name",
    "addressed",
    "epithet",
    "theme_word",
    "pronoun_en",
    "text_review",
)

_MARKS = "ً-ْٰ"  # tanween, harakat, shadda, sukun, dagger alif
_FATHA, _KASRA, _SUKUN, _DAMMA, _DAMMATAN = "َ", "ِ", "ْ", "ُ", "ٌ"
_TANWEEN = "ًٌٍ"
_STRIP = re.compile(f"[{_MARKS}ـ]")  # the marks and the tatweel
_WORD = re.compile(f"[ء-غف-يٱ{_MARKS}ـ]+")
_BREAK = re.compile(r"[.!?؟،,:;؛«»\"“”…—–()\[\]\n]")
_SENTENCE_END = re.compile(r"[.!?؟\n]")
_QUOTES = (("«", "»"), ("“", "”"), ('"', '"'))
_VARIANT = re.compile(r"\{([^{}/]+)/([^{}/]+)\}")
_YA = ("يا", "ويا", "فيا")


def plain(text: str) -> str:
    """The letters only: no tashkeel, no tatweel."""
    return _STRIP.sub("", text)


def norm(word: str) -> str:
    """A word for the lexicon: letters only, every alif form as «ا»."""
    return re.sub("[أإآٱ]", "ا", plain(word))


def _words(text: str) -> list[str]:
    return text.split()


def _letters(raw: str) -> list[tuple[str, str]]:
    """(letter, its marks) for each letter of a word."""
    out: list[tuple[str, str]] = []
    for ch in raw:
        if re.match(f"[{_MARKS}]", ch):
            if out:
                out[-1] = (out[-1][0], out[-1][1] + ch)
        elif ch != "ـ":
            out.append((ch, ""))
    return out


def final_mark(raw: str) -> str:
    """The marks written on a word's last letter («مَعَكِ» → kasra)."""
    letters = _letters(raw)
    return letters[-1][1] if letters else ""


def _mark_before_last(raw: str) -> str:
    """The marks on the letter before the last one («أَحْسَنْتِ» → the sukun on «ن»)."""
    letters = _letters(raw)
    return letters[-2][1] if len(letters) > 1 else ""


# ---- the lexicon -----------------------------------------------------------------------------------

# Past verbs (3rd person masculine, spelled with their hamza: the feminine is built on the spelling) that
# take no person as their object: the name right after them is their subject.
_SUBJECT_ONLY_PAST = _words("""
قال همس صاح صرخ هتف ضحك ابتسم بكى فرح حزن خاف شعر ركض مشى قفز جلس وقف نام استيقظ غفا ذهب عاد رجع وصل
خرج دخل صعد نزل طار سبح لعب كان صار ظل بقي بدأ اقترب ابتعد أسرع تنهد تعب ارتاح تردد نجح فاز تثاءب تسلق
اختبأ أبحر سافر فكر تخيل تمنى حلم أجاب تعلم رسم لون كتب قرأ أكل شرب لبس فتح أغلق صنع بنى زرع سقى قطف
جمع عد غنى صفق رقص لوح اكتشف بحث تذكر انتبه التفت هرول تسلل اندهش تعجب احمر خجل غضب نظر
""")
# … and the ones a person can be the object of («ضَمَّتْ يوسفَ»): the name after them may be the object.
_OBJECT_PAST = _words("""
نادى سأل حمل أمسك رفع وضع أخذ أعطى ساعد شارك شكر أحب رأى سمع وجد زار انتظر عانق ضم حضن قبل وعد علم فاجأ
استقبل ودع لاعب داعب احتضن أيقظ دغدغ أجلس أطعم حيا شجع طمأن أهدى سامح
""")
# imperfect stems: «ي» + stem is his, «ت» + stem hers (also «you», to a boy)
_SUBJECT_ONLY_IMPF = _words("""
قول همس صيح صرخ هتف ضحك بتسم بكي فرح حزن خاف شعر ركض مشي قفز جلس قف نام ستيقظ ذهب عود رجع صل خرج دخل
صعد نزل طير سبح لعب كون صير ظل بقى بدأ قترب بتعد سرع تنهد تعب رتاح تردد نجح فوز تثاءب تسلق ختبئ بحر سافر
فكر تخيل تمنى حلم جيب تعلم رسم لون كتب قرأ أكل شرب لبس فتح غلق صنع بني زرع سقي قطف جمع غني صفق رقص لوح
كتشف بحث تذكر نتبه لتفت غفو نظر
""")
_OBJECT_IMPF = _words("""
نادي سأل حمل مسك رفع ضع أخذ عطي ساعد شارك شكر حب رى سمع جد زور نتظر عانق ضم حضن قبل عد علم فاجئ ستقبل
ودع لاعب داعب حتضن وقظ دغدغ حيي شجع طمئن
""")
# words that are also common nouns, read as a verb only when their marks say so («شَعْرُ ليان» is her hair)
_NOUN_LIKE = frozenset(
    _words(
        "لون رسم حلم فرح حزن شعر لعب ضحك بحث جمع عد زرع كتب رقص صنع قطف نوم عمل وعد سفر نظر تعلم تذكر تخيل "
        "تخرج تنفس تسلق تردد تنهد"  # «تَخَرُّجُ», «تَنَفُّسُ»: nouns that look like «she …»
    )
)
# second-person words by gender: imperatives, and the jussive after «لا»
_IMPERATIVE = {
    "m": _words(
        "ارسم انظر اسمع اجلس العب اركض افتح اغمض امسك اختر ابتسم انتبه اقفز اذهب ارقص اصعد انزل اكتب اقرا "
        "البس احمل ارفع قل خذ قف نم تعال هات لون غن تنفس تذكر ساعدني"
    ),
    "f": _words(
        "ارسمي انظري اسمعي اجلسي العبي اركضي افتحي اغمضي امسكي اختاري ابتسمي انتبهي اقفزي اذهبي ارقصي "
        "اصعدي انزلي اكتبي اقرئي البسي احملي ارفعي قولي خذي قفي نامي تعالي هاتي عودي لوني غني تنفسي تذكري "
        "ساعديني كلي"
    ),
}
_NEGATED = {  # after «لا»: «لا تَخَفْ» / «لا تَخافي»
    "m": _words("تخف تحزن تقلق تنس تتاخر تذهب تلمس تخجل تبتعد تترك تياس تستسلم تتعب"),
    "f": _words("تخافي تحزني تقلقي تنسي تتاخري تذهبي تلمسي تخجلي تبتعدي تتركي تياسي تستسلمي تتعبي"),
}
_EPITHETS = {  # «يا بطل», «يا حبيبتي»: «بطل/بطلة» count anywhere, the rest in a quote to the hero
    "m": frozenset(_words("بطل بطلي حبيبي صغيري عزيزي شاطر بني ابني")),
    "f": frozenset(_words("بطلة بطلتي حبيبتي صغيرتي عزيزتي شاطرة بنيتي ابنتي اميرتي")),
}
_ANYWHERE_EPITHETS = frozenset(_words("بطل بطلي بطلة بطلتي"))
# words that end in «ك» but are not «you»: «السَّمَكِ», «ذَلِكَ», «ضَحِكَ»
_K_WORDS = frozenset(
    _words("""
ملك سمك ديك شباك شبك ضحك مسك فلك شوك بنك كعك سلك مبارك ذلك تلك هناك هنالك اولئك كذلك لذلك بذلك فلذلك امسك
شارك ترك فرك حرك تحرك بارك اشترك ادرك ضاحك هلك فكك دك عرك معترك مسلك سواك
""")
)
_K_IMPF_STEMS = ("ضحك", "مسك", "شارك", "ترك", "تحرك", "درك", "ملك", "بارك", "فرك", "حرك")
# the stems of a 2nd-person past the lexicon does not spell out («قُلْتَ», «كُنْتِ», «نِمْتَ»)
_SECOND_PAST_STEMS = frozenset(_words("قل كن صر نم خف عد زر طر سر رح بت نل جئ احسن فعل عرف كبر فز نجح"))
# English: words that bring another «she» or «he» into the sentence
_EN_FEMALE = re.compile(
    r"\b(mama|mom|mommy|mother|teta|grandma|granny|grandmother|sister|aunt|auntie|teacher|girl|girls|lady|"
    r"woman|queen|princess|turtle|star|tree)\b",
    re.I,
)
_EN_MALE = re.compile(
    r"\b(baba|dad|daddy|father|sido|jiddo|grandpa|grandfather|brother|uncle|boy|boys|man|king|prince)\b",
    re.I,
)
_EN_PRONOUNS = {
    "m": re.compile(r"\b(he|him|his|himself)\b", re.I),
    "f": re.compile(r"\b(she|her|hers|herself)\b", re.I),
}
_EN_REFLEXIVE = {"m": re.compile(r"\bhimself\b", re.I), "f": re.compile(r"\bherself\b", re.I)}
_EN_COMMON = frozenset(
    _words(
        "I The A An And Then But So When That This One In On At He She His Her Him It They We You Now Today "
        "Tomorrow What How Who Where Look Wow Oh Yes No Good Thank Welcome Here There Every All Soon After"
    )
)


def _fem_past(masc: str) -> str:
    """«قال» → «قالت», «مشى» → «مشت», «غفا» → «غفت», «بدأ» → «بدأت» (the spelling, not `norm`)."""
    return masc[:-1] + "ت" if masc[-1] in "ىا" else masc + "ت"


@dataclass(frozen=True)
class Lexicon:
    past: dict[str, tuple[Gender, bool]]  # verb → (its gender, whether a person can be its object)
    impf: dict[str, tuple[Gender, bool]]
    second: dict[str, Gender]  # 2nd-person words: imperatives («ارسمي»), «تحبين»
    negated: dict[str, Gender]  # after «لا»


def _variant_pairs(node: object) -> Iterator[tuple[str, str]]:
    if isinstance(node, str):
        for m in _VARIANT.finditer(node):
            yield m.group(1).strip(), m.group(2).strip()
    elif isinstance(node, dict):
        for v in node.values():
            yield from _variant_pairs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _variant_pairs(v)


def theme_pairs(content_dir: Path = CONTENT_DIR) -> list[tuple[str, str]]:
    """Every one-word Arabic `{m/f}` pair in the story themes and class books, as (masculine, feminine)."""
    out: list[tuple[str, str]] = []
    files = [
        *sorted((content_dir / "themes").glob("*/theme.yaml")),
        *sorted((content_dir / "class-books").glob("*.yaml")),
    ]
    for path in files:
        for m, f in _variant_pairs(yaml.safe_load(path.read_text(encoding="utf-8"))):
            if re.search("[؀-ۿ]", m) and len(m.split()) == 1 and len(f.split()) == 1:
                out.append((m, f))
    return out


def _unconj(word: str) -> str:
    """A word without the «و» / «ف» joined to it."""
    return word[1:] if len(word) > 3 and word[0] in "وف" else word


@cache
def lexicon() -> Lexicon:
    past: dict[str, tuple[Gender, bool]] = {}
    impf: dict[str, tuple[Gender, bool]] = {}
    for verbs, takes_object in ((_SUBJECT_ONLY_PAST, False), (_OBJECT_PAST, True)):
        for v in verbs:
            past.setdefault(norm(v), ("m", takes_object))
            past.setdefault(norm(_fem_past(v)), ("f", takes_object))
    for stems, takes_object in ((_SUBJECT_ONLY_IMPF, False), (_OBJECT_IMPF, True)):
        for s in stems:
            impf.setdefault(norm("ي" + s), ("m", takes_object))
            impf.setdefault(norm("ت" + s), ("f", takes_object))
    genders: tuple[Gender, ...] = ("m", "f")
    second: dict[str, Gender] = {w: g for g in genders for w in _IMPERATIVE[g]}
    negated: dict[str, Gender] = {w: g for g in genders for w in _NEGATED[g]}
    for m_raw, f_raw in theme_pairs():
        m, f = _unconj(norm(m_raw)), _unconj(norm(f_raw))
        if m == f:
            continue
        spelled = plain(m_raw)[len(norm(m_raw)) - len(m) :]  # with its hamza, without «و» / «ف»
        if f == norm(_fem_past(spelled)):
            past.setdefault(m, ("m", True))  # a past verb the lexicon did not have
            past.setdefault(f, ("f", True))
        elif m.startswith("ي") and f == "ت" + m[1:]:
            impf.setdefault(m, ("m", True))
            impf.setdefault(f, ("f", True))
        elif m.startswith("ت") and f.startswith(m[:-1]) and f.endswith(("ين", "ي")):
            second.setdefault(f, "f")  # «تقولين», «تنفسي» are a girl's; «تقول» is also «she says»
        elif f == m + "ي" and not m.startswith(("ي", "ت")):
            second.setdefault(m, "m")  # «ارسم / ارسمي»
            second.setdefault(f, "f")
    return Lexicon(past=past, impf=impf, second=second, negated=negated)


# ---- reading the text ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    raw: str
    key: str  # `norm`
    start: int
    end: int
    breaks_before: bool  # punctuation between this word and the one before


def tokens(text: str) -> list[Token]:
    out: list[Token] = []
    last = 0
    for m in _WORD.finditer(text):
        word = m.group(0)
        if plain(word):
            out.append(
                Token(word, norm(word), m.start(), m.end(), bool(_BREAK.search(text[last : m.start()])))
            )
        last = m.end()
    return out


@dataclass(frozen=True)
class GenderIssue:
    field: str  # "title", "dedication", "page:3", "lesson", "question:1", "blurb"
    word: str  # the word as written
    context: str  # the words around it
    rule: str  # one of RULES

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _context(text: str, start: int, end: int, width: int = 28) -> str:
    a, b = max(0, start - width), min(len(text), end + width)
    return ("…" if a else "") + text[a:b].strip() + ("…" if b < len(text) else "")


class _Name:
    """The hero's name in every case form («أبو بكر», «أبا بكر», «أبي بكر»), word by word."""

    def __init__(self, name: str) -> None:
        self.forms = [[norm(w) for w in f.split()] for f in case_forms(name.strip()) if f.strip()]

    def at(self, toks: list[Token], i: int) -> int:
        """How many words of the name start at `toks[i]` (0: none)."""
        for form in self.forms:
            n = len(form)
            same = i + n <= len(toks) and [t.key for t in toks[i : i + n]] == form
            if same and all(not toks[j].breaks_before for j in range(i + 1, i + n)):
                return n
        return 0

    def joined(self, tok: Token) -> bool:
        """The name written onto «لـ» («لِيوسف», «لِـليان», «لِأبي بكر» for a one-word name)."""
        key = tok.key
        return len(key) > 1 and key[0] == "ل" and any(key[1:] == f[0] for f in self.forms if len(f) == 1)


def _verb(lex: Lexicon, key: str) -> tuple[Gender, bool] | None:
    for k in dict.fromkeys((key, _unconj(key))):
        hit = lex.past.get(k) or lex.impf.get(k)
        if hit:
            return hit
    return None


def _subject_marked(name_tok: Token) -> bool:
    mark = final_mark(name_tok.raw)
    return _DAMMA in mark or _DAMMATAN in mark


def _verb_shaped(tok: Token) -> bool:
    """A word that is also a noun reads as a past verb only when its marks say so: «شَعَرَ», not «شَعْرُ»."""
    if _unconj(tok.key) not in _NOUN_LIKE:
        return True
    letters = _letters(tok.raw)
    if len(letters) < 2:
        return False
    last, before = letters[-1][1], letters[-2][1]
    return _FATHA in last and not any(t in last for t in _TANWEEN) and bool(before) and _SUKUN not in before


def _verbs_by_name(
    field: str, text: str, toks: list[Token], name: _Name, gender: Gender
) -> Iterator[GenderIssue]:
    lex = lexicon()
    if any(_verb(lex, form[0]) for form in name.forms):
        return  # a name that is also a verb («فرح», «وعد»): its neighbors cannot tell who does what
    for i in range(len(toks)):
        n = name.at(toks, i)
        if not n:
            continue
        last = toks[i + n - 1]
        if i > 0 and toks[i - 1].key in _YA:
            continue  # «يا ليان»: a call, not a subject
        if i > 0 and not toks[i].breaks_before:
            before = toks[i - 1]
            hit = _verb(lex, before.key)
            # a verb that takes a person as its object counts only when the name is marked as the subject
            if hit and hit[0] != gender and (not hit[1] or _subject_marked(last)) and _verb_shaped(before):
                yield GenderIssue(
                    field, before.raw, _context(text, before.start, last.end), "verb_before_name"
                )
        j = i + n
        if j < len(toks) and not toks[j].breaks_before:
            after = toks[j]
            hit = _verb(lex, after.key)
            if hit and hit[0] != gender and _verb_shaped(after):
                yield GenderIssue(
                    field, after.raw, _context(text, toks[i].start, after.end), "verb_after_name"
                )


def _quotes(text: str) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for open_, close in _QUOTES:
        i = 0
        while (a := text.find(open_, i)) != -1:
            b = text.find(close, a + 1)
            b = len(text) if b == -1 else b
            out.append((a + 1, b))
            i = b + 1
    return out


def _spans(text: str) -> list[tuple[int, int]]:
    """The quotes in a text, and what follows a colon outside a quote to the end of its sentence."""
    quotes = _quotes(text)
    spans = list(quotes)
    for m in re.finditer(":", text):
        if any(a <= m.start() < b for a, b in quotes) or text[m.end() :].lstrip()[:1] in ("«", "“", '"'):
            continue
        end = _SENTENCE_END.search(text, m.end())
        spans.append((m.end(), end.end() if end else len(text)))
    return sorted(spans)


def _addressed(text: str, toks: list[Token], span: tuple[int, int], name: _Name) -> bool:
    """The quote speaks to the hero: «يا يوسف» in it, or it follows «لِيوسف» in its sentence."""
    inside = [t for t in toks if span[0] <= t.start < span[1]]
    for k, t in enumerate(inside[:-1]):
        if t.key in _YA and (name.at(inside, k + 1) or inside[k + 1].key in _ANYWHERE_EPITHETS):
            return True  # «يا يوسف», «يا بطلة»
    sentence_start = max((m.end() for m in _SENTENCE_END.finditer(text, 0, span[0])), default=0)
    before = [t for t in toks if sentence_start <= t.start < span[0]]
    return any(name.joined(t) for t in before[-4:])


def _you(tok: Token, prev: Token | None, other: Gender) -> bool:
    """`tok` speaks to a person of gender `other` (the hero being the other gender)."""
    lex = lexicon()
    key = _unconj(tok.key)
    if prev is not None and prev.key in ("لا", "ولا") and lex.negated.get(key) == other:
        return True
    if lex.second.get(key) == other:
        # «تَذَكَّرُ», «تَنَفَّسَ» (she remembers, he breathed) are not the boy's imperative: «تَذَكَّرْ» is
        return other == "f" or not key.startswith("ت") or key == "تعال" or tok.raw.endswith(_SUKUN)
    if (
        other == "f"
        and key.startswith("ت")
        and len(key) >= 5
        and key.endswith("ين")
        and "ي" + key[1:-2] in lex.impf
    ):
        return True  # «تحبين», «تقولين»
    final = final_mark(tok.raw)
    if (_KASRA if other == "f" else _FATHA) not in final:
        return False
    if key == "انت":
        return True
    if key.endswith("ك"):
        stem = key.removeprefix("ال")
        bare = stem[1:] if stem[:1] in "وفبلك" and len(stem) > 3 else stem
        if {stem, bare, _unconj(bare)} & _K_WORDS or key in lex.past or _unconj(key) in lex.past:
            return False
        return not (len(key) >= 4 and key[0] in "يتنا" and key[1:].endswith(_K_IMPF_STEMS))
    if key.endswith("ت") and _SUKUN in _mark_before_last(tok.raw):  # «أَحْسَنْتِ», «قُلْتَ», «رَأَيْتِ»
        verb = _unconj(key[:-1])
        return (
            verb in lex.past
            or verb in _SECOND_PAST_STEMS
            or (verb.endswith("ي") and verb[:-1] + "ى" in lex.past)
        )
    return False


def _other(gender: Gender) -> Gender:
    return "f" if gender == "m" else "m"


def _in_quotes(
    field: str, text: str, toks: list[Token], name: _Name, gender: Gender
) -> Iterator[GenderIssue]:
    other = _other(gender)
    for span in _spans(text):
        inside = [t for t in toks if span[0] <= t.start < span[1]]
        to_hero = _addressed(text, toks, span, name)
        for k, t in enumerate(inside):
            prev = inside[k - 1] if k else None
            if prev is not None and prev.key in _YA and not t.breaks_before and t.key in _EPITHETS[other]:
                if to_hero or t.key in _ANYWHERE_EPITHETS:
                    yield GenderIssue(
                        field, f"{prev.raw} {t.raw}", _context(text, prev.start, t.end), "epithet"
                    )
                continue
            if to_hero and _you(t, prev, other):
                yield GenderIssue(field, t.raw, _context(text, t.start, t.end), "addressed")


def _epithets_outside(field: str, text: str, toks: list[Token], gender: Gender) -> Iterator[GenderIssue]:
    other = _other(gender)
    spans = _spans(text)
    for k in range(1, len(toks)):
        t, prev = toks[k], toks[k - 1]
        if any(a <= t.start < b for a, b in spans) or t.breaks_before:
            continue
        if prev.key in _YA and t.key in _EPITHETS[other] and t.key in _ANYWHERE_EPITHETS:
            yield GenderIssue(field, f"{prev.raw} {t.raw}", _context(text, prev.start, t.end), "epithet")


def _theme_words(
    field: str, text: str, toks: list[Token], template: str, gender: Gender
) -> Iterator[GenderIssue]:
    """The other gender's words of this text's `{m/f}` pairs, found in the hero's text."""
    right = tokens(render_template(template, gender, "{name}", "{companion}"))
    right_keys = {_unconj(t.key) for t in right}
    right_marked = {(_unconj(t.key), final_mark(t.raw)) for t in right}
    wrong_plain: set[str] = set()
    wrong_marked: dict[str, str] = {}  # the same letters with another final mark: «مَعَكِ» for «مَعَكَ»
    for m_raw, f_raw in (m.groups() for m in _VARIANT.finditer(template)):
        mine, theirs = (m_raw, f_raw) if gender == "m" else (f_raw, m_raw)
        for a, b in zip(tokens(mine), tokens(theirs), strict=False):
            ka, kb = _unconj(a.key), _unconj(b.key)
            mark_a, mark_b = final_mark(a.raw), final_mark(b.raw)
            if ka != kb and kb not in right_keys:
                wrong_plain.add(kb)
            elif ka == kb and mark_a and mark_b and mark_a != mark_b and (kb, mark_b) not in right_marked:
                wrong_marked[kb] = mark_b
    for t in toks:
        key = _unconj(t.key)
        if key in wrong_plain or (key in wrong_marked and final_mark(t.raw) == wrong_marked[key]):
            yield GenderIssue(field, t.raw, _context(text, t.start, t.end), "theme_word")


def _english(field: str, text: str, name: str, companion: str, gender: Gender) -> Iterator[GenderIssue]:
    other = _other(gender)
    named = re.compile(r"\b" + re.escape(name) + r"\b") if name.strip() else None
    others = _EN_FEMALE if other == "f" else _EN_MALE
    previous = ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        context, previous = previous + " " + sentence, sentence
        if named is None or not named.search(sentence):
            continue
        rest = named.sub("", context)
        if companion:
            if other == "m" and companion in rest:
                continue  # the companion is a «he»
            rest = rest.replace(companion, "")
        if others.search(rest) or [w for w in re.findall(r"\b[A-Z][a-z]+", rest) if w not in _EN_COMMON]:
            continue  # someone else in the sentence (or the one before) may be the «she» / «he»
        hit = _EN_REFLEXIVE[other].search(sentence) or _EN_PRONOUNS[other].search(named.sub("", sentence))
        if hit:
            yield GenderIssue(field, hit.group(0), sentence.strip()[:90], "pronoun_en")


def story_fields(story: StoryOut) -> list[tuple[str, str]]:
    """(field, text) for every text of a story, the way the book review names them."""
    return [
        ("title", story.title),
        ("dedication", story.dedication),
        *((f"page:{p.index}", p.text) for p in story.pages),
        ("lesson", story.parents_lesson),
        *((f"question:{i}", q) for i, q in enumerate(story.parents_questions, 1)),
        ("blurb", story.blurb),
    ]


def theme_templates(theme: Theme, lang: Lang) -> dict[str, str]:
    """The theme's own text for each story field (the base the model adapted)."""
    ar = lang == "ar"
    out = {"title": theme.title_ar if ar else theme.title_en}
    out |= {f"page:{p.index}": p.text_ar if ar else p.text_en for p in theme.pages}
    if theme.for_parents:
        fp = theme.for_parents
        out["lesson"] = fp.lesson_ar if ar else fp.lesson_en
        out |= {f"question:{i}": q for i, q in enumerate(fp.questions_ar if ar else fp.questions_en, 1)}
    out["blurb"] = (theme.blurb_ar if ar else theme.blurb_en) or ""
    return out


def check_texts(
    texts: Iterable[tuple[str, str]],
    name: str,
    gender: Gender,
    lang: Lang,
    *,
    companion: str = "",
    templates: dict[str, str] | None = None,
) -> list[GenderIssue]:
    """The words worth a second look in (field, text) pairs, once each, in reading order."""
    out: list[GenderIssue] = []
    hero = _Name(name)
    for field, text in texts:
        if not text or not text.strip():
            continue
        if lang == "en":
            out += _english(field, text, name, companion, gender)
            continue
        toks = tokens(text)
        out += _verbs_by_name(field, text, toks, hero, gender)
        out += _in_quotes(field, text, toks, hero, gender)
        out += _epithets_outside(field, text, toks, gender)
        template = (templates or {}).get(field)
        if template and _VARIANT.search(template):
            out += _theme_words(field, text, toks, template, gender)
    seen: set[tuple[str, str]] = set()
    unique: list[GenderIssue] = []
    for issue in out:
        if (issue.field, issue.word) not in seen:
            seen.add((issue.field, issue.word))
            unique.append(issue)
    return unique


def review_notes(notes: Iterable[str]) -> list[GenderIssue]:
    """The safety review's own gender notes («page 3: قالت → قال», story_safety.v3), as hints."""
    return [
        GenderIssue("review", n.strip()[:120], n.strip()[:200], "text_review") for n in notes if n.strip()
    ]


def gender_issues(
    story: StoryOut,
    name: str,
    gender: Gender,
    lang: Lang,
    *,
    companion: str = "",
    theme: Theme | None = None,
) -> list[GenderIssue]:
    """The hero's gender checked in every field of a story (`theme`: the base it was adapted from)."""
    templates = theme_templates(theme, lang) if theme is not None else None
    return check_texts(story_fields(story), name, gender, lang, companion=companion, templates=templates)
